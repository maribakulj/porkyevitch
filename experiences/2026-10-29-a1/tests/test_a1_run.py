"""A1 runner stages on fake data (numpy + scipy; no Brillfull, no cache). Run: python -I tests/test_a1_run.py"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import a1_core as a1  # noqa: E402
import a1_run as run  # noqa: E402

LEAVES = ["11H", "11H1", "12", "25F", "25F2", "31A", "86A", "1:86A", "25F:86A", "31A:12", "7", "73"]


class FakeData:
    def __init__(self, n_val=60, n_fit=80, seed=0):
        rng = np.random.default_rng(seed)
        self.vocab = sorted(set().union(*(a1.ancestors(c) for c in LEAVES)))
        self.vi = {c: k for k, c in enumerate(self.vocab)}
        self.labels = [list(rng.choice(LEAVES, rng.integers(1, 3), replace=False)) for _ in range(n_fit + n_val)]
        self.fit, self.val = np.arange(n_fit), np.arange(n_fit, n_fit + n_val)
        self.raw = {}
        for i in self.fit:
            for c in set(self.labels[i]):
                self.raw[c] = self.raw.get(c, 0) + 1
        self.pb = rng.random((n_val, len(self.vocab))).astype(np.float32)
        self.b_pred = a1.project(self.pb, self.vocab, 0.65)
        self.truth = [a1.drop86(self.labels[i]) for i in self.val]
        self.truth[3] = []
        self.eligible = [k for k, g in enumerate(self.truth) if g]
        self.vmd5 = [f"{k // 2:032x}" for k in range(n_val)]  # groups of two rows
        self.reg = [k for k in range(n_val) if (k // 2) % 2 == 0]
        self.diag = [k for k in range(n_val) if (k // 2) % 2 == 1]
        self.where = [("train-00000-of-00011", i) for i in range(n_fit + n_val)]
        self.nn = np.stack([rng.permutation(n_fit)[:8] for _ in range(n_val)])
        self.cos = np.sort(rng.uniform(0.6, 0.99, (n_val, 8)), axis=1)[:, ::-1]
        self.h_b, self.raw_tk_overlap, self._fp = 0.5, 1.0, {}

    def footprint(self, j):
        if j not in self._fp:
            self._fp[j] = a1.closure(a1.drop86(self.labels[self.fit[j]]))
        return self._fp[j]


class RunTest(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(run, k) for k in ("KS", "TAUS", "ETAS", "PI0S", "E1_CONFIG", "Data", "BOOT_DRAWS")}
        run.KS, run.TAUS, run.ETAS, run.PI0S = (2, 4, 8), (0.05, 0.1), (0, 1), (0, 0.5)
        run.E1_CONFIG, run.BOOT_DRAWS = {"K": 4, "tau": 0.05, "eta": 1, "pi0": 0.25}, 600
        self.fake = FakeData()
        run.Data = lambda *a: self.fake

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(run, k, v)

    def test_e0_e1(self):
        self.assertTrue(run.structure(self.fake)["t_transitive_ordered"])
        rep = run.e1_identity(self.fake, self.fake.reg[:6], 4, run.E1_CONFIG)
        self.assertEqual(len(rep), 6)
        self.assertEqual(run.e1_pi0_one(self.fake, self.fake.eligible), len(self.fake.eligible))

    def test_highs_presolve_regression(self):
        # E1-(i) found this case: HiGHS presolve claimed optimum 0.45380 (gap 0) where the closed sort set gives 0.45532.
        img = run.Image(self.fake, 36, 4)
        pb = img.set_q(0.05, 1, 0.25)
        for kk, val, _ in a1.flat_curve(pb):
            st, v, x, cert = a1.milp_k(pb, kk, emission=False)
            self.assertTrue(cert)
            self.assertAlmostEqual(v, val, places=9)

    def test_choose_ties(self):
        s = {(2, 0.05, 0, 0): {"H": 0.5}, (2, 0.1, 0, 0): {"H": 0.5}, (4, 0.1, 0, 0.5): {"H": 0.5}}
        self.assertEqual(run.choose(s), (2, 0.1, 0, 0))                  # smaller K, then larger tau
        self.assertEqual(run.best_t({0.1: 0.3, 0.2: 0.3, 0.05: 0.2}), 0.1)

    def test_reglage_then_diagnostic_needs_receipt(self):
        root = Path(tempfile.mkdtemp())
        blank = root / "blanc.json"
        blank.write_text(json.dumps({"status": "WITHIN_2H", "versions": run.versions()}))
        bsha = hashlib.sha256(blank.read_bytes()).hexdigest()
        A = lambda **k: type("A", (), dict(encoder="", inventory="", diag="", **k))
        run.stage_reglage(A(out=str(root / "reglage"), blank=str(blank), blank_sha256=bsha))
        sealed = json.loads((root / "reglage" / "reglage.json").read_text())
        self.assertEqual(len(sealed["scores_Vreg"]), 3 * 2 * 2 * 2)
        self.assertFalse(sealed["V_diagnostic_opened"])
        self.assertIn("t", sealed["secondary_threshold_control"])
        self.assertEqual(len(json.loads((root / "reglage" / "planche.json").read_text())["rows"]), 12)
        man = hashlib.sha256((root / "reglage" / "MANIFEST_REGLAGE.json").read_bytes()).hexdigest()
        bad = root / "bad.json"
        bad.write_text(json.dumps({"stage": "planche_a1_regardee", "reglage_manifest_sha256": man,
                                   "regards": [{"viewer": "wA:p1", "viewed_at": "t"}]}))
        with self.assertRaises(RuntimeError):
            run.stage_diagnostic(A(out=str(root / "d0"), reglage=str(root / "reglage"), receipt=str(bad)))
        good = root / "recu.json"
        good.write_text(json.dumps({"stage": "planche_a1_regardee", "reglage_manifest_sha256": man,
                                    "regards": [{"viewer": "wA:p1", "viewed_at": "t"}, {"viewer": "Grok p2", "viewed_at": "t"}]}))
        run.stage_diagnostic(A(out=str(root / "d1"), reglage=str(root / "reglage"), receipt=str(good)))
        d = json.loads((root / "d1" / "diagnostic.json").read_text())
        self.assertIn(d["mechanism"]["case"], ("refute_dans_ce_regime", "mecanisme_utile", "indecidable"))
        self.assertEqual(d["bootstrap"]["seed"], run.BOOT_SEED)
        self.assertEqual(d["eligible"], sum(1 for k in self.fake.diag if self.fake.truth[k]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
