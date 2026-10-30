"""Fictitious graphs only. Run: python3 -I tests/test_comptage.py"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import comptage as c  # noqa: E402

GEM = {"objects": [{"id": "a", "name": "man", "box": [0, 0, 400, 900]},
                   {"id": "b", "name": "staff", "box": [380, 0, 440, 900]},
                   {"id": "c", "name": "tree", "box": [600, 0, 1000, 800]}],
       "relations": [["a", "holds", "b"]]}


def g(d):
    p = Path(tempfile.mkdtemp()) / "x.json"
    p.write_text(json.dumps(d))
    return c.load(p)


class ComptageTest(unittest.TestCase):
    def test_identical_graphs_assert_nothing(self):
        r = c.count(g(GEM), g(GEM))
        self.assertEqual(r["pairs"], {"negatives": 5, "comparable": 5, "asserted_by_S1b": 0})
        self.assertEqual(r["objects"]["s1b_unmatched_joint"], 0)

    def test_s1b_asserts_a_gemini_negative_pair(self):
        s1b = {**GEM, "relations": [["a", "holds", "b"], ["a", "left of", "c"]]}
        r = c.count(g(GEM), g(s1b))
        self.assertEqual(r["pairs"]["asserted_by_S1b"], 1)          # (man, tree) had no Gemini relation
        self.assertEqual(r["predicates"]["left of"]["asserted_by_S1b"], 1)

    def test_predicate_negative_on_a_related_pair(self):
        s1b = {**GEM, "relations": [["a", "holds", "b"], ["a", "left of", "b"]]}
        r = c.count(g(GEM), g(s1b))
        self.assertEqual(r["pairs"]["asserted_by_S1b"], 0)          # the pair is related in Gemini
        self.assertEqual(r["predicates"]["left of"]["asserted_by_S1b"], 1)   # but 'left of' is a class negative
        self.assertEqual(r["predicates"]["holds"]["asserted_by_S1b"], 0)

    def test_unmatched_objects_are_not_comparable(self):
        s1b = {"objects": GEM["objects"][:2] + [{"id": "d", "name": "dog", "box": [0, 950, 100, 1000]}],
               "relations": [["a", "left of", "d"]]}
        r = c.count(g(GEM), g(s1b))
        self.assertEqual(r["matched_joint"], 2)
        self.assertEqual(r["objects"]["s1b_unmatched_joint"], 1)     # the dog would be learnt as "no object"
        self.assertEqual(r["pairs"]["comparable"], 1)               # only (staff, man) among the negatives
        self.assertEqual(r["pairs"]["asserted_by_S1b"], 0)

    def test_category_rule_vs_iou_alone(self):
        s1b = {"objects": [{"id": "a", "name": "man", "box": [0, 0, 400, 900]},
                           {"id": "b", "name": "staff", "box": [380, 0, 440, 900]},
                           {"id": "c", "name": "dog", "box": [600, 0, 1000, 800]}], "relations": []}
        r = c.count(g(GEM), g(s1b))
        self.assertEqual((r["matched_joint"], r["matched_iou"]), (2, 3))

    def test_totals_and_shares(self):
        s1b = {**GEM, "relations": [["a", "holds", "b"], ["a", "left of", "c"]]}
        t = c.total({"p1": c.count(g(GEM), g(GEM)), "p2": c.count(g(GEM), g(s1b))})
        self.assertEqual(t["pairs"]["negatives"], 10)
        self.assertAlmostEqual(t["pairs"]["asserted_share_of_comparable"], 0.1)
        self.assertEqual(t["objects"]["unmatched_share_joint"], 0.0)

    def test_main_checks_shas_and_twenty_six(self):
        root = Path(tempfile.mkdtemp())
        rows = []
        for k in range(26):
            name = f"p{k:03d}"
            (root / "gem" / name).mkdir(parents=True)
            (root / "gem" / name / "g.json").write_text(json.dumps(GEM))
            (root / "s1b").mkdir(exist_ok=True)
            (root / "s1b" / f"{name}.json").write_text(json.dumps(GEM))
            h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            rows.append({"name": name, "gemini_graph_sha256": h(root / "gem" / name / "g.json"),
                         "s1b_graph_sha256": h(root / "s1b" / f"{name}.json")})
        (root / "listes.json").write_text(json.dumps({"evaluation": rows + [{"name": "p999", "gemini_graph_sha256": None}]}))
        old = c.LISTES_SHA256
        c.LISTES_SHA256 = hashlib.sha256((root / "listes.json").read_bytes()).hexdigest()
        try:
            a = type("A", (), dict(listes=str(root / "listes.json"), gemini=str(root / "gem"), s1b=str(root / "s1b"),
                                   out=str(root / "out.json")))
            c.main(a)
            out = json.loads((root / "out.json").read_text())
            self.assertEqual(out["totals"]["images"], 26)
            self.assertTrue(out["no_gate"])
            (root / "s1b" / "p000.json").write_text("{}")
            with self.assertRaises(RuntimeError):
                c.main(a)
        finally:
            c.LISTES_SHA256 = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
