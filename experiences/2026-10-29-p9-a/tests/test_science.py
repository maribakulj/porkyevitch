"""Synthetic tests of p9a_science (numpy + scipy). Run: python -I tests/test_science.py"""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import p9a_science as sc  # noqa: E402
from p9a_common import code_f1, drop86, hier_f1, predictions  # noqa: E402

VOCAB = ["1", "11", "11H", "11H(JEROME)", "2", "25", "25F", "86", "86(x)", "31A:25F"]
# direct parents (indices) and topological levels, as TrainData.graph would give
IX = {c: i for i, c in enumerate(VOCAB)}
PARENTS = [[], [0], [1], [2], [], [4], [5], [], [7], [5]]
LEVELS = [[0, 4, 7], [1, 5, 8], [2, 6, 9], [3]]


class ScienceTest(unittest.TestCase):
    def test_envelope_is_max_over_descendants_and_alpha0_keeps_B(self):
        rng = np.random.default_rng(0)
        p = rng.random((30, len(VOCAB)))
        LB = sc.envelope(p, PARENTS, LEVELS)
        b = -np.expm1(-LB)
        desc = {c: {d for d in range(len(VOCAB)) if c == d or c in self.anc(d)} for c in range(len(VOCAB))}
        for c in range(len(VOCAB)):
            expect = np.clip(p[:, sorted(desc[c])].max(1), 1e-7, 1 - 1e-7)
            self.assertTrue(np.allclose(b[:, c], expect, atol=1e-12))
        self.assertEqual(sc.predict(b, VOCAB, 0.65), predictions(p, VOCAB, 0.65))  # envelope only adds ancestors

    def anc(self, d):
        out, todo = set(), list(PARENTS[d])
        while todo:
            a = todo.pop()
            if a not in out:
                out.add(a)
                todo += PARENTS[a]
        return out

    def test_mix_limits_and_alpha0_forbidden(self):
        LB = np.array([[0.1, 2.0]])
        Lh = np.array([[1.0, 0.5]])
        self.assertTrue(np.allclose(sc.mix(LB, Lh, 1.0), -np.expm1(-Lh)))
        self.assertTrue(np.allclose(sc.mix(LB, Lh, 0.5), -np.expm1(-(0.5 * LB + 0.5 * Lh))))
        with self.assertRaises(RuntimeError):
            sc.mix(LB, Lh, 0)

    def test_fast_h_equals_hier_f1(self):
        rng = np.random.default_rng(1)
        labels = [list(rng.choice(VOCAB, rng.integers(0, 3))) for _ in range(200)]
        truth = sc.Truth(labels)
        for i, y in enumerate(labels):
            pred = list(rng.choice(VOCAB, rng.integers(0, 3)))
            self.assertEqual(sc.fast_h(truth, i, pred), hier_f1(drop86(y), pred))

    def candidates(self, scores):
        grid = [{"alpha": a, "epoch": e, "theta": t, "H_Vreg": scores(a, e, t)}
                for e in range(1, 11) for a in sc.ALPHAS for t in sc.THETAS]
        return [{"alpha": 0, "epoch": None, "theta": 0.65, "H_Vreg": 0.5}] + grid

    def test_select_rule_and_ties(self):
        c = self.candidates(lambda a, e, t: 0.4)
        self.assertEqual(sc.select(c)["alpha"], 0)                           # B wins when nothing beats it
        c = self.candidates(lambda a, e, t: 0.6 if (a, t) in ((0.5, 0.3), (0.25, 0.4)) and e >= 3 else 0.4)
        self.assertEqual((sc.select(c)["alpha"], sc.select(c)["epoch"], sc.select(c)["theta"]), (0.25, 3, 0.4))
        c = self.candidates(lambda a, e, t: 0.5 + 5e-13 if a == 1.0 else 0.4)  # within 1e-12 of B: B kept
        self.assertEqual(sc.select(c)["alpha"], 0)
        c = self.candidates(lambda a, e, t: 0.7 if t in (0.2, 0.15) and a == 0.5 and e in (4, 7) else 0.1)
        self.assertEqual((sc.select(c)["epoch"], sc.select(c)["theta"]), (4, 0.15))
        with self.assertRaises(RuntimeError):
            sc.select(c[:-1])                                                # 570 grid points exactly
        self.assertEqual(len(c), 571)

    def test_measures_follow_section_8(self):
        labels = [["11H"], ["86(x)"], ["25F", "2"], ["31A:25F"]]
        preds = [["11H(JEROME)"], ["2"], ["25F"], []]
        truth = sc.Truth(labels)
        m = sc.measures(truth, preds, ["25F", "11H"], ["11H", "25F", "2", "zz"], {"11H": 7, "25F": 12, "2": 300},
                        VOCAB)
        self.assertEqual(m["eligible"], 3)
        self.assertAlmostEqual(m["H"], np.mean([hier_f1(["11H"], ["11H(JEROME)"]), hier_f1(["25F", "2"], ["25F"]), 0.0]))
        self.assertAlmostEqual(m["E"], np.mean([0.0, 2 / 3, 0.0]))
        self.assertEqual(m["rare"], code_f1([drop86(y) for y in labels], preds, ["25F", "11H"]))
        self.assertEqual(m["tranches"]["0"]["codes"], 1)                    # zz, absent from training
        self.assertEqual(m["tranches"]["21-100"], "not_applicable")

    def test_verdicts(self):
        b = {"H": 0.58, "E": 0.30, "F_R": 0.07}
        self.assertEqual(sc.verdict({"H": 0.586, "E": 0.295, "F_R": 0.0}, b, 0.5)["verdict"], "G")
        self.assertEqual(sc.verdict({"H": 0.576, "E": 0.295, "F_R": 0.08}, b, 0.5)["verdict"], "R")
        self.assertEqual(sc.verdict({"H": 0.574, "E": 0.29, "F_R": 0.08}, b, 0.5)["verdict"], "non_retenue")
        self.assertEqual(sc.verdict({"H": 0.586, "E": 0.28, "F_R": 0.08}, b, 0.5)["verdict"], "non_retenue")
        self.assertEqual(sc.verdict(b, b, 0)["verdict"], "reference_conservee")

    def test_mechanism(self):
        vd = {k: {"H": h, "F_R": r} for k, h, r in (("A", 0.60, 0.09), ("controle_global", 0.596, 0.08),
                                                     ("F", 0.59, 0.07), ("C", 0.61, 0.06))}
        m = sc.mechanism({"verdict": "G"}, vd, 150)
        self.assertTrue(m["general_local_nesting_supported"])
        self.assertTrue(m["rare_local_nesting_supported"])
        self.assertEqual(sc.mechanism({"verdict": "G"}, vd, 99)["rare_local_nesting_supported"],
                         "indecidable_support_Vdiag_below_100")
        vd["A"]["H"] = 0.598
        self.assertFalse(sc.mechanism({"verdict": "G"}, vd, 150)["general_local_nesting_supported"])

    def test_bootstrap_tables_match_direct_recomputation(self):
        rng = np.random.default_rng(3)
        labels = [list(rng.choice(VOCAB, rng.integers(0, 3))) for _ in range(40)]
        preds = [list(rng.choice(VOCAB, rng.integers(0, 3))) for _ in range(40)]
        truth = sc.Truth(labels)
        group_of = [i // 3 for i in range(40)]
        n_groups = max(group_of) + 1
        rare = ["11H", "25F", "2"]
        t = sc.group_tables(truth, preds, list(range(40)), group_of, n_groups, rare)
        counts = next(sc.group_draws(n_groups, draws=20, block=20))
        st = sc.draw_stats(t, counts)
        for d in range(20):
            rows = [i for g in range(n_groups) for _ in range(counts[d, g]) for i in range(40) if group_of[i] == g]
            el = [i for i in rows if truth.y[i]]
            self.assertAlmostEqual(st["H"][d], np.mean([sc.fast_h(truth, i, preds[i]) for i in el]))
            f = code_f1([truth.y[i] for i in rows], [preds[i] for i in rows], rare)
            self.assertAlmostEqual(st["F_R"][d], f["macro_F1"])
        again = next(sc.group_draws(n_groups, draws=20, block=20))
        self.assertTrue(np.array_equal(counts, again))  # same draws for every system

    def test_plate_rows_order(self):
        truth = sc.Truth([["11H"], ["25F"], ["2"], ["11"]])
        arm, b = [["11H"], ["25F"], [], ["11"]], [[], [], ["2"], ["11"]]
        where = [(3, 5), (1, 9), (1, 2), (0, 0)]
        self.assertEqual(sc.plate_rows(truth, arm, b, where, n=3), [2, 1, 0])  # ties |dH| = 1: (1,2), (1,9), (3,5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
