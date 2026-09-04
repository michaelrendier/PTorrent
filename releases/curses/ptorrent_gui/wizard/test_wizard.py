"""Model tests for File ▸ New. The interactive UI needs a real terminal; this
exercises the geometry math, the answers → .ptorrent mapping (through the core's
authoritative builder), the Unicode math helper, and a headless render pass."""
from __future__ import annotations

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
# .../releases/curses/ptorrent_gui/wizard  ->  repo/core/python  and  releases/curses
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "core", "python")))
sys.path.insert(0, os.path.normpath(os.path.join(_HERE, "..", "..")))

from ptorrent_gui.wizard import model as M                      # noqa: E402
from ptorrent_gui.wizard import faults as F                      # noqa: E402
from ptorrent_gui.common import geometry, mathtext, theme, dialog  # noqa: E402,F401
from ptorrent_core import parse_ptfile                           # noqa: E402


class TestMathText(unittest.TestCase):
    def test_unicodize_display_only(self):
        self.assertEqual(mathtext.unicodize("x**2 <= y"), "x² ≤ y")
        self.assertEqual(mathtext.unicodize("2**-1"), "2⁻¹")
        self.assertIn("√", mathtext.unicodize("sqrt(a)"))
        self.assertIn("Ω_ZS", mathtext.unicodize("OMEGA_ZS"))
        self.assertEqual(len(mathtext.band_table()), 6)


class TestGeometry(unittest.TestCase):
    def test_pct_scales(self):
        r = geometry.Rect(0, 0, 24, 80)
        self.assertEqual((r.pct(0, 0, 0.5, 1.0).w, r.pct(0, 0, 0.5, 1.0).h), (40, 24))
        self.assertEqual(geometry.sidebar_width(80, collapsed=False), 0)
        self.assertEqual(geometry.sidebar_width(120, collapsed=True), 0)
        self.assertGreaterEqual(geometry.sidebar_width(200, collapsed=False), 44)


class TestBuild(unittest.TestCase):
    def _valid(self, doc):
        parse_ptfile(json.dumps(doc))

    def test_plain_corpus_crawl(self):
        doc = M.build({"name": "Wave mechanics", "type": "corpus", "color": "cyan",
                       "description": "waves", "primary_tags": "PHYSICS",
                       "seeds": [{"tag": "WAVES", "url": "https://en.wikipedia.org/wiki/Wave_equation"}],
                       "resolution": ["declared_api", "known_api", "html"],
                       "ua": "Mozilla/5.0 (compatible; PtorrentBot/1.0; +https://x)",
                       "max_pages": 200, "hazards": []})["ptorrent"]
        self.assertEqual(doc["crawl"]["seeds"][0]["tag"], "WAVES")
        self.assertEqual(doc["crawl"]["scope"]["max_pages"], 200)
        self.assertNotIn("security", doc)
        self._valid(doc)

    def test_image_evaluation(self):
        doc = M.build({"name": "5000 thumbnails", "type": "evaluation", "color": "orange",
                       "description": "entropy scan", "primary_tags": "IMAGES",
                       "seeds": [{"tag": "IMG", "url": "https://example.org/api/images"}],
                       "enable_eval": True, "eval_alg": "img_entropy_ratio",
                       "fn_params": "bins=64", "max_rows": 5000, "hazards": []})["ptorrent"]
        self.assertEqual(doc["evaluation"]["fn"], "img_entropy_ratio")
        self.assertEqual(doc["evaluation"]["fn_params"], {"bins": 64})
        self._valid(doc)

    def test_cyber_level3_with_provenance(self):
        doc = M.build({"name": "ECC sedenion scan", "type": "evaluation", "color": "red",
                       "description": "attack vector eval", "primary_tags": "SECURITY",
                       "seeds": [{"tag": "D", "url": "https://example.org/api/curve"}],
                       "enable_eval": True, "eval_alg": "j_expr", "j_expr": "a / b",
                       "j_expr_cols": "a,b", "hazards": ["crypto_exploitable"],
                       "level3_test": True, "embargo_until": "2027-06-03",
                       "contact_orcid": "0000-0002-1825-0097", "cwe": "CWE-327",
                       "cvss_vector": "CVSS:4.0/AV:N/AC:L", "cvss_score": 8.1,
                       "auth_provenance": [
                           {"match": "s3://stpubdata/", "kind": "institutional", "detail": "MAST"},
                           {"match": "/media/rendier/Datasets/", "kind": "orcid-session", "detail": ""}]
                       })["ptorrent"]
        sec = doc["security"]
        self.assertEqual(sec["level"], 3)
        self.assertEqual(sec["labels"]["tlp"], "AMBER+STRICT")
        self.assertIn("crypto-attack-vector", sec["labels"]["hazard_class"])
        self.assertEqual(doc["auth_provenance"][0]["match"], "s3://stpubdata/")
        self._valid(doc)

    def test_poisoned_defensive(self):
        doc = M.build({"name": "adv benchmark", "type": "corpus", "color": "purple",
                       "description": "", "primary_tags": "ML", "bin": "m.bin",
                       "seeds": [{"tag": "T", "url": "https://example.org/x"}],
                       "hazards": ["poisonable"], "atlas_offensive": False,
                       "atlas_techniques": "AML.T0019", "atlas_mitigations": "AML.M0007"})["ptorrent"]
        self.assertEqual(doc["security"]["labels"]["tlp"], "GREEN")
        self.assertIn("adversarial-benchmark", doc["security"]["labels"]["hazard_class"])
        self._valid(doc)

    def test_phonebook_entry(self):
        doc = M.build({"name": "SDSS SkyServer", "type": "phonebook", "color": "cyan",
                       "description": "sky survey", "primary_tags": "ASTRO",
                       "dataset_url": "https://skyserver.sdss.org/", "license": "CC-BY-4.0",
                       "hazards": []})["ptorrent"]
        self.assertEqual(doc["type"], "phonebook")
        self.assertEqual(doc["phonebook"]["dataset_url"], "https://skyserver.sdss.org/")
        self._valid(doc)


class TestFaults(unittest.TestCase):
    def _sev(self, faults, sev):
        return [f for f in faults if f["severity"] == sev]

    def test_never_raises_on_garbage(self):
        for a in ({}, {"name": ""}, {"type": "evaluation", "enable_eval": True},
                  {"name": "x", "seeds": [{"url": "not a url"}]}):
            self.assertIsInstance(F.collect(a), list)   # no exception

    def test_missing_name_is_error(self):
        fs = F.collect({"type": "corpus"})
        self.assertTrue(any(f["field"] == "name" and f["severity"] == "error" for f in fs))

    def test_level3_without_embargo_is_error_not_fatal(self):
        fs = F.collect({"name": "v", "type": "evaluation", "enable_eval": True,
                        "eval_alg": "j_expr", "j_expr": "a/b", "j_expr_cols": "a,b",
                        "hazards": ["crypto_exploitable"], "level3_test": True})
        errs = self._sev(fs, "error")
        self.assertTrue(any(f["field"] == "embargo_until" for f in errs))
        self.assertTrue(any(f["field"] == "contact_orcid" for f in errs))

    def test_jexpr_undeclared_column_is_warning(self):
        fs = F.collect({"name": "v", "type": "evaluation", "enable_eval": True,
                        "eval_alg": "j_expr", "j_expr": "a / c", "j_expr_cols": "a,b",
                        "seeds": [{"tag": "T", "url": "https://x/y"}], "hazards": []})
        self.assertTrue(any(f["field"] == "j_expr_cols" and f["severity"] == "warning"
                            and "c" in f["message"] for f in fs))

    def test_bad_orcid_checksum_is_warning(self):
        fs = F.collect({"name": "v", "type": "corpus", "bin": "m.bin",
                        "seeds": [{"tag": "T", "url": "https://x/y"}],
                        "u_orcid": "0000-0000-0000-0000", "hazards": []})
        self.assertTrue(any(f["field"] == "u_orcid" and f["severity"] == "warning" for f in fs))

    def test_tlp_downgrade_is_error(self):
        fs = F.collect({"name": "v", "type": "corpus", "bin": "m.bin",
                        "seeds": [{"tag": "T", "url": "https://x/y"}],
                        "hazards": ["crypto_exploitable"], "level3_test": True,
                        "embargo_until": "2027-06-03", "contact_orcid": "0000-0002-1825-0097",
                        "tlp": "CLEAR"})
        self.assertTrue(any(f["field"] == "tlp" and f["severity"] == "error" for f in fs))

    def test_clean_input_no_actionable_faults(self):
        fs = F.collect({"name": "SPARC", "type": "corpus", "color": "cyan",
                        "description": "rc", "primary_tags": "ASTRO", "bin": "m.bin",
                        "seeds": [{"tag": "RC", "url": "https://astroweb.cwru.edu/SPARC/"}],
                        "hazards": []})
        self.assertEqual([f for f in fs if f["severity"] in ("error", "warning")], [])


class _FakeScr:
    def __init__(self, h, w): self._h, self._w = h, w
    def getmaxyx(self): return (self._h, self._w)
    def erase(self): pass
    def refresh(self): pass
    def keypad(self, *_): pass
    def move(self, *_): pass
    def addstr(self, *_a, **_k): pass
    def getch(self): return -1


class TestRenderHeadless(unittest.TestCase):
    def setUp(self):
        import curses
        from ptorrent_gui.wizard import wizard as W
        from ptorrent_gui.common import theme as T
        for name in ("init", "fill", "draw_box"):
            setattr(T, name, lambda *a, **k: None)
        T.addstr = lambda *a, **k: None
        T.attr = lambda *a, **k: 0
        T.glyphs = lambda *_: {k: "+" for k in
                               ("tl", "tr", "bl", "br", "h", "v", "lt", "rt",
                                "check", "empty", "arrow")}
        curses.curs_set = lambda *_: None
        self.W = W

    def test_draw_all_tabs_all_sizes(self):
        for (h, w) in ((24, 80), (14, 60), (60, 220), (40, 140)):
            a = self.W.WizardScreen(_FakeScr(h, w), engine=None, out_dir="/tmp")
            for tips in (False, True):
                a.tooltip_mode = tips
                for t in range(4):
                    a.tab = t
                    for r in range(len(a._fields())):
                        a.row = r
                        a._draw()
            a.collapsed = True
            a._draw()

    def test_faults_surface_in_footer_and_rows(self):
        a = self.W.WizardScreen(_FakeScr(40, 140), engine=None, out_dir="/tmp")
        a.answers["name"] = ""                       # -> an error fault on 'name'
        a._draw()
        self.assertTrue(any(f["severity"] == "error" for f in a._faults))
        # navigating to a fault must not raise
        err = next(f for f in a._faults if f["severity"] == "error")
        a._goto_fault(err)

    def test_derive_dualuse(self):
        a = self.W.WizardScreen(_FakeScr(40, 140), engine=None, out_dir="/tmp")
        a.answers["name"] = "ECC scan"
        a.tab = 2
        f = next(f for f in a._fields() if f.key == "hazards")
        a.row = a._fields().index(f)
        a.multi_cursor = f.choices.index("crypto_exploitable")
        a._activate(space=True)
        a.answers["level3_test"] = True
        summ = a._derived_summary()
        self.assertIn("dual-use", summ)
        self.assertIn("AMBER+STRICT", summ)


if __name__ == "__main__":
    unittest.main(verbosity=2)
