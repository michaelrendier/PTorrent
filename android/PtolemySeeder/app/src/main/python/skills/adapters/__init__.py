"""
skills/adapters — PTorrent data adapter registry.

Each adapter implements the DataAdapter interface:
    probe(source: dict) -> dict           returns data_model
    stream_rows(source, subset) -> Iterator[dict]
    can_handle(source: dict) -> bool

stream_rows() yields row dicts with guaranteed keys:
    _adapter   str   adapter name
    _source    str   source identifier
    _row_idx   int   row index
    raw        dict  complete original row
    value      float primary measurement (adapter fills what's available)
    coord_*    float coordinate fields named by dimension

Adapter selection: REGISTRY[source['mode']] or probe_auto(endpoint).
"""

from __future__ import annotations
from typing import Iterator, Dict, Any, Optional, Type

Row = Dict[str, Any]


class DataAdapter:
    NAME = "base"

    def probe(self, source: dict) -> dict:
        raise NotImplementedError

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        raise NotImplementedError

    @classmethod
    def can_handle(cls, source: dict) -> bool:
        return source.get("mode") == cls.NAME


def _lazy(module: str) -> "Type[DataAdapter]":
    """Return adapter class, importing its module on first call."""
    _cache: dict = {}
    if module not in _cache:
        import importlib
        mod = importlib.import_module(f"skills.adapters.{module}")
        _cache[module] = mod.ADAPTER_CLASS
    return _cache[module]


# mode string → adapter module name
_MODE_MAP: Dict[str, str] = {
    "fits":             "fits_adapter",
    "fits_table":       "fits_adapter",
    "hdf5_snapshot":    "hdf5_adapter",
    "hdf5":             "hdf5_adapter",
    "votable":          "votable_adapter",
    "tap_adql":         "tap_adapter",
    "mrt":              "mrt_adapter",
    "fortran_binary":   "fortran_binary_adapter",
    "cobol_vsam":       "cobol_adapter",
    "cobol_fixed":      "cobol_adapter",
    "github_repo":      "github_adapter",
    "github_dataset":   "github_adapter",
    "s3_fits":          "fits_adapter",
    "file_list":        None,   # handled by corpus.py
}


def get_adapter(source: dict) -> DataAdapter:
    mode = source.get("mode", "")
    module = _MODE_MAP.get(mode)
    if module is None:
        raise ValueError(
            f"No adapter for mode '{mode}'. "
            f"Available: {sorted(m for m in _MODE_MAP if _MODE_MAP[m])}"
        )
    import importlib
    mod = importlib.import_module(f"skills.adapters.{module}")
    return mod.ADAPTER_CLASS()


def probe_auto(endpoint: str) -> dict:
    """Stage 1-3 auto-probe: detect format from endpoint without a mode hint."""
    import urllib.request, urllib.error
    data_model: dict = {"endpoint": endpoint, "confidence": 0.0}

    try:
        req = urllib.request.Request(endpoint, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "")
            data_model["http_status"] = resp.status
            data_model["content_type"] = ct

            if "fits" in ct or endpoint.lower().endswith((".fits", ".fit")):
                data_model["mode"] = "fits"
                data_model["confidence"] = 0.90
            elif "hdf5" in ct or endpoint.lower().endswith((".hdf5", ".h5")):
                data_model["mode"] = "hdf5"
                data_model["confidence"] = 0.90
            elif "votable" in ct or "xml" in ct:
                data_model["mode"] = "votable"
                data_model["confidence"] = 0.75
            elif "json" in ct:
                data_model["mode"] = "tap_adql"
                data_model["confidence"] = 0.60
            else:
                data_model["mode"] = "unknown"
                data_model["confidence"] = 0.0

    except urllib.error.URLError as e:
        data_model["error"] = str(e)

    return data_model
