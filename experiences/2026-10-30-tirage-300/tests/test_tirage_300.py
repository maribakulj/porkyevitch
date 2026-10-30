"""Synthetic tests of tirage_300. No ICAI data. Run: python3 -I tests/test_tirage_300.py"""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import tirage_300 as t  # noqa: E402


def synthetic_rows(n=6000, seed=5):
    rng = np.random.default_rng(seed)
    weights = np.array([2, 5, 10, 8, 12, 15, 6, 25, 1.5, 0.5])  # chapter 9 rare, 8 small
    rows = []
    for i in range(n):
        md5 = f"{i:032x}"
        k = rng.integers(1, 4)
        labels = [f"{rng.choice(10, p=weights / weights.sum())}{rng.integers(10)}A" for _ in range(k)]
        if i % 97 == 0:
            labels = ["86(proverb)"]  # no chapter after drop86
        rows.append((f"train-{i % 11:05d}-of-00011", i, md5, labels))
        if i % 50 == 0:  # duplicated md5 in a later shard: first row wins
            rows.append(("train-00010-of-00011", 10_000 + i, md5, ["9Z"]))
    return rows


class TirageTest(unittest.TestCase):
    def test_chapter_rule_majority_then_rarer_then_digit(self):
        ch, none, present = t.image_chapters({"a": ["11H", "25F", "21A"], "b": ["11H", "71A"], "c": ["86(x)"],
                                              "d": ["13"]})
        self.assertEqual(ch["a"], "2")  # two codes of chapter 2 against one of chapter 1
        self.assertEqual(ch["b"], "7")  # tie 1/7: chapter 7 is present in 1 group, chapter 1 in 3
        self.assertEqual((none, present["1"], present["7"]), (["c"], 3, 1))

    def test_tie_on_presence_goes_to_smaller_digit(self):
        ch, _, _ = t.image_chapters({"a": ["11H", "71A"], "b": ["12", "72"]})
        self.assertEqual(ch, {"a": "1", "b": "1"})

    def test_allocation_minimum_proportional_caps(self):
        sizes = {"0": 1000, "1": 3000, "2": 5000, "3": 4, "4": 0, "5": 50, "6": 900, "7": 9000, "8": 12, "9": 30}
        a = t.allocate(sizes)
        self.assertEqual(sum(a.values()), 300)
        self.assertEqual((a["3"], a["4"]), (4, 0))
        self.assertTrue(all(a[h] >= min(10, s) and a[h] <= s for h, s in sizes.items()))
        self.assertGreater(a["7"], a["2"])
        self.assertGreater(a["2"], a["1"])

    def test_allocation_small_population_takes_everything(self):
        self.assertEqual(t.allocate({"0": 100, "1": 150}, n=300), {"0": 100, "1": 150})

    def test_largest_remainder_ties_smaller_digit(self):
        self.assertEqual(t.largest_remainder(1, {"0": 1, "1": 1}, {"0": 5, "1": 5}), {"0": 1, "1": 0})

    def test_plan_exclusions_counts_and_determinism(self):
        rows = synthetic_rows()
        groups = sorted({r[2] for r in rows})
        gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
        free = [g for g in groups if g not in gval]
        test_md5, pilot = set(free[:3]) | {"f" * 32}, set(free[3:203])
        p = t.plan(rows, test_md5, pilot)
        self.assertEqual(p, t.plan(rows, test_md5, pilot))
        md5s = {x["md5"] for x in p["picks"]}
        self.assertEqual(len(md5s), 300)
        self.assertFalse(md5s & (gval | test_md5 | pilot))
        self.assertEqual(p["test_copy_groups_excluded"], 3)
        self.assertEqual(sum(1 for x in p["picks"] if x["role"] == "validation_interne"), 60)
        self.assertEqual(sum(c["drawn"] for c in p["chapters"].values()), 300)
        self.assertGreaterEqual(p["chapters"]["9"]["drawn"], min(10, p["chapters"]["9"]["population"]))
        first = {}
        for r in rows:
            first.setdefault(r[2], r)
        for x in p["picks"]:
            self.assertEqual((x["shard"], x["row"]), first[x["md5"]][:2])  # first row in shard order
            self.assertEqual(t.image_chapters({x["md5"]: first[x["md5"]][3]})[0][x["md5"]] in t.CHAPTERS, True)
        self.assertEqual(sorted(x["name"] for x in p["picks"]), [f"t{k:03d}" for k in range(300)])
        by_name = [x["chapter"] for x in sorted(p["picks"], key=lambda x: x["name"])]
        self.assertNotEqual(by_name, sorted(by_name))  # names do not follow chapters

    def test_plan_refuses_pilot_in_validation(self):
        rows = synthetic_rows(2000)
        groups = sorted({r[2] for r in rows})
        gval = sorted(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
        with self.assertRaises(AssertionError):
            t.plan(rows, set(), {gval[0]})

    def test_chapter_counts_drop86_and_non_digit(self):
        self.assertEqual(t.chapter_counts(["86(x)", " 11H", "11H", "bad", "25F"]), {"1": 1, "2": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
