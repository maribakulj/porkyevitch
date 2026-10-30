"""D3 core and runner on fake data (numpy, scipy, torch CPU). Run: python -I tests/test_d3.py"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import d3_core as d3  # noqa: E402
import d3_run as run  # noqa: E402

REAL_DATA = run.Data

E3 = Path.home() / "porkyevitch/experiences/2026-10-25-iconclass-architecture/scripts/e3_spatial.py"
CODES = ["11", "11H", "11H1", "11H2", "11H(JEROME)", "25", "25F", "25F2", "25F3", "31A", "31A1", "86A", "1:86A", "7", "71",
         "72"]


class CoreTest(unittest.TestCase):
    @unittest.skipUnless(E3.is_file(), "historical E3 script absent")
    def test_parity_with_e3(self):
        tree = ast.parse(E3.read_text())
        keep = [x for x in tree.body if (isinstance(x, ast.FunctionDef) and x.name in
                {"ancestors", "hier_f1", "most_specific", "drop86"}) or
                (isinstance(x, ast.Assign) and any(getattr(t, "id", "") in {"PART", "TOKEN", "_anc"} for t in x.targets))]
        ns = {"re": re}
        exec(compile(ast.Module(keep, []), "e3", "exec"), ns)
        for c in CODES + [" 86(x)", "bad code"]:
            self.assertEqual(set(d3.ancestors(c)), set(ns["ancestors"](c)))
            self.assertEqual(d3.drop86([c]), ns["drop86"]([c]))

    def test_depth_case_and_parent(self):
        self.assertEqual(d3.depth_case("11H(JEROME)"), "4")
        self.assertEqual(d3.depth_case("1:86A"), "compose")
        self.assertEqual(d3.direct_parent("11H(JEROME)"), "11H")
        self.assertIsNone(d3.direct_parent("1:86A"))

    def test_families_by_training_support(self):
        vocab = sorted(set().union(*(d3.ancestors(c) for c in CODES)))
        n = {c: 200 for c in vocab}
        n["11H2"] = 3
        fam = d3.families(vocab, n)
        self.assertEqual(fam["11H"], ["11H(JEROME)", "11H1"])           # 11H2 below 5, composites and 86 out
        self.assertNotIn("86", fam)

    def test_routed_set_replaces_children_and_uses_gate(self):
        children, parent_of = ["11H1", "11H2"], {"11H1": "11H", "11H2": "11H"}
        out = d3.routed_set(["11H", "11H1", "7"], d3.closure(["11H1", "7"]), [0.1, 0.9], children, parent_of, 0.5)
        self.assertEqual(sorted(out), ["11H2", "7"])                    # B's 11H1 replaced by the head's 11H2
        out = d3.routed_set(["7"], d3.closure(["7"]), [0.9, 0.9], children, parent_of, 0.5)
        self.assertEqual(out, ["7"])                                    # gate closed: no child

    def test_child_counts_identity(self):
        c = d3.child_counts([["11H1", "11H2"], ["11H1"]], [["11H1"], []], ["11H1", "11H2"],
                            [{"11H1", "11H2"}, set()])
        self.assertEqual((c["true_children"], c["excluded_by_gate"], c["hits"]), (3, 1, 1))
        self.assertAlmostEqual(c["total_recall"], c["gate_coverage"] * c["conditional_recall"])

    def test_choose_t(self):
        curves = {0.3: {"precision": 0.5, "total_recall": 0.6}, 0.5: {"precision": 0.7, "total_recall": 0.4},
                  0.6: {"precision": 0.8, "total_recall": 0.4}}
        self.assertEqual(d3.choose_t(curves, 0.65, (0.3, 0.5, 0.6)), (0.6, False))
        self.assertEqual(d3.choose_t(curves, 0.9, (0.3, 0.5, 0.6)), (0.95, True))
        # B emits no child: its precision is None; reproduced TypeError of Codex p4, now the flagged 0.95
        self.assertEqual(d3.choose_t(curves, None, (0.3, 0.5, 0.6)), (0.95, True))

    def test_identity_with_closed_gate(self):
        # true children but the gate always closed: coverage 0, conditional None (reproduced TypeError of Codex p4)
        c = d3.child_counts([["11H1"], ["11H2"]], [[], []], ["11H1", "11H2"], [set(), set()])
        self.assertEqual((c["gate_coverage"], c["conditional_recall"], c["total_recall"]), (0.0, None, 0.0))
        run.check_identity(c, "closed")
        run.check_identity(d3.child_counts([[]], [[]], ["11H1"], [set()]), "no_true_child")
        bad = dict(c, hits=1)
        with self.assertRaises(RuntimeError):
            run.check_identity(bad, "closed_but_hit")
        with self.assertRaises(RuntimeError):
            run.check_identity(dict(c, gate_coverage=0.5, conditional_recall=0.5, total_recall=0.3), "broken")

    def test_no_silent_cpu_fallback(self):
        import torch
        saved = os.environ.pop(run.CPU_TEST_FLAG, None)
        try:
            if torch.cuda.is_available() and "T4" in torch.cuda.get_device_name(0):
                self.skipTest("a T4 is present")
            with self.assertRaises(RuntimeError):
                run.device()
        finally:
            if saved is not None:
                os.environ[run.CPU_TEST_FLAG] = saved

    def test_judges(self):
        self.assertTrue(d3.rule_g(0.596, 0.59, 0.30, 0.305))
        self.assertEqual(d3.route_r(0.1, 0.07, 0.586, 0.59, 0.3, 0.3, 99), "indecidable_moins_de_100_occurrences")
        self.assertTrue(d3.route_r(0.1, 0.07, 0.586, 0.59, 0.3, 0.3, 150))

    def test_mix_weight_zero_is_identity(self):
        p = np.random.default_rng(0).random(10).astype(np.float32)
        self.assertTrue(np.array_equal(d3.mix_rare(p, np.ones(3), np.array([1, 4, 7]), 0.0), p))

    def test_votes_closed_and_zero_weights(self):
        cl = {0: d3.closure(["11H1"]), 1: d3.closure(["25F"])}
        v = d3.votes([0, 1], [0.6, -0.2], cl.get, {"11H": 0, "25F": 1})
        self.assertEqual(v.tolist(), [1.0, 0.0])                        # negative cosine weighs 0

    def test_bootstrap_paired_and_deterministic(self):
        a = d3.bootstrap_groups({"x": [1, 0, 1, 0], "y": [0, 0, 1, 0]}, ["a", "a", "b", "c"], draws=600)
        b = d3.bootstrap_groups({"x": [1, 0, 1, 0], "y": [0, 0, 1, 0]}, ["a", "a", "b", "c"], draws=600)
        self.assertTrue(np.array_equal(a["x"], b["x"]))
        self.assertTrue((a["x"] - a["y"] >= -1e-12).all())


class FakeData:
    def __init__(self, n_fit=900, n_val=80, seed=0):
        rng = np.random.default_rng(seed)
        self.vocab = sorted(set().union(*(d3.ancestors(c) for c in CODES)))
        self.labels = [list(rng.choice(CODES, rng.integers(1, 3), replace=False)) for _ in range(n_fit + n_val)]
        self.fit, self.val = np.arange(n_fit), np.arange(n_fit, n_fit + n_val)
        self.n_raw, self.n_closed = {}, {}
        for i in self.fit:
            for c in set(self.labels[i]):
                self.n_raw[c] = self.n_raw.get(c, 0) + 1
            for c in d3.closure(self.labels[i]):
                self.n_closed[c] = self.n_closed.get(c, 0) + 1
        self.pb = rng.random((n_val, len(self.vocab))).astype(np.float32)
        self.b_pred = d3.project(self.pb, self.vocab, 0.65)
        self.truth = [d3.drop86(self.labels[i]) for i in self.val]
        self.eligible = [k for k, g in enumerate(self.truth) if g]
        self.vmd5 = [f"{k // 2:032x}" for k in range(n_val)]
        self.md5 = [f"{i:032x}" for i in range(n_fit)] + self.vmd5
        self.reg = [k for k in range(n_val) if (k // 2) % 2 == 0]
        self.lec = [k for k in range(n_val) if (k // 2) % 2 == 1]
        self.universe = sorted(set(d3.drop86(list(set(self.n_raw) | set(self.vocab)))))
        self.xf = rng.normal(size=(n_fit, 16)).astype(np.float32)
        self.xf /= np.linalg.norm(self.xf, axis=1, keepdims=True)
        self.xv = rng.normal(size=(n_val, 16)).astype(np.float32)
        self.xv /= np.linalg.norm(self.xv, axis=1, keepdims=True)
        self._cl = {}
        self.closure_fit = lambda j: d3.closure(self.labels[self.fit[j]])

    def neighbours(self, rows):
        return REAL_DATA.neighbours(self, rows)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(run, k) for k in ("Data", "EPOCHS", "DECISIONS_SHA256")}
        self.fake = FakeData()
        os.environ[run.CPU_TEST_FLAG] = "1"
        run.Data = lambda *a: self.fake
        run.EPOCHS = 2
        run.DECISIONS_SHA256 = run.legacy_sha([sorted(q) for q in self.fake.b_pred])

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(run, k, v)
        os.environ.pop(run.CPU_TEST_FLAG, None)

    def test_blank_then_complete(self):
        root = Path(tempfile.mkdtemp())
        A = lambda **k: type("A", (), dict(encoder="", inventory="", diag="", **k))
        run.stage_blanc(A(out=str(root / "blanc")))
        blank = root / "blanc" / "blanc.json"
        info = json.loads(blank.read_text())
        self.assertEqual(info["weight_zero_identity_rows"], 80)
        self.assertIsNone(info["scores"])
        self.assertEqual(info["environment"]["device"], "cpu")
        self.assertTrue(info["environment"]["local_cpu_test"])
        self.assertIn("numpy float32 on CPU", info["environment"]["neighbours"])
        blank.write_text(json.dumps({**info, "status": "WITHIN_2H"}))
        run.stage_complet(A(out=str(root / "complet"), blank=str(blank),
                            blank_sha256=hashlib.sha256(blank.read_bytes()).hexdigest()))
        b1 = json.loads((root / "complet" / "bras1.json").read_text())
        b2 = json.loads((root / "complet" / "bras2.json").read_text())
        self.assertIn("G", b1["verdict"])
        self.assertEqual(sorted(b2["seeds"]), ["0", "1", "2"])
        self.assertTrue(all(s["t"] in run.THRESHOLDS + (0.95,) for s in b2["seeds"].values()))
        self.assertIn("not concept recognition", b2["counting"])
        # a blank from another environment is refused by the complete stage
        other = root / "blanc" / "other.json"
        info2 = json.loads(blank.read_text())
        info2["environment"] = dict(info2["environment"], torch="0.0")
        other.write_text(json.dumps(info2))
        with self.assertRaises(RuntimeError):
            run.stage_complet(A(out=str(root / "complet2"), blank=str(other),
                                blank_sha256=hashlib.sha256(other.read_bytes()).hexdigest()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
