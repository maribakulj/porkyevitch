"""Resume branch of p9a_run (torch CPU, no data). Run: python -I tests/test_run_resume.py"""
from pathlib import Path
import sys
import tempfile
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import p9a_run as run  # noqa: E402
from p9a_common import sha, write_json  # noqa: E402

IDENTITY = {"seed": 0, "data_sha256": "d", "permutations_sha256": "p", "preparation_sha256": "q",
            "prereg_sha256": "r", "micro": 64}


def fixture(k=3, identity=IDENTITY, grid_per_epoch=57):
    d = Path(tempfile.mkdtemp())
    weights = {}
    for e in range(1, k + 1):
        torch.save({"w": torch.full((2,), float(e))}, d / f"A_epoch{e:02d}_weights.pt")
        weights[e] = sha(d / f"A_epoch{e:02d}_weights.pt")
    write_json(d / "A_seed.json", {"identity": identity, "epochs": [{}] * k, "grid": [{}] * (grid_per_epoch * k),
                                    "weights_sha256": weights})
    torch.save({"state": {}, "optimizer": {}, "scaler": {}, "rng": None, "epoch": k, "arm": "A", **IDENTITY},
               d / "A_resume.pt")
    return d


class ResumeTest(unittest.TestCase):
    def setUp(self):
        self.old = run.input_path
        run.input_path = lambda p: Path(p)

    def tearDown(self):
        run.input_path = self.old

    def test_valid_resume_copies_checked_weights(self):
        src, out = fixture(), Path(tempfile.mkdtemp())
        record, state = run.load_resume(src, "A", IDENTITY, out)
        self.assertEqual(state["epoch"], 3)
        self.assertEqual(sorted(record["weights_sha256"]), [1, 2, 3])
        self.assertTrue(all((out / f"A_epoch{e:02d}_weights.pt").exists() for e in (1, 2, 3)))

    def test_absent_state_means_restart(self):
        self.assertIsNone(run.load_resume(Path(tempfile.mkdtemp()), "A", IDENTITY, Path(tempfile.mkdtemp())))

    def test_refusals(self):
        with self.assertRaises(RuntimeError):
            run.load_resume(fixture(identity={**IDENTITY, "seed": 1}), "A", IDENTITY, Path(tempfile.mkdtemp()))
        with self.assertRaises(RuntimeError):
            run.load_resume(fixture(grid_per_epoch=56), "A", IDENTITY, Path(tempfile.mkdtemp()))
        src = fixture()
        torch.save({"w": torch.zeros(2)}, src / "A_epoch02_weights.pt")
        with self.assertRaises(RuntimeError):
            run.load_resume(src, "A", IDENTITY, Path(tempfile.mkdtemp()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
