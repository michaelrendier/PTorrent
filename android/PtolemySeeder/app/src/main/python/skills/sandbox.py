"""
skills/sandbox.py — PTorrent execution sandbox.

HAL BOUNDARY POLICY
-------------------
PTorrent accesses hardware and OS services exclusively through Android's
Hardware Abstraction Layer (HAL) and official Android APIs (Kotlin/Java layer).
The Python engine NEVER touches hardware, auth, or credential paths directly.

This policy applies identically to future iOS and desktop ports:
  Android:  Android HAL → KeyStore → BiometricPrompt → EncryptedSharedPreferences
  iOS:      Secure Enclave → Keychain → LocalAuthentication framework
  Desktop:  libsecret / GNOME Keyring / Windows DPAPI / macOS Keychain

Direct-path access to auth/credential/hardware files is a lateral attack vector.
A phone plugged in with ADB enabled is an open port. Any code — malicious .ptorrent
or otherwise — that reads ADB keys, lock screen hashes, or pattern files can be
used for device compromise. The sandbox blocks this class of attack entirely.

Installed before any skill or evaluation code runs. Blocks:
  - subprocess, pty, tty, ctypes, cffi, mmap, signal, multiprocessing
  - writes outside the app storage boundary
  - reads from auth/credential/ADB paths (HAL boundary)
  - reads from kernel/hardware interfaces

Call install() once at process startup in seed_runner.py.
All violations raise PermissionError or ImportError with an explicit
message naming the blocked operation and the HAL policy. Violations are logged.

Design: allowlist for writes (only PTOL_OUT_DIR and app storage paths),
blocklist for module imports (no subprocess or native-code bridges),
blocklist for reads of HAL-boundary sensitive paths.
"""

from __future__ import annotations
import os
import builtins
import logging
import time

_log = logging.getLogger("ptorrent.sandbox")

_BLOCKED_IMPORT = frozenset({
    "subprocess", "pty", "tty",
    "ctypes", "cffi", "_ctypes",
    "multiprocessing",
    "signal",
    "mmap",
    "resource",
    "pwd", "grp",
    "termios", "tty",
    "fcntl",
})

_BLOCKED_WRITE_PREFIXES = (
    "/system",
    "/vendor",
    "/boot",
    "/vbmeta",
    "/proc/sys",
    "/dev/",
    "/etc/",
    "/sys/",
    "/apex",
    "/oem",
    "/odm",
)

_BLOCKED_READ_PREFIXES = (
    # Kernel / hardware interfaces — go through HAL
    "/proc/sys",
    "/sys/kernel",
    "/dev/mem",
    "/dev/kmem",

    # ── HAL BOUNDARY: auth / credential / ADB paths ──────────────────────
    # These are the paths a malicious .ptorrent or compromised skill could
    # read to extract ADB authorisation keys, lock screen hashes, or pattern
    # files for offline brute-forcing. Phone plugged in + ADB enabled = open
    # port. None of these are legitimate PTorrent operations.

    # ADB trust chain — adb_keys grants full device access over USB
    "/data/misc/adb/",
    "/data/misc/keystore/",

    # Lock screen credentials (PIN hash, pattern hash, gesture hash)
    "/data/system/password.key",
    "/data/system/pattern.key",
    "/data/system/gesture.key",
    "/data/system/locksettings.db",
    "/data/system/locksettings.db-wal",
    "/data/system/locksettings.db-shm",
    "/data/system/gatekeeper",

    # Android Keystore key material — HAL only, never direct
    "/data/misc/keystore/",
    "/data/misc/credstore/",

    # Other apps' private data — never ours to read
    "/data/data/",
    "/data/user/",
    "/data/user_de/",

    # Telephony / SIM credentials
    "/data/misc/radio/",
    "/efs/",                    # Samsung EFS partition (IMEI, SIM lock)

    # WiFi / network credentials
    "/data/misc/wifi/",
    "/data/misc/ethernet/",

    # Biometric templates — HAL only
    "/data/vendor/fpc/",
    "/data/vendor/goodix/",
    "/data/biometrics/",
)

# Populated at install() from environment
_ALLOWED_WRITE_ROOTS: list[str] = []

_ORIGINAL_OPEN    = builtins.open
_ORIGINAL_IMPORT  = builtins.__import__
_INSTALLED        = False


def _safe_open(file, mode="r", *args, **kwargs):
    path = os.path.abspath(str(file)) if str(file).startswith("/") else str(file)

    writing = any(c in mode for c in ("w", "a", "x", "+"))
    reading = not writing or "r" in mode

    if writing:
        if any(path.startswith(p) for p in _BLOCKED_WRITE_PREFIXES):
            _log.error("SANDBOX BLOCK write: %s", path)
            raise PermissionError(
                f"PTorrent sandbox: write to protected path blocked: {path}\n"
                "System partitions are read-only to PTorrent.\n"
                "If a .ptorrent file triggered this, report the file's "
                "ANNOUNCE ORCID on the chain immediately."
            )
        if _ALLOWED_WRITE_ROOTS:
            if not any(path.startswith(r) for r in _ALLOWED_WRITE_ROOTS):
                _log.error("SANDBOX BLOCK write outside allowed roots: %s", path)
                raise PermissionError(
                    f"PTorrent sandbox: write outside app storage blocked: {path}\n"
                    f"Allowed write roots: {_ALLOWED_WRITE_ROOTS}"
                )

    if reading:
        if any(path.startswith(p) for p in _BLOCKED_READ_PREFIXES):
            _log.error("SANDBOX HAL BLOCK read: %s", path)
            raise PermissionError(
                f"PTorrent sandbox: HAL boundary violation — direct read blocked: {path}\n"
                "PTorrent accesses hardware and credentials exclusively through Android HAL.\n"
                "ADB keys, lock screen hashes, keystore material, and biometric templates\n"
                "are never accessible to the Python engine — by design.\n"
                "If a .ptorrent file triggered this, flag it on the chain immediately."
            )

    return _ORIGINAL_OPEN(file, mode, *args, **kwargs)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    base = name.split(".")[0]
    if base in _BLOCKED_IMPORT:
        _log.error("SANDBOX BLOCK import: %s", name)
        raise ImportError(
            f"PTorrent sandbox: module '{name}' is not permitted in seed skills.\n"
            "Blocked modules: subprocess, ctypes, pty, multiprocessing, signal, mmap.\n"
            "If a .ptorrent file attempted this import, flag it on the chain."
        )
    return _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)


def install(out_dir: str = "") -> None:
    """
    Install the sandbox. Call once at process startup.

    :param out_dir: App external files directory. Writes are restricted here.
    """
    global _INSTALLED, _ALLOWED_WRITE_ROOTS

    if _INSTALLED:
        return

    roots = []
    if out_dir:
        roots.append(os.path.abspath(out_dir))

    env_dir = os.environ.get("PTOL_OUT_DIR", "")
    if env_dir:
        roots.append(os.path.abspath(env_dir))

    # Android app storage path (always allowed if running in APK context)
    android_path = "/sdcard/Android/data/com.ptolemy.seeder/files"
    if os.path.exists(android_path):
        roots.append(android_path)

    # Desktop: allow current working directory tree
    cwd = os.getcwd()
    if not any(cwd.startswith(r) for r in roots):
        roots.append(cwd)

    _ALLOWED_WRITE_ROOTS = roots
    builtins.open          = _safe_open
    builtins.__import__    = _safe_import

    _INSTALLED = True
    _log.info(
        "PTorrent sandbox installed. "
        "Allowed write roots: %s. "
        "Blocked imports: %s",
        _ALLOWED_WRITE_ROOTS,
        sorted(_BLOCKED_IMPORT),
    )


def uninstall() -> None:
    """Restore original builtins. For testing only."""
    global _INSTALLED
    builtins.open       = _ORIGINAL_OPEN
    builtins.__import__ = _ORIGINAL_IMPORT
    _INSTALLED = False
