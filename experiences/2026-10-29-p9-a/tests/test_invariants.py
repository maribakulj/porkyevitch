"""Duplication (mass) invariant of the P9-A heads after smoke-1 (30/10). Needs torch (CPU is enough).
Run: python -I tests/test_invariants.py"""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from p9a_heads import Head  # noqa: E402
import p9a_smoke as smoke  # noqa: E402

V = 7907  # the parameter count check of Head needs the real vocabulary size


class Data:
    """Synthetic forest: 7907 codes, depth <= 4, a few codes with two parents (composites)."""
    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        self.vocab = [f"c{i}" for i in range(V)]
        depth = np.minimum(rng.integers(0, 4, V), np.arange(V))
        self.parents, levels = [], {}
        for c in range(V):
            older = [p for p in range(max(0, c - 50), c) if depth[p] == depth[c] - 1]
            ps = [] if depth[c] == 0 or not older else sorted(set(rng.choice(older, 1 + (c % 97 == 0), replace=True)))
            self.parents.append([int(p) for p in ps])
        self.level_of = {}
        for c in range(V):
            self.level_of[c] = 0 if not self.parents[c] else 1 + max(self.level_of[p] for p in self.parents[c])
            levels.setdefault(self.level_of[c], []).append(c)
        self.levels = [levels[d] for d in sorted(levels)]
        self.closed = {c: int(rng.integers(1, 2000)) for c in self.vocab}
        self.fit = list(range(80000))


def trained_like(arm, seed=0):
    torch.manual_seed(seed)
    data = Data()
    model = Head(arm, data, np.random.default_rng(1).standard_normal((V, 384)).astype(np.float32),
                 torch.randn(128, 1024) * 0.03)
    with torch.no_grad():  # what two updates do: U and delta leave zero, so the fp16 products stop being exact
        model.U.normal_(0, 0.05)
        model.delta.normal_(0, 0.05)
        model.w0.normal_(0, 0.03)
    return model.eval()


class InvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(3)
        cls.x = torch.randn(2, 64, 1024)
        cls.models = {arm: trained_like(arm) for arm in ("A", "controle_global")}

    def test_production_path_unchanged(self):
        for m in self.models.values():
            self.assertTrue(torch.equal(m(self.x), m(self.x, fp16=True)))

    def test_float64_duplication_error_far_below_tolerance(self):
        for arm, m in self.models.items():
            with torch.no_grad():
                err = smoke.duplication_errors(m, self.x)
            self.assertLess(err["float64_cpu"], 1e-12, arm)
            self.assertLessEqual(err["float64_cpu"], smoke.DUPLICATION_TOL_FLOAT64)

    def test_mass_defect_is_caught(self):
        # One duplicated cell counted 1/64 instead of 1/128 (the rest renormalised): a real nesting/mass defect.
        for arm, m in self.models.items():
            twin = copy.deepcopy(m).double()
            x = self.x.double()
            dup = torch.cat((x[:, :1], x[:, :1], x[:, 1:]), dim=1)
            w = torch.full((65,), 1 / 64, dtype=torch.float32)
            w[0], w[1] = 1 / 64, 1 / 128
            w[2:] = (1 - 3 / 128) / 63
            with torch.no_grad():
                err = float((twin(dup, w, fp16=False) - twin(x, fp16=False)).abs().max())
            self.assertGreater(err, 1e3 * smoke.DUPLICATION_TOL_FLOAT64, arm)

    def test_fp16_rounding_of_the_products_exceeds_1e6_only_after_training(self):
        # Mechanism of smoke-1: one fp16 rounding of v and dot (what a different GEMM shape changes on T4) moves
        # probabilities by more than 1e-6 once U, delta != 0, and by exactly 0 at initialisation (code = 0).
        def rounded_shift(model):
            with torch.no_grad():
                z = torch.nn.functional.layer_norm(self.x, (1024,), eps=1e-5)
                v = torch.nn.functional.linear(z, model.W)
                code = torch.nn.functional.linear(model.prototypes, model.U) + model.delta
                exact = (v @ code.T) / 128 ** 0.5 + model.b
                half = (v.half().float() @ code.half().float().T).half().float() / 128 ** 0.5 + model.b
                return exact, half
        m = self.models["A"]
        exact, half = rounded_shift(m)
        self.assertGreater(float((exact - half).abs().max()), 1e-4)
        init = Head("A", Data(), np.random.default_rng(1).standard_normal((V, 384)).astype(np.float32),
                    torch.randn(128, 1024) * 0.03)
        e0, h0 = rounded_shift(init)
        self.assertEqual(float((e0 - h0).abs().max()), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
