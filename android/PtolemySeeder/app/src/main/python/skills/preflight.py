"""
skills/preflight.py — PTorrent pre-flight resource checker.

Run before any Data Transversal begins. Checks all resource requirements
declared in the .ptorrent 'resources' block against device/system state.

On Android: called by SeedService via the Chaquopy bridge (or MCP socket).
On desktop: called directly by seed_runner before starting a job.

Returns a PreFlightResult with passed=True/False and a list of failures.
Each failure is a dict with: field, required, available, message.

The PreFlightCheck is foundational to the Data Transversal algorithm:
  No preflight pass → no traversal starts.
  Full stop.
"""

from __future__ import annotations
import os
import sys
import time
import shutil
import platform
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class PreFlightFailure:
    field:     str
    required:  Any
    available: Any
    message:   str


@dataclass
class PreFlightResult:
    passed:   bool
    failures: List[PreFlightFailure] = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "PRE-FLIGHT PASSED"
        lines = ["PRE-FLIGHT FAILED:"]
        for f in self.failures:
            lines.append(f"  [{f.field}] {f.message}")
        return "\n".join(lines)


# ── System state probes ───────────────────────────────────────────────────────

def _free_storage_gb(path: str = ".") -> float:
    try:
        st = shutil.disk_usage(path)
        return st.free / 1e9
    except Exception:
        return 999.0  # unknown → don't block


def _available_ram_gb() -> float:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    return kb / 1e6
    except Exception:
        pass
    try:
        import resource
        soft, _ = resource.getrlimit(resource.RLIMIT_AS)
        if soft > 0:
            return soft / 1e9
    except Exception:
        pass
    return 4.0  # unknown → assume 4 GB


def _cpu_temp_celsius() -> float:
    """Read CPU temperature from sysfs (Linux / Android)."""
    # Android thermal zone paths
    candidates = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
        "/sys/class/thermal/thermal_zone2/temp",
        "/proc/cpu_temp",
    ]
    for path in candidates:
        try:
            with open(path) as f:
                raw = int(f.read().strip())
                # Android reports millidegrees
                return raw / 1000.0 if raw > 1000 else float(raw)
        except Exception:
            continue
    return 35.0  # unknown → assume safe


def _battery_pct() -> int:
    """Read battery percentage (Android sysfs)."""
    paths = [
        "/sys/class/power_supply/battery/capacity",
        "/sys/class/power_supply/BAT0/capacity",
        "/sys/class/power_supply/BAT1/capacity",
    ]
    for path in paths:
        try:
            with open(path) as f:
                return int(f.read().strip())
        except Exception:
            continue
    return 100  # unknown → don't block


def _is_charging() -> bool:
    """Check if device is on AC/USB power (Android sysfs)."""
    paths = [
        "/sys/class/power_supply/battery/status",
        "/sys/class/power_supply/BAT0/status",
    ]
    for path in paths:
        try:
            with open(path) as f:
                status = f.read().strip().lower()
                return status in ("charging", "full", "not charging")
        except Exception:
            continue
    return True  # unknown → don't block


def _on_wifi() -> bool:
    """Best-effort WiFi detection. Android-specific."""
    # Check if a /sys wifi power node exists (rough indicator)
    wifi_paths = [
        "/sys/class/net/wlan0/operstate",
        "/sys/class/net/wlan1/operstate",
    ]
    for path in wifi_paths:
        try:
            with open(path) as f:
                return f.read().strip() == "up"
        except Exception:
            continue
    return True  # unknown → don't block


# ── Security classification check ────────────────────────────────────────────

def _check_security(ptorrent: dict) -> Optional[PreFlightFailure]:
    """
    Verify security preconditions before accessing a classified dataset.
    Returns a failure if the security block requires conditions not yet met.
    """
    sec = ptorrent.get("security", {})
    if not sec:
        return None

    level = sec.get("level", 0)
    embargo_until = sec.get("embargo_until", "")

    if embargo_until:
        today = time.strftime("%Y-%m-%d")
        if today < embargo_until:
            return PreFlightFailure(
                field="security.embargo_until",
                required=f"date >= {embargo_until}",
                available=today,
                message=(
                    f"Dataset is under embargo until {embargo_until}. "
                    f"Today is {today}. Seeding is blocked."
                ),
            )

    if level >= 2 and not sec.get("acknowledge_required", False):
        # Level 2+ requires acknowledgment — if not yet recorded, block
        # (Android: SeedService handles acknowledgment UI before calling preflight)
        pass  # acknowledgment enforced at APK layer

    return None


# ── Main preflight check ──────────────────────────────────────────────────────

def check(ptorrent: dict, out_dir: str = ".") -> PreFlightResult:
    """
    Run all pre-flight checks for a .ptorrent job.

    :param ptorrent: Parsed .ptorrent dict.
    :param out_dir:  Output directory (for storage check).
    :returns: PreFlightResult — inspect .passed and .failures.
    """
    resources: dict = ptorrent.get("resources", {})
    failures: List[PreFlightFailure] = []

    # ── Storage ───────────────────────────────────────────────────────────────
    min_storage = float(resources.get("min_free_storage_gb", 0))
    storage_job = float(resources.get("storage_gb", 0))
    required_gb = max(min_storage, storage_job * 1.2)  # 20% headroom

    if required_gb > 0:
        free_gb = _free_storage_gb(out_dir)
        if free_gb < required_gb:
            failures.append(PreFlightFailure(
                field="storage",
                required=f"{required_gb:.1f} GB",
                available=f"{free_gb:.1f} GB",
                message=(
                    f"Insufficient storage: {free_gb:.1f} GB free, "
                    f"{required_gb:.1f} GB required "
                    f"(job: {storage_job:.1f} GB + 20% headroom)"
                ),
            ))

    # ── RAM ───────────────────────────────────────────────────────────────────
    min_ram = float(resources.get("min_ram_gb", 0))
    if min_ram > 0:
        avail_ram = _available_ram_gb()
        if avail_ram < min_ram:
            failures.append(PreFlightFailure(
                field="ram",
                required=f"{min_ram:.1f} GB",
                available=f"{avail_ram:.1f} GB",
                message=(
                    f"Insufficient RAM: {avail_ram:.1f} GB available, "
                    f"{min_ram:.1f} GB required. "
                    "Close other apps before seeding."
                ),
            ))

    # ── CPU temperature ───────────────────────────────────────────────────────
    temp = _cpu_temp_celsius()
    if temp > 45.0:
        failures.append(PreFlightFailure(
            field="temperature",
            required="<= 45°C",
            available=f"{temp:.1f}°C",
            message=(
                f"Device too hot ({temp:.1f}°C). "
                "Let device cool before starting a long evaluation."
            ),
        ))

    # ── Charging requirement ──────────────────────────────────────────────────
    if resources.get("requires_charging", False):
        if not _is_charging():
            battery = _battery_pct()
            failures.append(PreFlightFailure(
                field="charging",
                required="charging",
                available=f"battery {battery}%",
                message=(
                    f"This job requires the device to be charging. "
                    f"Current battery: {battery}%. Plug in before starting."
                ),
            ))

    # ── Battery floor (always enforce) ───────────────────────────────────────
    battery = _battery_pct()
    if battery < 15 and not _is_charging():
        failures.append(PreFlightFailure(
            field="battery",
            required=">= 15%",
            available=f"{battery}%",
            message=(
                f"Battery too low ({battery}%) and not charging. "
                "Plug in to protect against mid-job shutdown and checkpoint corruption."
            ),
        ))

    # ── WiFi requirement ──────────────────────────────────────────────────────
    if resources.get("requires_wifi", False):
        if not _on_wifi():
            failures.append(PreFlightFailure(
                field="wifi",
                required="WiFi connected",
                available="not detected",
                message=(
                    "This job transfers large data and requires WiFi. "
                    "Connect to WiFi before starting."
                ),
            ))

    # ── Security / embargo ────────────────────────────────────────────────────
    sec_failure = _check_security(ptorrent)
    if sec_failure:
        failures.append(sec_failure)

    # ── Output directory writable ─────────────────────────────────────────────
    if not os.access(out_dir, os.W_OK):
        failures.append(PreFlightFailure(
            field="output_dir",
            required=f"writable: {out_dir}",
            available="not writable",
            message=f"Output directory is not writable: {out_dir}",
        ))

    return PreFlightResult(passed=len(failures) == 0, failures=failures)


# ── Thermal monitor (continuous) ─────────────────────────────────────────────

class ThermalMonitor:
    """
    Continuously monitors CPU temperature during a running job.
    Call check() at regular intervals from the seeding loop.
    """
    PAUSE_TEMP  = 48.0  # pause seeding above this
    RESUME_TEMP = 40.0  # resume seeding below this
    WARN_TEMP   = 44.0  # log warning above this

    def __init__(self):
        self._paused_for_temp = False

    def check(self) -> tuple[str, float]:
        """
        Returns (action, temp_celsius).
        action: "ok" | "warn" | "pause" | "resume"
        """
        temp = _cpu_temp_celsius()
        if temp > self.PAUSE_TEMP:
            self._paused_for_temp = True
            return "pause", temp
        if temp < self.RESUME_TEMP and self._paused_for_temp:
            self._paused_for_temp = False
            return "resume", temp
        if temp > self.WARN_TEMP:
            return "warn", temp
        return "ok", temp
