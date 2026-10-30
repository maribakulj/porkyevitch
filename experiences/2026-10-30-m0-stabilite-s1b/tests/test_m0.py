"""M0 on fictitious graphs only. Run: python3 -I tests/test_m0.py"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import m0  # noqa: E402

G = {"objects": [{"id": "o1", "name": "man", "box": [100, 100, 400, 900]},
                 {"id": "o2", "name": "staff", "box": [380, 100, 420, 900]},
                 {"id": "o3", "name": "tree", "box": [600, 0, 1000, 800]}],
     "relations": [["o1", "holds", "o2"], ["o1", "left of", "o3"]]}


def write(d, name, g):
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(g))


def variant(**changes):
    g = json.loads(json.dumps(G))
    for k, v in changes.items():
        if k == "rename":
            g["objects"][v[0]]["name"] = v[1]
        if k == "move":
            g["objects"][v[0]]["box"] = v[1]
        if k == "relations":
            g["relations"] = v
        if k == "add":
            g["objects"].append(v)
    return load(g)


def load(g):
    d = Path(tempfile.mkdtemp())
    write(d, "x", g)
    return m0.load(d / "x.json")


class M0Test(unittest.TestCase):
    def test_identical_passes(self):
        s = m0.pooled([m0.image_stats(load(G), load(G))])
        self.assertEqual((s["objects_matched_share"], s["category_agreement_iou_matched"],
                          s["relations_v0_jaccard_matched_pairs"]), (1.0, 1.0, 1.0))

    def test_name_differs_category_same_is_matched(self):
        st = m0.image_stats(load(G), variant(rename=(0, "old man")))
        self.assertEqual(st["matched"], 3)
        self.assertLess(st["raw_names_jaccard"], 1.0)                # raw names disagree, learnt targets agree

    def test_category_differs_same_place(self):
        st = m0.image_stats(load(G), variant(rename=(2, "dog")))
        self.assertEqual((st["matched"], st["iou_matched"], st["iou_matched_same_category"]), (2, 3, 2))

    def test_moved_box_and_changed_predicate(self):
        st = m0.image_stats(load(G), variant(move=(2, [0, 0, 100, 100]),
                                            relations=[["o1", "carries", "o2"], ["o1", "left of", "o3"]]))
        self.assertEqual(st["matched"], 2)
        # holds -> carries: holds is v0, carries becomes autre_relation; left of o3 lost (o3 unmatched)
        self.assertEqual((st["rel_inter"], st["rel_union"]), (0, 2))

    def test_degenerate_box_dropped_and_counted(self):
        g = variant(add={"id": "o4", "name": "cup", "box": [10, 10, 10, 50]})
        self.assertEqual(g["dropped"], 1)

    def test_greedy_tie_order(self):
        a = [{"box": [0, 0, 100, 100], "cat": "personne"}, {"box": [0, 0, 100, 100], "cat": "personne"}]
        b = [{"box": [0, 0, 100, 100], "cat": "personne"}]
        self.assertEqual(m0.match(a, b), {0: 0})

    def test_null_gates_give_no_decision_and_fixed_gates_decide(self):
        r = {"objects_matched_share": 0.8, "relations_v0_jaccard_matched_pairs": 0.3}
        self.assertIsNone(m0.decide(r, {"porte_objets_apparies_min": None,
                                        "porte_relations_jaccard_v0_cible_dure_min": 0.5})["decision"])
        d = m0.decide(r, {"porte_objets_apparies_min": 0.7, "porte_relations_jaccard_v0_cible_dure_min": 0.5})
        self.assertEqual((d["objects"], d["relations"]), ("cibles_dures_passe_1", "pas_de_cible_dure_relations_douces_ou_exclues"))
        d = m0.decide(r, {"porte_objets_apparies_min": 0.9, "porte_relations_jaccard_v0_cible_dure_min": 0.2})
        self.assertEqual((d["objects"], d["relations"]), ("cibles_douces_seconde_passe_240", "cible_dure_possible"))

    def test_main_on_sixty_fictitious_pairs(self):
        root = Path(tempfile.mkdtemp())
        picks = [{"name": f"t{k:03d}", "role": "validation_interne" if k < 60 else "apprentissage"} for k in range(70)]
        (root / "tirage.json").write_text(json.dumps({"picks": picks}))
        for k in range(60):
            write(root / "p1", f"t{k:03d}", G)
            write(root / "p2", f"t{k:03d}", G if k % 2 else json.loads(json.dumps(
                {**G, "objects": G["objects"][:2], "relations": G["relations"][:1]})))
        params = json.loads((Path(__file__).resolve().parents[1] / "PARAMETRES.json").read_text())
        (root / "params.json").write_text(json.dumps(params))
        old = m0.TIRAGE_SHA256
        m0.TIRAGE_SHA256 = hashlib.sha256((root / "tirage.json").read_bytes()).hexdigest()
        try:
            a = type("A", (), dict(pass1=str(root / "p1"), pass2=str(root / "p2"), tirage=str(root / "tirage.json"),
                                   params=str(root / "params.json"), out=str(root / "m0.json")))
            m0.main(a)
        finally:
            m0.TIRAGE_SHA256 = old
        out = json.loads((root / "m0.json").read_text())
        self.assertEqual(out["images"], 60)
        self.assertAlmostEqual(out["pooled"]["objects_matched_share"], 2 * (30 * 3 + 30 * 2) / (60 * 3 + 30 * 3 + 30 * 2))
        self.assertIsNone(out["decision"]["decision"])                # gates are null in PARAMETRES.json
        lo, hi = out["ci95_by_image"]["objects_matched_share"]
        self.assertLessEqual(lo, out["pooled"]["objects_matched_share"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
