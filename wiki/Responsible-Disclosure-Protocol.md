# PTorrent Responsible Disclosure Open Protocol (RDOP)
## Version 1.0 — Formal Specification

**Author:** Cody Michael Allison  
**Date:** 2026-06-03  
**Status:** Proposed Open Standard  
**License:** GNU GPL v3  
**Repository:** https://github.com/michaelrendier/PTorrent  

---

## Abstract

The PTorrent Responsible Disclosure Open Protocol (RDOP) defines a
machine-readable, blockchain-provenance-tracked, ORCID-attributed protocol
for the responsible disclosure of security vulnerabilities discovered during
open research. RDOP extends the `.ptorrent` file format and PTorrent
distributed ledger with a formal lifecycle for dual-use datasets and
vulnerability findings, from discovery through coordinated public disclosure.

RDOP is an open protocol. PTorrent is the reference implementation. Any
tool may implement RDOP. Compliance requires implementing the file format
extensions (§3), the chain transaction sequence (§4), and the agency
interface (§5).

---

## 1. Purpose and Scope

### 1.1 Purpose

Open research increasingly discovers findings with dual-use potential —
mathematical structures, algorithms, or datasets that are simultaneously
valuable for science and potentially exploitable for harm. Existing
responsible disclosure processes are ad hoc: individual emails, informal
timelines, no machine-readable format, no tamper-evident provenance.

RDOP addresses this gap by:

1. Embedding security classification directly in the `.ptorrent` file format
2. Recording the complete disclosure lifecycle on a distributed ledger
3. Generating standards-compliant (STIX 2.1) disclosure reports automatically
4. Providing structured interfaces to NIST, CISA, MITRE, CERT/CC, and
   international equivalents
5. Attributing all actions to verified researchers via ORCID identity
6. Enforcing embargo periods programmatically — seeding is blocked until
   the embargo has passed

### 1.2 Scope

RDOP covers:

- Cryptographic attack vectors discovered during mathematical research
- Dual-use datasets (data whose evaluation reveals exploitable structures)
- Pre-publication vulnerability findings requiring coordinated disclosure
- Security-relevant software, hardware (GDSII), or protocol datasets

RDOP does not cover:

- Export-controlled (ITAR/EAR) materials — these require institutional
  legal counsel beyond the scope of this protocol
- Active exploitation or offensive use — RDOP is a white-hat protocol only
- Vulnerabilities in PTorrent's own infrastructure — file separately

### 1.3 Relationship to Existing Standards

| Standard | Relationship |
|---|---|
| NIST IR 8388 (Vulnerability Disclosure Guide) | RDOP implements the researcher-side workflow described in §2 |
| CISA CVD Process | RDOP automates the coordinated disclosure filing described in CISA's CVD guide |
| STIX 2.1 (OASIS CTI TC) | RDOP generates compliant vulnerability, CoA, and report objects |
| TAXII 2.1 (OASIS CTI TC) | RDOP submits bundles via TAXII 2.1 to CISA AIS |
| CVE JSON 5.0 (MITRE) | RDOP generates CVE-compatible descriptions for MITRE submission |
| ORCID (ISNI) | RDOP uses ORCID for researcher identity throughout the ledger |

---

## 2. Roles and Obligations

### 2.1 Researcher

The researcher is the individual who discovers the vulnerability or dual-use
finding. Under RDOP:

**Obligations:**
- Maintain a complete ORCID profile with contact information
- File RDOP disclosure before any publication, preprint, or conference submission
- Provide a good-faith technical description in the STIX bundle
- Respect the embargo period
- Cooperate with agency coordination requests during the embargo

**Rights:**
- Retain full attribution for the discovery (ORCID in the CVE record)
- Set the publication timeline (within agency-negotiated limits)
- Retain the ability to publish if agencies are unresponsive within 90 days
- Receive acknowledgment in any downstream security advisory

### 2.2 PTorrent Chain

The PTorrent distributed ledger is the authoritative record of the
disclosure timeline. The chain's obligations:

- Record every state transition as an immutable transaction
- Enforce embargo dates: seeding blocked until `embargo_until` has passed
- Provide `NOTIFY` timestamp as Day 0 evidence
- Allow any party to verify the timeline independently

The chain is neutral. It records facts. It does not take sides.

### 2.3 Agencies

Agencies receiving RDOP disclosures are invited (not required) to:

- Acknowledge receipt within 5 business days
- Assign a tracking number (CVE for MITRE, advisory ID for CISA)
- Coordinate vendor notification
- Respect the researcher's requested embargo
- Publish the disclosure on or after the embargo date

Agencies that adopt RDOP as an intake format are requested to:
- Provide a TAXII 2.1 endpoint for machine-readable submission
- Return structured acknowledgments (STIX acknowledgment object)
- Communicate timeline changes back to the researcher's ORCID contact

---

## 3. File Format Extensions

### 3.1 The `security` Block in `.ptorrent`

Any `.ptorrent` file that describes, references, or evaluates a dual-use
or security-relevant dataset MUST include a `security` block.

```json
{
  "security": {
    "classification":       "dual-use",
    "level":                3,
    "warning":              "Full warning text as displayed to any researcher
                             attempting to access or seed this file.",
    "embargo_until":        "2027-06-03",
    "requires_credential":  "security_researcher",
    "disclosure_ref":       "NIST-PRE-DISCLOSURE-2026-AINULINDALE-UDEO",
    "contact_orcid":        "0000-0001-XXXX-XXXX",
    "acknowledge_required": true,
    "chain_of_custody":     true,
    "cve_id":               "CVE-YYYY-NNNNN"
  }
}
```

#### Classification Levels

| Level | Name | Access | Seeding Requirement |
|---|---|---|---|
| 0 | `public` | Unrestricted | None |
| 1 | `sensitive` | ORCID verified | Profile complete |
| 2 | `restricted` | Institution verified | ORCID + institution |
| 3 | `dual-use` | Explicit acknowledgment | ORCID + acknowledge |

Level 3 is the standard for cryptographic attack vectors, vulnerability
data, and any dataset whose evaluation could directly enable harm.

#### `embargo_until` Enforcement

The pre-flight checker (`skills/preflight.py`) compares `embargo_until`
against the current date. If the date has not passed:

- The job does not start. Full stop.
- No override is available.
- The chain records the attempted access.

The embargo enforcement is the protocol's primary deterrence mechanism.
A black hat who obtains a Level 3 `.ptorrent` file before the embargo lifts
cannot run it. The embargo is enforced in code, not by trust.

### 3.2 Security Annotation in `.peval` Files

When a Data Transversal (`type: evaluation`) is run on a security-classified
dataset, the output `.peval` file inherits the classification. The `.peval`
format includes a `disclosure` section:

```python
{
  "terms": {
    "framework":      "Ainulindale",
    "version":        "v1.218",
    "bin_hash":       "<SHA-256>",
    ...
  },
  "disclosure": {
    "classification":  "dual-use",
    "level":           3,
    "embargo_until":   "2027-06-03",
    "contact_orcid":   "0000-0001-XXXX-XXXX",
    "cve_id":          "CVE-YYYY-NNNNN",
    "notify_txs": [
      {"agency": "NIST",  "tx_hash": "...", "timestamp": "..."},
      {"agency": "CISA",  "tx_hash": "...", "timestamp": "..."},
      {"agency": "MITRE", "tx_hash": "...", "timestamp": "..."}
    ],
    "chain_file_hash":  "<SHA-256 of source dataset>",
    "report_hash":      "<SHA-256 of STIX bundle>"
  },
  "results": [ ... ]
}
```

The `notify_txs` array is written by the disclosure notifier after NOTIFY
transactions are committed. It creates a self-contained chain-of-custody
record within the `.peval` file itself.

### 3.3 The `evaluation` Type Formal Definition

The `evaluation` type is the primary vehicle for Data Transversal results.
When used with security-classified datasets:

```json
{
  "ptorrent_version": "1.0",
  "type":             "evaluation",
  "name":             "UDEO Attack Vectors — Ainulindale σ-face evaluation",
  "requires_bin":     "monad_sedenion.bin",
  "output":           "udeo_attack_vectors.peval",
  "primary_tags":     ["SECURITY", "ECC", "ZERO_DIVISOR", "CRYPTOGRAPHY"],
  "color":            "red",
  "description":      "Sedenion zero-divisor geometry evaluated against ECC
                       implementation structure. Pre-disclosure. Embargo active.",

  "security": {
    "classification":       "dual-use",
    "level":                3,
    "warning":              "...",
    "embargo_until":        "2027-06-03",
    "contact_orcid":        "0000-0001-XXXX-XXXX",
    "acknowledge_required": true
  },

  "resources": {
    "requires_charging": false,
    "thermal_risk":      "low",
    "warning":           "Algebraic evaluation only. Low resource requirement."
  },

  "data_model": {
    "type":   "algebraic_structure",
    "access": {"mode": "file_list"}
  },

  "evaluation": {
    "fn":       "σ_face_algebraic",
    "bin_hash": "<SHA-256 of monad_sedenion.bin>",
    "σ_table":  {"½": "causality", "1": "Yang-Mills",
                 "2": "gravity",   "∞": "BH interior"}
  }
}
```

---

## 4. Chain Transaction Sequence

### 4.1 The Disclosure State Machine

```
UNREPORTED
    │
    │ researcher runs classify()
    ▼
CLASSIFIED ──── CLASSIFY tx on chain
    │               (classification, level, embargo_until, contact_orcid)
    │ notifier.disclose() called
    ▼
NOTIFIED ─────── NOTIFY tx × N on chain (one per agency)
    │               (agency, report_hash, method, peer_id)
    │               NOTIFY commits BEFORE email/TAXII is sent.
    │               Chain record is authoritative regardless of delivery.
    │
    │  [embargo period — seeding blocked, coordination ongoing]
    │
    │ embargo_until date reached (auto or manual DISCLOSE call)
    ▼
DISCLOSED ────── DISCLOSE tx on chain
    │               (prev_classification, new_classification, peer_id)
    │ paper published / CVE goes live
    ▼
PUBLIC ────────── Classification level drops to 0
                  File is now seedable without restriction
```

### 4.2 Required Transaction Sequence

A compliant RDOP disclosure MUST produce this minimum transaction sequence
in the following order:

```
1. CLASSIFY    (file_hash, level=3, embargo_until, contact_orcid)
2. NOTIFY      (file_hash, agency="NIST",  report_hash, method)
3. NOTIFY      (file_hash, agency="CISA",  report_hash, method)
4. NOTIFY      (file_hash, agency="MITRE", report_hash, method)
   [Additional NOTIFY transactions for other agencies as appropriate]
5. ACKNOWLEDGE (file_hash, orcid_id, warning_hash, peer_id)
   [For each researcher granted access during embargo]
6. DISCLOSE    (file_hash, "dual-use", "public", peer_id)
```

Transactions 1-4 are produced by `DisclosureNotifier.disclose()`.
Transaction 5 is produced by `PTorrentChain.acknowledge()` in the APK.
Transaction 6 is produced by `PTorrentChain.disclose()` on the embargo date.

### 4.3 The NOTIFY Transaction — Authoritative Timestamp

The NOTIFY transaction is committed to the chain **before** the notification
is sent. This is the RDOP's fundamental design choice:

- The chain timestamp is the authoritative Day 0 record
- Email delivery failure does not affect the timestamp
- Agency server downtime does not affect the timestamp
- The chain record is independent of any agency's acknowledgment

If an agency challenges the disclosure timeline, the NOTIFY transaction hash
and timestamp in the PTorrent chain is the evidence. No email header, no
agency portal confirmation number, no server log — the chain is the record.

### 4.4 The `warning_hash` in ACKNOWLEDGE

The `warning_hash` field in the ACKNOWLEDGE transaction is SHA-256 of the
exact warning text that was displayed to the researcher before they entered
their ORCID. This proves:

1. A warning was displayed (hash exists)
2. This specific warning was displayed (hash is deterministic)
3. The researcher acknowledged this version (not a different one)

This is the RDOP equivalent of a signed legal document — a cryptographic
proof that the researcher read and accepted the specific security notice
associated with this dataset.

---

## 5. Agency Interface

### 5.1 Submission Sequence

Submit to agencies in this order. Do not wait for one agency to respond
before submitting to the next. Parallel submission is the correct procedure.

```
Day 0, simultaneous:
  1. CISA     vuln@cisa.dhs.gov
  2. NIST     nvd@nist.gov
  3. MITRE    cve@mitre.org
  4. CERT/CC  vulnreport@cert.org  (international/vendor coverage)

Day 0, if applicable:
  5. UK NCSC  ncscvulndisclosure@ncsc.gov.uk  (UK systems affected)
  6. ENISA    cert@enisa.europa.eu             (EU systems affected)
```

### 5.2 What Each Agency Does With the Submission

**CISA** — Takes ownership of vendor coordination. Contacts OpenSSL,
BoringSSL, libsodium, browser vendors, OS vendors, hardware vendors.
Manages the 90-180 day coordination window. Issues CISA advisories on
disclosure day. Accepts STIX 2.1 via TAXII 2.1 (preferred) or email.

**NIST NVD** — Enriches the CVE with CVSS score, CWE mapping, CPE
product list. Publishes the enriched record to the National Vulnerability
Database on disclosure day. Does not coordinate vendors.

**MITRE CVE** — Assigns the CVE identifier. Holds in RESERVED state during
embargo. Publishes the CVE record on authorization from the researcher.
The CVE ID is the permanent public identifier for this vulnerability.

**CERT/CC** — Coordinates with vendors that CISA cannot reach directly.
Particularly valuable for academic, international, or legacy software vendors.
Has established relationships with vendors going back to 1988.

### 5.3 Machine-Readable Submission (STIX/TAXII)

CISA's AIS (Automated Indicator Sharing) accepts STIX 2.1 bundles via
TAXII 2.1. This is the preferred submission method when the endpoint is
available. PTorrent's `notifier.py` implements TAXII 2.1 submission:

```python
# Configure via environment:
PTOL_TAXII_ENDPOINT = "https://ais.cisa.gov/taxii/..."
PTOL_TAXII_KEY      = "<AIS API key from CISA>"

notifier = DisclosureNotifier(chain)
result = notifier.disclose(
    file_hash     = chain_file_hash,
    vuln_name     = "UDEO Sedenion Zero-Divisor ECC Attack",
    description   = "...",
    mitigation    = "...",
    embargo_until = "2027-06-03",
    agencies      = ["NIST", "CISA", "MITRE", "CERTCC"],
)
```

If TAXII is not configured, PTorrent falls back to structured email with
STIX bundle attachment. If SMTP is not configured, PTorrent logs the
NOTIFY transaction to the chain and provides manual submission instructions.

### 5.4 The STIX 2.1 Bundle

Every RDOP disclosure produces a STIX 2.1 bundle containing:

```json
{
  "type":    "bundle",
  "id":      "bundle--<uuid>",
  "objects": [
    { "type": "identity",          ... },  // researcher (ORCID)
    { "type": "vulnerability",     ... },  // the finding
    { "type": "course-of-action",  ... },  // mitigation
    { "type": "report",            ... }   // wraps all objects
  ]
}
```

The `vulnerability` object's `external_references` contains:

```json
[
  { "source_name": "PTorrent chain",
    "external_id": "<file_hash>",
    "description": "Block ref: <chain_ref>" },
  { "source_name": "ORCID",
    "external_id": "<orcid_id>",
    "url": "https://orcid.org/<orcid_id>" }
]
```

This embeds the PTorrent chain reference permanently in the international
vulnerability record. When NIST publishes the CVE, the PTorrent chain
hash is in the record. The chain is the provenance.

---

## 6. Security Classification Reference

### 6.1 Level 3 — Dual-Use (Default for Cryptographic Attack Vectors)

Dual-use datasets are those where the evaluation methodology itself could
be extracted and used for harmful purposes. Criteria:

- The dataset or its `.peval` evaluation result reveals an exploitable
  structure in a deployed cryptographic system
- A competent attacker could use the evaluation result to construct a
  working exploit without the underlying paper
- The affected systems are in active deployment protecting real users

All UDEO-class findings are Level 3 by definition.

### 6.2 Level 2 — Restricted (Pre-Publication Embargo)

Research datasets that are not directly weaponizable but are under
publication embargo or contain unpublished findings. Criteria:

- The data or results have not yet been published
- Public release before the researcher's intended date would harm the
  researcher's academic standing or patent rights
- No immediate harm to deployed systems, but sensitivity warrants control

### 6.3 Level 1 — Sensitive (Privacy, Medical, Financial)

Datasets that contain personal, medical, or financial information subject
to applicable law. Criteria:

- Personally identifiable information (PII)
- Protected health information (PHI) under HIPAA or equivalent
- Financial transaction data subject to regulatory requirements
- Access requires IRB approval, institutional authorization, or legal basis

### 6.4 Level 0 — Public

No restrictions. All standard research data, published datasets, open
corpora. The default for all PTorrent datasets.

---

## 7. Researcher Requirements

### 7.1 ORCID Profile (Mandatory for Level 1+)

A researcher filing an RDOP disclosure must have:
- A valid ORCID ID (registered at https://orcid.org/)
- Display name set in ORCID profile
- Institution affiliation set (or explicit independent researcher status)
- Email address in PTorrent profile (may differ from ORCID public email)

The ORCID is verified against the public ORCID API during profile setup.
Seeding Level 1+ datasets is blocked until ORCID is verified.

### 7.2 Email Configuration (Mandatory for NOTIFY)

To send agency notifications, the researcher must configure SMTP
credentials in their PTorrent settings. Without SMTP, the NOTIFY
transaction still commits to the chain, but email delivery is manual.

PTorrent logs the exact email template to the app's storage directory
for manual submission via the researcher's own email client.

### 7.3 No Anonymous Dual-Use Seeding

Level 3 datasets may not be seeded by anonymous (unverified) peers.
The chain's `SEED` transaction for a Level 3 dataset is blocked if the
peer's `peer_id` does not match the format `ORCID:<id>@<device_hash>`.

This means: if you did not complete your researcher profile, you cannot
seed dual-use data. Period. The deterrence is structural.

---

## 8. Implementation Requirements

A tool claiming RDOP compliance MUST:

1. Implement the `security` block in its `.ptorrent` parser
2. Enforce `embargo_until` as a hard block on job execution
3. Commit NOTIFY transactions to the PTorrent chain BEFORE sending notifications
4. Generate STIX 2.1 compliant vulnerability objects with ORCID external reference
5. Support the CLASSIFY/NOTIFY/ACKNOWLEDGE/DISCLOSE transaction sequence
6. Display the full `security.warning` text and require explicit acknowledgment
   before allowing access to Level 2+ datasets
7. Block seeding of Level 3+ datasets by unverified (no-profile) peers

A tool MAY implement:
- TAXII 2.1 submission (recommended for CISA submissions)
- Automatic `DISCLOSE` transaction on `embargo_until` date
- Pre-check against NIST NVD and CISA KEV before filing
- Multi-agency parallel submission

---

## 9. Invitation to NIST and CISA

This protocol was developed during research that produced a security
finding (UDEO attack class) requiring coordinated disclosure. The disclosure
itself was filed using the PTorrent infrastructure described in this document.

We invite NIST and CISA to:

**Evaluate PTorrent as a researcher disclosure intake channel.**

A formal NIST/CISA endorsement of RDOP would provide the research community
with a clear, tool-supported path from discovery to coordinated disclosure —
eliminating the friction that currently discourages timely reporting.

Specifically, we request:
- A CISA AIS TAXII 2.1 endpoint accessible to ORCID-verified researchers
- A NIST NVD intake endpoint that accepts RDOP-formatted disclosures
- Feedback on the STIX bundle format (§5.4) for NVD compatibility
- A point of contact for PTorrent-CISA/NIST integration development

**Contact:**  
Cody Michael Allison  
ORCID: https://orcid.org/[ORCID]  
the.wandering.god@gmail.com  
PTorrent: https://github.com/michaelrendier/PTorrent  

The PTorrent infrastructure is GPL-3.0. There is no commercial interest.
The goal is open research infrastructure for the security research community,
developed in the same spirit as the open-source security tools researchers
already depend on.

---

## 10. Version History

| Version | Date | Notes |
|---|---|---|
| 1.0 | 2026-06-03 | Initial specification. CLASSIFY/NOTIFY/ACKNOWLEDGE/DISCLOSE/REVOKE/FLAG/EVALUATE chain transactions. STIX 2.1 bundle. TAXII 2.1 interface. NIST/CISA/MITRE/CERTCC/NCSC/ENISA agency table. Classification levels 0-3. ORCID attribution throughout. |

---

## Appendix A — Relevant Standards and References

| Document | Source | Relevance |
|---|---|---|
| NIST IR 8388 | NIST | Vulnerability Disclosure Policy guidance for researchers |
| CISA CVD Process | CISA | Coordinated Vulnerability Disclosure program description |
| STIX 2.1 | OASIS CTI TC | Structured Threat Information Expression format |
| TAXII 2.1 | OASIS CTI TC | Trusted Automated Exchange of Intelligence |
| CVE JSON 5.0 | MITRE | CVE record format |
| ISO/IEC 29147 | ISO | Vulnerability disclosure standard |
| ISO/IEC 30111 | ISO | Vulnerability handling processes |
| RFC 9116 | IETF | security.txt format for website disclosure policies |
| NIST SP 800-218 | NIST | Secure Software Development Framework (SSDF) |
| FIPS 186-5 | NIST | Digital Signature Standard (affected by UDEO class) |

## Appendix B — PTorrent Chain Transaction Reference

| Transaction | Fields | RDOP Role |
|---|---|---|
| `CLASSIFY` | file_hash, level, embargo_until, contact_orcid | Sets classification |
| `NOTIFY` | file_hash, agency, report_hash, method, peer_id | Day 0 record |
| `ACKNOWLEDGE` | file_hash, orcid_id, warning_hash, peer_id | Consent record |
| `DISCLOSE` | file_hash, prev_class, new_class, peer_id | Embargo lift |
| `REVOKE` | file_hash, revoked_peer_id, reason | Access withdrawal |
| `FLAG` | file_hash, reason, detail, evidence_hash | Malicious file block |
| `EVALUATE` | file_hash, dataset_hash, terms_hash, peer_id | Evaluation record |
