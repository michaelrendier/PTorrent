"""python3 -m ptorrent_gui  [--engine DIR] [--out DIR] [--wizard]

--engine DIR : attach a live ptorrent_core.Engine rooted at DIR — enables ORCID
               verification in the wizard and 'add job on save'. Without it the
               GUI still builds and previews .ptorrent files.
--out DIR    : default directory for written .ptorrent files (default: cwd).
--wizard     : skip the shell and open File ▸ New directly.
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "core", "python"))
if os.path.isdir(_CORE) and _CORE not in sys.path:
    sys.path.insert(0, _CORE)
sys.path.insert(0, os.path.dirname(_HERE))   # so `-m ptorrent_gui` resolves from anywhere


def _cli() -> int:
    ap = argparse.ArgumentParser(prog="ptorrent_gui",
                                 description="PTorrent curses GUI.")
    ap.add_argument("--engine", metavar="DIR", default=None)
    ap.add_argument("--out", metavar="DIR", default=".")
    ap.add_argument("--wizard", action="store_true",
                    help="open File ▸ New directly, skipping the shell")
    args = ap.parse_args()

    engine = None
    if args.engine:
        try:
            from ptorrent_core import Engine
            engine = Engine(os.path.expanduser(args.engine))
        except Exception as e:  # noqa: BLE001
            print(f"could not open engine at {args.engine!r}: {e}", file=sys.stderr)
            return 2
    out = os.path.expanduser(args.out)
    try:
        if args.wizard:
            from ptorrent_gui.wizard.wizard import run_standalone
            run_standalone(engine=engine, out_dir=out)
        else:
            from ptorrent_gui.shell import main
            main(engine=engine, out_dir=out)
    finally:
        if engine is not None:
            engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
