"""
skills/adapters/votable_adapter.py — IVOA VOTable adapter.
Pure Python XML parser. No astropy required.

Handles:
  mode: votable   VOTable XML (Gaia, VizieR, SIMBAD query responses, TAP results)

VOTable is XML. Fields are defined in FIELD elements.
Data is in TABLEDATA (ASCII) or BINARY sections.
This adapter handles TABLEDATA (most common for query responses).
"""

from __future__ import annotations
import xml.etree.ElementTree as ET
import urllib.request
from typing import Iterator, Optional, List, Dict

from skills.adapters import DataAdapter, Row

_NS = {
    "v1":  "http://www.ivoa.net/xml/VOTable/v1.1",
    "v12": "http://www.ivoa.net/xml/VOTable/v1.2",
    "v13": "http://www.ivoa.net/xml/VOTable/v1.3",
}
_ANY_NS = "{http://www.ivoa.net/xml/VOTable"


def _fetch_text(path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        req = urllib.request.Request(
            path_or_url,
            headers={"Accept": "application/x-votable+xml, text/xml, */*"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    with open(path_or_url, encoding="utf-8", errors="replace") as f:
        return f.read()


def _strip_ns(tag: str) -> str:
    """Remove XML namespace from tag."""
    if "}" in tag:
        return tag.split("}")[1]
    return tag


def _parse_votable(text: str) -> tuple[List[dict], List[List[str]]]:
    """Return (field_defs, data_rows) from VOTable XML."""
    root = ET.fromstring(text)
    fields: List[dict] = []
    rows:   List[List[str]] = []

    # Find all FIELD elements
    for elem in root.iter():
        if _strip_ns(elem.tag) == "FIELD":
            fields.append({
                "name":     elem.get("name", ""),
                "id":       elem.get("ID", elem.get("name", "")),
                "ucd":      elem.get("ucd", ""),
                "unit":     elem.get("unit", ""),
                "datatype": elem.get("datatype", "char"),
            })

    # Find TABLEDATA
    for elem in root.iter():
        if _strip_ns(elem.tag) == "TABLEDATA":
            for tr in elem:
                if _strip_ns(tr.tag) == "TR":
                    row = [td.text or "" for td in tr
                           if _strip_ns(td.tag) == "TD"]
                    rows.append(row)
            break

    return fields, rows


def _cast_votable(val: str, datatype: str):
    val = val.strip()
    if not val:
        return None
    if datatype in ("float", "double", "floatComplex", "doubleComplex"):
        try:
            return float(val)
        except ValueError:
            return None
    if datatype in ("int", "long", "short", "unsignedByte"):
        try:
            return int(val)
        except ValueError:
            return None
    return val


_UCD_TO_COORD = {
    "pos.eq.ra":     "coord_ra",
    "pos.eq.dec":    "coord_dec",
    "em.wl":         "coord_wavelength",
    "phys.veloc":    "coord_velocity",
    "phot.flux":     "value",
    "phot.flux.density": "value",
    "pos.galactic.lon": "coord_l",
    "pos.galactic.lat": "coord_b",
}


class VOTableAdapter(DataAdapter):
    NAME = "votable"

    def probe(self, source: dict) -> dict:
        path = source.get("file") or source.get("url", "")
        dm: dict = {
            "native_format": "VOTable",
            "access": {"mode": "votable"},
        }
        try:
            text = _fetch_text(path)
            fields, rows = _parse_votable(text)
            dm["columns"] = [f["name"] for f in fields]
            dm["ucds"]    = {f["name"]: f["ucd"] for f in fields}
            dm["units"]   = {f["name"]: f["unit"] for f in fields}
            dm["n_rows"]  = len(rows)
            dm["type"]    = "catalog"
            dm["confidence"] = 0.90
        except Exception as e:
            dm["error"] = str(e)
            dm["confidence"] = 0.0
        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        path = source.get("file") or source.get("url", "")
        val_col = source.get("value_col")

        text   = _fetch_text(path)
        fields, rows = _parse_votable(text)

        if not fields:
            raise ValueError(f"VOTable adapter: no FIELD elements in {path}")

        # Auto-select value column by UCD
        if val_col is None:
            for f in fields:
                if "phot.flux" in f["ucd"] or "phys.veloc" in f["ucd"]:
                    val_col = f["name"]
                    break
            if val_col is None and fields:
                val_col = fields[0]["name"]

        for idx, row_vals in enumerate(rows):
            raw: Dict = {}
            coords: Dict = {}

            for i, fld in enumerate(fields):
                if i >= len(row_vals):
                    break
                cast = _cast_votable(row_vals[i], fld["datatype"])
                raw[fld["name"]] = cast
                # Map known UCDs to standard coordinate names
                coord_key = _UCD_TO_COORD.get(fld["ucd"].split(";")[0])
                if coord_key and cast is not None:
                    if isinstance(cast, (int, float)):
                        coords[coord_key] = float(cast)

            val = raw.get(val_col)
            if val is None:
                try:
                    val = next(v for v in raw.values()
                               if isinstance(v, float))
                except StopIteration:
                    val = 0.0

            yield {
                "_adapter": "votable",
                "_source":   path,
                "_row_idx":  idx,
                "value":     float(val) if isinstance(val, (int, float)) else 0.0,
                "raw":       raw,
                **coords,
            }


ADAPTER_CLASS = VOTableAdapter
