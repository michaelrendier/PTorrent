"""
skills/disclosure/notifier.py — PTorrent responsible disclosure notifier.
Pure Python. smtplib + urllib only.

Dispatches vulnerability disclosures to:
  NIST NVD       nvd@nist.gov        + web portal
  CISA           vuln@cisa.dhs.gov   + optional TAXII 2.1
  MITRE CVE      cve@mitre.org       (CVE assignment request)
  CERT/CC        vulnreport@cert.org (coordination fallback)
  UK NCSC        ncscvulndisclosure@ncsc.gov.uk  (UK systems)

Every notification is recorded on the PTorrent chain as a NOTIFY transaction
before the notification is sent. The chain record is authoritative — if the
email bounces or the TAXII endpoint is down, the chain still records the
attempted disclosure with timestamp and report hash.

Environment variables (all optional — notifier degrades gracefully):
  PTOL_RESEARCHER_ORCID   Researcher's ORCID
  PTOL_RESEARCHER_EMAIL   Reply-to address
  PTOL_RESEARCHER_NAME    Full name
  PTOL_SMTP_HOST          SMTP relay (default: no email, log only)
  PTOL_SMTP_PORT          SMTP port (default 587)
  PTOL_SMTP_USER          SMTP username
  PTOL_SMTP_PASS          SMTP password
  PTOL_TAXII_ENDPOINT     CISA AIS TAXII 2.1 base URL
  PTOL_TAXII_KEY          CISA AIS API key

White hat principle: every sent notification has a corresponding NOTIFY
transaction on-chain. The chain IS the disclosure record.
"""

from __future__ import annotations
import hashlib
import json
import logging
import os
import smtplib
import ssl
import time
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from typing import Optional

from skills.disclosure.stix_builder import STIXBuilder
from skills.adapters.nist_nvd_adapter import check_cve_exists
from skills.adapters.cisa_kev_adapter  import check_kev, get_kev_summary

_log = logging.getLogger("ptorrent.disclosure")

# ── Agency contact table ──────────────────────────────────────────────────────

AGENCIES = {
    "NIST": {
        "email":    "nvd@nist.gov",
        "portal":   "https://nvd.nist.gov/vuln/vulnerability-disclosure",
        "name":     "NIST National Vulnerability Database",
        "priority": 1,
    },
    "CISA": {
        "email":    "vuln@cisa.dhs.gov",
        "portal":   "https://www.cisa.gov/reporting-cyber-vulnerabilities",
        "name":     "CISA Cybersecurity and Infrastructure Security Agency",
        "priority": 1,
    },
    "MITRE": {
        "email":    "cve@mitre.org",
        "portal":   "https://cveform.mitre.org/",
        "name":     "MITRE CVE Program",
        "priority": 2,
    },
    "CERTCC": {
        "email":    "vulnreport@cert.org",
        "portal":   "https://kb.cert.org/vuls/report/",
        "name":     "CERT Coordination Center",
        "priority": 3,
    },
    "NCSC": {
        "email":    "ncscvulndisclosure@ncsc.gov.uk",
        "portal":   "https://www.ncsc.gov.uk/section/about-ncsc/vulnerability-reporting",
        "name":     "UK National Cyber Security Centre",
        "priority": 4,
    },
    "ENISA": {
        "email":    "cert@enisa.europa.eu",
        "portal":   "https://www.enisa.europa.eu/topics/csirts-in-europe",
        "name":     "ENISA / EU-CERT",
        "priority": 4,
    },
}


# ── DisclosureNotifier ────────────────────────────────────────────────────────

class DisclosureNotifier:
    """
    Coordinates the full responsible disclosure workflow.

    Usage:
        notifier = DisclosureNotifier(chain)
        result = notifier.disclose(
            file_hash     = "a3f2c1...",
            vuln_name     = "UDEO Sedenion Zero-Divisor ECC Attack",
            description   = "Full technical description...",
            mitigation    = "Patch / workaround description...",
            embargo_until = "2027-06-03",
            agencies      = ["NIST", "CISA", "MITRE"],
        )
    """

    def __init__(self, chain=None):
        """
        :param chain: PTorrentChain instance. If provided, NOTIFY transactions
                      are committed for each notification sent.
        """
        self._chain  = chain
        self._orcid  = os.environ.get("PTOL_RESEARCHER_ORCID", "")
        self._email  = os.environ.get("PTOL_RESEARCHER_EMAIL", "")
        self._name   = os.environ.get("PTOL_RESEARCHER_NAME", "PTorrent Researcher")
        self._smtp_host = os.environ.get("PTOL_SMTP_HOST", "")
        self._smtp_port = int(os.environ.get("PTOL_SMTP_PORT", "587"))
        self._smtp_user = os.environ.get("PTOL_SMTP_USER", "")
        self._smtp_pass = os.environ.get("PTOL_SMTP_PASS", "")
        self._taxii_ep  = os.environ.get("PTOL_TAXII_ENDPOINT", "")
        self._taxii_key = os.environ.get("PTOL_TAXII_KEY", "")

        self._builder = STIXBuilder(
            researcher_orcid=self._orcid,
            researcher_name=self._name,
            researcher_email=self._email,
        )

    # ── Pre-disclosure check ──────────────────────────────────────────────────

    def pre_check(self, keyword: str) -> dict:
        """
        Before filing, check if this vulnerability is already known.
        Returns: existing CVEs and KEV status.
        """
        _log.info("Pre-disclosure check for: %s", keyword)
        existing_cves = check_cve_exists(keyword, max_results=10)
        kev_summary   = get_kev_summary()
        return {
            "existing_cves": existing_cves,
            "kev_count":     kev_summary.get("count", 0),
            "kev_updated":   kev_summary.get("date_released", ""),
            "note": (
                f"Found {len(existing_cves)} existing CVEs matching '{keyword}'. "
                "If a CVE already exists, reference it rather than filing new."
                if existing_cves else
                f"No existing CVEs found for '{keyword}'. Proceed with filing."
            ),
        }

    # ── Main disclosure method ────────────────────────────────────────────────

    def disclose(
        self,
        file_hash:     str,
        vuln_name:     str,
        description:   str,
        mitigation:    str,
        embargo_until: Optional[str] = None,
        agencies:      Optional[list] = None,
        cve_id:        Optional[str]  = None,
        cvss_score:    Optional[float] = None,
        affected_systems: Optional[list] = None,
    ) -> dict:
        """
        Execute full disclosure workflow:
          1. Build STIX bundle
          2. For each agency: commit NOTIFY tx → send notification
          3. Return summary with chain references

        :param file_hash:      PTorrent chain file_hash of the vulnerable/dual-use file.
        :param vuln_name:      Short vulnerability name.
        :param description:    Full technical description.
        :param mitigation:     Recommended fix or workaround.
        :param embargo_until:  ISO date of planned public disclosure.
        :param agencies:       List of agency keys. Default: ["NIST", "CISA"].
        :param cve_id:         Existing CVE ID if already assigned.
        :param cvss_score:     CVSS v3 base score.
        :param affected_systems: List of affected product strings.
        """
        if agencies is None:
            agencies = ["NIST", "CISA"]

        chain_ref = ""
        if self._chain:
            try:
                chain_ref = self._chain._chain[-1].hash if self._chain._chain else ""
            except Exception:
                pass

        # Build the STIX bundle
        bundle = self._builder.build_disclosure_bundle(
            vuln_name=vuln_name,
            vuln_description=description,
            file_hash=file_hash,
            chain_ref=chain_ref,
            mitigation=mitigation,
            embargo_until=embargo_until,
            cve_id=cve_id,
            cvss_score=cvss_score,
            affected_systems=affected_systems,
        )
        bundle_json   = self._builder.to_json(bundle)
        report_hash   = hashlib.sha256(bundle_json.encode("utf-8")).hexdigest()
        peer_id       = f"ORCID:{self._orcid}" if self._orcid else "unknown"

        results = {
            "file_hash":   file_hash,
            "report_hash": report_hash,
            "agencies":    {},
            "stix_bundle": bundle,
        }

        for agency_key in agencies:
            agency = AGENCIES.get(agency_key.upper())
            if not agency:
                _log.warning("Unknown agency: %s", agency_key)
                continue

            _log.info("Filing disclosure with %s...", agency["name"])

            # 1. Commit NOTIFY transaction BEFORE sending
            if self._chain:
                try:
                    self._chain.notify(
                        file_hash   = file_hash,
                        agency      = agency_key.upper(),
                        report_hash = report_hash,
                        method      = "email",
                        peer_id     = peer_id,
                    )
                    self._chain.commit()
                    _log.info("NOTIFY transaction committed for %s", agency_key)
                except Exception as e:
                    _log.error("Chain NOTIFY failed for %s: %s", agency_key, e)

            # 2. Send notification
            sent    = False
            method  = "none"
            error   = ""

            # Try TAXII first for CISA (if configured)
            if agency_key.upper() == "CISA" and self._taxii_ep:
                try:
                    self._send_taxii(bundle_json)
                    sent   = True
                    method = "stix_taxii"
                    _log.info("STIX/TAXII submission to CISA succeeded")
                except Exception as e:
                    error = str(e)
                    _log.warning("TAXII failed, falling back to email: %s", e)

            # Email notification
            if not sent and self._smtp_host and agency.get("email"):
                try:
                    self._send_email(
                        to_addr      = agency["email"],
                        agency_name  = agency["name"],
                        vuln_name    = vuln_name,
                        description  = description,
                        mitigation   = mitigation,
                        embargo_until = embargo_until,
                        bundle_json  = bundle_json,
                        report_hash  = report_hash,
                        file_hash    = file_hash,
                        cve_id       = cve_id,
                    )
                    sent   = True
                    method = "email"
                    _log.info("Email notification to %s succeeded", agency["email"])
                except Exception as e:
                    error = str(e)
                    _log.error("Email to %s failed: %s", agency["email"], e)

            if not sent:
                method = "manual_required"
                _log.warning(
                    "No automated delivery to %s. "
                    "Manual submission required at: %s",
                    agency["name"], agency.get("portal", "")
                )

            results["agencies"][agency_key] = {
                "sent":    sent,
                "method":  method,
                "email":   agency.get("email", ""),
                "portal":  agency.get("portal", ""),
                "error":   error,
                "note":    "" if sent else (
                    f"Automated delivery failed. Submit manually at:\n"
                    f"{agency.get('portal', '')}\n"
                    f"Attach the STIX bundle (report_hash: {report_hash[:16]}…)"
                ),
            }

        results["summary"] = _build_summary(results, vuln_name, embargo_until)
        _log.info("Disclosure complete. Report hash: %s", report_hash)
        return results

    # ── TAXII 2.1 submission ──────────────────────────────────────────────────

    def _send_taxii(self, bundle_json: str) -> None:
        """Submit STIX bundle to CISA AIS via TAXII 2.1."""
        collection_url = self._taxii_ep.rstrip("/") + "/collections/default/objects/"
        headers = {
            "Content-Type":  "application/taxii+json;version=2.1",
            "Accept":        "application/taxii+json;version=2.1",
            "User-Agent":    "PTorrent/2.0 (TAXII 2.1 client)",
        }
        if self._taxii_key:
            headers["Authorization"] = f"Bearer {self._taxii_key}"

        data = bundle_json.encode("utf-8")
        req  = urllib.request.Request(
            collection_url, data=data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201, 202):
                raise RuntimeError(f"TAXII returned HTTP {resp.status}")

    # ── Email notification ────────────────────────────────────────────────────

    def _send_email(self, to_addr: str, agency_name: str,
                    vuln_name: str, description: str,
                    mitigation: str, embargo_until: Optional[str],
                    bundle_json: str, report_hash: str,
                    file_hash: str, cve_id: Optional[str]) -> None:
        """Send structured disclosure email with STIX bundle attachment."""

        subject = (
            f"[PTorrent Responsible Disclosure] {vuln_name}"
            + (f" | Embargo: {embargo_until}" if embargo_until else "")
        )

        body = _email_body(
            agency_name   = agency_name,
            vuln_name     = vuln_name,
            description   = description,
            mitigation    = mitigation,
            embargo_until = embargo_until,
            report_hash   = report_hash,
            file_hash     = file_hash,
            researcher_name  = self._name,
            researcher_orcid = self._orcid,
            researcher_email = self._email,
            cve_id        = cve_id,
        )

        msg = MIMEMultipart()
        msg["From"]    = self._email or self._smtp_user
        msg["To"]      = to_addr
        msg["Subject"] = subject
        msg["Reply-To"] = self._email or ""
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach STIX bundle as JSON file
        attachment = MIMEBase("application", "json")
        attachment.set_payload(bundle_json.encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"ptorrent_disclosure_{report_hash[:16]}.json"
        )
        msg.attach(attachment)

        context = ssl.create_default_context()
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(self._smtp_user, self._smtp_pass)
            server.sendmail(
                msg["From"], [to_addr], msg.as_string()
            )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _email_body(agency_name: str, vuln_name: str, description: str,
                mitigation: str, embargo_until: Optional[str],
                report_hash: str, file_hash: str,
                researcher_name: str, researcher_orcid: str,
                researcher_email: str, cve_id: Optional[str]) -> str:
    embargo_line = (
        f"EMBARGO DATE: {embargo_until} — Please do not publish before this date.\n"
        if embargo_until else
        "No embargo. Coordinated disclosure requested within 90 days.\n"
    )
    cve_line = f"EXISTING CVE: {cve_id}\n" if cve_id else "CVE STATUS: Requesting assignment\n"

    return f"""Dear {agency_name} Vulnerability Disclosure Team,

I am filing a responsible disclosure report for a vulnerability discovered
during research using the PTorrent open research infrastructure.

RESEARCHER: {researcher_name}
ORCID: {researcher_orcid}
CONTACT: {researcher_email}
PTORRENT REPORT HASH: {report_hash}
PTORRENT FILE HASH: {file_hash}

{cve_line}
{embargo_line}

VULNERABILITY NAME:
{vuln_name}

DESCRIPTION:
{description}

MITIGATION / RECOMMENDED ACTION:
{mitigation}

A STIX 2.1 bundle is attached to this email (JSON format) containing the
full structured disclosure including vulnerability, course-of-action, and
report objects with ORCID attribution.

The PTorrent distributed ledger contains a tamper-evident NOTIFY transaction
recording this disclosure attempt with timestamp and report hash. The chain
provides an independent record of the disclosure timeline.

I am available for coordination at the email address above.

Respectfully,
{researcher_name}
ORCID: https://orcid.org/{researcher_orcid}

---
Filed via PTorrent responsible disclosure infrastructure.
https://github.com/michaelrendier/PTorrent
GPL-3.0 | White hat research | ORCID-attributed
"""


def _build_summary(results: dict, vuln_name: str,
                   embargo_until: Optional[str]) -> str:
    lines = [
        f"DISCLOSURE SUMMARY: {vuln_name}",
        f"Report hash: {results['report_hash'][:32]}…",
        "",
    ]
    for agency, r in results["agencies"].items():
        status = "✓ SENT" if r["sent"] else "⚠ MANUAL REQUIRED"
        lines.append(f"  {agency}: {status} via {r['method']}")
        if not r["sent"]:
            lines.append(f"    Portal: {r['portal']}")
    if embargo_until:
        lines.append(f"\nEmbargo until: {embargo_until}")
        lines.append("DISCLOSE transaction will auto-fire on this date.")
    return "\n".join(lines)
