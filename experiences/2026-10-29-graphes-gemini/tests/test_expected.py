"""--expected N (30/10, D9): the image count must equal N (default 200, the pilot) before any call. No agy call is made:
every case here stops at the count check. Run: python -I tests/test_expected.py"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "graphes_agy.py"


def pilot(n):
    root = Path(tempfile.mkdtemp())
    (root / "images").mkdir()
    for k in range(n):
        (root / "images" / f"p{k:03d}.jpg").write_bytes(b"x")
    (root / "consigne.md").write_text("c")
    (root / "schema.json").write_text("{}")
    return root


def run(root, *extra):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), str(root), str(root / "consigne.md"), str(root / "schema.json"),
                           *extra], capture_output=True, text=True, timeout=60)


class ExpectedTest(unittest.TestCase):
    def test_default_is_still_200(self):
        root = pilot(60)
        r = run(root)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("AssertionError: (60, 200)", r.stderr)
        self.assertFalse((root / "appels").exists() or (root / "graphes").exists())

    def test_expected_must_match_the_folder(self):
        root = pilot(59)
        r = run(root, "--expected", "60", "--jobs", "1")
        self.assertIn("AssertionError: (59, 60)", r.stderr)
        self.assertFalse((root / "appels").exists() or (root / "graphes").exists())

    def test_val60_folder_count(self):
        val60 = Path.home() / "porkyevitch-donnees/graphes-gemini/val60/images"
        if not val60.is_dir():
            self.skipTest("val60 absent")
        self.assertEqual(len(sorted(val60.glob("p[0-9][0-9][0-9].*"))), 60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
