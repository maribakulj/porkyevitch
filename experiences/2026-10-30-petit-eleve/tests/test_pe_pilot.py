"""Pilot amendments (30/10): pinned open_clip and ultralytics installs before the subprocess, scripts pinned, mesures stage."""
import ast
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "scripts" / "kaggle_pe_run.py"


def literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


class TestPilot(unittest.TestCase):
    def test_pin_and_order(self):
        src = PILOT.read_text()
        self.assertEqual(literal(ast.parse(src), "OPEN_CLIP"), "open_clip_torch==3.3.0")
        self.assertEqual(literal(ast.parse(src), "ULTRALYTICS"), "ultralytics==8.4.177")
        sha_gate = src.index("sha256 is not the reviewed one")
        install = src.index('for package in (OPEN_CLIP, ULTRALYTICS):')
        check = src.index('versions["ultralytics"] != ULTRALYTICS.split("==")[1]')
        child = src.index('"pe_kaggle.py"), "--stage"')
        self.assertTrue(sha_gate < install < check < child)

    def test_reviewed_scripts_unchanged(self):
        pins = literal(ast.parse(PILOT.read_text()), "SCRIPT_SHA256")
        self.assertEqual(set(pins), {"pe_kaggle.py", "pe_common.py"})
        self.assertEqual(pins["pe_common.py"], "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af")
        for name, want in pins.items():
            self.assertEqual(hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest(), want)

    def test_mesures_stage_needs_sealed_predictions_and_receipt(self):
        src = PILOT.read_text()
        self.assertIn('only("MANIFEST_PREDICTIONS.json", mounted)', src)
        self.assertIn('receipt = only("recu_planche_pe.json")', src)
        self.assertIn("if len(sealed) != 1:", src)
        self.assertIn("if len(receipt) != 1:", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
