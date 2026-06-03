# PTorrent Security Classification
## Level Definitions, Enforcement, and Researcher Obligations

**Part of:** PTorrent Responsible Disclosure Open Protocol (RDOP) v1.0  
**See also:** [Responsible-Disclosure-Protocol.md](Responsible-Disclosure-Protocol.md)

---

## Classification Levels at a Glance

```
Level 0 — PUBLIC      No restrictions. Standard research data.
Level 1 — SENSITIVE   ORCID verified. Privacy/medical/financial data.
Level 2 — RESTRICTED  Institution verified. Pre-publication embargo.
Level 3 — DUAL-USE    Explicit acknowledgment. Cryptographic attack vectors.
```

No Level 4. ITAR/EAR export-controlled materials are outside PTorrent's scope.
If your dataset requires export control review, consult your institution's
legal office before using PTorrent.

---

## Level 0 — Public

**No restrictions.** All standard research datasets, published results, open
corpora. The default for every PTorrent dataset.

SPARC rotation curves: Level 0.  
JWST spectral cubes (public release): Level 0.  
NIST NVD CVE records: Level 0.  
CISA KEV catalog: Level 0.

No `security` block required. No ORCID required to seed. No warnings displayed.

---

## Level 1 — Sensitive

**ORCID required to seed.** Applied to datasets containing personal, medical,
or financial information governed by applicable law.

### When to Classify Level 1

- Dataset contains PII (names, addresses, identifiers)
- Dataset contains PHI (health records, clinical trial data, genomic data)
- Dataset contains financial transaction records
- Dataset is derived from human subjects research requiring IRB consent
- Access to the underlying dataset required institutional authorization

### Enforcement

- Seeding: ORCID profile required and verified
- Warning: orange banner displayed before job starts
- Chain: CLASSIFY transaction at level=1
- Seeder must enter ORCID into acknowledgment field

### Example Warning Text

```
This dataset contains [medical/financial/personal] information.
Access requires: [IRB approval number / regulatory basis].
Do not re-seed without authorization from: [CONTACT_ORCID].
```

### Researcher Obligations

- Verify you have lawful basis to process the data
- Do not re-seed without original data provider authorization
- Contact the `contact_orcid` holder with questions about access rights

---

## Level 2 — Restricted

**Institution verification recommended.** Applied to pre-publication research
findings, embargoed results, and data under contractual confidentiality.

### When to Classify Level 2

- Results that have not yet been published and would harm the researcher's
  academic standing if released prematurely
- Data under a data use agreement (DUA) with access restrictions
- Collaborative research data where co-authors have not authorized release
- Dataset access requires an approved data access request (DAR)

### Enforcement

- Seeding: ORCID required + `embargo_until` enforced as hard block
- Warning: orange full-screen notice before job starts
- Chain: CLASSIFY transaction at level=2 with `embargo_until`
- `DISCLOSE` transaction auto-fires when `embargo_until` date is reached

### Example Warning Text

```
This dataset is subject to a publication embargo until [DATE].
Results derived from this dataset may not be published, presented,
or shared until that date. Violation may constitute breach of
data use agreement or scientific misconduct.
Contact: [CONTACT_ORCID]
```

---

## Level 3 — Dual-Use

**Explicit ORCID acknowledgment required. No override.** Applied to any
dataset or evaluation result that:

- Reveals an exploitable structure in a deployed cryptographic system
- Contains functional attack vectors against algorithms in active use
- Would enable a competent attacker to construct a working exploit

### When to Classify Level 3

The test is not "could this be misused" — almost anything could be misused.
The test is:

> **Could a competent attacker, given only this dataset and publicly available
> information, construct a working exploit against a deployed system within
> a reasonable time frame?**

If the answer is yes: Level 3.

Examples that ARE Level 3:
- Mathematical proof that demonstrates an attack against ECDSA P-256
- Sedenion zero-divisor geometry mapped to ECC curve structure
- Hash function preimage collision dataset
- Side-channel measurement dataset from a specific HSM model

Examples that are NOT Level 3 (they are academic/theoretical):
- A proof that a class of curves is theoretically weak under exotic conditions
- A demonstration that a retired algorithm (DES, MD5) has known weaknesses
- Historical analysis of previously-disclosed vulnerabilities

When in doubt: classify Level 3. You can always lower the classification.
You cannot un-release a dual-use dataset.

### Enforcement

- Seeding: ORCID required + explicit acknowledgment (ORCID typed into field)
- Warning: red full-screen interstitial, not dismissible without ORCID entry
- Chain: CLASSIFY + ACKNOWLEDGE per researcher, NOTIFY per agency
- `embargo_until` is a hard block — no override, no "proceed anyway"
- APK checks for FLAG transactions on every Level 3 ptorrent before execution
- Anonymous (no-profile) peers cannot seed Level 3 data under any circumstances

### The Acknowledgment Screen

The APK displays this before any Level 3 access:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠  SECURITY NOTICE — LEVEL 3: DUAL-USE  ⚠                    │
│                                                                  │
│  CLASSIFICATION: DUAL-USE                                        │
│  EMBARGO UNTIL:  [DATE]                                          │
│  CONTACT:        [NAME] (ORCID: [ID])                           │
│                                                                  │
│  [FULL WARNING TEXT FROM security.warning FIELD]                │
│                                                                  │
│  By entering your ORCID, you acknowledge that:                  │
│  • You have read and understood this warning                     │
│  • You will use this data only for authorized research           │
│  • You will not redistribute this data to unauthorized parties   │
│  • You will respect the embargo date                             │
│  • Your access is recorded on the PTorrent chain                │
│                                                                  │
│  This acknowledgment is permanent and irrevocable.              │
│                                                                  │
│  Enter your ORCID to proceed:                                   │
│  [                              ]                                │
│                                                                  │
│  [ CANCEL ]                    [ ACKNOWLEDGE AND PROCEED ]      │
└─────────────────────────────────────────────────────────────────┘
```

The `warning_hash` of this displayed text is recorded in the ACKNOWLEDGE
transaction. Proof of exactly what was displayed, to whom, when.

### Researcher Obligations Under Level 3

**Before classifying Level 3:**
- File RDOP disclosure with NIST, CISA, and MITRE
- Set `embargo_until` to your planned disclosure date
- Set `contact_orcid` to your ORCID

**During embargo:**
- Do not share the dataset or evaluation results with unauthorized parties
- Cooperate with agency coordination requests
- Grant access to ACKNOWLEDGE-verified security researchers on request
- Monitor for evidence of independent discovery or active exploitation

**On disclosure day:**
- Authorize MITRE to publish the RESERVED CVE
- Run `chain.disclose(file_hash, "dual-use", "public", peer_id)`
- Submit paper / post preprint
- The DISCLOSE transaction drops classification to Level 0 automatically

---

## Automatic Disclosure on Embargo Date

PTorrent's pre-flight checker compares `embargo_until` against today's date
on every job start. But the embargo lift (DISCLOSE transaction) can be
automated:

```python
# In a scheduled job or cron:
from ptorrent_chain import PTorrentChain
import time

chain = PTorrentChain(store_path="ptorrent_chain.json")
today = time.strftime("%Y-%m-%d")

for block in chain._chain:
    for tx in block.transactions:
        if tx.type == "CLASSIFY":
            cls = chain.get_classification(tx.file_hash)
            if cls and cls["embargo_until"] and cls["embargo_until"] <= today:
                # Embargo has passed — lift it
                chain.disclose(
                    file_hash          = tx.file_hash,
                    prev_classification = cls["classification"],
                    new_classification  = "public",
                    peer_id            = "ORCID:" + cls["contact_orcid"],
                )
                chain.commit()
```

This can be set as a daily cron on the researcher's desktop or on any device
that holds the chain. When the DISCLOSE transaction is committed, every device
syncing the chain sees the classification drop and seeding becomes unrestricted.

---

## Classifying a Dataset — Step by Step

### 1. Determine the level

Use the tests in §Level 3 above. When uncertain, choose the higher level.

### 2. Write the warning text

The warning must:
- State exactly what makes this dataset sensitive
- Name the specific harm that could result from misuse
- State the embargo date (if applicable)
- Provide contact information for access questions

### 3. Classify via PTorrent chain

```python
chain.classify(
    file_hash      = PTorrentChain.hash_file("mydata.peval"),
    classification = "dual-use",
    level          = 3,
    embargo_until  = "2027-06-03",
    contact_orcid  = "0000-0001-XXXX-XXXX",
    peer_id        = "ORCID:0000-0001-XXXX-XXXX@device",
    disclosure_ref = "NIST-PRE-DISCLOSURE-2026-EXAMPLE",
)
chain.commit()
```

### 4. File RDOP disclosure (Level 3 only)

```python
from skills.disclosure import DisclosureNotifier
notifier = DisclosureNotifier(chain)
notifier.disclose(
    file_hash     = "...",
    vuln_name     = "...",
    description   = "...",
    mitigation    = "...",
    embargo_until = "2027-06-03",
    agencies      = ["NIST", "CISA", "MITRE", "CERTCC"],
)
```

### 5. Add `security` block to `.ptorrent`

```json
{
  "security": {
    "classification":       "dual-use",
    "level":                3,
    "warning":              "<warning text from step 2>",
    "embargo_until":        "2027-06-03",
    "contact_orcid":        "0000-0001-XXXX-XXXX",
    "acknowledge_required": true,
    "disclosure_ref":       "NIST-PRE-DISCLOSURE-2026-EXAMPLE"
  }
}
```

### 6. Distribute the classified `.ptorrent`

The classified `.ptorrent` can now be shared with selected researchers.
Each researcher who accesses it will see the Level 3 warning, must enter
their ORCID, and will produce an ACKNOWLEDGE transaction on the chain.
Their access is permanently recorded. Yours is protected.

---

## Lowering a Classification

Classifications can be lowered (e.g. Level 3 → Level 0 on disclosure day)
by submitting a DISCLOSE transaction. They cannot be raised after the fact
in a way that retroactively restricts access that has already been granted
— the ACKNOWLEDGE transactions already in the chain are permanent.

This is intentional. The chain is append-only. History cannot be revised.
Plan your classification before distributing the file.
