"""File ▸ New — the .ptorrent wizard screen.

Rufus-style: every option on screen, laddered, split across four tabs
(Dataset · Crawler options · Cybersecurity · User information). Legacy-BIOS
layout — field ladder on the left, an 'Item Specific Help' panel on the right
that grows with the window and collapses when it is narrow. All geometry is a
percentage of the terminal. All on-screen text is Unicode.

Embeddable: `WizardScreen(stdscr, engine, out_dir).run()` takes an existing
curses screen and returns when the researcher leaves the wizard (the GUI shell
regains control); `run_standalone()` wraps its own curses session.
"""
from __future__ import annotations

import curses
import json
import os
import textwrap

from ..common import dialog as D
from ..common import mathtext as MT
from ..common import theme
from ..common.geometry import Rect, sidebar_width
from . import faults as F
from . import model as M
from . import profile as P


class WizardScreen:
    def __init__(self, stdscr, engine=None, out_dir="."):
        self.s = stdscr
        self.engine = engine
        self.out_dir = out_dir
        self.tab = 0
        self.row = 0
        self.multi_cursor = 0
        self.scroll = 0
        self.collapsed = False
        self.result: str | None = None
        self._faults: list = []
        self._focus_xy: tuple[int, int] | None = None
        self.status = ("F8 check   F9 preview   F10 build   Tab section   "
                       "t tooltips   s sidebar   Esc back")
        self.answers: dict = {}
        self._seed_defaults()
        prof = P.load()
        self.tooltip_mode = bool(prof.pop("w_tooltip", False))
        self.answers.update(prof)
        if engine is not None:
            try:
                ident = engine.identity.current()
                if ident.orcid:
                    self.answers.setdefault("u_orcid", ident.orcid)
                if ident.name:
                    self.answers.setdefault("u_name", ident.name)
            except Exception:  # noqa: BLE001
                pass
        self.unicode_ok = self._unicode_probe()

    # ── setup ──
    def _seed_defaults(self):
        for _, fields in M.TABS:
            for f in fields:
                if f.kind == "multi":
                    self.answers.setdefault(f.key, list(f.default) if f.default else [])
                elif f.kind == "list":
                    self.answers.setdefault(f.key, [])
                elif f.kind not in ("info", "action"):
                    self.answers.setdefault(f.key, f.default)
        if self.answers.get("u_ua"):
            self.answers.setdefault("ua", self.answers["u_ua"])
        if self.answers.get("u_delay"):
            self.answers.setdefault("default_delay_s", self.answers["u_delay"])

    @staticmethod
    def _unicode_probe() -> bool:
        enc = (os.environ.get("LANG", "") + os.environ.get("LC_ALL", "")).lower()
        return "utf-8" in enc or "utf8" in enc

    # ── visible-field helpers ──
    def _fields(self):
        return [f for f in M.TABS[self.tab][1] if f.visible(self.answers)]

    def _cur_field(self):
        fs = self._fields()
        self.row = max(0, min(self.row, len(fs) - 1))
        return fs[self.row] if fs else None

    # ══ loop ════════════════════════════════════════════════════════════════
    def run(self) -> str | None:
        curses.curs_set(0)
        self.s.keypad(True)
        theme.init()
        while True:
            self._draw()
            ch = self.s.getch()
            if ch == curses.KEY_RESIZE:
                continue
            if ch in (ord("q"), 27):
                if self._confirm("Leave the wizard?  (y/n)"):
                    return self.result
                continue
            if ch in (ord("\t"), curses.KEY_RIGHT) and not self._editing_field():
                f = self._cur_field()
                if ch == curses.KEY_RIGHT and f and f.kind in ("choice", "toggle", "multi"):
                    self._cycle(+1)
                else:
                    self.tab = (self.tab + 1) % len(M.TABS)
                    self.row = self.scroll = 0
                continue
            if ch == curses.KEY_BTAB or (ch == curses.KEY_LEFT and not self._editing_field()):
                f = self._cur_field()
                if ch == curses.KEY_LEFT and f and f.kind in ("choice", "toggle", "multi"):
                    self._cycle(-1)
                else:
                    self.tab = (self.tab - 1) % len(M.TABS)
                    self.row = self.scroll = 0
                continue
            if ord("1") <= ch <= ord("4"):
                self.tab = ch - ord("1")
                self.row = self.scroll = 0
                continue
            if ch in (curses.KEY_UP, ord("k")):
                self.row = max(0, self.row - 1)
                self.multi_cursor = 0
                continue
            if ch in (curses.KEY_DOWN, ord("j")):
                self.row = min(len(self._fields()) - 1, self.row + 1)
                self.multi_cursor = 0
                continue
            if ch == ord("s"):
                self.collapsed = not self.collapsed
                continue
            if ch == ord("t"):
                self.tooltip_mode = not self.tooltip_mode
                self._flash("tooltips " + ("on" if self.tooltip_mode else "off"))
                continue
            if ch == curses.KEY_F8:
                self._check()
                continue
            if ch == curses.KEY_F9:
                self._preview()
                continue
            if ch == curses.KEY_F10:
                self._build_and_save()
                continue
            if ch in (curses.KEY_ENTER, 10, 13, ord(" ")):
                self._activate(space=(ch == ord(" ")))
                continue

    # ── field interaction ──
    def _editing_field(self) -> bool:
        f = self._cur_field()
        return bool(f) and f.kind in ("text", "int", "float")

    def _cycle(self, d: int):
        f = self._cur_field()
        if not f:
            return
        if f.kind == "toggle":
            self.answers[f.key] = not self.answers.get(f.key, False)
        elif f.kind == "choice":
            opts = f.choices
            cur = self.answers.get(f.key, opts[0] if opts else "")
            i = opts.index(cur) if cur in opts else 0
            self.answers[f.key] = opts[(i + d) % len(opts)]
        elif f.kind == "multi":
            self.multi_cursor = (self.multi_cursor + d) % max(1, len(f.choices))

    def _activate(self, space: bool):
        f = self._cur_field()
        if not f or f.kind == "info":
            return
        if f.kind == "toggle":
            self.answers[f.key] = not self.answers.get(f.key, False)
        elif f.kind == "multi":
            cur = set(self.answers.get(f.key, []))
            cur.symmetric_difference_update({f.choices[self.multi_cursor]})
            self.answers[f.key] = [c for c in f.choices if c in cur]
        elif f.kind == "choice":
            self._cycle(+1)
        elif f.kind in ("text", "int", "float"):
            self._edit_line(f)
        elif f.kind == "list":
            self._edit_list(f)
        elif f.kind == "action":
            self._do_action(f.action)

    # ── inline line editor ──
    def _edit_line(self, f):
        curses.curs_set(1)
        buf = str(self.answers.get(f.key, "") or "")
        pos = len(buf)
        while True:
            self._draw(edit=(f.key, buf, pos))
            ch = self.s.getch()
            if ch == 27:
                break
            if ch in (curses.KEY_ENTER, 10, 13):
                val = buf.strip()
                if f.kind == "int":
                    try:
                        self.answers[f.key] = int(val or 0)
                    except ValueError:
                        self._flash("not an integer"); continue
                elif f.kind == "float":
                    try:
                        self.answers[f.key] = float(val or 0)
                    except ValueError:
                        self._flash("not a number"); continue
                else:
                    self.answers[f.key] = val
                break
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if pos > 0:
                    buf = buf[:pos - 1] + buf[pos:]; pos -= 1
            elif ch == curses.KEY_LEFT:
                pos = max(0, pos - 1)
            elif ch == curses.KEY_RIGHT:
                pos = min(len(buf), pos + 1)
            elif ch == curses.KEY_HOME:
                pos = 0
            elif ch == curses.KEY_END:
                pos = len(buf)
            elif ch == curses.KEY_DC:
                buf = buf[:pos] + buf[pos + 1:]
            elif 32 <= ch < 127:
                buf = buf[:pos] + chr(ch) + buf[pos:]; pos += 1
        curses.curs_set(0)

    # ── list editor modal ──
    def _edit_list(self, f):
        rows = [dict(r) for r in self.answers.get(f.key, [])]
        sel = 0
        g = theme.glyphs(self.unicode_ok)
        while True:
            scr = Rect.screen(self.s)
            box = scr.pct(0.10, 0.12, 0.90, 0.88, min_w=40, min_h=8)
            theme.fill(self.s, box, theme.BASE)
            theme.draw_box(self.s, box, g,
                           f"{f.label}   a add · d delete · ↵ edit cell · Esc done")
            inner = box.inset(1, 2)
            theme.addstr(self.s, inner.y, inner.x,
                         ("  ".join(f"{c:<18}" for c in f.columns))[: inner.w],
                         theme.attr(theme.DIM, bold=True))
            for i, r in enumerate(rows[: inner.h - 2]):
                line = "  ".join(f"{str(r.get(c, '')):<18}" for c in f.columns)
                a = theme.attr(theme.SEL) if i == sel else theme.attr(theme.BASE)
                theme.addstr(self.s, inner.y + 1 + i, inner.x,
                             line[: inner.w].ljust(inner.w), a)
            self.s.refresh()
            ch = self.s.getch()
            if ch == 27:
                break
            if ch == ord("a"):
                rows.append({c: "" for c in f.columns}); sel = len(rows) - 1
            elif ch == ord("d") and rows:
                rows.pop(sel); sel = max(0, sel - 1)
            elif ch in (curses.KEY_UP, ord("k")):
                sel = max(0, sel - 1)
            elif ch in (curses.KEY_DOWN, ord("j")):
                sel = min(len(rows) - 1, sel + 1)
            elif ch in (curses.KEY_ENTER, 10, 13) and rows:
                self._edit_row_cells(f, rows[sel])
        self.answers[f.key] = [r for r in rows if any(v.strip() for v in r.values())]

    def _edit_row_cells(self, f, row: dict):
        for c in f.columns:
            curses.curs_set(1)
            buf = str(row.get(c, ""))
            pos = len(buf)
            while True:
                scr = Rect.screen(self.s)
                bar = scr.pct(0.0, 0.92, 1.0, 1.0, min_h=1)
                theme.fill(self.s, bar, theme.HINT)
                lead = f"{f.label} · {c}: "
                theme.addstr(self.s, bar.y, bar.x, (" " + lead + buf)[: bar.w].ljust(bar.w),
                             theme.attr(theme.HINT))
                self.s.move(bar.y, min(bar.w - 1, bar.x + 1 + len(lead) + pos))
                self.s.refresh()
                ch = self.s.getch()
                if ch in (27, curses.KEY_ENTER, 10, 13):
                    row[c] = buf.strip(); break
                if ch in (curses.KEY_BACKSPACE, 127, 8) and pos > 0:
                    buf = buf[:pos - 1] + buf[pos:]; pos -= 1
                elif 32 <= ch < 127:
                    buf = buf[:pos] + chr(ch) + buf[pos:]; pos += 1
            curses.curs_set(0)

    # ── actions ──
    def _do_action(self, action: str):
        if action == "save_profile":
            if self.answers.get("u_ua"):
                self.answers["ua"] = self.answers["u_ua"]
            self._flash(f"saved {P.save({**self.answers, 'w_tooltip': self.tooltip_mode})}")
        elif action == "load_profile":
            self.answers.update(P.load()); self._flash("profile loaded")
        elif action == "verify_orcid":
            if self.engine is None:
                self._flash("no engine attached — launch the GUI with --engine <dir>")
                return
            orc = self.answers.get("u_orcid", "").strip()
            if not orc:
                self._flash("enter an ORCID first"); return
            try:
                self.engine.identity_set(orc)
                ident = self.engine.identity_verify()
                self.answers["u_name"] = ident.get("name") or self.answers.get("u_name", "")
                self._flash(f"VERIFIED as {ident.get('name')}")
            except Exception as e:  # noqa: BLE001
                self._flash(f"verify failed: {e}")

    # ── faults / preview / build  (all non-fatal) ──
    def _goto_fault(self, fault: dict):
        want = fault.get("tab") or ""
        for i, (name, _) in enumerate(M.TABS):
            if name == want:
                self.tab = i
                break
        self.row = self.scroll = 0
        key = fault.get("field")
        if key:
            fs = self._fields()
            for r, f in enumerate(fs):
                if f.key == key:
                    self.row = r
                    break
            else:
                self._flash(f"field '{key}' is hidden until a related option is set")

    def _check(self):
        faults = F.collect(self.answers)
        if not faults:
            D.message_box(self.s, "✓ .ptorrent check",
                          ["No faults or inconsistencies.",
                           "The file as entered builds cleanly."],
                          ("OK",), self.unicode_ok)
            return
        verb, payload = D.fault_dialog(self.s, faults, save_path=False,
                                       unicode_ok=self.unicode_ok)
        if verb == "fix":
            self._goto_fault(payload)

    def _preview(self):
        try:
            res = M.build(self.answers)
            text = json.dumps(res["ptorrent"], indent=2, ensure_ascii=False)
            warns = res.get("warnings", [])
        except Exception as e:  # noqa: BLE001
            D.message_box(self.s, "✖ cannot build a preview",
                          [str(e), "",
                           "The fields as entered do not form a valid .ptorrent.",
                           "Press F8 to see the full fault list."],
                          ("OK",), self.unicode_ok)
            return
        lines = text.splitlines()
        if warns:
            lines = ["⚠ " + w for w in warns] + ["", "─" * 40, ""] + lines
        self._scroll_view(".ptorrent preview   (↑↓ scroll · any other key closes)", lines)

    def _build_and_save(self):
        faults = F.collect(self.answers)
        errors = [f for f in faults if f["severity"] == "error"]
        actionable = [f for f in faults if f["severity"] in ("error", "warning")]
        if actionable:
            verb, payload = D.fault_dialog(self.s, faults, save_path=True,
                                           unicode_ok=self.unicode_ok)
            if verb == "fix":
                self._goto_fault(payload)
                return
            if verb == "dismiss":
                return
            # verb == "save": only reachable when there are no errors
        if errors:
            return  # never write a file that will not parse

        try:
            doc = M.build(self.answers)["ptorrent"]
        except Exception as e:  # noqa: BLE001
            D.message_box(self.s, "✖ build failed", [str(e)], ("OK",), self.unicode_ok)
            return
        slug = "".join(ch if ch.isalnum() else "_"
                       for ch in doc.get("name", "job").lower())[:40] or "job"
        path = self._prompt("Write .ptorrent to",
                            os.path.join(self.out_dir, f"{slug}.ptorrent"))
        if not path:
            return
        try:
            with open(os.path.expanduser(path), "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=2, ensure_ascii=False)
        except OSError as e:
            D.message_box(self.s, "✖ write failed", [str(e)], ("OK",), self.unicode_ok)
            return
        self.result = f"built:{path}"
        msg = f"wrote {path}"
        if self.engine is not None and D.confirm(self.s, "Add this job to the engine now?",
                                                 unicode_ok=self.unicode_ok):
            try:
                r = self.engine.add(os.path.expanduser(path), start=False)
                msg += f"  ·  job {r['job_id']}  ·  phonebook {r['phonebook_key']}"
            except Exception as e:  # noqa: BLE001
                msg += f"  ·  add failed: {e}"
        warn_n = sum(1 for f in faults if f["severity"] == "warning")
        if warn_n:
            msg += f"   (saved with {warn_n} warning(s))"
        self._flash(msg)

    # ══ drawing ═════════════════════════════════════════════════════════════
    def _draw(self, edit=None):
        self.s.erase()
        if edit is None:
            try:
                self._faults = F.collect(self.answers)
            except Exception:  # noqa: BLE001  — the check itself must never be fatal
                self._faults = []
        self._focus_xy = None
        scr = Rect.screen(self.s)
        g = theme.glyphs(self.unicode_ok)
        head_h = max(2, round(scr.h * 0.10))
        foot_h = max(2, round(scr.h * 0.09))
        head, rest = scr.rows(head_h)
        body, foot = rest.rows(rest.h - foot_h)

        theme.fill(self.s, head, theme.TITLE)
        theme.addstr(self.s, head.y, head.x + 1, "PTorrent — new .ptorrent"[: scr.w - 2],
                     theme.attr(theme.TITLE, bold=True))
        tx = head.x + 1
        for i, (label, _) in enumerate(M.TABS):
            tag = f" {i+1} {label} "
            a = theme.attr(theme.SEL, bold=True) if i == self.tab else theme.attr(theme.DIM)
            theme.addstr(self.s, head.y + max(1, head.h - 1), tx, tag, a)
            tx += len(tag) + 1

        sw = sidebar_width(body.w, self.collapsed)
        main, side = body.cols(sw)
        theme.fill(self.s, main, theme.BASE)
        theme.draw_box(self.s, main, g, M.TABS[self.tab][0])
        self._draw_fields(main.inset(1, 2), edit)
        if sw:
            theme.fill(self.s, side, theme.BASE)
            theme.draw_box(self.s, side, g, "Item Specific Help")
            self._draw_sidebar(side.inset(1, 2))

        errs = sum(1 for x in self._faults if x["severity"] == "error")
        warns = sum(1 for x in self._faults if x["severity"] == "warning")
        right = (f"✖ {errs} error(s)  ▲ {warns}" if errs
                 else (f"▲ {warns} warning(s)  F8" if warns else "✓ ok"))
        theme.fill(self.s, foot, theme.HINT)
        theme.addstr(self.s, foot.y, foot.x + 1,
                     self.status[: max(0, foot.w - len(right) - 3)], theme.attr(theme.HINT))
        theme.addstr(self.s, foot.y, foot.right - len(right) - 1, right,
                     theme.attr(theme.WARN if errs else (theme.ACCENT if warns else theme.HINT),
                                bold=bool(errs or warns)))

        if self.tooltip_mode and edit is None and self._focus_xy:
            self._draw_tooltip(*self._focus_xy)
        self.s.refresh()

    def _draw_tooltip(self, y: int, x: int):
        f = self._cur_field()
        if not f or f.kind in ("info",):
            return
        lines = [MT.unicodize((f.help or "").split(".")[0].strip() or f.label)]
        if f.kind == "choice" and f.choices:
            lines.append("values: " + " / ".join(c or "(default)" for c in f.choices))
        elif f.kind == "toggle":
            lines.append("Space or ←→ to toggle")
        elif f.kind == "multi":
            lines.append("Space toggles the ▸ option")
        elif f.kind == "list":
            lines.append("↵ opens the row editor")
        elif f.kind in ("int", "float"):
            lines.append(f"number — current: {self.answers.get(f.key)}")
        mine = [x for x in self._faults if x.get("field") == f.key]
        for m in mine[:2]:
            gl = "✖" if m["severity"] == "error" else "▲"
            lines.append(f"{gl} {m['message']}")
        D.tooltip(self.s, y, x, [ln[:72] for ln in lines if ln], self.unicode_ok)

    def _draw_fields(self, area: Rect, edit):
        fs = self._fields()
        if self.row < self.scroll:
            self.scroll = self.row
        elif self.row >= self.scroll + area.h:
            self.scroll = self.row - area.h + 1
        label_w = min(28, max(16, area.w // 3))
        for vi in range(area.h):
            fi = self.scroll + vi
            if fi >= len(fs):
                break
            f = fs[fi]
            y = area.y + vi
            focused = fi == self.row
            if focused and f.kind not in ("info",):
                self._focus_xy = (y, area.x + label_w + 2)
            if f.kind == "info":
                theme.addstr(self.s, y, area.x, f.label[: area.w],
                             theme.attr(theme.ACCENT, bold=True))
                continue
            if f.kind == "action":
                theme.addstr(self.s, y, area.x, f"[ {f.label} ]",
                             theme.attr(theme.SEL if focused else theme.OK, bold=True))
                continue
            lbl = (f.label + " ")[:label_w].ljust(label_w, "·")
            val = self._render_value(f, edit)
            line = f"{lbl}: {val}"
            theme.addstr(self.s, y, area.x, line[: area.w].ljust(min(area.w, len(line) + 2)),
                         theme.attr(theme.SEL) if focused else theme.attr(theme.BASE))
            fsev = {x["severity"] for x in self._faults if x.get("field") == f.key}
            if focused and f.required and not str(self.answers.get(f.key, "")).strip():
                theme.addstr(self.s, y, area.right - 11, " required ",
                             theme.attr(theme.WARN, bold=True))
            elif fsev:
                gl = "✖" if "error" in fsev else "▲"
                theme.addstr(self.s, y, area.right - 2, gl,
                             theme.attr(theme.WARN if "error" in fsev else theme.ACCENT,
                                        bold=True))

    def _render_value(self, f, edit) -> str:
        if edit and edit[0] == f.key:
            _, buf, pos = edit
            return buf[:pos] + "▏" + buf[pos:]
        v = self.answers.get(f.key)
        if f.kind == "toggle":
            return "[×] yes" if v else "[ ] no"
        if f.kind == "choice":
            return f"‹ {v or '(default)'} ›"
        if f.kind == "multi":
            parts = []
            for i, opt in enumerate(f.choices):
                mark = "×" if opt in (v or []) else " "
                cur = "▸" if (self._cur_field() is f and i == self.multi_cursor) else " "
                parts.append(f"{cur}[{mark}]{opt}")
            return "  ".join(parts)
        if f.kind == "list":
            return f"[{len(v or [])} row(s)]  (↵ to edit)"
        if f.key in ("j_expr",) and v:
            return f"{v}    ⟶  {MT.unicodize(str(v))}"
        return str(v if v not in (None, "") else "")

    def _draw_sidebar(self, area: Rect):
        f = self._cur_field()
        lines: list[str] = []
        if f:
            lines += textwrap.wrap(MT.unicodize(f.help or ""), area.w) or [""]
            if f.kind == "choice" and f.choices:
                lines += ["", "Values:"] + [f"  {c or '(default)'}" for c in f.choices]
            if f.kind == "multi":
                hz = dict(M.HAZARDS)
                lines += ["", "Toggle with Space:"]
                for opt in f.choices:
                    mark = "×" if opt in (self.answers.get(f.key) or []) else " "
                    lines.append(f"  [{mark}] {opt}")
                    if opt in hz:
                        lines += ["      " + w for w in textwrap.wrap(hz[opt], max(8, area.w - 6))]
            if self.tab == 1 and f.key == "eval_alg":
                alg = self.answers.get("eval_alg", "")
                d = M.TABULAR_FN.get(alg) or M.IMAGE_FN.get(alg)
                if d:
                    lines += ["", "This reduction:"] + textwrap.wrap(MT.unicodize(d), area.w)
                lines += ["", MT.CONSTANTS_LINE, "", "σ-face bands (J):"]
                lines += ["  " + ln for ln in MT.band_table()]
        if self.tab == 2 and self.answers.get("hazards"):
            lines += ["", "── derived ──"] + textwrap.wrap(self._derived_summary(), area.w)
        if self.tab == 3 and f and f.key == "u_keys" and self.engine is not None:
            try:
                from ptorrent_core.keys import keys as _k
                lines += ["", "set: " + (", ".join(_k.list()) or "(none)")]
            except Exception:  # noqa: BLE001
                pass
        for i, ln in enumerate(lines[: area.h]):
            theme.addstr(self.s, area.y + i, area.x, ln[: area.w], theme.attr(theme.HELP))

    def _derived_summary(self) -> str:
        try:
            doc = M.build(self.answers)["ptorrent"]
        except Exception as e:  # noqa: BLE001
            return f"(preview: {e})"
        sec = doc.get("security")
        if not sec:
            return "Level 0 · public · TLP:CLEAR · no security block"
        lab = sec.get("labels", {})
        return (f"{sec.get('classification','?')} · level {sec.get('level','?')} · "
                f"TLP:{lab.get('tlp','?')}"
                + (f" · embargo {sec.get('embargo_until')}" if sec.get("embargo_until") else "")
                + (f" · {','.join(lab.get('hazard_class', []))}"
                   if lab.get("hazard_class") else ""))

    def _warn_count(self) -> int:
        try:
            return len(M.build(self.answers).get("warnings", []))
        except Exception:  # noqa: BLE001
            return 0

    # ── little modals ──
    def _flash(self, msg: str):
        self.status = msg

    def _confirm(self, q: str) -> bool:
        scr = Rect.screen(self.s)
        bar = scr.pct(0.0, 0.92, 1.0, 1.0, min_h=1)
        theme.fill(self.s, bar, theme.WARN)
        theme.addstr(self.s, bar.y, bar.x + 1, q[: bar.w - 2], theme.attr(theme.WARN, bold=True))
        self.s.refresh()
        return self.s.getch() in (ord("y"), ord("Y"))

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

    def _scroll_view(self, title: str, lines: list[str]):
        top = 0
        g = theme.glyphs(self.unicode_ok)
        while True:
            scr = Rect.screen(self.s)
            box = scr.pct(0.04, 0.05, 0.96, 0.95, min_w=40, min_h=8)
            theme.fill(self.s, box, theme.BASE)
            theme.draw_box(self.s, box, g, title)
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


# ── entry points ───────────────────────────────────────────────────────────

def run_embedded(stdscr, engine=None, out_dir=".", tooltips: bool | None = None) -> str | None:
    """Run the wizard on an existing curses screen. Returns 'built:<path>' or None."""
    w = WizardScreen(stdscr, engine, out_dir)
    if tooltips is not None:
        w.tooltip_mode = bool(tooltips)
    return w.run()


def run_standalone(engine=None, out_dir="."):
    return curses.wrapper(lambda scr: WizardScreen(scr, engine, out_dir).run())
