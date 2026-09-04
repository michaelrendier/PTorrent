"""The PTorrent curses GUI shell.

A menu bar over a content area. Each screen is its own module; the first one
shipped is File ▸ New — the .ptorrent wizard (ptorrent_gui.wizard). The rest of
the console face (job list, phonebook browser, seeds, access requests) mounts
here later against the same Engine.snapshot() / events() surface.
"""
from __future__ import annotations

import curses
import json
import os
import time

from . import alarms as A
from . import config as C
from .common import dialog as D
from .common import mathtext as MT
from .common import theme
from .common.geometry import Rect
from .menu import MenuBar

_MENU = MenuBar([
    ("File", [
        ("New .ptorrent", "new"),
        ("Open .ptorrent…", "open"),
        (None, None),
        ("Quit", "quit"),
    ]),
    ("Settings", [
        ("Preferences…", "prefs"),
        ("Reload from disk", "reload_cfg"),
        (None, None),
        (f"Config file: {C.path()}", None),
    ]),
    ("Help", [("Keys", "keys"), ("About", "about")]),
])

_ABOUT = [
    "PTorrent — curses GUI",
    "",
    "A native-curses face over ptorrent_core: the runtime core for finding,",
    f"fetching, evaluating in situ ({MT.SIGMA}-face), and seeding research datasets.",
    "",
    "LGPL-3.0-or-later.   github.com/michaelrendier/PTorrent",
    "",
    "This build ships one screen — File ▸ New, the .ptorrent wizard.",
    "The job list, phonebook browser, seeds and access panes mount next.",
]
_KEYS = [
    "F1            open the menu bar",
    "n             File ▸ New   (the .ptorrent wizard)",
    "o             File ▸ Open a .ptorrent for preview",
    "p             Settings ▸ Preferences",
    "q             quit",
    "",
    "In the wizard:  Tab / 1-4 switch section  ·  ↑↓ fields  ·  ←→ change",
    "                ↵ edit  ·  Space toggle  ·  s sidebar  ·  t tooltips",
    "                F8 check  ·  F9 preview  ·  F10 build & save  ·  Esc back",
]


class Shell:
    def __init__(self, stdscr, engine=None, out_dir="."):
        self.s = stdscr
        self.engine = engine
        self.cfg = C.load()
        self.out_dir = out_dir or C.get(self.cfg, "paths.out_dir", ".")
        self.status = "F1 menu   n new   o open   p preferences   q quit"
        u = C.get(self.cfg, "display.unicode", "auto")
        self.unicode_ok = (u == "on") or (u == "auto" and "utf-8" in (
            os.environ.get("LANG", "") + os.environ.get("LC_ALL", "")).lower())
        self._alarm_state: dict = {}
        self._last_seq = 0

    def run(self):
        curses.curs_set(0)
        self.s.keypad(True)
        theme.init()
        if self.engine is not None:
            self.s.timeout(max(200, int(C.get(self.cfg, "paths.poll_interval_s", 1.0) * 1000)))
        while True:
            self._draw()
            ch = self.s.getch()
            if ch == -1:                      # idle tick (only when engine attached)
                self._tick()
                continue
            if ch == curses.KEY_RESIZE:
                continue
            if ch in (curses.KEY_F1,):
                act = _MENU.navigate(self.s, row=0)
                if act and not self._dispatch(act):
                    return
                continue
            if ch in (ord("q"),):
                if not C.get(self.cfg, "display.confirm_on_quit", True) or \
                        D.confirm(self.s, "Quit PTorrent?", unicode_ok=self.unicode_ok):
                    return
                continue
            if ch in (ord("n"), curses.KEY_F2):
                self._dispatch("new")
            elif ch in (ord("o"),):
                self._dispatch("open")
            elif ch in (ord("p"),):
                self._dispatch("prefs")
            elif ch in (ord("?"), ord("h")):
                self._dispatch("about")

    # ── periodic: alarms + notification events ──
    def _tick(self):
        if self.engine is None:
            return
        try:
            snap = self.engine.snapshot()
        except Exception:  # noqa: BLE001
            return
        for hit in A.evaluate(self.cfg.get("alarms", []), snap, self._alarm_state):
            A.fire(hit["rule"].get("action", "bell"), hit["message"],
                   self.cfg.get("notifications", {}))
            self.status = "⏰ " + hit["message"]
        # event-driven notifications
        ncfg = self.cfg.get("notifications", {})
        if ncfg.get("enabled", True):
            evmap = {"JOB_DONE": "job_complete", "JOB_ERROR": "job_error",
                     "DISCLOSE": "embargo_lifted", "REQUEST": "access_request",
                     "GRANT": "grant_received", "VOTE_CAST": "vote_received",
                     "PHONEBOOK_VERIFY": "phonebook_stale"}
            try:
                evs = self.engine.events(since=self._last_seq, limit=200)
            except Exception:  # noqa: BLE001
                evs = []
            for e in evs:
                self._last_seq = max(self._last_seq, e.get("seq", 0))
                key = evmap.get(e.get("kind", ""))
                if key and ncfg.get("events", {}).get(key):
                    msg = f"{e.get('kind')}  {e.get('payload', {})}"
                    A.fire("desktop" if ncfg.get("channel") in ("desktop", "both") else "bell",
                           msg[:120], ncfg)
                    self.status = "🔔 " + msg[:100]

    # ── actions ──  return False only to quit the shell
    def _dispatch(self, act: str) -> bool:
        if act == "quit":
            return False
        if act == "new":
            from .wizard.wizard import run_embedded
            res = run_embedded(self.s, self.engine, self.out_dir,
                               tooltips=C.get(self.cfg, "display.tooltips_default", False))
            if res and res.startswith("built:"):
                self.status = "built " + res.split(":", 1)[1]
        elif act == "open":
            self._open_ptorrent()
        elif act == "prefs":
            from .settings import run_embedded as run_settings
            got = run_settings(self.s, self.cfg, self.engine)
            if got is not None:
                self.cfg = got
                self.status = "settings saved"
        elif act == "reload_cfg":
            self.cfg = C.load()
            self.status = "settings reloaded from disk"
        elif act == "about":
            self._pager("About", _ABOUT)
        elif act == "keys":
            self._pager("Keys", _KEYS)
        return True

    def _open_ptorrent(self):
        path = self._prompt("Open .ptorrent", os.path.join(self.out_dir, ""))
        if not path:
            return
        try:
            with open(os.path.expanduser(path), encoding="utf-8") as fh:
                doc = json.load(fh)
            body = json.dumps(doc, indent=2, ensure_ascii=False).splitlines()
            self._pager(os.path.basename(path), body)
            self.status = f"opened {path}"
        except Exception as e:  # noqa: BLE001
            self.status = f"open failed: {e}"

    # ── drawing ──
    def _draw(self):
        self.s.erase()
        scr = Rect.screen(self.s)
        g = theme.glyphs(self.unicode_ok)
        _MENU.render(self.s, 0, scr.w, active=None)
        _, rest = scr.rows(1)
        body, foot = rest.rows(rest.h - max(2, round(scr.h * 0.08)))

        theme.fill(self.s, body, theme.BASE)
        theme.draw_box(self.s, body, g, "PTorrent")
        inner = body.inset(2, 4)
        eng = "engine: attached" if self.engine is not None else \
              "engine: none  (launch with --engine <dir> to verify ORCID / add jobs)"
        msg = [
            "No job open.",
            "",
            "File ▸ New   —  build a .ptorrent through the four-tab wizard",
            "File ▸ Open  —  preview an existing .ptorrent",
            "",
            eng,
        ]
        for i, ln in enumerate(msg[: inner.h]):
            theme.addstr(self.s, inner.y + i, inner.x, ln[: inner.w], theme.attr(theme.BASE))

        theme.fill(self.s, foot, theme.HINT)
        theme.addstr(self.s, foot.y, foot.x + 1, self.status[: foot.w - 2],
                     theme.attr(theme.HINT))
        self.s.refresh()

    def _pager(self, title: str, lines: list[str]):
        top = 0
        g = theme.glyphs(self.unicode_ok)
        while True:
            scr = Rect.screen(self.s)
            box = scr.pct(0.06, 0.08, 0.94, 0.92, min_w=40, min_h=8)
            theme.fill(self.s, box, theme.BASE)
            theme.draw_box(self.s, box, g, f"{title}   (↑↓ scroll · any other key closes)")
            inner = box.inset(1, 2)
            for i in range(inner.h):
                if top + i >= len(lines):
                    break
                theme.addstr(self.s, inner.y + i, inner.x, lines[top + i][: inner.w],
                             theme.attr(theme.BASE))
            self.s.refresh()
            ch = self.s.getch()
            if ch in (curses.KEY_UP, ord("k")):
                top = max(0, top - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                top = min(max(0, len(lines) - inner.h), top + 1)
            elif ch in (curses.KEY_NPAGE, ord(" ")):
                top = min(max(0, len(lines) - inner.h), top + inner.h)
            elif ch == curses.KEY_PPAGE:
                top = max(0, top - inner.h)
            else:
                return

    def _prompt(self, q: str, default: str) -> str:
        curses.curs_set(1)
        buf, pos = default, len(default)
        while True:
            scr = Rect.screen(self.s)
            bar = scr.pct(0.0, 0.90, 1.0, 1.0, min_h=2)
            theme.fill(self.s, bar, theme.HINT)
            theme.addstr(self.s, bar.y, bar.x + 1, (q + "   (↵ ok · Esc cancel)")[: bar.w - 2],
                         theme.attr(theme.HINT, bold=True))
            theme.addstr(self.s, bar.y + 1, bar.x + 1, buf[: bar.w - 3].ljust(bar.w - 3),
                         theme.attr(theme.HINT))
            self.s.move(bar.y + 1, min(bar.x + 1 + pos, bar.right - 2))
            self.s.refresh()
            ch = self.s.getch()
            if ch == 27:
                curses.curs_set(0); return ""
            if ch in (curses.KEY_ENTER, 10, 13):
                curses.curs_set(0); return buf.strip()
            if ch in (curses.KEY_BACKSPACE, 127, 8) and pos > 0:
                buf = buf[:pos - 1] + buf[pos:]; pos -= 1
            elif 32 <= ch < 127:
                buf = buf[:pos] + chr(ch) + buf[pos:]; pos += 1


def main(engine=None, out_dir="."):
    return curses.wrapper(lambda scr: Shell(scr, engine, out_dir).run())
