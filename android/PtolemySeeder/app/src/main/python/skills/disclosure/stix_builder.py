"""
skills/disclosure/stix_builder.py — STIX 2.1 object builder.
Pure Python. json + uuid + datetime only.

Builds STIX 2.1 JSON objects for vulnerability disclosure:
  vulnerability    the discovered flaw
  indicator        observable pattern related to the vulnerability
  course-of-action recommended mitigation
  report           bundles the above with metadata

STIX 2.1 spec: https://docs.oasis-open.org/cti/stix/v2.1/

These objects are submitted to:
  CISA AIS (Automated Indicator Sharing) via TAXII 2.1
  NIST NVD (as supporting material for CVE request)
  MITRE CVE (as part of CVE assignment request)

All objects carry the researcher's ORCID in external_references,
providing ORCID attribution in the international vulnerability record.
"""

from __future__ import annotations
import json
import uuid
import time
from typing import Optional, List


def _stix_id(obj_type: str) -> str:
    return f"{obj_type}--{uuid.uuid4()}"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())


class STIXBuilder:
    """
    Builds STIX 2.1 bundles for PTorrent vulnerability disclosures.
    All methods return plain dicts (JSON-serialisable).
    """

    def __init__(self, researcher_orcid: str, researcher_name: str,
                 researcher_email: str):
        self.orcid = researcher_orcid
        self.name  = researcher_name
        self.email = researcher_email

    def _identity(self) -> dict:
        return {
            "type":            "identity",
            "spec_version":    "2.1",
            "id":              _stix_id("identity"),
            "created":         _now(),
            "modified":        _now(),
            "name":            self.name,
            "identity_class":  "individual",
            "contact_information": self.email,
            "external_references": [{
                "source_name": "ORCID",
                "external_id": self.orcid,
                "url":         f"https://orcid.org/{self.orcid}",
            }],
        }

    def vulnerability(
        self,
        name: str,
        description: str,
        file_hash: str,
        ptorrent_chain_ref: str,
        cvss_score: Optional[float] = None,
        cve_id: Optional[str] = None,
        affected_systems: Optional[List[str]] = None,
        embargo_until: Optional[str] = None,
    ) -> dict:
        """
        Build a STIX 2.1 vulnerability object.

        :param name:                Short vulnerability name.
        :param description:         Full technical description.
        :param file_hash:           PTorrent chain file_hash (links to CLASSIFY tx).
        :param ptorrent_chain_ref:  Chain tip_hash or block hash at time of discovery.
        :param cvss_score:          CVSS v3 base score (0.0-10.0) if known.
        :param cve_id:              Existing CVE ID if already assigned.
        :param affected_systems:    List of affected product strings.
        :param embargo_until:       ISO date of planned public disclosure.
        """
        obj: dict = {
            "type":          "vulnerability",
            "spec_version":  "2.1",
            "id":            _stix_id("vulnerability"),
            "created":       _now(),
            "modified":      _now(),
            "name":          name,
            "description":   description,
            "external_references": [
                {
                    "source_name": "PTorrent chain",
                    "external_id": file_hash,
                    "description": f"PTorrent chain file_hash. "
                                   f"Block ref: {ptorrent_chain_ref}",
                },
                {
                    "source_name": "ORCID",
                    "external_id": self.orcid,
                    "url":         f"https://orcid.org/{self.orcid}",
                    "description": f"Discovering researcher: {self.name}",
                },
            ],
            "labels": ["ptorrent-disclosure"],
        }

        if cve_id:
            obj["external_references"].insert(0, {
                "source_name": "cve",
                "external_id": cve_id,
                "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            })
            obj["name"] = f"{cve_id}: {name}"

        if cvss_score is not None:
            obj["description"] += f"\n\nCVSS v3 Base Score: {cvss_score:.1f}"

        if affected_systems:
            obj["description"] += (
                "\n\nAffected systems:\n" +
                "\n".join(f"  - {s}" for s in affected_systems)
            )

        if embargo_until:
            obj["description"] += (
                f"\n\nEmbargo: public disclosure planned {embargo_until}. "
                "Do not publish before this date."
            )
            obj["labels"].append(f"embargo-until-{embargo_until}")

        return obj

    def course_of_action(self, title: str, description: str) -> dict:
        return {
            "type":         "course-of-action",
            "spec_version": "2.1",
            "id":           _stix_id("course-of-action"),
            "created":      _now(),
            "modified":     _now(),
            "name":         title,
            "description":  description,
        }

    def indicator(self, pattern: str, description: str,
                  indicator_types: Optional[List[str]] = None) -> dict:
        return {
            "type":            "indicator",
            "spec_version":    "2.1",
            "id":              _stix_id("indicator"),
            "created":         _now(),
            "modified":        _now(),
            "name":            description[:100],
            "description":     description,
            "pattern":         pattern,
            "pattern_type":    "stix",
            "valid_from":      _now(),
            "indicator_types": indicator_types or ["malicious-activity"],
        }

    def bundle(self, *objects) -> dict:
        """Wrap STIX objects in a bundle."""
        identity = self._identity()
        return {
            "type":         "bundle",
            "id":           _stix_id("bundle"),
            "spec_version": "2.1",
            "objects":      [identity] + list(objects),
        }

    def report(self, title: str, description: str,
               *referenced_objects: dict) -> dict:
        obj_refs = [o["id"] for o in referenced_objects]
        return {
            "type":         "report",
            "spec_version": "2.1",
            "id":           _stix_id("report"),
            "created":      _now(),
            "modified":     _now(),
            "name":         title,
            "description":  description,
            "published":    _now(),
            "report_types": ["vulnerability"],
            "object_refs":  obj_refs,
        }

    def to_json(self, bundle: dict, indent: int = 2) -> str:
        return json.dumps(bundle, indent=indent, ensure_ascii=False)

    def build_disclosure_bundle(
        self,
        vuln_name: str,
        vuln_description: str,
        file_hash: str,
        chain_ref: str,
        mitigation: str,
        embargo_until: Optional[str] = None,
        cve_id: Optional[str] = None,
        cvss_score: Optional[float] = None,
        affected_systems: Optional[List[str]] = None,
    ) -> dict:
        """
        Build a complete STIX disclosure bundle:
          identity + vulnerability + course-of-action + report
        """
        vuln = self.vulnerability(
            name=vuln_name,
            description=vuln_description,
            file_hash=file_hash,
            ptorrent_chain_ref=chain_ref,
            cvss_score=cvss_score,
            cve_id=cve_id,
            affected_systems=affected_systems,
            embargo_until=embargo_until,
        )
        coa = self.course_of_action(
            title=f"Mitigation: {vuln_name}",
            description=mitigation,
        )
        rpt = self.report(
            title=f"PTorrent Disclosure: {vuln_name}",
            description=(
                f"Responsible disclosure filed by {self.name} "
                f"(ORCID: {self.orcid}) via PTorrent chain. "
                f"File hash: {file_hash}"
            ),
            vuln, coa,
        )
        return self.bundle(vuln, coa, rpt)
