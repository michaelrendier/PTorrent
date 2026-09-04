"""End-to-end smoke test for the PTorrent core spine. Stdlib unittest, no network
in the default path (crawl seeds point at a local file:// via a temp http shim is
overkill — instead we exercise every module that does not require the network,
and one offline crawl with an unreachable host to prove the item statuses)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ptorrent_core import Engine, build_ptorrent, parse_ptfile  # noqa: E402
from ptorrent_core.jexpr import JExpr  # noqa: E402
from ptorrent_core.sigma import classify, SigmaFace  # noqa: E402
from ptorrent_core.corpuslist import CorpusList, ItemStatus  # noqa: E402
from ptorrent_core.errors import PtError, PtErr  # noqa: E402
from ptorrent_core import labels as L  # noqa: E402


class TestJExpr(unittest.TestCase):
    def test_precedence(self):
        self.assertEqual(JExpr("-2**2").eval({}), -4.0)
        self.assertEqual(JExpr("2**-1").eval({}), 0.5)
        self.assertAlmostEqual(JExpr("sqrt(pmra**2 + pmdec**2) / max(parallax, 0.001)")
                               .eval({"pmra": 3, "pmdec": 4, "parallax": 2}), 2.5)

    def test_nan_discipline(self):
        import math
        self.assertTrue(math.isnan(JExpr("a / b").eval({"a": 1, "b": 0})))
        self.assertTrue(math.isnan(JExpr("sqrt(x)").eval({"x": -1})))
        self.assertTrue(math.isnan(JExpr("log(x)").eval({"x": 0})))

    def test_unbound_is_config_error(self):
        with self.assertRaises(PtError) as ctx:
            JExpr("a + b").eval({"a": 1})           # b never bound
        self.assertEqual(ctx.exception.code, PtErr.E_NOTFOUND)

    def test_no_names_leak(self):
        with self.assertRaises(PtError):
            JExpr("__import__('os')").eval({})


class TestSigma(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(classify(0.1), SigmaFace.INF)     # below d*
        self.assertEqual(classify(0.5), SigmaFace.HALF)
        self.assertEqual(classify(2.0), SigmaFace.ONE)
        self.assertEqual(classify(4.3), SigmaFace.TWO)
        self.assertEqual(classify(99.0), SigmaFace.INF)    # force extreme

    def test_nonfinite_is_undefined_not_inf(self):
        self.assertEqual(classify(float("nan")), SigmaFace.UNDEFINED)
        self.assertEqual(classify(float("inf")), SigmaFace.UNDEFINED)


class TestCorpusList(unittest.TestCase):
    def test_wide_tag_and_count_dont_drop(self):
        text = "# header\n[DARK_MATTER] https://example.org/a\ngarbage line\n\n[TAG2] https://example.org/b\n"
        cl = CorpusList.parse(text)
        self.assertEqual(cl.count_status(ItemStatus.OK), 2)         # DARK_MATTER survives
        self.assertEqual(cl.count_status(ItemStatus.MALFORMED), 1)  # 'garbage line' counted
        self.assertEqual(cl.count_status(ItemStatus.IGNORED), 2)


class TestPtFileValidation(unittest.TestCase):
    def test_fail_closed(self):
        with self.assertRaises(PtError):
            parse_ptfile(json.dumps({"ptorrent_version": "1.2", "type": "corpus",
                                     "name": "x", "color": "gold", "description": ""}))
        # ↑ no bin, no txt/urls/seeds

    def test_security_requires_labels(self):
        with self.assertRaises(PtError):
            parse_ptfile(json.dumps({
                "type": "corpus", "name": "x", "color": "red", "description": "",
                "bin": "m.bin", "urls": [{"tag": "T", "url": "https://e.org/x"}],
                "security": {"level": 2, "classification": "restricted"}}))


class TestLabels(unittest.TestCase):
    def test_tlp_caps(self):
        self.assertTrue(L.TLP_CAPS["CLEAR"]["phonebook_list"])
        self.assertFalse(L.TLP_CAPS["AMBER+STRICT"]["grant_transitive"])

    def test_labels_hash_ignores_epss(self):
        a = {"tlp": "AMBER", "cwe": ["CWE-327"], "epss": 0.1}
        b = {"tlp": "AMBER", "cwe": ["CWE-327"], "epss": 0.9}
        self.assertEqual(L.labels_hash(a), L.labels_hash(b))


class TestWizard(unittest.TestCase):
    def test_clean_dataset_is_level0(self):
        out = build_ptorrent({"name": "SPARC", "type": "corpus",
                              "seeds": [{"tag": "RC", "url": "https://astroweb.cwru.edu/SPARC/"}],
                              "hazards": []})
        self.assertNotIn("security", out["ptorrent"])

    def test_level3_dualuse(self):
        out = build_ptorrent({
            "name": "ECC attack", "type": "evaluation",
            "evaluation": {"j_expr": "a / b", "j_expr_cols": ["a", "b"]},
            "hazards": ["crypto_exploitable"], "level3_test": True,
            "embargo_until": "2027-06-03", "contact_orcid": "0000-0002-1825-0097",
            "cwe": ["CWE-327"]})
        sec = out["ptorrent"]["security"]
        self.assertEqual(sec["level"], 3)
        self.assertEqual(sec["labels"]["tlp"], "AMBER+STRICT")
        self.assertIn("crypto-attack-vector", sec["labels"]["hazard_class"])


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ptcore-")
        self.e = Engine(self.tmp)

    def tearDown(self):
        self.e.close()

    def test_add_and_phonebook_intake(self):
        doc = {
            "ptorrent_version": "1.2", "type": "corpus", "name": "Physics corpus",
            "color": "cyan", "description": "wave mechanics", "bin": "monad_physics.bin",
            "primary_tags": ["PHYSICS"],
            "crawl": {"seeds": [{"tag": "WAVES", "url": "https://nonexistent.invalid/x"}],
                      "politeness": {"on_robots_unreachable": "deny"}},
        }
        res = self.e.add(doc, start=False)
        self.assertIn("job_id", res)
        self.assertEqual(res["quarantine"], "admitted")
        # phonebook got the entry
        hits = self.e.phonebook_search("Physics")
        self.assertTrue(any(h["name"] == "Physics corpus" for h in hits))
        snap = self.e.snapshot()
        self.assertEqual(len(snap["jobs"]), 1)
        self.assertTrue(snap["chain"]["valid"])

    def test_identity_gate_blocks_vote(self):
        with self.assertRaises(PtError) as ctx:
            self.e.vote("deadbeef", "up")
        self.assertEqual(ctx.exception.code, PtErr.E_IDENTITY)

    def test_identity_checksum(self):
        i = self.e.identity_set("0000-0002-1825-0097")   # a valid ORCID checksum
        self.assertEqual(i["state"], "CLAIMED")
        with self.assertRaises(PtError):
            self.e.identity_set("1234-5678-9012-3456")   # bad check digit

    def test_offline_crawl_marks_items(self):
        # 127.0.0.1:9 (discard) refuses instantly -> robots unreachable -> deny
        doc = {
            "type": "corpus", "name": "offline job", "color": "gold",
            "description": "", "bin": "m.bin",
            "crawl": {"seeds": [{"tag": "T", "url": "http://127.0.0.1:9/a"}],
                      "politeness": {"on_robots_unreachable": "deny",
                                     "backoff": {"on": [429, 503], "base_s": 1,
                                                 "max_s": 2, "give_up_after": 1}}},
        }
        res = self.e.add(doc, start=True)
        jid = res["job_id"]
        for _ in range(150):
            if self.e.job(jid)["status"] in ("DONE", "ERROR"):
                break
            __import__("time").sleep(0.2)
        items = self.e.items(jid)
        self.assertGreaterEqual(len(items), 1)
        self.assertIn(items[0]["status"],
                      ("ROBOTS_DENIED", "ERROR", "DEFERRED", "SKIPPED", "PENDING"))

    def test_chain_export_case_and_native(self):
        self.e.add({"type": "phonebook", "name": "SDSS", "color": "cyan",
                    "description": "survey",
                    "phonebook": {"dataset_url": "https://skyserver.sdss.org/"}})
        native = self.e.chain_export("native")
        self.assertIn("blocks", native)
        case = self.e.chain_export("case")
        self.assertIn("@graph", case)
        self.assertTrue(any(n["uco-core:description"] == "PHONEBOOK_ADD"
                            for n in case["@graph"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
