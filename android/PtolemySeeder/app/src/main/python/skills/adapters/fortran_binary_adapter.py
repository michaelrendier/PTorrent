"""
skills/adapters/fortran_binary_adapter.py — Fortran unformatted binary adapter.
Pure Python. struct module only.

Handles:
  mode: fortran_binary   Fortran WRITE(*) sequential unformatted files

Fortran unformatted records are wrapped in record markers:
  [4-byte marker: record_length_bytes][data][4-byte marker: record_length_bytes]

source fields:
  file              str         path to binary file
  endian            str         "little" | "big" (default "big")
  marker_bytes      int         record marker size: 4 or 8 (default 4)
  record_structure  list[dict]  field definitions:
    name   str   field name
    type   str   "int32" | "int64" | "float32" | "float64" | "char"
    count  int   number of elements (default 1)
  value_field       str         which field is primary value
  skip_records      int         number of header records to skip (default 0)
"""

from __future__ import annotations
import struct
import os
from typing import Iterator, Optional, List, Dict, Any

from skills.adapters import DataAdapter, Row


_TYPE_FMT = {
    "int32":   ("i", 4),
    "int64":   ("q", 8),
    "float32": ("f", 4),
    "float64": ("d", 8),
    "int16":   ("h", 2),
    "uint8":   ("B", 1),
}


def _endian_char(endian: str) -> str:
    return ">" if endian == "big" else "<"


def _read_record(f, endian: str, marker_bytes: int) -> bytes:
    """Read one Fortran record. Returns raw bytes of the record body."""
    ec = _endian_char(endian)
    marker_fmt = ec + ("I" if marker_bytes == 4 else "Q")
    marker_raw = f.read(marker_bytes)
    if len(marker_raw) < marker_bytes:
        return b""
    (length,) = struct.unpack(marker_fmt, marker_raw)
    data = f.read(length)
    f.read(marker_bytes)  # trailing marker
    return data


def _decode_record(data: bytes, structure: List[dict],
                   endian: str) -> Dict[str, Any]:
    ec = _endian_char(endian)
    result: Dict[str, Any] = {}
    offset = 0

    for field in structure:
        name   = field["name"]
        ftype  = field.get("type", "float32")
        count  = int(field.get("count", 1))

        if ftype == "char":
            byte_count = count
            raw = data[offset: offset + byte_count]
            result[name] = raw.decode("ascii", errors="replace").rstrip()
            offset += byte_count
        else:
            fmt_char, nbytes = _TYPE_FMT.get(ftype, ("f", 4))
            total_bytes = nbytes * count
            if offset + total_bytes > len(data):
                break
            vals = struct.unpack_from(ec + str(count) + fmt_char, data, offset)
            result[name] = vals[0] if count == 1 else list(vals)
            offset += total_bytes

    return result


class FortranBinaryAdapter(DataAdapter):
    NAME = "fortran_binary"

    def probe(self, source: dict) -> dict:
        path = source.get("file", "")
        dm: dict = {
            "native_format": "Fortran unformatted binary",
            "access": {"mode": "fortran_binary"},
            "file": path,
        }
        if not os.path.exists(path):
            dm["error"] = f"File not found: {path}"
            dm["confidence"] = 0.0
            return dm

        structure = source.get("record_structure", [])
        if not structure:
            dm["warning"] = (
                "No record_structure provided. "
                "Cannot auto-detect Fortran binary format — "
                "provide 'record_structure' in the .ptorrent source block."
            )
            dm["confidence"] = 0.30
        else:
            dm["fields"]     = [f["name"] for f in structure]
            dm["confidence"] = 0.85
            dm["type"]       = "simulation_snapshot"

        dm["file_size_bytes"] = os.path.getsize(path)
        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        path      = source.get("file", "")
        endian    = source.get("endian", "big")
        m_bytes   = int(source.get("marker_bytes", 4))
        structure = source.get("record_structure", [])
        val_field = source.get("value_field",
                               structure[0]["name"] if structure else None)
        skip      = int(source.get("skip_records", 0))

        if not structure:
            raise ValueError(
                "fortran_binary adapter requires 'record_structure' — "
                "a list of {name, type, count} dicts describing each field."
            )

        with open(path, "rb") as f:
            # Skip header records
            for _ in range(skip):
                _read_record(f, endian, m_bytes)

            idx = 0
            while True:
                raw_bytes = _read_record(f, endian, m_bytes)
                if not raw_bytes:
                    break

                decoded = _decode_record(raw_bytes, structure, endian)

                val = decoded.get(val_field, 0.0)
                if isinstance(val, list):
                    val = sum(v**2 for v in val) ** 0.5

                coords: dict = {}
                # Common Fortran simulation conventions
                pos = decoded.get("pos") or decoded.get("Pos") or decoded.get("x")
                if isinstance(pos, list) and len(pos) >= 3:
                    coords = {"coord_x": float(pos[0]),
                              "coord_y": float(pos[1]),
                              "coord_z": float(pos[2])}

                yield {
                    "_adapter": "fortran_binary",
                    "_source":   path,
                    "_row_idx":  idx,
                    "value":     float(val) if isinstance(val, (int, float)) else 0.0,
                    "raw":       {k: (v if not isinstance(v, list) else v[:4])
                                  for k, v in decoded.items()},
                    **coords,
                }
                idx += 1


ADAPTER_CLASS = FortranBinaryAdapter
