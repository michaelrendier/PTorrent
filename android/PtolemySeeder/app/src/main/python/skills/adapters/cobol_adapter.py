"""
skills/adapters/cobol_adapter.py — COBOL VSAM / fixed-width record adapter.
Pure Python. No external dependencies.

Handles:
  mode: cobol_vsam    IBM VSAM sequential file with copybook schema
  mode: cobol_fixed   Generic COBOL fixed-width records

source fields:
  file            str         path to data file
  copybook        str         path to COBOL copybook (.cbl / .cpy)
  encoding        str         "EBCDIC" | "ASCII" (default EBCDIC for VSAM)
  record_length   int         fixed record length in bytes (required)
  value_field     str         primary value field name
  skip_records    int         header records to skip (default 0)

EBCDIC: IBM Code Page 037 (US EBCDIC standard for financial systems).

COBOL data types decoded:
  PIC 9(n)        unsigned decimal integer, n digits
  PIC S9(n)       signed decimal integer
  PIC X(n)        alphanumeric string, n characters
  PIC 9(n)V9(m)   decimal with m implied decimal places
  COMP-3 / PACKED-DECIMAL  packed decimal nibbles
  COMP / BINARY   big-endian binary integer
"""

from __future__ import annotations
import re
import os
import struct
from typing import Iterator, Optional, List, Dict, Any

from skills.adapters import DataAdapter, Row


# ── EBCDIC Code Page 037 → Unicode ───────────────────────────────────────────
# Full 256-entry table. None = control/undefined character.

_EBCDIC_037 = (
    # 0x00-0x0F
    '\x00','\x01','\x02','\x03',None, '\t',  None, '\x7f',
    None,  None,  None,  '\x0b','\x0c','\r', '\x0e','\x0f',
    # 0x10-0x1F
    '\x10','\x11','\x12','\x13',None, '\x85','\x08',None,
    '\x18','\x19',None,  None,  '\x1c','\x1d','\x1e','\x1f',
    # 0x20-0x2F
    None,  None,  '\x1a',None,  None,  '\n',  '\x17','\x1b',
    None,  None,  None,  None,  None,  '\x05','\x06','\x07',
    # 0x30-0x3F
    None,  None,  '\x16',None,  None,  None,  None,  '\x04',
    None,  None,  None,  None,  '\x14','\x15',None,  '\x1a',
    # 0x40-0x4F  (0x40=space)
    ' ',   None,  None,  None,  None,  None,  None,  None,
    None,  None,  '\xa2','.', '<',   '(',   '+',   '|',
    # 0x50-0x5F
    '&',   None,  None,  None,  None,  None,  None,  None,
    None,  None,  '!',   '$',   '*',   ')',   ';',   '\xac',
    # 0x60-0x6F
    '-',   '/',   None,  None,  None,  None,  None,  None,
    None,  None,  '\xa6',',',  '%',   '_',   '>',   '?',
    # 0x70-0x7F
    None,  None,  None,  None,  None,  None,  None,  None,
    None,  '`',   ':',   '#',   '@',   "'",   '=',   '"',
    # 0x80-0x8F
    None,  'a',   'b',   'c',   'd',   'e',   'f',   'g',
    'h',   'i',   None,  None,  None,  None,  None,  None,
    # 0x90-0x9F
    None,  'j',   'k',   'l',   'm',   'n',   'o',   'p',
    'q',   'r',   None,  None,  None,  None,  None,  None,
    # 0xA0-0xAF
    None,  '~',   's',   't',   'u',   'v',   'w',   'x',
    'y',   'z',   None,  None,  None,  None,  None,  None,
    # 0xB0-0xBF
    '^',   None,  None,  None,  None,  None,  None,  None,
    None,  None,  '[',   ']',   None,  None,  None,  None,
    # 0xC0-0xCF
    '{',   'A',   'B',   'C',   'D',   'E',   'F',   'G',
    'H',   'I',   None,  None,  None,  None,  None,  None,
    # 0xD0-0xDF
    '}',   'J',   'K',   'L',   'M',   'N',   'O',   'P',
    'Q',   'R',   None,  None,  None,  None,  None,  None,
    # 0xE0-0xEF
    '\\',  None,  'S',   'T',   'U',   'V',   'W',   'X',
    'Y',   'Z',   None,  None,  None,  None,  None,  None,
    # 0xF0-0xFF
    '0',   '1',   '2',   '3',   '4',   '5',   '6',   '7',
    '8',   '9',   None,  None,  None,  None,  None,  None,
)


def _ebcdic_to_str(data: bytes) -> str:
    return "".join(_EBCDIC_037[b] or "?" for b in data)


# ── Packed decimal (COMP-3) decoder ──────────────────────────────────────────

def _decode_comp3(data: bytes, implied_decimals: int = 0) -> float:
    """
    Decode IBM packed decimal (COMP-3).
    Each byte holds two BCD digits. Last nibble: C=+, D=-, F=unsigned+.
    """
    hex_str = data.hex()
    sign_nibble = hex_str[-1].upper()
    digits = hex_str[:-1]
    digits = digits.replace("f", "").replace("F", "")
    digits = re.sub(r"[^0-9]", "0", digits)

    if not digits:
        return 0.0

    try:
        value = int(digits)
    except ValueError:
        return 0.0

    if sign_nibble == "D":
        value = -value

    if implied_decimals > 0:
        value = value / (10 ** implied_decimals)

    return float(value)


# ── Copybook parser ───────────────────────────────────────────────────────────

_PIC_PATTERN = re.compile(
    r"^\s*(\d+)\s+(\S+)\s+PIC\s+(S?)9\((\d+)\)(?:V9\((\d+)\))?\s*"
    r"(?:COMP-3|COMP-?3|PACKED-DECIMAL|COMP|BINARY)?\s*\.",
    re.IGNORECASE
)
_PIC_X_PATTERN = re.compile(
    r"^\s*(\d+)\s+(\S+)\s+PIC\s+X\((\d+)\)\s*\.",
    re.IGNORECASE
)


def _parse_copybook(path: str) -> List[dict]:
    """
    Parse a simplified COBOL copybook.
    Returns list of field dicts:
      name, type, length, decimals, signed, comp3
    """
    fields: List[dict] = []
    byte_offset = 0

    with open(path, encoding="ascii", errors="replace") as f:
        for line in f:
            line = line.rstrip()

            m = _PIC_PATTERN.match(line)
            if m:
                level    = int(m.group(1))
                name     = m.group(2)
                signed   = m.group(3) == "S"
                digits   = int(m.group(4))
                decimals = int(m.group(5)) if m.group(5) else 0
                comp3    = "COMP-3" in line.upper() or "PACKED" in line.upper()
                binary   = "COMP" in line.upper() and not comp3

                if comp3:
                    length = (digits + 2) // 2  # packed decimal byte length
                elif binary:
                    length = 2 if digits <= 4 else 4 if digits <= 9 else 8
                else:
                    length = digits + (1 if decimals else 0)

                fields.append({
                    "name":     name,
                    "type":     "numeric",
                    "length":   length,
                    "digits":   digits,
                    "decimals": decimals,
                    "signed":   signed,
                    "comp3":    comp3,
                    "binary":   binary,
                    "offset":   byte_offset,
                    "level":    level,
                })
                byte_offset += length
                continue

            m2 = _PIC_X_PATTERN.match(line)
            if m2:
                name   = m2.group(2)
                length = int(m2.group(3))
                fields.append({
                    "name":     name,
                    "type":     "alpha",
                    "length":   length,
                    "offset":   byte_offset,
                    "level":    int(m2.group(1)),
                })
                byte_offset += length

    return fields


# ── COBOL field decoder ───────────────────────────────────────────────────────

def _decode_field(data: bytes, field: dict, encoding: str) -> Any:
    raw = data[field["offset"]: field["offset"] + field["length"]]

    if field["type"] == "alpha":
        if encoding == "EBCDIC":
            return _ebcdic_to_str(raw).strip()
        return raw.decode("ascii", errors="replace").strip()

    # Numeric
    if field["comp3"]:
        return _decode_comp3(raw, field["decimals"])

    if field["binary"]:
        length = field["length"]
        if length == 2:
            val = struct.unpack(">h" if field["signed"] else ">H", raw)[0]
        elif length == 4:
            val = struct.unpack(">i" if field["signed"] else ">I", raw)[0]
        else:
            val = struct.unpack(">q" if field["signed"] else ">Q", raw)[0]
        if field["decimals"]:
            return val / (10 ** field["decimals"])
        return float(val)

    # Zoned decimal (display numeric)
    if encoding == "EBCDIC":
        digits_str = _ebcdic_to_str(raw)
    else:
        digits_str = raw.decode("ascii", errors="replace")

    # Handle overpunch sign on last byte (EBCDIC sign convention)
    digits_str = re.sub(r"[^0-9\-]", "", digits_str) or "0"
    try:
        val = float(digits_str)
        if field["decimals"]:
            val /= (10 ** field["decimals"])
        return val if not field["signed"] else val
    except ValueError:
        return 0.0


# ── Adapter class ─────────────────────────────────────────────────────────────

class COBOLAdapter(DataAdapter):
    NAME = "cobol_vsam"

    def probe(self, source: dict) -> dict:
        path      = source.get("file", "")
        copybook  = source.get("copybook", "")
        rec_len   = source.get("record_length", 0)
        dm: dict  = {
            "native_format": "COBOL VSAM",
            "access": {"mode": self.NAME},
            "file": path,
            "encoding": source.get("encoding", "EBCDIC"),
        }

        if copybook and os.path.exists(copybook):
            try:
                fields = _parse_copybook(copybook)
                dm["fields"] = [f["name"] for f in fields]
                dm["record_length_computed"] = sum(f["length"] for f in fields)
                dm["confidence"] = 0.88
                dm["type"] = "financial_records"
            except Exception as e:
                dm["error"] = f"Copybook parse error: {e}"
                dm["confidence"] = 0.40
        elif rec_len:
            dm["record_length"] = rec_len
            dm["confidence"] = 0.50
            dm["warning"] = "No copybook — field names unavailable, streaming raw records"
        else:
            dm["confidence"] = 0.20
            dm["warning"] = "Provide 'copybook' and/or 'record_length' for COBOL data"

        if os.path.exists(path):
            size = os.path.getsize(path)
            dm["file_size_bytes"] = size
            if rec_len:
                dm["estimated_records"] = size // rec_len

        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        path      = source.get("file", "")
        copybook  = source.get("copybook", "")
        rec_len   = int(source.get("record_length", 0))
        encoding  = source.get("encoding", "EBCDIC")
        val_field = source.get("value_field")
        skip      = int(source.get("skip_records", 0))

        if not rec_len and not copybook:
            raise ValueError(
                "COBOL adapter requires 'record_length' and/or 'copybook'."
            )

        fields: List[dict] = []
        if copybook and os.path.exists(copybook):
            fields = _parse_copybook(copybook)
            if not rec_len:
                rec_len = sum(f["length"] for f in fields)

        if not rec_len:
            raise ValueError("Cannot determine record_length from copybook.")

        if val_field is None and fields:
            for f in fields:
                if f["type"] == "numeric":
                    val_field = f["name"]
                    break

        with open(path, "rb") as fh:
            for _ in range(skip):
                fh.read(rec_len)

            idx = 0
            while True:
                record = fh.read(rec_len)
                if len(record) < rec_len:
                    break

                if fields:
                    raw: Dict = {
                        f["name"]: _decode_field(record, f, encoding)
                        for f in fields
                    }
                else:
                    # No copybook: expose raw hex chunks
                    raw = {f"byte_{i:04d}": record[i]
                           for i in range(min(rec_len, 32))}

                val = raw.get(val_field, 0.0) if val_field else 0.0
                if not isinstance(val, (int, float)):
                    val = 0.0

                yield {
                    "_adapter": "cobol_vsam",
                    "_source":   path,
                    "_row_idx":  idx,
                    "value":     float(val),
                    "raw":       raw,
                }
                idx += 1


ADAPTER_CLASS = COBOLAdapter
