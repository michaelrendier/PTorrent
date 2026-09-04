"""Colour pairs + box drawing. Legacy-BIOS palette: blue field, grey panels,
cyan selection, a red band for anything cybersecurity-classified."""
from __future__ import annotations

import curses

# pair ids
BASE = 1        # panel text on panel bg
TITLE = 2       # header / tab bar
SEL = 3         # focused field row
HELP = 4        # sidebar body
HINT = 5        # status bar
WARN = 6        # validation warnings / classified band
OK = 7         # confirmations
DIM = 8        # inactive tab / disabled field
ACCENT = 9     # values, editable markers

_HAVE_COLOR = False


def init() -> None:
    global _HAVE_COLOR
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    _HAVE_COLOR = True
    curses.init_pair(BASE,   curses.COLOR_WHITE,  curses.COLOR_BLUE)
    curses.init_pair(TITLE,  curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(SEL,    curses.COLOR_BLACK,  curses.COLOR_WHITE)
    curses.init_pair(HELP,   curses.COLOR_YELLOW, curses.COLOR_BLUE)
    curses.init_pair(HINT,   curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(WARN,   curses.COLOR_WHITE,  curses.COLOR_RED)
    curses.init_pair(OK,     curses.COLOR_GREEN,  curses.COLOR_BLUE)
    curses.init_pair(DIM,    curses.COLOR_CYAN,   curses.COLOR_BLUE)
    curses.init_pair(ACCENT, curses.COLOR_CYAN,   curses.COLOR_BLUE)


def attr(pair: int, *, bold: bool = False) -> int:
    a = curses.color_pair(pair) if _HAVE_COLOR else curses.A_NORMAL
    if pair in (SEL,) and not _HAVE_COLOR:
        a = curses.A_REVERSE
    if pair in (TITLE, HINT) and not _HAVE_COLOR:
        a = curses.A_REVERSE
    if pair == WARN and not _HAVE_COLOR:
        a = curses.A_REVERSE | curses.A_BOLD
    if bold:
        a |= curses.A_BOLD
    return a


# box glyphs — fall back to ASCII where the locale can't render them
_UNI = {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│",
        "lt": "├", "rt": "┤", "check": "•", "empty": "·", "arrow": "▸"}
_ASC = {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|",
        "lt": "+", "rt": "+", "check": "*", "empty": ".", "arrow": ">"}


def glyphs(unicode_ok: bool) -> dict:
    return _UNI if unicode_ok else _ASC


def draw_box(win, rect, g, title: str = "", pair: int = BASE) -> None:
    a = attr(pair)
    y, x, h, w = rect.y, rect.x, rect.h, rect.w
    if h < 2 or w < 2:
        return
    top = g["tl"] + g["h"] * (w - 2) + g["tr"]
    bot = g["bl"] + g["h"] * (w - 2) + g["br"]
    _addstr(win, y, x, top, a)
    _addstr(win, y + h - 1, x, bot, a)
    for row in range(y + 1, y + h - 1):
        _addstr(win, row, x, g["v"], a)
        _addstr(win, row, x + w - 1, g["v"], a)
    if title:
        t = f" {title} "[: max(0, w - 4)]
        _addstr(win, y, x + 2, t, attr(TITLE, bold=True))


def fill(win, rect, pair: int = BASE) -> None:
    a = attr(pair)
    blank = " " * rect.w
    for row in range(rect.y, rect.bottom):
        _addstr(win, row, rect.x, blank, a)


def _addstr(win, y: int, x: int, s: str, a: int) -> None:
    try:
        win.addstr(y, x, s, a)
    except curses.error:
        pass


addstr = _addstr
