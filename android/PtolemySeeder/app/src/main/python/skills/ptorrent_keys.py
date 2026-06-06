"""
skills/ptorrent_keys.py — User API key store (Android Keystore bridge).

On Android (Chaquopy): reads via KeyManager JNI bridge.
On desktop/CI: falls back to os.environ with PTOL_ prefix.

Usage:
    from skills.ptorrent_keys import keys
    api_key = keys.get('nist_nvd')   # works on Android and desktop
    if keys.is_set('anthropic'):
        ...
"""

import os

_SLOTS = {
    'anthropic': 'ANTHROPIC_API_KEY',
    'openai':    'OPENAI_API_KEY',
    'nist_nvd':  'PTOL_NIST_API_KEY',
    'github':    'GITHUB_TOKEN',
    'smtp_pass': 'PTOL_SMTP_PASS',
}


class KeyStore:
    """Unified key store — Android Keystore on device, os.environ on desktop."""

    def get(self, slot: str) -> 'str | None':
        try:
            from jnius import autoclass
            km = autoclass('com.ptolemy.seeder.KeyManager')
            # getInstance requires a Context; on Chaquopy use PythonActivity
            ctx = autoclass('org.kivy.android.PythonActivity').mActivity
            val = km.getInstance(ctx).get(slot)
            return val if val else None
        except Exception:
            env_var = _SLOTS.get(slot, slot.upper())
            val = os.environ.get(env_var)
            return val if val else None

    def set(self, slot: str, value: str) -> None:
        try:
            from jnius import autoclass
            km = autoclass('com.ptolemy.seeder.KeyManager')
            ctx = autoclass('org.kivy.android.PythonActivity').mActivity
            km.getInstance(ctx).set(slot, value)
        except Exception:
            # Desktop: warn only — os.environ is read-only at runtime
            import warnings
            warnings.warn(
                f"ptorrent_keys.set('{slot}') has no effect on desktop — "
                f"set {_SLOTS.get(slot, slot.upper())} in your environment.",
                stacklevel=2
            )

    def is_set(self, slot: str) -> bool:
        return self.get(slot) is not None

    def list(self) -> list:
        """Returns slot names that are currently set."""
        try:
            from jnius import autoclass
            km = autoclass('com.ptolemy.seeder.KeyManager')
            ctx = autoclass('org.kivy.android.PythonActivity').mActivity
            return list(km.getInstance(ctx).list())
        except Exception:
            return [s for s in _SLOTS if os.environ.get(_SLOTS[s])]


# Singleton — import and use directly
keys = KeyStore()
