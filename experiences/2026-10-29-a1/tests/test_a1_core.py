"""A1 core against exhaustive enumeration on small universes (numpy + scipy). Run: python -I tests/test_a1_core.py"""
import ast
from itertools import combinations
from pathlib import Path
import re
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import a1_core as a1  # noqa: E402

E3 = Path.home() / "porkyevitch/experiences/2026-10-25-iconclass-architecture/scripts/e3_spatial.py"
LEAVES = ["11H", "11H1", "12", "25F", "25F2", "31A", "86A", "86B1", "1:86A", "25F:86B1", "31A:12", "7"]


def exhaustive(pb, emission=True):
    """Best utility over closed subsets (no non-emissible maximal if emission); ties: smallest size."""
    n = len(pb.nodes)
    best = (0.0, 0, [])
    for size in range(1, n + 1):
        for s in combinations(range(n), size):
            if not pb.is_closed(s):
                continue
            if emission and any(pb.n86[i] for i in pb.maximal(s)):
                continue
            v = pb.utility(s)
            if v > best[0] + 1e-12:
                best = (v, size, list(s))
    return best


def random_problem(rng, pi0=0.25):
    vocab = set().union(*(a1.ancestors(c) for c in LEAVES))
    t0 = a1.closure(list(rng.choice(LEAVES, rng.integers(0, 2), replace=False)))
    fps = [a1.closure(list(rng.choice(LEAVES, rng.integers(0, 3), replace=False)) + (["zz9"] if rng.random() < .3 else []))
           for _ in range(4)]
    vi = {c: i for i, c in enumerate(sorted(vocab))}
    atoms, q = a1.make_q(t0, fps, rng.uniform(0.5, 1, 4), rng.normal(0, 1, len(vi)), vi, 0.05, 1.0, pi0)
    return a1.Problem(t0, atoms, q, vocab)


class CoreTest(unittest.TestCase):
    @unittest.skipUnless(E3.is_file(), "historical E3 script absent")
    def test_parity_with_e3(self):
        tree = ast.parse(E3.read_text())
        keep = [x for x in tree.body if (isinstance(x, ast.FunctionDef) and x.name in
                {"ancestors", "hier_f1", "most_specific", "drop86"}) or
                (isinstance(x, ast.Assign) and any(getattr(t, "id", "") in {"PART", "TOKEN", "_anc"} for t in x.targets))]
        ns = {"re": re}
        exec(compile(ast.Module(keep, []), "e3", "exec"), ns)
        rng = np.random.default_rng(0)
        codes = LEAVES + ["bad code", " 86(x)", "11H(JEROME)3"]
        for c in codes:
            self.assertEqual(set(a1.ancestors(c)), set(ns["ancestors"](c)))
        for _ in range(200):
            g, p = list(rng.choice(codes, 2)), list(rng.choice(codes, 2))
            self.assertEqual(a1.hier_f1(g, p), ns["hier_f1"](g, p))
            self.assertEqual(a1.most_specific(p), ns["most_specific"](p))
            self.assertEqual(a1.drop86(p), ns["drop86"](p))

    def test_sort_closed_and_optimal_for_closure_each_k(self):
        rng = np.random.default_rng(1)
        for _ in range(40):
            pb = random_problem(rng)
            n = len(pb.nodes)
            for k, val, idx in a1.flat_curve(pb):
                self.assertTrue(pb.is_closed(idx))
                best = max(pb.utility(s) for s in combinations(range(n), k) if pb.is_closed(s))
                self.assertAlmostEqual(val, best, places=12)
                self.assertAlmostEqual(val, pb.utility(idx), places=12)

    def test_decoder_equals_exhaustive_with_emission(self):
        rng = np.random.default_rng(2)
        solver_used = 0
        for _ in range(60):
            pb = random_problem(rng, pi0=float(rng.choice([0, 0.25, 0.5])))
            out = a1.decode(pb)
            best, size, _ = exhaustive(pb)
            self.assertAlmostEqual(out["value"], best, places=9)
            self.assertTrue(out["certified"])
            if out["S"]:
                self.assertEqual(len(out["S"]), size)                      # smallest size among optima
                self.assertTrue(pb.is_closed(out["S"]))
                self.assertFalse(any(pb.n86[i] for i in pb.maximal(out["S"])))
                # E1-(iii): utility of the closure of what is really emitted
                emitted_closure = a1.closure(out["emitted"])
                self.assertAlmostEqual(pb.utility([pb.index[a] for a in emitted_closure]), out["value"], places=9)
            solver_used += out["path"] == "solver"
        self.assertGreater(solver_used, 0)                                 # the constrained branch is exercised

    def test_milp_closure_only_equals_sort(self):
        rng = np.random.default_rng(3)
        for _ in range(15):
            pb = random_problem(rng)
            for k, val, _ in a1.flat_curve(pb):
                st, v, x, cert = a1.milp_k(pb, k, emission=False)
                self.assertTrue(cert)
                self.assertAlmostEqual(v, val, places=9)

    def test_codex_style_forbidden_maximal(self):
        vocab = set().union(*(a1.ancestors(f"{i}:86") for i in range(1, 6)))
        fps = [a1.closure([f"{i}:86"]) for i in range(1, 6)]
        vi = {c: i for i, c in enumerate(sorted(vocab))}
        atoms, q = a1.make_q(frozenset(), fps, [1.0] * 5, np.zeros(len(vi)), vi, 1.0, 0.0, 0.0)
        pb = a1.Problem(frozenset(), atoms, q, vocab)
        k, val, idx = a1.flat_optimum(pb)
        self.assertTrue(any(pb.n86[i] for i in pb.maximal(idx)))          # the sort alone emits a forbidden maximal
        out = a1.decode(pb)
        self.assertEqual(out["path"], "solver")
        self.assertAlmostEqual(out["value"], exhaustive(pb)[0], places=9)
        self.assertLess(out["value"], val)

    def test_pi0_one_returns_t0(self):
        rng = np.random.default_rng(4)
        vocab = set().union(*(a1.ancestors(c) for c in LEAVES))
        vi = {c: i for i, c in enumerate(sorted(vocab))}
        for _ in range(30):
            b = sorted(a1.drop86(a1.most_specific(list(rng.choice(LEAVES, rng.integers(0, 3), replace=False)))))
            t0 = a1.closure(b)
            fps = [a1.closure(list(rng.choice(LEAVES, 2))) for _ in range(3)]
            atoms, q = a1.make_q(t0, fps, [0.9, 0.8, 0.7], np.zeros(len(vi)), vi, 0.05, 1.0, 1.0)
            out = a1.decode(a1.Problem(t0, atoms, q, vocab))
            self.assertEqual(out["emitted"], sorted(a1.drop86(a1.most_specific(b))))

    def test_threshold_control_removes_n_first(self):
        vocab = set().union(*(a1.ancestors(c) for c in ["1:86A", "11H"]))
        vi = {c: i for i, c in enumerate(sorted(vocab))}
        atoms, q = a1.make_q(frozenset(), [a1.closure(["1:86A"]), a1.closure(["11H"])], [1, 1], np.zeros(len(vi)), vi,
                             1.0, 0.0, 0.0)
        pb = a1.Problem(frozenset(), atoms, q, vocab)
        out = a1.threshold_control(pb, 0.5)
        self.assertNotIn("86A", out)
        self.assertIn("1:86A", out)

    def test_project_casts_threshold_to_float32(self):
        p = np.array([[np.float32(0.65)]], dtype=np.float32)
        self.assertEqual(a1.project(p, ["11H"], 0.65), [["11H"]])          # float32(0.65) >= float32(0.65)
        self.assertEqual(a1.project(p.astype(np.float64), ["11H"], 0.65), [[]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
