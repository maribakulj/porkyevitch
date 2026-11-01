"""Sonnet audit (30/10): budget.json is rewritten after MANIFEST_PLANCHES.json, so the reviewed check_plate_receipt of
29faa62 always fails. On the REAL plates of seed 0 (local copy, skipped if absent): the old code fails with
'plate file missing or changed', the new one passes, and a changed image or HTML is still refused. Also checks that
nothing else in p9a_run.py differs from 29faa62 (AST of every other function and class). Run: python -I tests/..."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
REAL = Path.home() / "porkyevitch-donnees/p9a/planches-0b/p9a-planches-0/planches"
OLD_COMMIT = "29faa62"
GEL = "13f75f3acfb890724d6463e30c66ae6437e9d6f7c2e95161641623272be50101"


def old_source():
    return subprocess.run(["git", "-C", str(HERE), "show", f"{OLD_COMMIT}:experiences/2026-10-29-p9-a/scripts/p9a_run.py"],
                          capture_output=True, text=True, check=True).stdout


def load(name, source):
    d = Path(tempfile.mkdtemp())
    for f in (HERE / "scripts").glob("*.py"):
        shutil.copy(f, d / f.name)
    (d / "p9a_run.py").write_text(source)
    sys.path.insert(0, str(d))
    try:
        spec = importlib.util.spec_from_file_location(name, d / "p9a_run.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(d))
    mod.input_path = lambda p: Path(p)
    return mod


def receipt(plates, folder):
    m = json.loads((plates / "MANIFEST_PLANCHES.json").read_text())["files"]
    r = {"stage": "planches_p9a_regardees",
         "manifest_sha256": hashlib.sha256((plates / "MANIFEST_PLANCHES.json").read_bytes()).hexdigest(),
         "plates_html_sha256": {a: m[f"planche_{a}.html"] for a in ("F", "controle_global", "A", "C")},
         "regards": [{"viewer": "wA:p1", "viewed_at": "2026-10-30T12:00:00Z"},
                     {"viewer": "Grok p2", "viewed_at": "2026-10-30T12:05:00Z"}]}
    path = Path(folder) / "recu.json"
    path.write_text(json.dumps(r))
    return path


@unittest.skipUnless((REAL / "planches.json").is_file() and (REAL / "planches.json").stat().st_size > 0,
                     "real plates of seed 0 absent")
class RealPlatesTest(unittest.TestCase):
    def setUp(self):
        self.plates = Path(tempfile.mkdtemp()) / "planches"
        shutil.copytree(REAL, self.plates)
        self.recu = receipt(self.plates, self.plates.parent)

    def test_old_code_fails_new_code_passes(self):
        old = load("p9a_run_old", old_source())
        with self.assertRaisesRegex(RuntimeError, "plate file missing or changed"):
            old.check_plate_receipt(self.plates, self.recu, GEL)
        new = load("p9a_run_new", (HERE / "scripts/p9a_run.py").read_text())
        r = new.check_plate_receipt(self.plates, self.recu, GEL)
        self.assertEqual([x["viewer"] for x in r["regards"]], ["wA:p1", "Grok p2"])

    def test_plate_content_still_guarded(self):
        new = load("p9a_run_new2", (HERE / "scripts/p9a_run.py").read_text())
        image = sorted((self.plates / "images").glob("*.image"))[0]
        image.write_bytes(image.read_bytes() + b"x")
        with self.assertRaisesRegex(RuntimeError, "plate file missing or changed"):
            new.check_plate_receipt(self.plates, self.recu, GEL)

    def test_html_and_index_still_guarded(self):
        new = load("p9a_run_new3", (HERE / "scripts/p9a_run.py").read_text())
        html = self.plates / "planche_A.html"
        html.write_text(html.read_text() + " ")
        with self.assertRaisesRegex(RuntimeError, "plate file missing or changed"):
            new.check_plate_receipt(self.plates, self.recu, GEL)
        shutil.rmtree(self.plates)
        shutil.copytree(REAL, self.plates)
        (self.plates / "planches.json").unlink()
        with self.assertRaisesRegex(RuntimeError, "plate file missing or changed"):
            new.check_plate_receipt(self.plates, self.recu, GEL)

    def test_budget_json_absent_or_changed_is_irrelevant(self):
        new = load("p9a_run_new4", (HERE / "scripts/p9a_run.py").read_text())
        (self.plates / "budget.json").unlink()
        new.check_plate_receipt(self.plates, self.recu, GEL)


class OnlyTheCheckChangedTest(unittest.TestCase):
    def test_every_other_definition_is_identical_to_29faa62(self):
        def defs(src):
            tree = ast.parse(src)
            return {n.name: ast.dump(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        old, new = defs(old_source()), defs((HERE / "scripts/p9a_run.py").read_text())
        self.assertEqual(set(old), set(new))
        changed = sorted(k for k in old if old[k] != new[k])
        self.assertEqual(changed, ["check_plate_receipt"])
        # stage_seed and stage_planches, which produced gel 13f75f3a and the plates, are byte-for-byte the same AST
        self.assertEqual(old["stage_seed"], new["stage_seed"])
        self.assertEqual(old["stage_planches"], new["stage_planches"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
