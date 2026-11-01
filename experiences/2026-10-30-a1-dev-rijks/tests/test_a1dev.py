"""A1-dev on fictitious data (numpy and scipy, no torch, no network). Run: python -I tests/test_a1dev.py"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import a1_core as a1  # noqa: E402
import a1dev_core as dc  # noqa: E402
import a1dev_run as run  # noqa: E402
import kaggle_a1dev_run as k  # noqa: E402

VOCAB = ["1", "11", "11H", "11H1", "2", "25", "25F"]


class CoreTest(unittest.TestCase):
    def test_paired_component_bootstrap_and_reading(self):
        comps = [1, 1, 2, 3, 3, 3, 4, 5]
        rule = np.array([0.6, 0.5, 0.7, 0.4, 0.5, 0.6, 0.8, 0.3])
        b = rule - np.array([0.1, 0.05, 0.02, 0.1, 0.0, 0.03, 0.2, 0.01])
        boot = dc.component_bootstrap({"rule": rule, "B": b, "d": rule - b}, comps, draws=500, seed=dc.SEED)
        self.assertEqual((boot["components"], boot["images"], boot["seed"]), (5, 8, 20261034))
        d = boot["contrasts"]["d"]
        self.assertAlmostEqual(d["mean"], float(np.mean(rule - b)))
        self.assertEqual(d["defined_draws"] + d["undefined_draws"], 500)
        self.assertTrue(dc.reading(d)["signal_exploratoire_de_transfert"])  # every image gains: lower bound > 0
        again = dc.component_bootstrap({"rule": rule, "B": b, "d": rule - b}, comps, draws=500, seed=dc.SEED)
        self.assertEqual(boot, again)

    def test_reading_is_strict(self):
        self.assertFalse(dc.reading({"mean": 0.01, "ci95": [0.0, 0.02]})["signal_exploratoire_de_transfert"])
        self.assertFalse(dc.reading({"mean": 0.0, "ci95": [0.001, 0.002]})["signal_exploratoire_de_transfert"])
        self.assertFalse(dc.reading({"mean": 0.02, "ci95": None})["signal_exploratoire_de_transfert"])
        r = dc.reading({"mean": -0.01, "ci95": [-0.03, 0.01]})
        self.assertIn("transfert non établi", r["read_as"])

    def test_strata_and_gains(self):
        self.assertEqual(dc.gains_losses([1, 2, 3], [1, 1, 4]), {"gains": 1, "losses": 1, "ties": 1})
        s = dc.strata([0.1, 0.3, 0.5], ["a", "b", "a"])
        self.assertEqual(s["a"], {"images": 2, "mean": 0.3})


class FakeData:
    """The attributes a1_run.Image and a1dev_run.dev_view read, on a 7-code vocabulary and 70 training rows (A1's
    neighbours() always takes the top 64)."""
    def __init__(self):
        rng = np.random.default_rng(0)
        self.vocab = VOCAB
        self.vi = {c: j for j, c in enumerate(VOCAB)}
        self.labels = [[["11H1"], ["11H"], ["25F"], ["2"], ["11"], ["25"], []][j % 7] for j in range(70)]
        xf = rng.normal(size=(70, 8)).astype(np.float32)
        self.nf_train = np.linalg.norm(xf, axis=1)
        self.xf_unit = xf / self.nf_train[:, None]

    def footprint(self, j):
        return a1.closure(a1.drop86(self.labels[j]))


class DevViewTest(unittest.TestCase):
    def setUp(self):
        self.data = FakeData()
        rng = np.random.default_rng(1)
        self.xd = rng.normal(size=(3, 8)).astype(np.float32)
        self.pb = rng.uniform(0, 1, (3, len(VOCAB))).astype(np.float32)
        self.b_pred = a1.project(self.pb, VOCAB, 0.65)

    def test_neighbours_are_the_brute_force_cosine_order(self):
        view, _ = run.dev_view(self.data, self.pb, self.b_pred, self.xd)
        u = self.xd / np.linalg.norm(self.xd, axis=1, keepdims=True)
        sim = u @ self.data.xf_unit.T
        for r in range(3):
            order = sorted(range(70), key=lambda j: (-sim[r, j], j))[:64]
            self.assertEqual(list(view.nn[r]), order)
            self.assertTrue(np.allclose(view.cos[r], sim[r, order]))

    def test_pi0_one_gives_B_and_rule_is_threshold_control(self):
        view, _ = run.dev_view(self.data, self.pb, self.b_pred, self.xd)
        old = dict(run.RULE)
        run.RULE.update(K=16)
        try:
            ones = run.rule_sets(view, range(3), pi0=1.0)
            self.assertEqual(ones, [sorted(b) for b in self.b_pred])
            rule = run.rule_sets(view, range(3))
            for kk, s in enumerate(rule):
                img = run.a1r.Image(view, kk, 16)
                self.assertEqual(s, a1.threshold_control(img.set_q(0.02, 1, 0.25), 0.3))
        finally:
            run.RULE.clear()
            run.RULE.update(old)

    def test_frozen_rule(self):
        self.assertEqual(run.RULE, {"K": 16, "tau": 0.02, "eta": 1, "pi0": 0.25, "t": 0.3})
        self.assertEqual(run.VALIDATION_H, 0.6101628934369521)
        self.assertEqual(dc.SEED, 20261034)
        self.assertEqual(dc.DRAWS, 10_000)

    def test_json_conversion(self):
        obj = run.jsonable({"a": np.int64(2), "b": [np.float32(0.5), np.bool_(True)], np.int64(3): np.arange(2)})
        self.assertEqual(json.loads(json.dumps(obj, sort_keys=True, allow_nan=False)), {"a": 2, "b": [0.5, True], "3": [0, 1]})


class SourcesTest(unittest.TestCase):
    def test_dev_items_is_d10_verbatim_except_the_projection_module(self):
        nt = (ROOT.parent / "2026-10-30-non-transfert/scripts/nt_run.py").read_text()
        mine = (ROOT / "scripts/a1dev_run.py").read_text()
        body = lambda src: ast.unparse(next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)
                                             and n.name == "dev_items").body[1:])  # docstring left out
        self.assertEqual(body(nt).replace("mm.drop86", "DROP"), body(mine).replace("a1.drop86", "DROP"))

    def test_pinned_a1_modules_are_the_reviewed_bytes(self):
        for name in ("a1_core.py", "a1_run.py"):
            mine = hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
            self.assertEqual(mine, k.SCRIPTS[name])
            self.assertEqual(mine, hashlib.sha256((ROOT.parent / "2026-10-29-a1/scripts" / name).read_bytes()).hexdigest())
        for name, want in k.SCRIPTS.items():
            self.assertEqual(hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest(), want)


class PilotTest(unittest.TestCase):
    calm = staticmethod(lambda pid, w: (1 << 20, 0, 1 << 40, 1 << 40))

    def test_wall_and_non_empty_output(self):
        w = tempfile.mkdtemp()
        clock = iter(range(0, 10 ** 6, 1000))
        rec = k.run_child([sys.executable, "-c", "import time; time.sleep(30)"], dict(os.environ),
                          os.path.join(w, "a1-dev"), 0.0, 3600, w, None, lambda: float(next(clock)),
                          lambda s: time.sleep(0.05), self.calm)
        self.assertEqual(rec["failure"], "wall time ceiling exceeded")
        w = tempfile.mkdtemp()
        out = Path(w, "a1-dev")
        out.mkdir()
        (out / "dev.json").write_text("earlier")
        rec = k.run_child([sys.executable, "-c", "pass"], dict(os.environ), str(out), 0.0, 3600, w, None,
                          lambda: 0.0, lambda s: None, self.calm)
        self.assertFalse(rec["started"])
        self.assertEqual((out / "dev.json").read_text(), "earlier")

    def test_pilot_constants(self):
        src = (ROOT / "scripts/kaggle_a1dev_run.py").read_text()
        self.assertEqual(k.WALL_SECONDS, {"dev": 3600})
        self.assertEqual(k.A1_ENV, {"python": "3.13.15", "numpy": "2.1.3", "scipy": "1.16.3"})
        self.assertIn('CUDA_VISIBLE_DEVICES="0", OMP_NUM_THREADS="1"', src)
        liaison = ROOT.parent / "2026-10-30-non-transfert/liaison/sources-gel-pkyevitch.json"
        self.assertEqual(hashlib.sha256(liaison.read_bytes()).hexdigest(), k.BINDING)


if __name__ == "__main__":
    unittest.main(verbosity=2)
