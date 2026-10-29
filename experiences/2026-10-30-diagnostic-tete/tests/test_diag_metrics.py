"""Synthetic tests of diag_metrics. No ICAI data. Run: python3 -I tests/test_diag_metrics.py"""
import ast
from pathlib import Path
import re
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import diag_metrics as dm  # noqa: E402

E3 = Path.home() / "porkyevitch/experiences/2026-10-25-iconclass-architecture/scripts/e3_spatial.py"
CODES = ["1", "11", "11H", "11H(JEROME)", "11H(JEROME)3", "25F23(LION)", "25F23(LION)(+12)", "31A:25F",
         "86(Amor)", "73D82", "73D8", "7", "0:49D3", "bad code", "11H(PAUL)"]


def e3_functions():
    tree = ast.parse(E3.read_text())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in
            {"ancestors", "hier_f1", "most_specific", "drop86"}) or
            (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in {"PART", "TOKEN", "_anc"} for t in n.targets))]
    ns = {"re": re}
    exec(compile(ast.Module(keep, []), "e3_spatial.py", "exec"), ns)
    return ns


class MetricsTest(unittest.TestCase):
    @unittest.skipUnless(E3.is_file(), "historical E3 script absent")
    def test_parity_with_e3_functions(self):
        e3 = e3_functions()
        rng = np.random.default_rng(0)
        for c in CODES:
            self.assertEqual(dm.ancestors(c), e3["ancestors"](c))
        for _ in range(500):
            g = list(rng.choice(CODES, rng.integers(0, 4)))
            p = list(rng.choice(CODES, rng.integers(0, 4)))
            self.assertEqual(dm.hier_f1(g, p), e3["hier_f1"](g, p))
            self.assertEqual(dm.most_specific(p), e3["most_specific"](p))
            self.assertEqual(dm.drop86(p), e3["drop86"](p))

    def test_project_order_threshold_most_specific_drop86(self):
        vocab = ["11", "11H", "86", "86(Amor)", "7"]
        prob = np.array([[0.9, 0.7, 0.9, 0.9, 0.2]])
        self.assertEqual(dm.project(prob, vocab, 0.65), [["11H"]])
        self.assertEqual(dm.project(prob, vocab, np.array([0.5, 0.8, 0.5, 0.5, 0.1])), [["11", "7"]])

    def test_tranche_boundaries(self):
        self.assertEqual([dm.tranche(n) for n in (0, 1, 4, 5, 20, 21, 100, 101, 1000, 1001)],
                         ["0", "1-4", "1-4", "5-20", "5-20", "21-100", "21-100", "101-1000", "101-1000", ">1000"])

    def test_tranche_table_keeps_absent_codes_in_macro_denominator(self):
        gts = [["a"], ["a"], []]
        preds = [["a"], [], ["b"]]
        table = dm.tranche_table(gts, preds, {"a": 10, "b": 12, "c": 7}, ["a", "b", "c"])
        row = table["5-20"]
        self.assertEqual((row["codes"], row["represented"], row["tp"], row["fp"], row["fn"]), (3, 1, 1, 1, 1))
        self.assertAlmostEqual(row["macro_f1"], (2 / 3 + 0 + 0) / 3)
        self.assertAlmostEqual(row["micro_f1"], 2 / 4)
        self.assertEqual(table["0"], "not_applicable")
        self.assertEqual(table["outside_universe_counts"], 0)

    def test_node_depth_table(self):
        table = dm.node_depth_table([["11H(JEROME)"]], [["11H(PAUL)"]])
        self.assertEqual(table["3"]["tp"], 1)  # 11H shared
        self.assertEqual((table["4"]["tp"], table["4"]["fp"], table["4"]["fn"]), (0, 1, 1))

    def test_stop_depth_of_missed_codes(self):
        rows = dm.stop_depths([["11H(JEROME)", "7"]], [["11H", "7"]])
        self.assertEqual(rows, [{"true_depth": "4", "stop_depth": 3, "count": 1}])
        self.assertEqual(dm.stop_depths([["25F23(LION)"]], [["11H"]]),
                         [{"true_depth": str(len(dm.ancestors("25F23(LION)"))), "stop_depth": 0, "count": 1}])

    def test_confident_absent_excludes_truth_closure_and_returns_identifiers_only(self):
        vocab = ["11", "11H", "11H(PAUL)", "7"]
        prob = np.array([[0.95, 0.95, 0.95, 0.95], [0.95, 0.95, 0.1, 0.1]])
        ids = [{"shard": "s", "row": 0, "md5": "m0"}, {"shard": "s", "row": 1, "md5": "m1"}]
        out = dm.confident_absent(prob, vocab, [["11H(JEROME)"], ["11H"]], ids, size=10)
        codes = sorted((s["row"], s["code"]) for s in out["sample"])
        self.assertEqual(codes, [(0, "11H(PAUL)"), (0, "7")])  # 11H is an ancestor of the truth: excluded
        self.assertTrue(all(set(s) == {"shard", "row", "md5", "code", "p"} for s in out["sample"]))
        capped = dm.confident_absent(prob, vocab, [["11H(JEROME)"], ["11H"]], ids, size=10, per_image=1)
        self.assertEqual(len(capped["sample"]), 1)

    def test_tranche_threshold_upper_bound_never_below_start(self):
        rng = np.random.default_rng(1)
        vocab = ["1", "11", "11H", "2", "25", "25F"]
        gts = [list(rng.choice(vocab, 2)) for _ in range(60)]
        prob = rng.random((60, len(vocab)))
        code_tranche = {c: t for c, t in zip(vocab, ("0", "5-20", ">1000", "1-4", "5-20", "21-100"))}
        start = dm.mean_hier(gts, dm.project(prob, vocab, 0.65))
        res = dm.tranche_threshold_upper_bound(prob, vocab, code_tranche, gts, 0.65, [0.3, 0.5, 0.65, 0.8])
        self.assertGreaterEqual(res["hf1_upper_bound"], start)
        vector = np.array([res["thresholds"][code_tranche[c]] for c in vocab])
        self.assertAlmostEqual(dm.mean_hier(gts, dm.project(prob, vocab, vector)), res["hf1_upper_bound"])

    def test_group_bootstrap_deterministic_and_centred(self):
        values = {"x": [1.0, 0.0, 1.0, 0.0]}
        a = dm.group_bootstrap(values, ["g1", "g1", "g2", "g3"], draws=200)
        b = dm.group_bootstrap(values, ["g1", "g1", "g2", "g3"], draws=200)
        self.assertEqual(a, b)
        self.assertEqual(a["x"]["mean"], 0.5)

    def test_error_overlap(self):
        res = dm.error_overlap([["a", "b"], ["c"]], [["a"], ["d"]], [["b"], ["d"]], [0.5, 0.0], [0.5, 0.0])
        self.assertAlmostEqual(res["jaccard_false_codes"], 1.0)
        self.assertAlmostEqual(res["jaccard_missed_codes"], 1 / 3)
        self.assertEqual(res["both_below_0.3"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
