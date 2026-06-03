"""
skills/adapters/cisa_kev_adapter.py — CISA Known Exploited Vulnerabilities adapter.
Pure Python. urllib only.

Handles:
  mode: cisa_kev      Full KEV catalog (single JSON download, ~1000+ entries)
  mode: cisa_kev_check  Check if a specific CVE is actively exploited

CISA KEV Catalog:
  https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
  Updated: continuously
  License: public domain (US government)
  No API key required

source fields:
  vendor_project  str    filter by vendor/project (e.g. "Microsoft", "Apache")
  product         str    filter by product name
  cve_id          str    check a specific CVE
  keyword         str    search in vulnerability name + notes
  date_added_from str    ISO date YYYY-MM-DD — filter by date added to catalog

Each row yielded:
  cve_id, vendor_project, product, vulnerability_name, date_added,
  due_date, required_action, known_ransomware, notes

Critical for responsible disclosure: if a vulnerability is in the KEV catalog,
it is actively exploited in the wild. CISA notification is mandatory.
"""

from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
from typing import Iterator, Optional, List

from skills.adapters import DataAdapter, Row

_KEV_URL  = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
_AGENT    = "PTorrent/2.0 (white-hat research; responsible disclosure)"
_CACHE_TTL = 3600   # re-download KEV at most once per hour


_kev_cache:    Optional[dict] = None
_kev_cached_at: float = 0.0


def _fetch_kev() -> dict:
    global _kev_cache, _kev_cached_at
    now = time.time()
    if _kev_cache and (now - _kev_cached_at) < _CACHE_TTL:
        return _kev_cache

    req = urllib.request.Request(
        _KEV_URL,
        headers={"User-Agent": _AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    _kev_cache    = data
    _kev_cached_at = now
    return data


def _matches(entry: dict, source: dict) -> bool:
    vendor  = source.get("vendor_project", "").lower()
    product = source.get("product", "").lower()
    cve     = source.get("cve_id", "").upper()
    keyword = source.get("keyword", "").lower()
    from_dt = source.get("date_added_from", "")

    if cve and entry.get("cveID", "") != cve:
        return False
    if vendor and vendor not in entry.get("vendorProject", "").lower():
        return False
    if product and product not in entry.get("product", "").lower():
        return False
    if keyword:
        searchable = (
            entry.get("vulnerabilityName", "") +
            entry.get("notes", "") +
            entry.get("vendorProject", "")
        ).lower()
        if keyword not in searchable:
            return False
    if from_dt and entry.get("dateAdded", "") < from_dt:
        return False
    return True


class CISAKEVAdapter(DataAdapter):
    NAME = "cisa_kev"

    def probe(self, source: dict) -> dict:
        return {
            "native_format":  "CISA KEV JSON",
            "access":         {"mode": "cisa_kev", "endpoint": _KEV_URL},
            "type":           "vulnerability_catalog",
            "confidence":     0.95,
            "license":        "public domain (US government)",
            "update_freq":    "continuous",
            "note":           "Actively exploited vulnerabilities only. "
                              "No API key required.",
        }

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        data     = _fetch_kev()
        entries  = data.get("vulnerabilities", [])
        catalog_ver = data.get("catalogVersion", "")
        date_rel    = data.get("dateReleased", "")

        for idx, entry in enumerate(entries):
            if not _matches(entry, source):
                continue

            ransomware = entry.get("knownRansomwareCampaignUse", "Unknown")
            yield {
                "_adapter":            "cisa_kev",
                "_source":             _KEV_URL,
                "_row_idx":            idx,
                "value":               1.0 if ransomware == "Known" else 0.5,
                "cve_id":              entry.get("cveID", ""),
                "vendor_project":      entry.get("vendorProject", ""),
                "product":             entry.get("product", ""),
                "vulnerability_name":  entry.get("vulnerabilityName", ""),
                "date_added":          entry.get("dateAdded", ""),
                "due_date":            entry.get("dueDate", ""),
                "required_action":     entry.get("requiredAction", ""),
                "known_ransomware":    ransomware,
                "notes":               entry.get("notes", ""),
                "catalog_version":     catalog_ver,
                "catalog_released":    date_rel,
                "raw": {
                    "cveID":    entry.get("cveID", ""),
                    "product":  entry.get("product", ""),
                    "ransomware": ransomware,
                },
            }


def check_kev(cve_id: str) -> Optional[dict]:
    """
    Check if a CVE is in the CISA KEV catalog (actively exploited).
    Returns the KEV entry or None. Used by disclosure notifier.
    """
    try:
        data    = _fetch_kev()
        entries = data.get("vulnerabilities", [])
        for e in entries:
            if e.get("cveID", "").upper() == cve_id.upper():
                return e
    except Exception:
        pass
    return None


def get_kev_summary() -> dict:
    """Return metadata about the current KEV catalog."""
    try:
        data = _fetch_kev()
        return {
            "count":           len(data.get("vulnerabilities", [])),
            "catalog_version": data.get("catalogVersion", ""),
            "date_released":   data.get("dateReleased", ""),
            "title":           data.get("title", ""),
        }
    except Exception as e:
        return {"error": str(e)}


ADAPTER_CLASS = CISAKEVAdapter
