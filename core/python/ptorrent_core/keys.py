"""Unified key store — Android Keystore on device, os.environ on desktop.

Adapted from android/PtolemySeeder/app/src/main/python/skills/ptorrent_keys.py
(Cody Michael Allison, LGPL-3.0-or-later).
"""
from __future__ import annotations

import os

_SLOTS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "nist_nvd": "PTOL_NIST_API_KEY",
    "github": "GITHUB_TOKEN",
    "smtp_pass": "PTOL_SMTP_PASS",
    "orcid_client": "PTOL_ORCID_CLIENT_ID",
    "orcid_secret": "PTOL_ORCID_CLIENT_SECRET",
    "virustotal": "PTOL_VIRUSTOTAL_KEY",
}


class KeyStore:
    def get(self, slot: str) -> str | None:
        try:  # Android / Chaquopy
            from jnius import autoclass  # type: ignore
            km = autoclass("com.ptolemy.seeder.KeyManager")
            ctx = autoclass("org.kivy.android.PythonActivity").mActivity
            val = km.getInstance(ctx).get(slot)
            return val or None
        except Exception:
            return os.environ.get(_SLOTS.get(slot, slot.upper())) or None

    def is_set(self, slot: str) -> bool:
        return self.get(slot) is not None

    def list(self) -> list[str]:
        return [s for s in _SLOTS if os.environ.get(_SLOTS[s])]


keys = KeyStore()
