"""Pre-flight resource + security gate.

Adapted from android/PtolemySeeder/app/src/main/python/skills/preflight.py
(Cody Michael Allison, LGPL-3.0-or-later). No pre-flight pass -> no job starts.
Added: label/marking sanity, embargo returns a distinct failure the engine
maps to E_EMBARGO.
"""
from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field

from . import labels as _labels


@dataclass
class Failure:
    field: str
    required: str
    available: str
    message: str
    fatal_embargo: bool = False


@dataclass
class Result:
    passed: bool
    failures: list = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "PRE-FLIGHT PASSED"
        return "PRE-FLIGHT FAILED:\n" + "\n".join(f"  [{f.field}] {f.message}" for f in self.failures)

    def to_dict(self) -> dict:
        return {"passed": self.passed,
                "failures": [f.__dict__ for f in self.failures],
                "embargo": any(f.fatal_embargo for f in self.failures)}


def _free_gb(path: str) -> float:
    try:
        return shutil.disk_usage(path).free / 1e9
    except Exception:
        return 999.0


def _avail_ram_gb() -> float:
    try:
        with open("/proc/meminfo") as f:
            for ln in f:
                if ln.startswith("MemAvailable:"):
                    return int(ln.split()[1]) / 1e6
    except Exception:
        pass
    return 4.0


def _cpu_temp_c() -> float:
    for p in ("/sys/class/thermal/thermal_zone0/temp",
              "/sys/class/thermal/thermal_zone1/temp"):
        try:
            raw = int(open(p).read().strip())
            return raw / 1000.0 if raw > 1000 else float(raw)
        except Exception:
            continue
    return 35.0


def _battery_pct() -> int:
    for p in ("/sys/class/power_supply/battery/capacity",
              "/sys/class/power_supply/BAT0/capacity"):
        try:
            return int(open(p).read().strip())
        except Exception:
            continue
    return 100


def _charging() -> bool:
    for p in ("/sys/class/power_supply/battery/status",
              "/sys/class/power_supply/BAT0/status"):
        try:
            return open(p).read().strip().lower() in ("charging", "full", "not charging")
        except Exception:
            continue
    return True


def check(pf, out_dir: str, today_iso: str | None = None) -> Result:
    today_iso = today_iso or time.strftime("%Y-%m-%d")
    res: dict = pf.resources or {}
    sec: dict = pf.security or {}
    fails: list[Failure] = []

    # storage
    min_store = float(res.get("min_free_storage_gb", 0))
    job_store = float(res.get("storage_gb", 0))
    need = max(min_store, job_store * 1.2)
    if need > 0:
        free = _free_gb(out_dir)
        if free < need:
            fails.append(Failure("storage", f"{need:.1f} GB", f"{free:.1f} GB",
                                 f"insufficient storage: {free:.1f} < {need:.1f} GB"))

    # ram
    min_ram = float(res.get("min_ram_gb", 0))
    if min_ram > 0:
        avail = _avail_ram_gb()
        if avail < min_ram:
            fails.append(Failure("ram", f"{min_ram:.1f} GB", f"{avail:.1f} GB",
                                 f"insufficient RAM: {avail:.1f} < {min_ram:.1f} GB"))

    # thermal
    temp = _cpu_temp_c()
    if temp > 45.0:
        fails.append(Failure("temperature", "<=45C", f"{temp:.1f}C",
                             f"device too hot ({temp:.1f}C)"))

    # power
    if res.get("requires_charging") and not _charging():
        fails.append(Failure("charging", "charging", f"battery {_battery_pct()}%",
                             "job requires the device to be charging"))
    if _battery_pct() < 15 and not _charging():
        fails.append(Failure("battery", ">=15%", f"{_battery_pct()}%",
                             "battery too low and not charging"))

    # embargo
    e = sec.get("embargo_until", "")
    if e and today_iso < e:
        fails.append(Failure("security.embargo_until", f">= {e}", today_iso,
                             f"dataset is under embargo until {e}", fatal_embargo=True))

    # label / marking sanity
    lvl = int(sec.get("level", 0))
    if lvl >= 1 and not sec.get("labels"):
        fails.append(Failure("security.labels", "present", "missing",
                             "security.level >= 1 requires a labels block"))
    if sec.get("labels"):
        probs = _labels.validate(sec["labels"])
        if probs:
            fails.append(Failure("security.labels", "valid", "invalid", "; ".join(probs)))

    # output dir writable
    if not os.access(out_dir, os.W_OK):
        fails.append(Failure("output_dir", f"writable {out_dir}", "not writable",
                             f"output directory not writable: {out_dir}"))

    return Result(passed=not fails, failures=fails)
