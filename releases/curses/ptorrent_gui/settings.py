"""Settings ▸ Preferences — every user-adjustable console setting.

One scrolling field ladder + a BIOS 'Item Specific Help' sidebar, same look as
the wizard. Controls are text boxes, on/off toggles, and ‹cycle› choices
(radio-equivalent) as appropriate. Section alarms get their own row editor.

Backed by ptorrent_gui.config (~/.config/ptorrent/gui.json).
"""
from __future__ import annotations

import curses
import os

from . import alarms as A
from . import config as C
from .common import dialog as D
from .common import theme
from .common.geometry import Rect, sidebar_width
from .wizard.model import Field

# (Field, dotted-config-key). kind: toggle | choice | text | int | float | list | info | action
_SPEC: list[tuple[Field, str]] = [
    (Field("_n", "── Notifications ──", "info",
           help="How PTorrent tells you something happened."), ""),
    (Field("notif_enabled", "Enable notifications", "toggle",
           help="Master switch. Off silences every event and every alarm action."),
     "notifications.enabled"),
    (Field("notif_channel", "Channel", "choice",
           choices=["bell", "desktop", "both", "off"],
           help="bell: terminal \\a.  desktop: notify-send / kdialog popup.  "
                "both: ring and pop.  off: neither (status line only)."),
     "notifications.channel"),
    (Field("ev_job_complete", "· on job complete", "toggle",
           help="Ding when a job reaches DONE."), "notifications.events.job_complete"),
    (Field("ev_job_error", "· on job error", "toggle",
           help="Ding when a job ends in ERROR."), "notifications.events.job_error"),
    (Field("ev_embargo", "· on embargo lifted", "toggle",
           help="A CLASSIFY/DISCLOSE on the chain drops a marking to public."),
     "notifications.events.embargo_lifted"),
    (Field("ev_request", "· on access request received", "toggle",
           help="Another researcher asked you for a password to protected content."),
     "notifications.events.access_request"),
    (Field("ev_grant", "· on grant received", "toggle",
           help="A researcher granted you access you had requested."),
     "notifications.events.grant_received"),
    (Field("ev_vote", "· on vote received", "toggle",
           help="Someone up/down-voted an artifact you produced."),
     "notifications.events.vote_received"),
    (Field("ev_stale", "· on phonebook entry gone stale/dead", "toggle",
           help="A verification crawl found a dataset endpoint no longer live."),
     "notifications.events.phonebook_stale"),

    (Field("_a", "── Section alarms (heartbeats) ──", "info",
           help="User-defined periodic / conditional alerts. The shipped rule "
                "'still-alive ping' dings every 3 hours while any job is RUNNING "
                "— so a 12-day download reminds you it is still going."), ""),
    (Field("alarms", "Alarm rules", "list",
           columns=["name", "on", "when", "every", "action"],
           help="↵ opens the rule editor.  a add · d delete.  Fields per rule: "
                "name, enabled, when (" + " / ".join(A.WHEN) + "), interval, "
                "threshold, count, scope (any_job/each_job), action "
                "(bell/desktop/status), repeat."), "alarms"),

    (Field("_d", "── Display ──", "info", help=""), ""),
    (Field("theme", "Theme", "choice", choices=["bios-blue", "mono"],
           help="bios-blue: the legacy-BIOS palette.  mono: attributes only, no colour."),
     "display.theme"),
    (Field("sidebar", "Help sidebar", "choice", choices=["auto", "always", "never"],
           help="auto: grows > 170 cols, hides < 90.  always / never: force it."),
     "display.sidebar"),
    (Field("tooltips_default", "Tooltips on by default", "toggle",
           help="Start the wizard with the floating field tooltips already on."),
     "display.tooltips_default"),
    (Field("confirm_on_quit", "Confirm on quit", "toggle",
           help="Ask before leaving the GUI."), "display.confirm_on_quit"),
    (Field("unicode", "Unicode glyphs", "choice", choices=["auto", "on", "off"],
           help="auto: from $LANG.  Forces box-drawing / maths glyphs on or off."),
     "display.unicode"),

    (Field("_df", "── Defaults for new .ptorrent ──", "info", help=""), ""),
    (Field("pol_delay", "Politeness delay (s)", "float",
           help="Pre-fills the wizard's Crawler tab default per-host delay."),
     "defaults.politeness_delay_s"),
    (Field("ua", "User-Agent", "text",
           help="Pre-fills the wizard's Crawler tab UA."), "defaults.user_agent"),

    (Field("_p", "── Paths ──", "info", help=""), ""),
    (Field("out_dir", "Output directory", "text",
           help="Where File ▸ New writes the .ptorrent by default."), "paths.out_dir"),
    (Field("engine_dir", "Engine root", "text",
           help="Directory an attached Engine is rooted at (used when the GUI is "
                "launched with --engine)."), "paths.engine_dir"),
    (Field("poll_s", "Poll interval (s)", "float",
           help="How often the shell re-reads snapshot()/events() and evaluates alarms."),
     "paths.poll_interval_s"),

    (Field("_reset", "Reset all to defaults", "action", help="Restore every setting."), ""),
]

_WHEN_CHOICES = list(A.WHEN)
_UNIT_CHOICES = list(A.UNITS)
_ACTION_CHOICES = ["bell", "desktop", "status"]
_SCOPE_CHOICES = ["any_job", "each_job"]


class SettingsScreen:
    def __init__(self, stdscr, cfg: dict, engine=None):
        self.s = stdscr
        self.cfg = cfg
        self.engine = engine
        self.row = 0
        self.scroll = 0
        self.dirty = False
        u = C.get(cfg, "display.unicode", "auto")
        self.unicode_ok = (u == "on") or (u == "auto" and "utf-8" in (
            os.environ.get("LANG", "") + os.environ.get("LC_ALL", "")).lower())
        self.status = "↑↓ move   ←→/↵ change   F10 save   Esc back"

    # ── field <-> config ──
    def _fields(self):
        return _SPEC

    def _val(self, key: str):
        return C.get(self.cfg, key)

    def _put(self, key: str, v):
        C.set_(self.cfg, key, v)
        self.dirty = True

    # ── loop ──
    def run(self):
        curses.curs_set(0)
        self.s.keypad(True)
        theme.init()
        while True:
            self._draw()
            ch = self.s.getch()
            if ch == curses.KEY_RESIZE:
                continue
            if ch in (27, ord("q")):
                if not self.dirty or D.confirm(self.s, "Discard unsaved changes?",
                                               unicode_ok=self.unicode_ok):
                    return None
                continue
            if ch == curses.KEY_F10:
                path = C.save(self.cfg)
                D.message_box(self.s, "Saved", [f"Settings written to", path],
                              ("OK",), self.unicode_ok)
                return self.cfg
            if ch in (curses.KEY_UP, ord("k")):
                self.row = max(0, self.row - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                self.row = min(len(self._fields()) - 1, self.row + 1)
            elif ch in (curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_ENTER, 10, 13, ord(" ")):
                self._activate(ch)

    def _cur(self):
        f, key = self._fields()[self.row]
        return f, key

    def _activate(self, ch):
        f, key = self._cur()
        if f.kind == "info":
            return
        if f.kind == "action" and f.key == "_reset":
            if D.confirm(self.s, "Reset ALL settings to defaults?", unicode_ok=self.unicode_ok):
                import copy
                self.cfg.clear()
                self.cfg.update(copy.deepcopy(C.DEFAULTS))
                self.dirty = True
            return
        if f.kind == "toggle":
            self._put(key, not bool(self._val(key)))
        elif f.kind == "choice":
            d = 1 if ch != curses.KEY_LEFT else -1
            cur = self._val(key)
            i = f.choices.index(cur) if cur in f.choices else 0
            self._put(key, f.choices[(i + d) % len(f.choices)])
        elif f.kind in ("text", "int", "float") and ch in (curses.KEY_ENTER, 10, 13):
            self._edit_line(f, key)
        elif f.kind == "list" and ch in (curses.KEY_ENTER, 10, 13):
            self._alarm_editor()

    # ── inline editor ──
    def _edit_line(self, f, key):
        curses.curs_set(1)
        buf = str(self._val(key) if self._val(key) is not None else "")
        pos = len(buf)
        while True:
            self._draw(edit=(key, buf, pos))
            c = self.s.getch()
            if c == 27:
                break
            if c in (curses.KEY_ENTER, 10, 13):
                if f.kind == "int":
                    try: self._put(key, int(buf or 0))
                    except ValueError: pass
                elif f.kind == "float":
                    try: self._put(key, float(buf or 0))
                    except ValueError: pass
                else:
                    self._put(key, buf.strip())
                break
            if c in (curses.KEY_BACKSPACE, 127, 8) and pos:
                buf = buf[:pos - 1] + buf[pos:]; pos -= 1
            elif c == curses.KEY_LEFT: pos = max(0, pos - 1)
            elif c == curses.KEY_RIGHT: pos = min(len(buf), pos + 1)
            elif 32 <= c < 127:
                buf = buf[:pos] + chr(c) + buf[pos:]; pos += 1
        curses.curs_set(0)

    # ── alarm rule list + per-rule editor ──
    def _alarm_editor(self):
        rules = [dict(r) for r in self.cfg.get("alarms", [])]
        sel = 0
        g = theme.glyphs(self.unicode_ok)
        while True:
            scr = Rect.screen(self.s)
            box = scr.pct(0.06, 0.10, 0.94, 0.90, min_w=48, min_h=10)
            theme.fill(self.s, box, theme.BASE)
            theme.draw_box(self.s, box, g,
                           "Section alarms   a add · d delete · ↵ edit · Esc back")
            inner = box.inset(1, 2)
            cols = ["name", "on", "when", "every", "action"]
            theme.addstr(self.s, inner.y, inner.x,
                         f"{'name':<20}{'on':<5}{'when':<26}{'every':<10}{'action'}",
                         theme.attr(theme.DIM, bold=True))
            for i, r in enumerate(rules[: inner.h - 2]):
                ev = r.get("every", {})
                line = (f"{str(r.get('name',''))[:19]:<20}"
                        f"{'yes' if r.get('enabled', True) else 'no':<5}"
                        f"{r.get('when','')[:25]:<26}"
                        f"{str(ev.get('n',''))+ (ev.get('unit','')[:1]):<10}"
                        f"{r.get('action','')}")
                a = theme.attr(theme.SEL) if i == sel else theme.attr(theme.BASE)
                theme.addstr(self.s, inner.y + 1 + i, inner.x, line[:inner.w].ljust(inner.w), a)
            self.s.refresh()
            c = self.s.getch()
            if c == 27:
                break
            if c == ord("a"):
                import copy
                rules.append(copy.deepcopy(C.DEFAULTS["alarms"][0]))
                rules[-1]["name"] = "new alarm"
                sel = len(rules) - 1
            elif c == ord("d") and rules:
                rules.pop(sel); sel = max(0, sel - 1)
            elif c in (curses.KEY_UP, ord("k")):
                sel = max(0, sel - 1)
            elif c in (curses.KEY_DOWN, ord("j")):
                sel = min(len(rules) - 1, sel + 1)
            elif c in (curses.KEY_ENTER, 10, 13) and rules:
                self._rule_form(rules[sel])
        self.cfg["alarms"] = rules
        self.dirty = True

    def _rule_form(self, rule: dict):
        rule.setdefault("every", {"n": 3, "unit": "hours"})
        rule.setdefault("threshold", {"n": 1, "unit": "hours"})
        fields = [
            ("name", "text", "name", None),
            ("enabled", "toggle", "enabled", None),
            ("when", "choice", "when", _WHEN_CHOICES),
            ("every.n", "int", "every n", None),
            ("every.unit", "choice", "every unit", _UNIT_CHOICES),
            ("threshold.n", "int", "threshold n", None),
            ("threshold.unit", "choice", "threshold unit", _UNIT_CHOICES),
            ("count", "int", "error count", None),
            ("scope", "choice", "scope", _SCOPE_CHOICES),
            ("action", "choice", "action", _ACTION_CHOICES),
            ("repeat", "toggle", "repeat", None),
        ]
        r = 0
        g = theme.glyphs(self.unicode_ok)

        def gv(dot):
            cur = rule
            for p in dot.split("."):
                cur = cur.get(p) if isinstance(cur, dict) else None
            return cur

        def sv(dot, v):
            cur = rule
            ps = dot.split(".")
            for p in ps[:-1]:
                cur = cur.setdefault(p, {})
            cur[ps[-1]] = v

        while True:
            scr = Rect.screen(self.s)
            box = scr.pct(0.14, 0.18, 0.86, 0.82, min_w=40, min_h=len(fields) + 4)
            theme.fill(self.s, box, theme.BASE)
            theme.draw_box(self.s, box, g, f"alarm: {rule.get('name','')}   ↵ edit · Esc done")
            inner = box.inset(1, 2)
            for i, (dot, kind, label, choices) in enumerate(fields):
                v = gv(dot)
                if kind == "toggle":
                    disp = "[×] yes" if v else "[ ] no"
                elif kind == "choice":
                    disp = f"‹ {v} ›"
                else:
                    disp = str(v)
                a = theme.attr(theme.SEL) if i == r else theme.attr(theme.BASE)
                theme.addstr(self.s, inner.y + i, inner.x,
                             f"{label:<16}: {disp}"[:inner.w].ljust(inner.w), a)
            sidebar = A.WHEN.get(gv("when"), "")
            theme.addstr(self.s, inner.y + len(fields) + 1, inner.x,
                         ("when → " + sidebar)[:inner.w], theme.attr(theme.HELP))
            self.s.refresh()
            c = self.s.getch()
            if c == 27:
                return
            dot, kind, label, choices = fields[r]
            if c in (curses.KEY_UP, ord("k")):
                r = max(0, r - 1)
            elif c in (curses.KEY_DOWN, ord("j")):
                r = min(len(fields) - 1, r + 1)
            elif kind == "toggle" and c in (curses.KEY_ENTER, 10, 13, ord(" "),
                                            curses.KEY_LEFT, curses.KEY_RIGHT):
                sv(dot, not bool(gv(dot)))
            elif kind == "choice" and c in (curses.KEY_LEFT, curses.KEY_RIGHT,
                                            curses.KEY_ENTER, 10, 13):
                d = -1 if c == curses.KEY_LEFT else 1
                i = choices.index(gv(dot)) if gv(dot) in choices else 0
                sv(dot, choices[(i + d) % len(choices)])
            elif kind in ("int", "text") and c in (curses.KEY_ENTER, 10, 13):
                self._mini_prompt(rule, dot, kind)

    def _mini_prompt(self, rule, dot, kind):
        curses.curs_set(1)
        cur = rule
        ps = dot.split(".")
        for p in ps[:-1]:
            cur = cur.setdefault(p, {})
        buf = str(cur.get(ps[-1], ""))
        pos = len(buf)
        while True:
            scr = Rect.screen(self.s)
            bar = scr.pct(0.0, 0.92, 1.0, 1.0, min_h=1)
            theme.fill(self.s, bar, theme.HINT)
            theme.addstr(self.s, bar.y, bar.x + 1, (f" {dot} = {buf} ")[:bar.w].ljust(bar.w),
                         theme.attr(theme.HINT))
            self.s.move(bar.y, min(bar.w - 1, bar.x + 4 + len(dot) + pos))
            self.s.refresh()
            c = self.s.getch()
            if c in (27, curses.KEY_ENTER, 10, 13):
                val = buf.strip()
                if kind == "int":
                    try: cur[ps[-1]] = int(val or 0)
                    except ValueError: pass
                else:
                    cur[ps[-1]] = val
                break
            if c in (curses.KEY_BACKSPACE, 127, 8) and pos:
                buf = buf[:pos - 1] + buf[pos:]; pos -= 1
            elif 32 <= c < 127:
                buf = buf[:pos] + chr(c) + buf[pos:]; pos += 1
        curses.curs_set(0)

    # ── draw ──
    def _draw(self, edit=None):
        self.s.erase()
        scr = Rect.screen(self.s)
        g = theme.glyphs(self.unicode_ok)
        head, rest = scr.rows(max(2, round(scr.h * 0.08)))
        body, foot = rest.rows(rest.h - max(2, round(scr.h * 0.08)))
        theme.fill(self.s, head, theme.TITLE)
        theme.addstr(self.s, head.y, head.x + 1,
                     ("PTorrent — Settings" + ("   *modified" if self.dirty else ""))[:scr.w - 2],
                     theme.attr(theme.TITLE, bold=True))

        sw = sidebar_width(body.w, False)
        main, side = body.cols(sw)
        theme.fill(self.s, main, theme.BASE)
        theme.draw_box(self.s, main, g, "Preferences")
        self._draw_ladder(main.inset(1, 2), edit)
        if sw:
            theme.fill(self.s, side, theme.BASE)
            theme.draw_box(self.s, side, g, "Item Specific Help")
            self._draw_help(side.inset(1, 2))

        theme.fill(self.s, foot, theme.HINT)
        theme.addstr(self.s, foot.y, foot.x + 1, self.status[:foot.w - 2], theme.attr(theme.HINT))
        self.s.refresh()

    def _draw_ladder(self, area: Rect, edit):
        fs = self._fields()
        if self.row < self.scroll:
            self.scroll = self.row
        elif self.row >= self.scroll + area.h:
            self.scroll = self.row - area.h + 1
        lw = min(30, max(18, area.w // 3))
        for vi in range(area.h):
            fi = self.scroll + vi
            if fi >= len(fs):
                break
            f, key = fs[fi]
            y = area.y + vi
            foc = fi == self.row
            if f.kind == "info":
                theme.addstr(self.s, y, area.x, f.label[:area.w],
                             theme.attr(theme.ACCENT, bold=True))
                continue
            if f.kind == "action":
                theme.addstr(self.s, y, area.x, f"[ {f.label} ]",
                             theme.attr(theme.SEL if foc else theme.OK, bold=True))
                continue
            if edit and edit[0] == key:
                _, buf, pos = edit
                disp = buf[:pos] + "▏" + buf[pos:]
            else:
                v = self._val(key)
                if f.kind == "toggle":
                    disp = "[×] yes" if v else "[ ] no"
                elif f.kind == "choice":
                    disp = f"‹ {v} ›"
                elif f.kind == "list":
                    disp = f"[{len(self.cfg.get('alarms', []))} rule(s)]  (↵ to edit)"
                else:
                    disp = str(v if v is not None else "")
            lbl = (f.label + " ")[:lw].ljust(lw, "·")
            theme.addstr(self.s, y, area.x, f"{lbl}: {disp}"[:area.w].ljust(area.w),
                         theme.attr(theme.SEL) if foc else theme.attr(theme.BASE))

    def _draw_help(self, area: Rect):
        import textwrap
        f, key = self._cur()
        lines = textwrap.wrap(f.help or "", area.w) or [""]
        if f.kind == "choice":
            lines += ["", "Values:"] + [f"  {c}" for c in f.choices]
        if f.key == "alarms":
            lines += ["", "when:"]
            for k, v in A.WHEN.items():
                lines += [f"  {k}"] + ["    " + w for w in textwrap.wrap(v, max(8, area.w - 4))]
        for i, ln in enumerate(lines[:area.h]):
            theme.addstr(self.s, area.y + i, area.x, ln[:area.w], theme.attr(theme.HELP))


def run_embedded(stdscr, cfg: dict, engine=None):
    return SettingsScreen(stdscr, cfg, engine).run()
