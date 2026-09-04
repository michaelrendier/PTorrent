"""A small dropdown menu bar. Legacy-BIOS / DOS-TUI flavour.

    bar = MenuBar([
        ("File", [("New .ptorrent", "new"), ("Open .ptorrent…", "open"),
                  (None, None), ("Quit", "quit")]),
        ("Help", [("About", "about")]),
    ])
    bar.render(stdscr, row=0, width=W, active=None)   # always-visible bar
    action = bar.navigate(stdscr, row=0)              # blocking; returns action id or None
"""
from __future__ import annotations

import curses

from .common import theme


class MenuBar:
    def __init__(self, entries: list[tuple[str, list]]):
        self.entries = entries

    # ── always-visible bar ──
    def render(self, stdscr, row: int, width: int, active: int | None = None) -> list[int]:
        theme.addstr(stdscr, row, 0, " " * width, theme.attr(theme.TITLE))
        xs = []
        x = 1
        for i, (label, _) in enumerate(self.entries):
            xs.append(x)
            a = theme.attr(theme.SEL, bold=True) if i == active else theme.attr(theme.TITLE, bold=True)
            theme.addstr(stdscr, row, x, f" {label} ", a)
            x += len(label) + 3
        return xs

    # ── interactive navigation ──
    def navigate(self, stdscr, row: int) -> str | None:
        my, mx = stdscr.getmaxyx()
        mi = 0                       # menu index
        ii = 0                       # item index
        g = theme.glyphs(True)
        while True:
            xs = self.render(stdscr, row, mx, active=mi)
            items = self.entries[mi][1]
            # dropdown
            col = xs[mi]
            w = max((len(t) for t, _ in items if t), default=8) + 4
            w = min(w, mx - col - 1)
            h = len(items) + 2
            for r in range(h):
                y = row + 1 + r
                if y >= my:
                    break
                if r == 0:
                    theme.addstr(stdscr, y, col, g["tl"] + g["h"] * (w - 2) + g["tr"],
                                 theme.attr(theme.BASE))
                elif r == h - 1:
                    theme.addstr(stdscr, y, col, g["bl"] + g["h"] * (w - 2) + g["br"],
                                 theme.attr(theme.BASE))
                else:
                    lbl, _ = items[r - 1]
                    if lbl is None:
                        body = g["lt"] + g["h"] * (w - 2) + g["rt"]
                        theme.addstr(stdscr, y, col, body, theme.attr(theme.BASE))
                    else:
                        sel = (r - 1) == ii
                        text = f" {lbl} ".ljust(w - 2)[: w - 2]
                        theme.addstr(stdscr, y, col, g["v"] + text + g["v"],
                                     theme.attr(theme.SEL if sel else theme.BASE,
                                                bold=sel))
            stdscr.refresh()
            ch = stdscr.getch()
            if ch == 27:
                return None
            if ch == curses.KEY_LEFT:
                mi = (mi - 1) % len(self.entries); ii = 0
            elif ch == curses.KEY_RIGHT:
                mi = (mi + 1) % len(self.entries); ii = 0
            elif ch in (curses.KEY_UP, ord("k")):
                ii = self._step(items, ii, -1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                ii = self._step(items, ii, +1)
            elif ch in (curses.KEY_ENTER, 10, 13):
                lbl, act = items[ii]
                if act:
                    return act
            elif ch == curses.KEY_RESIZE:
                my, mx = stdscr.getmaxyx()

    @staticmethod
    def _step(items, i, d):
        n = len(items)
        for _ in range(n):
            i = (i + d) % n
            if items[i][0] is not None:
                return i
        return i
