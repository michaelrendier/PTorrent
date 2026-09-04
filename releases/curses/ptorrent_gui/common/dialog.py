"""Modal dialog boxes — messages, confirms, and the fault list.

Everything here is non-fatal: a dialog reports, the caller decides. A dialog
never raises; it returns a small string (or a (verb, payload) tuple) telling the
caller what the user chose.
"""
from __future__ import annotations

import curses
import textwrap

from . import theme
from .geometry import Rect

_SEV_GLYPH = {"error": "✖", "warning": "▲", "info": "•"}
_SEV_PAIR = {"error": theme.WARN, "warning": theme.ACCENT, "info": theme.DIM}


def _button_row(stdscr, y: int, x: int, w: int, buttons: list[str], sel: int) -> None:
    labels = [f"  {b}  " for b in buttons]
    total = sum(len(s) for s in labels) + (len(labels) - 1)
    cx = x + max(0, (w - total) // 2)
    for i, s in enumerate(labels):
        a = theme.attr(theme.SEL, bold=True) if i == sel else theme.attr(theme.BASE)
        theme.addstr(stdscr, y, cx, s, a)
        cx += len(s) + 1


def _run_buttons(stdscr, draw, buttons: list[str], default: int = 0) -> str:
    sel = default
    while True:
        draw(sel)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (curses.KEY_LEFT, curses.KEY_BTAB, ord("h")):
            sel = (sel - 1) % len(buttons)
        elif ch in (curses.KEY_RIGHT, ord("\t"), ord("l")):
            sel = (sel + 1) % len(buttons)
        elif ch in (curses.KEY_ENTER, 10, 13):
            return buttons[sel]
        elif ch == 27:
            return buttons[-1]
        elif ch == curses.KEY_RESIZE:
            continue


def message_box(stdscr, title: str, lines, buttons=("OK",), unicode_ok=True) -> str:
    """A scrollable message with a button row. Returns the chosen button label."""
    lines = list(lines)
    buttons = list(buttons)
    g = theme.glyphs(unicode_ok)
    top = 0

    def draw(sel):
        scr = Rect.screen(stdscr)
        box = scr.pct(0.10, 0.12, 0.90, 0.88, min_w=36, min_h=8)
        theme.fill(stdscr, box, theme.BASE)
        theme.draw_box(stdscr, box, g, title)
        inner = box.inset(1, 2)
        body_h = inner.h - 2
        wrapped: list[str] = []
        for ln in lines:
            wrapped += textwrap.wrap(ln, inner.w) or [""]
        nonlocal top
        top = max(0, min(top, max(0, len(wrapped) - body_h)))
        for i in range(body_h):
            if top + i >= len(wrapped):
                break
            theme.addstr(stdscr, inner.y + i, inner.x, wrapped[top + i][: inner.w],
                         theme.attr(theme.BASE))
        if len(wrapped) > body_h:
            theme.addstr(stdscr, inner.y + body_h - 1, inner.right - 12, " ↑↓ more ",
                         theme.attr(theme.DIM))
        _button_row(stdscr, inner.y + inner.h - 1, inner.x, inner.w, buttons, sel)

    sel = 0
    while True:
        draw(sel)
        stdscr.refresh()
        ch = stdscr.getch()
        if ch in (curses.KEY_UP, ord("k")):
            top = max(0, top - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            top += 1
        elif ch in (curses.KEY_NPAGE, ord(" ")):
            top += 8
        elif ch == curses.KEY_PPAGE:
            top = max(0, top - 8)
        elif ch in (curses.KEY_LEFT, curses.KEY_BTAB):
            sel = (sel - 1) % len(buttons)
        elif ch in (curses.KEY_RIGHT, ord("\t")):
            sel = (sel + 1) % len(buttons)
        elif ch in (curses.KEY_ENTER, 10, 13):
            return buttons[sel]
        elif ch == 27:
            return buttons[-1]


def confirm(stdscr, question: str, yes="Yes", no="No", unicode_ok=True) -> bool:
    return message_box(stdscr, "Confirm", [question], (yes, no), unicode_ok) == yes


def fault_dialog(stdscr, faults: list, *, save_path: bool = False, unicode_ok=True):
    """Render the .ptorrent fault list.

    Returns:
        ("fix", fault)      — user picked a fault to go correct
        ("save", None)      — only warnings, user chose to save anyway
        ("dismiss", None)   — closed
    Faults are dicts: {severity, tab, field, message, hint}.
    """
    if not faults:
        return ("dismiss", None)
    g = theme.glyphs(unicode_ok)
    has_error = any(f["severity"] == "error" for f in faults)
    buttons = ["Fix selected", "Dismiss"]
    if save_path and not has_error:
        buttons = ["Fix selected", "Save anyway", "Dismiss"]
    sel_row = 0
    sel_btn = 0
    title = ("✖ .ptorrent faults — cannot build" if has_error
             else "▲ .ptorrent inconsistencies — build is still allowed")

    while True:
        scr = Rect.screen(stdscr)
        box = scr.pct(0.06, 0.08, 0.94, 0.92, min_w=44, min_h=10)
        theme.fill(stdscr, box, theme.BASE)
        theme.draw_box(stdscr, box, g, title)
        inner = box.inset(1, 2)
        list_h = inner.h - 3
        sel_row = max(0, min(sel_row, len(faults) - 1))
        first = max(0, sel_row - list_h + 1)
        for i in range(list_h):
            fi = first + i
            if fi >= len(faults):
                break
            f = faults[fi]
            gl = _SEV_GLYPH.get(f["severity"], "•")
            loc = f.get("tab", "")
            head = f"{gl} [{loc}] {f.get('field') or ''}"
            row = f"{head:<30} {f['message']}"
            a = theme.attr(theme.SEL) if fi == sel_row else \
                theme.attr(_SEV_PAIR.get(f["severity"], theme.BASE),
                           bold=(f["severity"] == "error"))
            theme.addstr(stdscr, inner.y + i, inner.x, row[: inner.w].ljust(inner.w), a)
        # hint for the selected fault
        hint = faults[sel_row].get("hint", "")
        theme.addstr(stdscr, inner.y + list_h, inner.x,
                     ("→ " + hint)[: inner.w].ljust(inner.w), theme.attr(theme.HELP))
        theme.addstr(stdscr, inner.y + list_h + 1, inner.x,
                     ("↑↓ select fault   " +
                      ("errors block the build — fix them" if has_error
                       else "warnings only — you may build anyway"))[: inner.w],
                     theme.attr(theme.DIM))
        _button_row(stdscr, inner.y + inner.h - 1, inner.x, inner.w, buttons, sel_btn)
        stdscr.refresh()

        ch = stdscr.getch()
        if ch in (curses.KEY_UP, ord("k")):
            sel_row = max(0, sel_row - 1)
        elif ch in (curses.KEY_DOWN, ord("j")):
            sel_row = min(len(faults) - 1, sel_row + 1)
        elif ch in (curses.KEY_LEFT, curses.KEY_BTAB):
            sel_btn = (sel_btn - 1) % len(buttons)
        elif ch in (curses.KEY_RIGHT, ord("\t")):
            sel_btn = (sel_btn + 1) % len(buttons)
        elif ch in (curses.KEY_ENTER, 10, 13):
            b = buttons[sel_btn]
            if b == "Fix selected":
                return ("fix", faults[sel_row])
            if b == "Save anyway":
                return ("save", None)
            return ("dismiss", None)
        elif ch == 27:
            return ("dismiss", None)
        elif ch == curses.KEY_RESIZE:
            continue


def tooltip(stdscr, anchor_y: int, anchor_x: int, lines: list[str], unicode_ok=True) -> None:
    """A small non-interactive popup near a field. Drawn once by the caller's
    render pass; it does not consume input."""
    if not lines:
        return
    g = theme.glyphs(unicode_ok)
    my, mx = stdscr.getmaxyx()
    w = min(max(len(s) for s in lines) + 4, max(20, mx - 4))
    h = min(len(lines) + 2, my - 2)
    y = anchor_y + 1
    x = anchor_x
    if x + w > mx:
        x = max(0, mx - w - 1)
    if y + h > my:
        y = max(0, anchor_y - h)
    rect = Rect(y, x, h, w)
    theme.fill(stdscr, rect, theme.HINT)
    theme.draw_box(stdscr, rect, g, "", pair=theme.HINT)
    for i, ln in enumerate(lines[: h - 2]):
        theme.addstr(stdscr, y + 1 + i, x + 2, ln[: w - 4], theme.attr(theme.HINT))
