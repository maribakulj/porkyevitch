"""Pilot amendment (30/10): pinned open_clip install before the subprocess; the reviewed scripts stay pinned unchanged."""
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
        sha_gate = src.index("sha256 is not the reviewed one")
        install = src.index('"pip", "install", "-q", OPEN_CLIP]')
        check = src.index('versions["open_clip_torch"] != OPEN_CLIP.split("==")[1]')
        child = src.index('"pe_kaggle.py"), "--stage"')
        self.assertTrue(sha_gate < install < check < child)

    def test_reviewed_scripts_unchanged(self):
        pins = literal(ast.parse(PILOT.read_text()), "SCRIPT_SHA256")
        self.assertEqual(pins, {"pe_kaggle.py": "017f488863fc58b5f9e7457d354a714a0b04d48bfc5e5409c497563d0c626a91",
                                "pe_common.py": "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af"})
        for name, want in pins.items():
            self.assertEqual(hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest(), want)


if __name__ == "__main__":
    unittest.main(verbosity=2)
