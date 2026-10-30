"""Synthetic tests of pe_common (numpy only). Run: python3 -I tests/test_pe_common.py"""
import itertools
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pe_common as pc  # noqa: E402


class NamesTest(unittest.TestCase):
    def test_priorities(self):
        cases = {"winged child": "surnaturel", "coat of arms": "texte_image", "coat": "vetement_parure",
                 "rider on horse": "personne", "horse": "animal", "hobby horses": "objet", "bow tie": "vetement_parure",
                 "bow": "objet", "man's head": "autre", "statue": "construction", "foliage ornament": "texte_image",
                 "trees": "paysage", "boxes": "objet", "zeppelin": "autre"}
        for name, cat in cases.items():
            self.assertEqual(pc.categorie(name)[0], cat, name)

    def test_relation_class_keeps_teacher_names_and_groups_rare(self):
        self.assertEqual(pc.relation_class("Left of"), "left of")
        self.assertEqual(pc.relation_class("kneels before"), pc.AUTRE_RELATION)


class BoxesTest(unittest.TestCase):
    def test_clean_box(self):
        self.assertEqual(pc.clean_box([900, 100, 50, 1200]), [50.0, 100.0, 900.0, 1000.0])
        self.assertIsNone(pc.clean_box([10, 10, 10, 50]))

    def test_greedy_match_coco_order(self):
        gt = [[0, 0, 100, 100], [200, 200, 300, 300]]
        pred = [[0, 0, 100, 100], [0, 0, 100, 100], [200, 200, 300, 310]]
        tp, scores = pc.greedy_match(pred, [0.5, 0.9, 0.2], gt)
        self.assertEqual(scores, [0.9, 0.5, 0.2])
        self.assertEqual(tp.tolist(), [True, False, True])  # the duplicate is a false positive
        _, assign = pc.greedy_assign(pred, [0.5, 0.9, 0.2], gt)
        self.assertEqual(assign, {0: 1, 1: 2})

    def test_recall_at_k_and_pooled(self):
        imgs = [([[0, 0, 100, 100], [500, 500, 600, 600]], [0.1, 0.9], [[0, 0, 100, 100]]),
                ([], [], [[0, 0, 10, 10], [20, 20, 30, 30]])]
        self.assertEqual(pc.recall_counts(imgs, 1), [(0, 1), (0, 2)])
        self.assertEqual(pc.recall_counts(imgs, 2), [(1, 1), (0, 2)])
        self.assertAlmostEqual(pc.pooled_recall(pc.recall_counts(imgs, 2)), 1 / 3)

    def test_average_precision_perfect_and_half(self):
        gt = [[0, 0, 100, 100], [200, 200, 300, 300]]
        self.assertAlmostEqual(pc.average_precision([(gt, [0.9, 0.8], gt)]), 1.0)
        ap = pc.average_precision([([gt[0], [500, 500, 600, 600]], [0.9, 0.8], gt)])
        self.assertAlmostEqual(ap, 51 / 101)  # recall reaches 0.5 at precision 1, never more

    def test_bootstrap_paired_and_deterministic(self):
        counts_a = [(3, 4), (1, 4), (4, 4)]
        counts_b = [(1, 4), (1, 4), (2, 4)]
        stat = lambda idx: pc.pooled_recall(counts_a, idx) - pc.pooled_recall(counts_b, idx)
        r1, r2 = pc.bootstrap(stat, 3, draws=300, seed=5), pc.bootstrap(stat, 3, draws=300, seed=5)
        self.assertEqual(r1, r2)
        self.assertGreaterEqual(r1["low"], 0.0)  # every image has a >= b: a paired difference never goes below 0

    def test_bootstrap_all_nan(self):
        self.assertEqual(pc.bootstrap(lambda idx: float("nan"), 3, draws=10)["draws"], 0)

    def test_kmeans_deterministic(self):
        rng = np.random.default_rng(0)
        b = rng.uniform(0, 500, (200, 2))
        boxes = np.concatenate([b, b + rng.uniform(10, 400, (200, 2))], 1)
        p1, s1 = pc.kmeans_prototypes(boxes)
        p2, s2 = pc.kmeans_prototypes(boxes)
        self.assertEqual((p1, s1), (p2, s2))
        self.assertEqual(len(p1), 30)
        self.assertAlmostEqual(sum(s1), 1.0)


class ReadingTest(unittest.TestCase):
    def test_all_eighteen_cases_have_one_issue(self):
        seen = set()
        for loc, ap, d in itertools.product(("Loc+", "Loc-", "Loc?"), ("AP+", "AP-", "AP?"), ("D+", "D-")):
            out = pc.issue(loc, ap, d)
            self.assertIn(out, {"signal", "pas de signal", "indécidable"})
            seen.add((loc, ap, d, out))
        self.assertEqual(len(seen), 18)
        self.assertEqual(sum(1 for s in seen if s[3] == "signal"), 1)

    def test_states_examples(self):
        self.assertEqual(pc.states([0.2] * 3, [0.05] * 3, [0.3] * 3, [0.0] * 3, 1.2), ("Loc+", "AP+", "D+"))
        self.assertEqual(pc.states([0.05] * 3, [-0.1] * 3, [0.14] * 3, [-0.1] * 3, 0.5), ("Loc-", "AP-", "D-"))
        self.assertEqual(pc.states([0.10] * 3, [-0.02] * 3, [0.22] * 3, [0.0, -0.1, 0.0], 1.0), ("Loc?", "AP?", "D+"))
        self.assertEqual(pc.states([0.2] * 3, [0.01, 0.0, 0.02], [0.3] * 3, [float("nan")] * 3, 1)[0:2], ("Loc?", "AP?"))
        self.assertEqual(pc.issue("Loc+", "AP+", "D+", technical_failure=True), "panne technique")


if __name__ == "__main__":
    unittest.main(verbosity=2)
