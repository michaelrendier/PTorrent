"""
skills/adapters/mrt_adapter.py — AAS Machine-Readable Table adapter.
Pure Python. No external dependencies.

Handles:
  mode: mrt    AAS MRT fixed-width tables (SPARC, most journal data tables)

MRT format:
  Lines starting with '---' are separators.
  Lines starting with ' ' in the header define columns:
    bytes start-end  format  unit  label  explanation
  Data lines are fixed-width per the column byte ranges.

Works for SPARC_Lelli2016c.mrt and all standard AAS MRT files.
"""

from __future__ import annotations
import re
import urllib.request
from typing import Iterator, Optional, List, Tuple

from skills.adapters import DataAdapter, Row


_COL_PATTERN = re.compile(
    r"^\s+(\d+)-\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(.*)?$"
)
_SINGLE_COL = re.compile(
    r"^\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(.*)?$"
)


def _fetch(path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        with urllib.request.urlopen(path_or_url, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    with open(path_or_url, encoding="utf-8", errors="replace") as f:
        return f.read()


def _parse_mrt(text: str) -> Tuple[List[dict], List[str]]:
    """Parse MRT header → list of column defs, and data lines."""
    columns: List[dict] = []
    data_lines: List[str] = []
    in_header = True
    separator_count = 0

    for line in text.splitlines():
        if in_header:
            if line.startswith("---"):
                separator_count += 1
                if separator_count == 3:
                    in_header = False
                continue
            m = _COL_PATTERN.match(line)
            if m:
                col = {
                    "start":  int(m.group(1)) - 1,  # 0-indexed
                    "end":    int(m.group(2)),
                    "format": m.group(3),
                    "unit":   m.group(4),
                    "label":  m.group(5),
                    "desc":   m.group(6).strip(),
                }
                columns.append(col)
                continue
            m2 = _SINGLE_COL.match(line)
            if m2:
                pos = int(m2.group(1)) - 1
                col = {
                    "start": pos,
                    "end":   pos + 1,
                    "format": m2.group(2),
                    "unit":   m2.group(3),
                    "label":  m2.group(4),
                    "desc":   m2.group(5).strip() if m2.group(5) else "",
                }
                columns.append(col)
        else:
            if line.strip() and not line.startswith("---"):
                data_lines.append(line)

    return columns, data_lines


def _cast(val: str, fmt: str):
    val = val.strip()
    if not val or val in ("---", "...", ""):
        return None
    if fmt.startswith("F") or fmt.startswith("E") or fmt.startswith("f"):
        try:
            return float(val)
        except ValueError:
            return None
    if fmt.startswith("I") or fmt.startswith("i"):
        try:
            return int(val)
        except ValueError:
            return None
    return val


class MRTAdapter(DataAdapter):
    NAME = "mrt"

    def probe(self, source: dict) -> dict:
        path = source.get("file") or source.get("url", "")
        dm: dict = {
            "native_format": "MRT",
            "access": {"mode": "mrt"},
            "file": path,
        }
        try:
            text = _fetch(path)
            cols, data_lines = _parse_mrt(text)
            dm["columns"] = [c["label"] for c in cols]
            dm["units"] = {c["label"]: c["unit"] for c in cols}
            dm["n_rows"] = len(data_lines)
            dm["confidence"] = 0.92
            dm["type"] = "catalog"
            dm["dimensions"] = [c["label"] for c in cols]
        except Exception as e:
            dm["error"] = str(e)
            dm["confidence"] = 0.0
        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        path = source.get("file") or source.get("url", "")
        val_col = source.get("value_col")

        text = _fetch(path)
        columns, data_lines = _parse_mrt(text)

        if not columns:
            raise ValueError(f"MRT adapter: no columns parsed from {path}")

        # Auto-select value column: first float column
        if val_col is None:
            for c in columns:
                if c["format"].startswith(("F", "E", "f", "e")):
                    val_col = c["label"]
                    break
            if val_col is None:
                val_col = columns[0]["label"]

        for idx, line in enumerate(data_lines):
            raw: dict = {}
            for col in columns:
                raw_str = line[col["start"]:col["end"]]
                raw[col["label"]] = _cast(raw_str, col["format"])

            val = raw.get(val_col)
            if val is None:
                try:
                    val = next(v for v in raw.values()
                               if isinstance(v, float))
                except StopIteration:
                    val = 0.0

            # SPARC-specific coordinate mapping
            coords: dict = {}
            if "r_kpc" in raw or "R_kpc" in raw:
                r = raw.get("r_kpc") or raw.get("R_kpc") or 0.0
                coords["coord_r_kpc"] = float(r) if r else 0.0
            if "Vobs" in raw or "V_obs" in raw:
                vobs = raw.get("Vobs") or raw.get("V_obs")
                if vobs:
                    coords["coord_vobs"] = float(vobs)
            if "Vbar" in raw or "V_bar" in raw:
                vbar = raw.get("Vbar") or raw.get("V_bar")
                if vbar:
                    coords["coord_vbar"] = float(vbar)

            yield {
                "_adapter": "mrt",
                "_source":   path,
                "_row_idx":  idx,
                "value":     float(val) if isinstance(val, (int, float)) else 0.0,
                "raw":       raw,
                **coords,
            }


ADAPTER_CLASS = MRTAdapter
