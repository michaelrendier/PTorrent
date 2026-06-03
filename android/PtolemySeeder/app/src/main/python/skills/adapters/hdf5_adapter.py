"""
skills/adapters/hdf5_adapter.py — HDF5 simulation snapshot adapter.

Handles:
  mode: hdf5_snapshot    EAGLE / IllustrisTNG / AREPO / GADGET snapshots
  mode: hdf5             generic HDF5 file

source fields:
  file        str         path to .hdf5 file
  groups      list[str]   HDF5 group paths to stream (e.g. ["PartType0"])
  fields      list[str]   dataset names within each group
  value_field str         which field is the primary value (default: first)

Requires h5py. Falls back to header-only probe if unavailable.
"""

from __future__ import annotations
import os
from typing import Iterator, Optional, List

from skills.adapters import DataAdapter, Row

try:
    import h5py as _h5
    _H5PY = True
except ImportError:
    _H5PY = False


class HDF5Adapter(DataAdapter):
    NAME = "hdf5_snapshot"

    def probe(self, source: dict) -> dict:
        path = source.get("file", "")
        dm: dict = {
            "native_format": "HDF5",
            "access": {"mode": self.NAME},
            "file": path,
        }

        if not _H5PY:
            dm["type"] = "unknown"
            dm["confidence"] = 0.0
            dm["error"] = "h5py not installed — cannot probe HDF5 structure"
            return dm

        try:
            with _h5.File(path, "r") as f:
                groups = list(f.keys())
                dm["groups"] = groups
                dm["confidence"] = 0.90

                # Detect GADGET / EAGLE / AREPO by group naming
                part_groups = [g for g in groups if g.startswith("PartType")]
                if part_groups:
                    dm["type"] = "simulation_snapshot"
                    dm["format_hint"] = "GADGET/EAGLE/AREPO"
                    # Read Header group if present
                    if "Header" in f:
                        hdr = dict(f["Header"].attrs)
                        dm["num_particles"] = {
                            k: int(v) for k, v in hdr.items()
                            if "NumPart" in k or "Npart" in k
                        }
                        dm["redshift"] = float(hdr.get("Redshift", hdr.get("Time", 0)))
                    dm["part_groups"] = part_groups
                    # List fields in first PartType
                    dm["available_fields"] = list(f[part_groups[0]].keys()) \
                        if part_groups else []
                else:
                    dm["type"] = "hdf5_generic"
                    dm["available_groups"] = groups

        except Exception as e:
            dm["type"] = "unknown"
            dm["confidence"] = 0.0
            dm["error"] = str(e)

        return dm

    def stream_rows(self, source: dict,
                    subset: Optional[dict] = None) -> Iterator[Row]:
        if not _H5PY:
            raise ImportError(
                "h5py is required for HDF5 adapter. "
                "Install: pip install h5py"
            )

        path    = source.get("file", "")
        groups  = source.get("groups", [])
        fields  = source.get("fields", [])
        val_fld = source.get("value_field", fields[0] if fields else None)

        with _h5.File(path, "r") as f:
            for group_name in groups:
                if group_name not in f:
                    continue
                group = f[group_name]
                avail = [fld for fld in fields if fld in group]
                if not avail:
                    avail = list(group.keys())[:8]  # probe first 8 fields

                # Load all requested arrays
                arrays: dict = {}
                n = 0
                for fld in avail:
                    try:
                        arr = group[fld][:]
                        arrays[fld] = arr
                        if n == 0:
                            n = len(arr) if hasattr(arr, "__len__") else 1
                    except Exception:
                        pass

                if n == 0:
                    continue

                primary = arrays.get(val_fld, arrays.get(avail[0]))

                for i in range(n):
                    raw = {}
                    for fld, arr in arrays.items():
                        try:
                            v = arr[i]
                            # Flatten small arrays (e.g. 3-component velocity)
                            if hasattr(v, "__len__"):
                                for j, vj in enumerate(v):
                                    raw[f"{fld}_{j}"] = float(vj)
                                raw[f"{fld}_mag"] = float(
                                    sum(float(vj)**2 for vj in v) ** 0.5
                                )
                            else:
                                raw[fld] = float(v)
                        except (TypeError, ValueError, IndexError):
                            pass

                    # Standard coordinate extraction
                    coords: dict = {}
                    if "Coordinates" in arrays:
                        c = arrays["Coordinates"][i]
                        coords = {"coord_x": float(c[0]),
                                  "coord_y": float(c[1]),
                                  "coord_z": float(c[2])}
                    elif "Velocities" in arrays:
                        v3 = arrays["Velocities"][i]
                        coords["coord_vx"] = float(v3[0])
                        coords["coord_vy"] = float(v3[1])
                        coords["coord_vz"] = float(v3[2])

                    val = float(primary[i]) if primary is not None else 0.0
                    if hasattr(val, "__len__"):
                        val = float(sum(v**2 for v in val) ** 0.5)

                    yield {
                        "_adapter": "hdf5",
                        "_source":   f"{path}::{group_name}",
                        "_row_idx":  i,
                        "value":     val,
                        "group":     group_name,
                        "raw":       raw,
                        **coords,
                    }


ADAPTER_CLASS = HDF5Adapter
