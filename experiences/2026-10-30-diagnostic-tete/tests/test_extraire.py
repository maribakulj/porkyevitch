"""Synthetic tests of extraire_confiants_absents. No ICAI data. Run: python3 -I tests/test_extraire.py"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import diag_metrics as dm  # noqa: E402
import extraire_confiants_absents as ex  # noqa: E402


class ExtraireTest(unittest.TestCase):
    def test_parser_identical_to_the_diagnostic(self):
        for c in ["11H(JEROME)3", "25F23(LION)(+12)", "31A:25F", "86(Amor)", "bad code", "61B:31A2212(+1)"]:
            self.assertEqual(ex.ancestors(c), dm.ancestors(c))
            self.assertEqual(ex.drop86([c]), dm.drop86([c]))

    def test_describe_exact_then_broader_fallback(self):
        texts = {"31A": "the human figure", "31A2": "postures", "61B": "historical persons"}
        self.assertEqual(ex.describe("31A", texts), {"exact": True, "text": "the human figure"})
        d = ex.describe("61B:31A2212(+1)", texts)
        self.assertFalse(d["exact"])
        self.assertEqual(d["text"], "Iconclass notation: 61B:31A2212(+1). Broader concepts: "
                                    "the human figure ; historical persons ; postures")
        self.assertEqual(ex.describe("bad code", texts)["text"], "Iconclass notation: bad code.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
