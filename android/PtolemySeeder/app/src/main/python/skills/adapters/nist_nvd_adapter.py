"""
skills/adapters/nist_nvd_adapter.py — NIST National Vulnerability Database adapter.
Pure Python. urllib only.

Handles:
  mode: nist_nvd     Query NVD CVE database for vulnerability context
  mode: nist_nvd_cpe Query NVD CPE (product) database

NIST NVD API v2:
  Base: https://services.nvd.nist.gov/rest/json/cves/2.0
  Rate limit: 5 req/30s (unauthenticated), 50 req/30s (API key)
  API key env var: PTOL_NIST_API_KEY

source fields:
  keyword        str         free-text search (e.g. "ECC sedenion zero-divisor")
  cve_id         str         specific CVE (e.g. "CVE-2024-12345")
  severity       str         "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  pub_start      str         ISO date YYYY-MM-DD — publication start
  pub_end        str         ISO date YYYY-MM-DD — publication end
  max_results    int         max CVEs to return (default 100)

Each row yielded:
  cve_id, description, severity, cvss_score, published, modified,
  affected_products, references

Used by the disclosure notifier to check if a vulnerability is already known
before filing a new report.
"""

from __future__ import annotations
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Iterator, Optional

from skills.adapters import DataAdapter, Row

_BASE   = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_AGENT  = "PTorrent/2.0 (white-hat research; responsible disclosure)"
_DELAY  = 6.5    # seconds between requests without API key (5/30s limit)
_DELAY_KEY = 0.7 # seconds with API key (50/30s limit)


def _get_api_key() -> Optional[str]:
    try:
        from skills.ptorrent_keys import keys
        return keys.get('nist_nvd')
    except Exception:
        return os.environ.get("PTOL_NIST_API_KEY")


def _nvd_get(params: dict) -> dict:
    key   = _get_api_key()
    delay = _DELAY_KEY if key else _DELAY

    headers = {
        "User-Agent": _AGENT,
        "Accept":     "application/json",
    }
    if key:
        headers["apiKey"] = key

    url = _BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            time.sleep(30)
            raise RuntimeError(
                "NVD rate limit hit. Set PTOL_NIST_API_KEY for higher limits. "
                "Request a free key at: https://nvd.nist.gov/developers/request-an-api-key"
            )
        raise
    finally:
        time.sleep(delay)


def _parse_cve(item: dict) -> Row:
    cve  = item.get("cve", {})
    cid  = cve.get("id", "")
    desc = ""
    for d in cve.get("descriptions", []):
        if d.get("lang") == "en":
            desc = d.get("value", "")
            break

    # CVSS v3.1 or v3.0
    metrics  = cve.get("metrics", {})
    severity = "UNKNOWN"
    score    = 0.0
    for ver in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if ver in metrics and metrics[ver]:
            m = metrics[ver][0]
            d_  = m.get("cvssData", {})
            severity = d_.get("baseSeverity", m.get("baseSeverity", "UNKNOWN"))
            score    = float(d_.get("baseScore", 0.0))
            break

    products = []
    for config in cve.get("configurations", []):
        for node in config.get("nodes", []):
            for cpe in node.get("cpeMatch", []):
                if cpe.get("vulnerable"):
                    products.append(cpe.get("criteria", ""))

    refs = [r.get("url", "") for r in cve.get("references", [])]

    return {
        "_adapter":         "nist_nvd",
        "_source":          "https://nvd.nist.gov",
        "_row_idx":         0,
        "value":            score,
        "cve_id":           cid,
        "description":      desc,
        "severity":         severity,
        "cvss_score":       score,
        "published":        cve.get("published", ""),
        "modified":         cve.get("lastModified", ""),
        "affected_products": products[:10],
        "references":       refs[:5],
        "raw":              {"cve_id": cid, "score": score, "severity": severity},
    }


class NISTNVDAdapter(DataAdapter):
    NAME = "nist_nvd"

    def probe(self, source: dict) -> dict:
        dm: dict = {
            "native_format": "NVD JSON",
            "access": {"mode": "nist_nvd",
                       "endpoint": _BASE},
            "type": "vulnerability_catalog",
            "confidence": 0.92,
        }
        key = _get_api_key()
        dm["api_key_present"] = key is not None
        dm["rate_limit"] = "50/30s" if key else "5/30s"
        dm["note"] = (
            "Set PTOL_NIST_API_KEY for higher rate limits. "
            "Free key: https://nvd.nist.gov/developers/request-an-api-key"
        )
        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        keyword  = source.get("keyword", "")
        cve_id   = source.get("cve_id", "")
        severity = source.get("severity", "")
        max_r    = int(source.get("max_results", 100))
        pub_start = source.get("pub_start", "")
        pub_end   = source.get("pub_end", "")

        params: dict = {"resultsPerPage": min(max_r, 2000), "startIndex": 0}
        if cve_id:
            params["cveId"] = cve_id
        if keyword:
            params["keywordSearch"] = keyword
        if severity:
            params["cvssV3Severity"] = severity
        if pub_start:
            params["pubStartDate"] = pub_start + "T00:00:00.000"
        if pub_end:
            params["pubEndDate"] = pub_end + "T23:59:59.999"

        total_fetched = 0
        while total_fetched < max_r:
            data = _nvd_get(params)
            vulns = data.get("vulnerabilities", [])
            if not vulns:
                break
            for i, item in enumerate(vulns):
                row = _parse_cve(item)
                row["_row_idx"] = total_fetched + i
                yield row
            total_fetched += len(vulns)
            total_results  = data.get("totalResults", 0)
            if total_fetched >= total_results:
                break
            params["startIndex"] = total_fetched


def check_cve_exists(keyword: str, max_results: int = 20) -> list[dict]:
    """
    Quick check: does a CVE already exist for this vulnerability type?
    Returns list of matching CVE summaries. Used by disclosure notifier.
    """
    adapter = NISTNVDAdapter()
    results = []
    for row in adapter.stream_rows({
        "keyword": keyword,
        "max_results": max_results,
    }):
        results.append({
            "cve_id":   row["cve_id"],
            "severity": row["severity"],
            "score":    row["cvss_score"],
            "desc":     row["description"][:200],
        })
    return results


ADAPTER_CLASS = NISTNVDAdapter
