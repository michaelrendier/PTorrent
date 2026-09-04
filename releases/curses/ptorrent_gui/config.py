"""GUI configuration — every user-adjustable setting, persisted to
~/.config/ptorrent/gui.json. Distinct from wizard_profile.json (researcher
identity for .ptorrent auto-input); this file is how the *console* behaves.
"""
from __future__ import annotations

import copy
import json
import os

_DIR = os.path.expanduser(os.environ.get("PTOL_CONFIG_DIR", "~/.config/ptorrent"))
_PATH = os.path.join(_DIR, "gui.json")

DEFAULTS: dict = {
    "notifications": {
        "enabled": True,
        "channel": "bell",                 # bell | desktop | both | off
        "events": {
            "job_complete": True,
            "job_error": True,
            "embargo_lifted": True,
            "access_request": True,
            "grant_received": True,
            "vote_received": False,
            "phonebook_stale": False,
        },
    },
    # user-defined heartbeat / section alarms. Ships with the "still-alive ping"
    # the user described: a 12-day download dings once every 3 hours.
    "alarms": [
        {
            "name": "still-alive ping",
            "enabled": True,
            "when": "periodic_while_running",   # see alarms.WHEN
            "every": {"n": 3, "unit": "hours"},
            "threshold": {"n": 1, "unit": "hours"},
            "count": 5,
            "scope": "any_job",                # any_job | each_job
            "action": "bell",                  # bell | desktop | status
            "repeat": True,
        }
    ],
    "display": {
        "theme": "bios-blue",                  # bios-blue | mono
        "sidebar": "auto",                     # auto | always | never
        "tooltips_default": False,
        "confirm_on_quit": True,
        "unicode": "auto",                     # auto | on | off
    },
    "defaults": {
        "politeness_delay_s": 1.0,
        "user_agent": "Mozilla/5.0 (compatible; PtorrentBot/1.0; +https://github.com/michaelrendier/PTorrent)",
    },
    "paths": {
        "out_dir": ".",
        "engine_dir": "",
        "poll_interval_s": 1.0,
    },
}


def _merge(base: dict, over) -> dict:
    out = copy.deepcopy(base)
    if isinstance(over, dict):
        for k, v in over.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _merge(out[k], v)
            else:
                out[k] = v
    return out


def load() -> dict:
    try:
        with open(_PATH, encoding="utf-8") as f:
            return _merge(DEFAULTS, json.load(f))
    except Exception:  # noqa: BLE001
        return copy.deepcopy(DEFAULTS)


def save(cfg: dict) -> str:
    os.makedirs(_DIR, exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _PATH)
    try:
        os.chmod(_PATH, 0o600)
    except OSError:
        pass
    return _PATH


def path() -> str:
    return _PATH


def get(cfg: dict, dotted: str, default=None):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_(cfg: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    cur = cfg
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value
