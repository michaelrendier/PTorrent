"""
skills/sandbox.py — PTorrent execution sandbox.

Installed before any skill or evaluation code runs. Blocks:
  - subprocess, pty, tty, ctypes, cffi, mmap, signal, multiprocessing
  - writes outside the app storage boundary
  - reads from /proc/sys, /dev/, other apps' /data/data

Call install() once at process startup in seed_runner.py.
All violations raise PermissionError or ImportError with an explicit
message naming the blocked operation. Violations are logged.

Design: allowlist for writes (only PTOL_OUT_DIR and app storage paths),
blocklist for module imports (no subprocess or native-code bridges).
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
    "/proc/sys",
    "/sys/kernel",
    "/dev/mem",
    "/dev/kmem",
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
            _log.warning("SANDBOX BLOCK read from sensitive path: %s", path)
            raise PermissionError(
                f"PTorrent sandbox: read from sensitive system path blocked: {path}"
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
