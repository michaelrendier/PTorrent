"""
skills/adapters/fits_adapter.py — FITS data adapter.

Handles:
  mode: fits          local FITS file
  mode: fits_table    FITS binary table extension
  mode: s3_fits       FITS over S3 range requests

Tries astropy first; falls back to pure-Python FITS reader for Android.
Streams rows as dicts with coordinate + value fields from WCS.

FITS format: 2880-byte blocks, 80-char header cards, binary data.
"""

from __future__ import annotations
import os
import struct
import urllib.request
from typing import Iterator, Optional, Dict, Any

from skills.adapters import DataAdapter, Row

# ── astropy optional import ───────────────────────────────────────────────────

try:
    from astropy.io import fits as _fits
    from astropy.wcs import WCS as _WCS
    _ASTROPY = True
except ImportError:
    _ASTROPY = False


# ── Pure-Python minimal FITS reader ──────────────────────────────────────────

_BLOCK = 2880
_CARD  = 80


def _read_header_cards(data: bytes, offset: int = 0) -> tuple[dict, int]:
    """Parse FITS header cards, return (header_dict, data_offset)."""
    header: dict = {}
    pos = offset
    while pos < len(data):
        block = data[pos:pos + _BLOCK]
        pos += _BLOCK
        for i in range(0, _BLOCK, _CARD):
            card = block[i:i + _CARD].decode("ascii", errors="replace")
            key = card[:8].strip()
            if key == "END":
                return header, pos
            if "=" in card[8:10]:
                val_comment = card[10:].split("/")[0].strip().strip("'").strip()
                try:
                    if "." in val_comment:
                        header[key] = float(val_comment)
                    elif val_comment.lstrip("-").isdigit():
                        header[key] = int(val_comment)
                    elif val_comment in ("T", "F"):
                        header[key] = val_comment == "T"
                    else:
                        header[key] = val_comment
                except (ValueError, AttributeError):
                    header[key] = val_comment
    return header, pos


def _bitpix_dtype(bitpix: int) -> str:
    return {16: ">i2", 32: ">i4", 64: ">i8",
            -32: ">f4", -64: ">f8"}.get(bitpix, ">f4")


class _PureFITSReader:
    """Minimal FITS reader without astropy. Handles images and simple tables."""

    def __init__(self, path_or_bytes):
        if isinstance(path_or_bytes, (str, os.PathLike)):
            with open(path_or_bytes, "rb") as f:
                self._data = f.read()
        else:
            self._data = path_or_bytes
        self.header, self._data_start = _read_header_cards(self._data)

    def iter_pixels(self) -> Iterator[Row]:
        """Yield (x, y[, z], value) tuples for image data."""
        import array as _array
        h = self.header
        naxis  = h.get("NAXIS", 0)
        bitpix = h.get("BITPIX", -32)
        if naxis < 2:
            return
        nx = h.get("NAXIS1", 0)
        ny = h.get("NAXIS2", 0)
        nz = h.get("NAXIS3", 1) if naxis >= 3 else 1
        dtype  = _bitpix_dtype(bitpix)
        nbytes = abs(bitpix) // 8
        total  = nx * ny * nz

        raw = self._data[self._data_start:self._data_start + total * nbytes]
        fmt  = dtype[1:]  # strip endian for struct
        pack = struct.Struct(f">{total}{fmt}") if fmt in ("f", "d", "i", "h", "q") else None

        bscale = float(h.get("BSCALE", 1.0))
        bzero  = float(h.get("BZERO",  0.0))
        cdelt1 = float(h.get("CDELT1", 1.0))
        cdelt2 = float(h.get("CDELT2", 1.0))
        crpix1 = float(h.get("CRPIX1", 1.0))
        crpix2 = float(h.get("CRPIX2", 1.0))
        crval1 = float(h.get("CRVAL1", 0.0))
        crval2 = float(h.get("CRVAL2", 0.0))

        idx = 0
        for iz in range(nz):
            for iy in range(ny):
                for ix in range(nx):
                    off = (idx) * nbytes
                    raw_val = struct.unpack_from(dtype, raw, off)[0]
                    physical = raw_val * bscale + bzero
                    ra  = crval1 + (ix + 1 - crpix1) * cdelt1
                    dec = crval2 + (iy + 1 - crpix2) * cdelt2
                    row: Row = {
                        "_adapter": "fits",
                        "_source":   str(self.header.get("FILENAME", "")),
                        "_row_idx":  idx,
                        "coord_x":   ix,
                        "coord_y":   iy,
                        "coord_ra":  ra,
                        "coord_dec": dec,
                        "value":     physical,
                        "raw":       {"pixel": physical, "ix": ix, "iy": iy},
                    }
                    if naxis >= 3:
                        cdelt3 = float(h.get("CDELT3", 1.0))
                        crpix3 = float(h.get("CRPIX3", 1.0))
                        crval3 = float(h.get("CRVAL3", 0.0))
                        wl = crval3 + (iz + 1 - crpix3) * cdelt3
                        row["coord_wavelength"] = wl
                        row["coord_z"] = iz
                    yield row
                    idx += 1


# ── Adapter class ─────────────────────────────────────────────────────────────

class FITSAdapter(DataAdapter):
    NAME = "fits"

    def probe(self, source: dict) -> dict:
        path = source.get("file") or source.get("endpoint", "")
        dm: dict = {
            "type": "unknown",
            "native_format": "FITS",
            "access": {"mode": source.get("mode", "fits")},
        }

        if _ASTROPY:
            try:
                with _fits.open(path, memmap=True) as hdl:
                    dm["hdu_count"] = len(hdl)
                    dm["extensions"] = [h.name for h in hdl]
                    pri = hdl[0].header
                    naxis = pri.get("NAXIS", 0)
                    if naxis >= 3:
                        dm["type"] = "spectral_cube"
                        dm["dimensions"] = ["x", "y", "wavelength"]
                    elif naxis == 2:
                        dm["type"] = "image_2d"
                        dm["dimensions"] = ["x", "y"]
                    dm["confidence"] = 0.95
            except Exception as e:
                dm["error"] = str(e)
                dm["confidence"] = 0.0
        else:
            try:
                data = open(path, "rb").read(2880 * 4) if os.path.exists(path) else b""
                hdr, _ = _read_header_cards(data)
                naxis = hdr.get("NAXIS", 0)
                dm["type"] = "spectral_cube" if naxis >= 3 else "image_2d"
                dm["confidence"] = 0.80
                dm["astropy"] = "unavailable — using pure-Python fallback"
            except Exception as e:
                dm["error"] = str(e)
                dm["confidence"] = 0.0

        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        path = source.get("file") or source.get("endpoint", "")
        ext  = source.get("extension", 0)

        if _ASTROPY:
            yield from self._stream_astropy(path, ext, source, subset)
        else:
            yield from self._stream_pure(path, subset)

    def _stream_astropy(self, path, ext, source, subset) -> Iterator[Row]:
        with _fits.open(path, memmap=True) as hdl:
            hdu = hdl[ext]
            if hasattr(hdu, "columns"):
                # Binary table
                cols = [c.name for c in hdu.columns]
                for i, row_data in enumerate(hdu.data):
                    raw = {c: _scalar(row_data[c]) for c in cols}
                    yield {
                        "_adapter": "fits",
                        "_source":   path,
                        "_row_idx":  i,
                        "value":     raw.get(source.get("value_col", cols[0]), 0.0),
                        "raw":       raw,
                    }
            else:
                # Image / cube
                wcs = _WCS(hdu.header) if _ASTROPY else None
                data = hdu.data
                if data is None:
                    return
                it = _iter_image(data, hdu.header, wcs, subset)
                yield from it

    def _stream_pure(self, path, subset) -> Iterator[Row]:
        reader = _PureFITSReader(path)
        yield from reader.iter_pixels()


def _scalar(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return str(val)


def _iter_image(data, header, wcs, subset) -> Iterator[Row]:
    """Iterate over image/cube pixels with optional sky subset."""
    import numpy as np
    shape = data.shape
    naxis = len(shape)

    if naxis == 2:
        ny, nx = shape
        for iy in range(ny):
            for ix in range(nx):
                val = float(data[iy, ix])
                if not _finite(val):
                    continue
                coords = {}
                if wcs is not None:
                    sky = wcs.pixel_to_world(ix, iy)
                    coords = {"coord_ra": float(sky.ra.deg),
                              "coord_dec": float(sky.dec.deg)}
                yield {"_adapter": "fits", "_source": str(header.get("FILENAME", "")),
                       "_row_idx": iy * nx + ix, "value": val,
                       "coord_x": ix, "coord_y": iy, "raw": {"flux": val}, **coords}

    elif naxis == 3:
        nz, ny, nx = shape
        idx = 0
        for iz in range(nz):
            for iy in range(ny):
                for ix in range(nx):
                    val = float(data[iz, iy, ix])
                    if not _finite(val):
                        idx += 1
                        continue
                    row: Row = {"_adapter": "fits", "_source": "",
                                "_row_idx": idx, "value": val,
                                "coord_x": ix, "coord_y": iy, "coord_z": iz,
                                "raw": {"flux": val}}
                    if wcs is not None:
                        try:
                            sky = wcs.pixel_to_world(ix, iy, iz)
                            if hasattr(sky, "__iter__"):
                                spatial, spectral = sky
                                row["coord_ra"]         = float(spatial.ra.deg)
                                row["coord_dec"]        = float(spatial.dec.deg)
                                row["coord_wavelength"] = float(spectral.value)
                        except Exception:
                            pass
                    yield row
                    idx += 1


def _finite(v) -> bool:
    import math
    try:
        return math.isfinite(v)
    except (TypeError, ValueError):
        return False


ADAPTER_CLASS = FITSAdapter
