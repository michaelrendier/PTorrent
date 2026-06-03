"""
skills/disclosure — PTorrent responsible disclosure infrastructure.

Modules:
  stix_builder.py    Build STIX 2.1 vulnerability + report objects (pure Python)
  notifier.py        Dispatch notifications to NIST, CISA, MITRE, CERT/CC

Environment variables:
  PTOL_RESEARCHER_ORCID   Researcher's ORCID (required for all disclosures)
  PTOL_RESEARCHER_EMAIL   Contact email for disclosure replies
  PTOL_RESEARCHER_NAME    Full name
  PTOL_NIST_API_KEY       NVD API key (optional, raises rate limits)
  PTOL_SMTP_HOST          SMTP server for email notifications
  PTOL_SMTP_PORT          SMTP port (default 587)
  PTOL_SMTP_USER          SMTP username
  PTOL_SMTP_PASS          SMTP password
  PTOL_TAXII_ENDPOINT     CISA AIS TAXII endpoint (optional)
  PTOL_TAXII_KEY          CISA AIS API key (optional)

White hat principle:
  All disclosures are recorded on the PTorrent chain with NOTIFY transactions.
  The chain provides a tamper-evident timeline of the full disclosure lifecycle:
    CLASSIFY → NOTIFY (agencies) → ACKNOWLEDGE (researchers) → DISCLOSE
  No disclosure leaves this module without a corresponding chain record.
"""

from skills.disclosure.notifier import DisclosureNotifier
from skills.disclosure.stix_builder import STIXBuilder

__all__ = ["DisclosureNotifier", "STIXBuilder"]
