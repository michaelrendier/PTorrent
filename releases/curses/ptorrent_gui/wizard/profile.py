"""User-information persistence — the 'save for auto-input' half of Tab 4."""
from __future__ import annotations

import json
import os

_DIR = os.path.expanduser(os.environ.get("PTOL_CONFIG_DIR", "~/.config/ptorrent"))
_PATH = os.path.join(_DIR, "wizard_profile.json")

_KEYS = ("u_name", "u_orcid", "u_email", "u_affiliation", "u_ua", "u_delay",
         "u_smtp_host", "u_smtp_port", "u_smtp_user", "w_tooltip")


def load() -> dict:
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {k: data[k] for k in _KEYS if k in data}
    except Exception:  # noqa: BLE001
        return {}


def save(answers: dict) -> str:
    os.makedirs(_DIR, exist_ok=True)
    payload = {k: answers.get(k, "") for k in _KEYS}
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, _PATH)
    try:
        os.chmod(_PATH, 0o600)
    except OSError:
        pass
    return _PATH


def path() -> str:
    return _PATH
