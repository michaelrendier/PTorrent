# PTorrent Agency Interface
## NIST · CISA · MITRE · CERT/CC · NCSC · ENISA

**Part of:** PTorrent Responsible Disclosure Open Protocol (RDOP) v1.0  
**See also:** [Responsible-Disclosure-Protocol.md](Responsible-Disclosure-Protocol.md)

---

## Quick Reference

| Agency | Role | Primary Contact | Method |
|---|---|---|---|
| CISA | Vendor coordination, national security | vuln@cisa.dhs.gov | STIX/TAXII or email |
| NIST NVD | CVE enrichment, NVD publication | nvd@nist.gov | Email + portal |
| MITRE CVE | CVE assignment (RESERVED → published) | cve@mitre.org | Web form + email |
| CERT/CC | Fallback coordination, legacy vendors | vulnreport@cert.org | Web form + email |
| UK NCSC | UK-affecting vulnerabilities | ncscvulndisclosure@ncsc.gov.uk | Email |
| ENISA | EU-affecting vulnerabilities | cert@enisa.europa.eu | Email |
| BSI | Germany-specific | bsi@bsi.bund.de | Email |

Submit to CISA, NIST, and MITRE simultaneously on Day 0. Do not wait for acknowledgment before proceeding to the next agency.

---

## Agency Profiles

### CISA — Cybersecurity and Infrastructure Security Agency

**Role in RDOP:** Primary coordinator. CISA takes ownership of vendor notification, patch coordination, and disclosure timing. For vulnerabilities affecting federal systems or critical infrastructure, CISA is the lead agency.

**What CISA wants:**
- National security impact assessment: does this affect FIPS-approved algorithms? Federal systems? Critical infrastructure sectors?
- Affected vendor list (they will contact vendors directly)
- CVSS v3 estimate
- Proposed embargo timeline
- STIX 2.1 bundle (their preferred machine-readable format)

**Submission:**
```
Primary:    TAXII 2.1 to CISA AIS endpoint (configure PTOL_TAXII_ENDPOINT)
Fallback:   vuln@cisa.dhs.gov (email with STIX bundle attachment)
Portal:     https://www.cisa.gov/reporting-cyber-vulnerabilities
AIS signup: https://www.cisa.gov/ais
```

**CISA AIS (Automated Indicator Sharing):**
CISA's AIS program accepts STIX 2.1 bundles via TAXII 2.1. Organizations can apply for AIS participation to receive bidirectional threat intelligence sharing. PTorrent researchers are encouraged to register for AIS access, which enables direct TAXII submission without manual email.

**Response timeline:** 2-5 business days for acknowledgment. CISA assigns an advisory tracking number.

**Environment variables for PTorrent:**
```bash
PTOL_TAXII_ENDPOINT="https://ais.cisa.gov/taxii/..."  # provided by CISA on AIS registration
PTOL_TAXII_KEY="<AIS API key>"
```

---

### NIST NVD — National Vulnerability Database

**Role in RDOP:** Enriches CVE records with CVSS score, CWE weakness type, CPE product identifiers. Publishes to the NVD. Does not assign CVE IDs (MITRE does that) and does not coordinate vendors (CISA does that).

**What NIST NVD wants:**
- CVSS v3 vector string (they may recalculate, but a researcher estimate is helpful)
- CWE mapping (CWE-327 for broken crypto, CWE-310 for structural crypto issues)
- CPE product identifiers for affected software/hardware
- Embargo date

**Submission:**
```
Email:   nvd@nist.gov
Portal:  https://nvd.nist.gov/vuln/vulnerability-disclosure
API key: https://nvd.nist.gov/developers/request-an-api-key (free)
```

**API key:** A free NVD API key increases rate limits from 5 req/30s to 50 req/30s. Request one at the link above. Set as `PTOL_NIST_API_KEY` in PTorrent environment.

**Response timeline:** NIST acknowledges and routes to MITRE for CVE assignment. The NVD record is published when MITRE authorizes.

---

### MITRE CVE — Common Vulnerabilities and Exposures

**Role in RDOP:** Assigns the CVE identifier. Holds in RESERVED state during embargo. Publishes the CVE description on researcher authorization.

**What MITRE wants:**
- Affected product(s) and version(s)
- CWE type
- One-paragraph public description (this becomes the CVE record verbatim)
- At least one public reference (your paper URL, once published)

**Important:** The CVE description you provide becomes permanent public record. Write it carefully. It will be indexed, cited, and referenced indefinitely.

**Submission:**
```
Web form: https://cveform.mitre.org/
Email:    cve@mitre.org
```

**CVE states:**
```
RESERVED    → CVE assigned, held pending your authorization
PUBLISHED   → You authorized publication (embargo lifted)
REJECTED    → Duplicate or not a valid vulnerability
```

**Pre-publication:** When you file, explicitly state "Please hold in RESERVED state until [DATE] or until I authorize publication." MITRE will comply.

**CNA consideration:** For organizations that regularly discover vulnerabilities, becoming a CVE Numbering Authority (CNA) enables self-assignment of CVE IDs. PTorrent itself could become a CNA for security findings discovered via its research infrastructure.

---

### CERT/CC — Carnegie Mellon CERT Coordination Center

**Role in RDOP:** Coordination fallback for vendors that CISA cannot directly reach — particularly academic software, international vendors, open-source projects without corporate backing, and legacy systems.

CERT/CC has operated since 1988 and has established relationships with vendors and security teams globally. For a vulnerability like UDEO that affects foundational cryptographic libraries used by thousands of projects, CERT/CC's breadth of vendor contacts is uniquely valuable.

**Submission:**
```
Web form: https://kb.cert.org/vuls/report/
Email:    vulnreport@cert.org
```

---

### UK NCSC

**Use when:** The vulnerability affects UK government systems, UK-based critical infrastructure, or algorithms mandated by UK security standards.

```
Email:   ncscvulndisclosure@ncsc.gov.uk
Portal:  https://www.ncsc.gov.uk/section/about-ncsc/vulnerability-reporting
```

---

### ENISA — European Union Agency for Cybersecurity

**Use when:** The vulnerability affects EU critical infrastructure or EU-mandated cryptographic standards (eIDAS, NIS2 directive scope).

```
Email:   cert@enisa.europa.eu
Portal:  https://www.enisa.europa.eu/topics/csirts-in-europe
```

---

## Email Templates

### Template 1 — CISA Primary Disclosure

```
To:      vuln@cisa.dhs.gov
CC:      nvd@nist.gov
Subject: [COORDINATED VULNERABILITY DISCLOSURE] <VULN_NAME>
         | Pre-Publication | 180-Day Embargo | <PTORRENT_REPORT_HASH_SHORT>

Attachments:
  1. STIX 2.1 bundle (ptorrent_disclosure_<hash>.json)
  2. Technical paper draft (EMBARGO UNTIL <DATE>)
  3. PTorrent chain export

Dear CISA Vulnerability Coordination Team,

I am filing a pre-publication coordinated disclosure for a vulnerability
discovered during open research. I request a 180-day embargo from this
filing date, with public disclosure coordinated for <DATE>.

RESEARCHER: <NAME>
ORCID: https://orcid.org/<ORCID>
CONTACT: <EMAIL>
PTORRENT CHAIN REFERENCE:
  File hash:   <FILE_HASH>
  NOTIFY tx:   <NOTIFY_TX_HASH>
  Timestamp:   <TIMESTAMP_UTC>
  Report hash: <REPORT_HASH>

CVE STATUS: Requesting assignment via MITRE (simultaneous filing)

EMBARGO DATE: <DATE>
PUBLICATION: <VENUE> (<YEAR>)

━━━ VULNERABILITY SUMMARY ━━━

Name:        <VULN_NAME>
Class:       <ATTACK_CLASS>
Severity:    <CVSS_SCORE> (<SEVERITY>)
CVSS Vector: <VECTOR>
CWE:         <CWE_ID> (<CWE_NAME>)

━━━ AFFECTED SYSTEMS ━━━

<AFFECTED_ALGORITHMS_AND_IMPLEMENTATIONS>

FIPS relevance: <YES/NO — WHICH FIPS STANDARDS>

━━━ TECHNICAL DESCRIPTION ━━━

<DESCRIPTION — SUFFICIENT FOR CISA ASSESSMENT, NOT A WORKING EXPLOIT>

━━━ MITIGATION ━━━

Short-term: <IMMEDIATE_MITIGATIONS>
Long-term:  <STRUCTURAL_FIX>

━━━ PROPOSED TIMELINE ━━━

Day 0   (<DATE>): This filing
Day 30:           CISA assessment, CVE assignment
Day 30-90:        Vendor notification and patch development
Day 90-150:       Patch testing
Day 150-180:      Final coordination
Day 180 (<DATE>): Public disclosure + paper submission

━━━ PTORRENT DISCLOSURE INFRASTRUCTURE ━━━

This disclosure was filed using PTorrent's responsible disclosure
module (GPL-3.0). The STIX 2.1 bundle was auto-generated and the
NOTIFY transaction was committed to the PTorrent blockchain before
this email was sent. The chain provides an independent timestamped
record of this disclosure.

We invite CISA to evaluate PTorrent as a standardized researcher
disclosure intake channel. Details:
https://github.com/michaelrendier/PTorrent
wiki/Responsible-Disclosure-Protocol.md

Respectfully,
<NAME>
ORCID: https://orcid.org/<ORCID>
<EMAIL>
```

### Template 2 — MITRE CVE Request

```
To:      cve@mitre.org
Subject: CVE Request — <VULN_NAME> | Pre-Publication | Embargo <DATE>

Dear MITRE CVE Team,

I am requesting CVE assignment for a vulnerability discovered during
algebraic/mathematical research.

PRODUCT AFFECTED:
  <PRODUCT LIST WITH VERSIONS>

VULNERABILITY TYPE:
  CWE-<ID>: <CWE_NAME>

CVE DESCRIPTION (for public record):
  <2-3 SENTENCE TECHNICAL DESCRIPTION SUITABLE FOR PERMANENT PUBLIC RECORD>
  Discovered by <NAME> (ORCID: <ORCID>), <YEAR>.
  Coordinated disclosure via CISA (simultaneous filing).

PUBLIC REFERENCE (available on disclosure):
  <PAPER TITLE>, <VENUE>, <YEAR>

EMBARGO REQUEST:
  Please hold CVE in RESERVED state until <DATE> or until I authorize
  publication. I will provide authorization by email on embargo lift date.

CISA REFERRAL:
  Filed simultaneously with CISA (vuln@cisa.dhs.gov).
  NIST filed simultaneously (nvd@nist.gov).

<NAME>
ORCID: https://orcid.org/<ORCID>
<EMAIL>
```

---

## PTorrent API for Disclosure

### Programmatic Disclosure

```python
from skills.disclosure import DisclosureNotifier
from ptorrent_chain import PTorrentChain

chain = PTorrentChain(store_path="ptorrent_chain.json")
notifier = DisclosureNotifier(chain)

# Pre-check: is this already known?
existing = notifier.pre_check("ECC sedenion zero-divisor")
print(existing["note"])

# File the disclosure
result = notifier.disclose(
    file_hash      = "a3f2c1...",
    vuln_name      = "UDEO Sedenion Zero-Divisor ECC Attack",
    description    = "...",
    mitigation     = "...",
    embargo_until  = "2027-06-03",
    agencies       = ["NIST", "CISA", "MITRE", "CERTCC"],
    cvss_score     = 8.1,
    affected_systems = ["OpenSSL ECDSA", "BoringSSL EC", "libsodium Ed25519"],
)

print(result["summary"])
# DISCLOSURE SUMMARY: UDEO Sedenion Zero-Divisor ECC Attack
# Report hash: a3f2c1b8e9d2...
#
#   NIST:   ✓ SENT via email
#   CISA:   ✓ SENT via stix_taxii
#   MITRE:  ✓ SENT via email
#   CERTCC: ✓ SENT via email
#
# Embargo until: 2027-06-03
# DISCLOSE transaction will auto-fire on this date.
```

### Environment Configuration

```bash
# Required for ORCID-attributed disclosures
export PTOL_RESEARCHER_ORCID="0000-0001-XXXX-XXXX"
export PTOL_RESEARCHER_NAME="Cody Michael Allison"
export PTOL_RESEARCHER_EMAIL="the.wandering.god@gmail.com"

# Required for email delivery
export PTOL_SMTP_HOST="smtp.example.com"
export PTOL_SMTP_PORT="587"
export PTOL_SMTP_USER="user@example.com"
export PTOL_SMTP_PASS="<app-specific-password>"

# Optional — CISA AIS direct submission
export PTOL_TAXII_ENDPOINT="https://ais.cisa.gov/taxii/..."
export PTOL_TAXII_KEY="<AIS key>"

# Optional — higher NVD API rate limits
export PTOL_NIST_API_KEY="<NVD API key>"
```

---

## What PTorrent Asks of NIST and CISA

One specific ask per agency:

**NIST:** Provide a structured intake endpoint that accepts RDOP-format disclosures (STIX 2.1 + PTorrent chain reference). Currently, NIST NVD intake is email-only. A machine-readable intake endpoint would allow PTorrent to submit directly, reducing processing time and human error.

**CISA:** Provide AIS TAXII 2.1 endpoint access for ORCID-verified individual researchers (currently AIS is primarily for organizations). PTorrent can verify ORCID at intake, giving CISA confidence in researcher identity without requiring organizational membership.

Both asks are compatible with existing NIST and CISA infrastructure. They require policy decisions, not technical development, on the agency side.

The technical development — the RDOP reference implementation — is already done. It is here: https://github.com/michaelrendier/PTorrent
