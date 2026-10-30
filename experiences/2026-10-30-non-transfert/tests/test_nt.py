"""Non-transfer diagnostic on fictitious data (numpy only). Run: python -I tests/test_nt.py"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import nt_core as nt  # noqa: E402
import nt_run as run  # noqa: E402

# depth: "1" = 1, "11" = 2, "11H" = 3, "11H1" = 4, "25" = 2, "25F" = 3
VOCAB = ["1", "11", "11H", "11H1", "2", "25", "25F"]
VI = {c: j for j, c in enumerate(VOCAB)}


def closure_idx(codes):
    return {VI[a] for c in codes for a in nt.mm.ancestors(c) if a in VI}


def bank():
    """Two query images; four training rows; counts make 11H and 11H1 frequent (> 100), 25F mid (21-100)."""
    fit = [["11H1"], ["25F"], ["11"], ["11H"]]
    anc = [closure_idx(y) for y in fit]
    counts = {"11H": 150, "11H1": 120, "25F": 50, "11": 300}
    p = np.zeros((2, len(VOCAB)), dtype=np.float32)
    p[0, VI["11H"]] = 0.7   # above T* threshold 0.6
    p[0, VI["11H1"]] = 0.65  # above, and the most specific: 11H is emitted only through closure
    b = {"truths": [["11H1", "25F", "99X"], ["11H"]],          # 99X outside V
         "star": [["11H1"], []], "star_prob": p,
         "tk": [["11H1"], ["11H"]], "tk_score": np.zeros_like(p),
         "nn_weight": [np.array([0.9, 0.0, -0.2, 0.1]), np.array([0.5, 0.5, 0.0, 0.0])],
         "nn_index": [np.array([0, 1, 2, 3]), np.array([2, 1, 0, 3])],
         "rand_index": [np.array([1, 2]), np.array([3, 1])],
         "groups": ["a", "b"]}
    b["tk_score"][1, VI["11H"]] = 0.6
    return b, anc, counts


class CoreTest(unittest.TestCase):
    def test_cells_and_main_target(self):
        vset = set(VOCAB)
        self.assertEqual(nt.cell("11H", vset, {"11H": 150}), (">100", "3-4"))
        self.assertTrue(nt.in_main(nt.cell("11H1", vset, {"11H1": 101})))
        self.assertFalse(nt.in_main(nt.cell("11H1", vset, {"11H1": 100})))   # > 100 strictly
        self.assertFalse(nt.in_main(nt.cell("11", vset, {"11": 900})))       # depth 2
        self.assertIsNone(nt.cell("99X", vset, {}))

    def test_pair_records(self):
        b, anc, counts = bank()
        recs = nt.pair_records(b, VOCAB, counts, anc, 0.5, 0.6)
        self.assertEqual([(r["image"], r["code"]) for r in recs], [(0, "11H1"), (0, "25F"), (1, "11H")])
        r0, r1, r2 = recs
        self.assertTrue(r0["head_exact"] and r0["head_closure"] and r0["head_above_threshold"])
        # neighbours of image 0: weights 0.9, 0, -0.2 -> 0, 0.1; 11H1 only in row 0 (w 0.9) -> vote 0.9 / 1.0
        self.assertTrue(r0["vote_available"])
        self.assertAlmostEqual(r0["vote"], 0.9)
        # 25F is in row 1 whose weight is 0: present among the 20 but NOT available (positive weight required)
        self.assertFalse(r1["vote_available"])
        self.assertEqual(r1["vote"], 0.0)
        self.assertTrue(r1["random_available"])   # random rows 1, 2: row 1 carries 25F
        # image 1: 11H in rows 0 (11H1) and 3 (11H); weights 0.5 / 0.5 on rows 2 and 1 -> not available
        self.assertFalse(r2["vote_available"])
        self.assertFalse(r2["head_closure"])
        self.assertTrue(r2["tk_exact"] and r2["tk_above_threshold"])
        self.assertEqual(r2["random_vote"], 0.5)   # random rows 3 (11H) and 1

    def test_summary_paired_table_and_threshold_chain(self):
        b, anc, counts = bank()
        recs = nt.pair_records(b, VOCAB, counts, anc, 0.5, 0.6)
        s = nt.summary(recs)
        t = s["paired_head_closure_x_vote_available"]
        self.assertEqual(sum(t.values()), s["pairs"])
        self.assertEqual(t, {"both": 1, "head_only": 0, "vote_only": 0, "neither": 2})
        self.assertAlmostEqual(s["recall"]["head_closure"], 1 / 3)
        chain = s["threshold_to_most_specific"]
        self.assertEqual(chain["emitted_exactly"], 1)
        self.assertEqual(nt.summary([])["pairs"], 0)

    def test_cross_table_has_every_cell(self):
        b, anc, counts = bank()
        table = nt.cross_table(nt.pair_records(b, VOCAB, counts, anc, 0.5, 0.6))
        self.assertEqual(len(table), 9)
        self.assertEqual(table[">100|3-4"]["pairs"], 2)
        self.assertEqual(table["21-100|3-4"]["pairs"], 1)
        self.assertEqual(table["5-20|1-2"]["pairs"], 0)

    def test_common_codes_macro_leaves_absent_codes_out(self):
        a = {"x": {"head_closure": 1.0}, "y": {"head_closure": 0.0}}
        b = {"y": {"head_closure": 1.0}, "z": {"head_closure": 0.0}}
        self.assertEqual(nt.common_codes(a, b, "head_closure"), {"codes": 1, "a": 0.0, "b": 1.0})
        self.assertEqual(nt.common_codes(a, {}, "head_closure"), {"codes": 0})

    def test_bootstrap_by_group_is_paired_and_reproducible(self):
        b, anc, counts = bank()
        recs = nt.pair_records(b, VOCAB, counts, anc, 0.5, 0.6)
        x = nt.bootstrap(recs, 2, b["groups"], 200, 7)
        y = nt.bootstrap(recs, 2, b["groups"], 200, 7)
        self.assertEqual(x, y)
        self.assertEqual(x["groups"], 2)
        lo, hi = x["ci95"]["head_closure"]
        self.assertTrue(0 <= lo <= hi <= 1)
        self.assertIn("vote_available-random_available", x["ci95"])

    def test_bank_report(self):
        b, anc, counts = bank()
        recs, rep = nt.bank_report(b, VOCAB, counts, anc, {"alpha": 0.75, "tk_threshold": 0.5, "star_threshold": 0.6},
                                   100, 1)
        self.assertEqual(rep["main"]["pairs"], 2)
        self.assertEqual(rep["images_without_main_target"], 0)
        self.assertEqual(rep["outside_vocabulary_pairs"], 1)


class DevOnlyTest(unittest.TestCase):
    def frozen(self, test_bytes):
        dev = {"items": [{"pid": f"https://id/{k}", "truth": ["11H", "86A"], "truth_projected": ["11H"], "component": k,
                          "support": "print", "iiif": "u", "image_sha256": "0" * 64, "width": 1, "height": 1}
                         for k in range(300)]}
        body = (b'{\n "date_utc": "x",\n "test": ' + test_bytes + b',\n "dev": ' +
                json.dumps(dev, indent=1).replace("\n", "\n ").encode() + b',\n "audit": {}\n}')
        p = Path(tempfile.mkdtemp()) / "frozen.json"
        p.write_bytes(body)
        return p

    def require(self, ok, code):
        if not ok:
            raise RuntimeError(code)

    def sha(self, p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()

    def test_test_member_is_never_decoded(self):
        # the "test" member here is not even valid UTF-8 or JSON: decoding it anywhere would raise
        p = self.frozen(b'\xff\xfe NOT JSON {{{')
        old = run.nt_frozen_sha
        run.nt_frozen_sha = lambda: self.sha(p)
        try:
            items = run.dev_items(p, self.sha, self.require)
        finally:
            run.nt_frozen_sha = old
        self.assertEqual(len(items), 300)
        self.assertEqual(items[0]["truth_projected"], ["11H"])

    def test_wrong_sha_and_boundary_refused(self):
        p = self.frozen(b'{}')
        with self.assertRaises(RuntimeError):
            old = run.nt_frozen_sha
            run.nt_frozen_sha = lambda: "0" * 64
            try:
                run.dev_items(p, self.sha, self.require)
            finally:
                run.nt_frozen_sha = old
        q = Path(tempfile.mkdtemp()) / "f.json"
        q.write_bytes(p.read_bytes().replace(b',\n "audit": {}\n}', b'}'))
        old = run.nt_frozen_sha
        run.nt_frozen_sha = lambda: self.sha(q)
        try:
            with self.assertRaisesRegex(RuntimeError, "dev_member_boundary"):
                run.dev_items(q, self.sha, self.require)
        finally:
            run.nt_frozen_sha = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
