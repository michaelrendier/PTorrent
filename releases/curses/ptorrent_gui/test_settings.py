"""Settings + alarms tests. The interactive screen needs a real terminal;
this covers the config store, the alarm rule engine, and a headless render."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", "..", "core", "python")))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..")))

from ptorrent_gui import alarms as A            # noqa: E402
from ptorrent_gui import config as C            # noqa: E402


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ptcfg-")
        os.environ["PTOL_CONFIG_DIR"] = self.tmp
        import importlib
        importlib.reload(C)

    def test_defaults_and_roundtrip(self):
        cfg = C.load()
        self.assertTrue(C.get(cfg, "notifications.enabled"))
        self.assertEqual(C.get(cfg, "alarms")[0]["name"], "still-alive ping")
        C.set_(cfg, "notifications.channel", "desktop")
        C.set_(cfg, "display.tooltips_default", True)
        C.save(cfg)
        back = C.load()
        self.assertEqual(C.get(back, "notifications.channel"), "desktop")
        self.assertTrue(C.get(back, "display.tooltips_default"))
        # unknown keys fall back to defaults via merge
        self.assertIn("job_error", C.get(back, "notifications.events"))

    def test_get_set_dotted(self):
        cfg = {"a": {"b": 1}}
        self.assertEqual(C.get(cfg, "a.b"), 1)
        self.assertIsNone(C.get(cfg, "a.c.d"))
        C.set_(cfg, "a.c.d", 9)
        self.assertEqual(cfg["a"]["c"]["d"], 9)


class TestAlarms(unittest.TestCase):
    def _snap(self, *statuses, **progress):
        return {"jobs": [{"id": f"j{i}", "name": f"job {i}", "status": s,
                          "progress": dict(progress)} for i, s in enumerate(statuses)]}

    def test_periodic_while_running_respects_interval(self):
        rule = {"name": "ping", "enabled": True, "when": "periodic_while_running",
                "every": {"n": 3, "unit": "hours"}, "action": "bell", "scope": "any_job"}
        state = {}
        snap = self._snap("RUNNING")
        t0 = 1_000_000.0
        self.assertEqual(len(A.evaluate([rule], snap, state, now=t0)), 1)          # first tick
        self.assertEqual(len(A.evaluate([rule], snap, state, now=t0 + 600)), 0)    # 10 min later: quiet
        self.assertEqual(len(A.evaluate([rule], snap, state, now=t0 + 3 * 3600 + 1)), 1)  # 3h+: ding
        self.assertEqual(A.evaluate([rule], self._snap("DONE"), state, now=t0 + 99999), [])  # nothing running

    def test_running_longer_than(self):
        rule = {"name": "12d", "enabled": True, "when": "job_running_longer_than",
                "threshold": {"n": 12, "unit": "days"}, "every": {"n": 3, "unit": "hours"},
                "repeat": True, "action": "desktop", "scope": "each_job"}
        state = {}
        snap = self._snap("RUNNING", studied=100)
        t0 = 2_000_000.0
        A.evaluate([rule], snap, state, now=t0)                     # register start
        self.assertEqual(A.evaluate([rule], snap, state, now=t0 + 11 * 86400), [])  # not yet 12d
        hits = A.evaluate([rule], snap, state, now=t0 + 12 * 86400 + 60)
        self.assertEqual(len(hits), 1)
        self.assertIn("still running", hits[0]["message"])
        self.assertIn("12d", hits[0]["message"])

    def test_all_done_fires_once(self):
        rule = {"name": "finish", "enabled": True, "when": "all_done", "action": "bell"}
        state = {}
        self.assertEqual(A.evaluate([rule], self._snap("RUNNING", "DONE"), state), [])
        got = A.evaluate([rule], self._snap("DONE", "DONE"), state)
        self.assertEqual(len(got), 1)
        self.assertEqual(A.evaluate([rule], self._snap("DONE", "DONE"), state), [])  # not again

    def test_disabled_rule_never_fires(self):
        rule = {"name": "x", "enabled": False, "when": "periodic_while_running",
                "every": {"n": 1, "unit": "minutes"}, "action": "bell"}
        self.assertEqual(A.evaluate([rule], self._snap("RUNNING"), {}), [])

    def test_fire_is_safe_when_disabled(self):
        A.fire("bell", "hi", {"enabled": False})       # must not raise
        A.fire("status", "hi", {"enabled": True, "channel": "bell"})  # status = caller renders


class _FakeScr:
    def __init__(self, h, w): self._h, self._w = h, w
    def getmaxyx(self): return (self._h, self._w)
    def erase(self): pass
    def refresh(self): pass
    def keypad(self, *_): pass
    def move(self, *_): pass
    def addstr(self, *_a, **_k): pass
    def getch(self): return -1


class TestSettingsRender(unittest.TestCase):
    def setUp(self):
        import curses
        from ptorrent_gui.common import theme as T
        for n in ("init", "fill", "draw_box"):
            setattr(T, n, lambda *a, **k: None)
        T.addstr = lambda *a, **k: None
        T.attr = lambda *a, **k: 0
        T.glyphs = lambda *_: {k: "+" for k in
                               ("tl", "tr", "bl", "br", "h", "v", "lt", "rt",
                                "check", "empty", "arrow")}
        curses.curs_set = lambda *_: None

    def test_draw_all_rows_all_sizes(self):
        from ptorrent_gui.settings import SettingsScreen
        cfg = C.load()
        for (h, w) in ((24, 80), (16, 60), (50, 200)):
            sc = SettingsScreen(_FakeScr(h, w), cfg)
            for r in range(len(sc._fields())):
                sc.row = r
                sc._draw()

    def test_f10_saves_and_returns(self):
        import curses
        from ptorrent_gui.common import dialog as Dlg
        Dlg.message_box = lambda *a, **k: "OK"      # no interactive dialog
        from ptorrent_gui.settings import SettingsScreen

        class _Keyed(_FakeScr):
            def __init__(s, keys):
                super().__init__(40, 160); s._k = list(keys)
            def getch(s):
                return s._k.pop(0) if s._k else 27

        tmp = tempfile.mkdtemp(prefix="ptcfg2-")
        os.environ["PTOL_CONFIG_DIR"] = tmp
        import importlib
        importlib.reload(C)
        cfg = C.load()
        sc = SettingsScreen(_Keyed([curses.KEY_F10]), cfg)
        out = sc.run()
        self.assertIsNotNone(out)
        self.assertTrue(os.path.exists(os.path.join(tmp, "gui.json")))


class TestShellTick(unittest.TestCase):
    def test_tick_fires_alarm_via_fake_engine(self):
        from ptorrent_gui import alarms as _A
        from ptorrent_gui import shell as SH
        rung = []
        _A.fire = lambda action, msg, ncfg: rung.append((action, msg))

        class _Eng:
            def snapshot(self):
                return {"jobs": [{"id": "j0", "name": "big pull", "status": "RUNNING",
                                  "progress": {"studied": 3}}]}
            def events(self, since=0, limit=200):
                return []

        sh = SH.Shell.__new__(SH.Shell)
        sh.engine = _Eng()
        sh.cfg = C.load()
        sh._alarm_state = {}
        sh._last_seq = 0
        sh.status = ""
        # first tick registers + fires the still-alive ping (interval elapsed from 0)
        sh._tick()
        self.assertTrue(rung, "expected the still-alive alarm to fire on first tick")
        self.assertIn("big pull", rung[0][1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
