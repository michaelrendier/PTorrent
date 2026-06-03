"""
skills/adapters/tap_adapter.py — IVOA TAP/ADQL adapter.
Pure Python. urllib only.

Handles:
  mode: tap_adql    IVOA Table Access Protocol with ADQL queries

source fields:
  endpoint      str     TAP service base URL
                        e.g. "https://gea.esac.esa.int/tap-server/tap"
                        e.g. "http://tapvizier.u-strasbg.fr/TAPVizieR/tap"
                        e.g. "https://vo.rubin.lsst.org/tap"
  query         str     ADQL query string
  table         str     table name (used to build default query if no query)
  columns       list    columns to select (used with table)
  max_rows      int     MAXREC parameter (default 10000)
  format        str     response format: "votable" | "json" | "csv" (default votable)
  value_col     str     primary value column

TAP sync endpoint: {endpoint}/sync
"""

from __future__ import annotations
import urllib.request
import urllib.parse
import urllib.error
import time
from typing import Iterator, Optional

from skills.adapters import DataAdapter, Row
from skills.adapters.votable_adapter import _parse_votable, _cast_votable, _UCD_TO_COORD


_USER_AGENT = "PTorrent/2.0 (IVOA TAP client; research use)"


def _tap_sync(endpoint: str, query: str, max_rows: int,
              fmt: str = "votable") -> bytes:
    """Execute TAP sync query. Returns raw response bytes."""
    sync_url = endpoint.rstrip("/") + "/sync"

    fmt_map = {
        "votable": "application/x-votable+xml",
        "json":    "application/json",
        "csv":     "text/csv",
    }
    mime = fmt_map.get(fmt, "application/x-votable+xml")

    params = urllib.parse.urlencode({
        "REQUEST": "doQuery",
        "LANG":    "ADQL",
        "QUERY":   query,
        "MAXREC":  str(max_rows),
        "FORMAT":  mime,
    }).encode("utf-8")

    req = urllib.request.Request(
        sync_url,
        data=params,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent":   _USER_AGENT,
            "Accept":       mime,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _build_query(source: dict) -> str:
    if source.get("query"):
        return source["query"]
    table   = source.get("table", "")
    columns = source.get("columns", ["*"])
    col_str = ", ".join(columns) if columns != ["*"] else "*"
    max_r   = source.get("max_rows", 10000)
    return f"SELECT TOP {max_r} {col_str} FROM {table}"


class TAPAdapter(DataAdapter):
    NAME = "tap_adql"

    def probe(self, source: dict) -> dict:
        endpoint = source.get("endpoint", "")
        dm: dict = {
            "native_format": "TAP/ADQL",
            "access": {"mode": "tap_adql", "endpoint": endpoint},
        }

        # Check TAP availability
        tables_url = endpoint.rstrip("/") + "/tables"
        try:
            req = urllib.request.Request(
                tables_url,
                headers={"User-Agent": _USER_AGENT, "Accept": "text/xml, */*"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read(4096).decode("utf-8", errors="replace")
                dm["tap_available"] = True
                dm["confidence"]    = 0.88
                dm["type"]          = "tap_catalog"
                # Quick table count from XML
                import re
                table_names = re.findall(r'<tableName>([^<]+)</tableName>', body)
                if table_names:
                    dm["tables_sample"] = table_names[:10]
        except Exception as e:
            dm["tap_available"] = False
            dm["confidence"]    = 0.0
            dm["error"]         = str(e)

        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        endpoint  = source.get("endpoint", "")
        max_rows  = int(source.get("max_rows", 10000))
        fmt       = source.get("format", "votable")
        val_col   = source.get("value_col")
        query     = _build_query(source)

        # Apply subset as WHERE clause if specified and no custom query
        if subset and not source.get("query"):
            conditions = []
            if "ra_range" in subset:
                ra = subset["ra_range"]
                conditions.append(f"ra BETWEEN {ra[0]} AND {ra[1]}")
            if "dec_range" in subset:
                dec = subset["dec_range"]
                conditions.append(f"dec BETWEEN {dec[0]} AND {dec[1]}")
            if conditions:
                where = " AND ".join(conditions)
                if "WHERE" in query.upper():
                    query += f" AND {where}"
                else:
                    query += f" WHERE {where}"

        try:
            raw_bytes = _tap_sync(endpoint, query, max_rows, fmt)
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"TAP query failed (HTTP {e.code}): {e.reason}\n"
                f"Query: {query}"
            )

        # Parse VOTable response
        text = raw_bytes.decode("utf-8", errors="replace")
        fields, rows = _parse_votable(text)

        if not fields:
            return

        if val_col is None:
            for f in fields:
                if "phot.flux" in f.get("ucd", "") or \
                   "phys.veloc" in f.get("ucd", ""):
                    val_col = f["name"]
                    break
            if val_col is None and fields:
                val_col = fields[0]["name"]

        for idx, row_vals in enumerate(rows):
            raw: dict = {}
            coords: dict = {}
            for i, fld in enumerate(fields):
                if i >= len(row_vals):
                    break
                cast = _cast_votable(row_vals[i], fld.get("datatype", "char"))
                raw[fld["name"]] = cast
                coord_key = _UCD_TO_COORD.get(
                    fld.get("ucd", "").split(";")[0]
                )
                if coord_key and isinstance(cast, float):
                    coords[coord_key] = cast

            val = raw.get(val_col)
            if val is None:
                try:
                    val = next(v for v in raw.values()
                               if isinstance(v, float))
                except StopIteration:
                    val = 0.0

            yield {
                "_adapter": "tap_adql",
                "_source":   f"{endpoint}::{source.get('table', 'query')}",
                "_row_idx":  idx,
                "value":     float(val) if isinstance(val, (int, float)) else 0.0,
                "raw":       raw,
                **coords,
            }


ADAPTER_CLASS = TAPAdapter
