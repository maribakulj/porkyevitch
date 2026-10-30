"""Pilot of the non-transfer diagnostic: global monitor and B3 refusal (same code as D3), pins. Fictitious processes."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kaggle_nt_run as k  # noqa: E402

SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]
calm = lambda pid, w: (1 << 20, 0, 1 << 40, 1 << 40)


class Clock:
    def __init__(self, step, t=0.0):
        self.t, self.step = t, step

    def __call__(self):
        self.t += self.step
        return self.t


class PilotTest(unittest.TestCase):
    def test_wall_breach_stops_the_group(self):
        w = tempfile.mkdtemp()
        rec = k.run_child(SLEEPER, dict(os.environ), os.path.join(w, "non-transfert"), 0.0, 3600, w, None,
                          Clock(900.0), lambda s: time.sleep(0.05), calm)
        self.assertEqual((rec["status"], rec["failure"]), ("failed", "wall time ceiling exceeded"))

    def test_non_empty_output_refused_before_start(self):
        w = tempfile.mkdtemp()
        out = Path(w, "non-transfert")
        out.mkdir()
        (out / "diagnostic.json").write_bytes(b"earlier")
        marker = os.path.join(w, "started")
        rec = k.run_child([sys.executable, "-c", "import sys; open(sys.argv[1], 'w')", marker], dict(os.environ),
                          str(out), 0.0, 3600, w, None, Clock(0.0), lambda s: None, calm)
        self.assertFalse(rec["started"])
        self.assertFalse(os.path.exists(marker))
        self.assertEqual((out / "diagnostic.json").read_bytes(), b"earlier")

    def test_pins(self):
        here = Path(__file__).resolve().parents[1] / "scripts"
        for name, want in k.SCRIPTS.items():
            self.assertEqual(hashlib.sha256((here / name).read_bytes()).hexdigest(), want)
        gel = Path(__file__).resolve().parents[2] / "2026-10-29-gel-phase1" / "scripts"
        for name, want in k.GEL.items():
            self.assertEqual(hashlib.sha256((gel / name).read_bytes()).hexdigest(), want)
        self.assertEqual(k.WALL_SECONDS, {"diagnostic": 3600})

    def test_binding_pin_is_the_committed_pkyevitch_binding(self):
        import json
        liaison = Path(__file__).resolve().parents[1] / "liaison" / "sources-gel-pkyevitch.json"
        self.assertEqual(hashlib.sha256(liaison.read_bytes()).hexdigest(), k.BINDING)
        paths = json.loads(liaison.read_text())
        self.assertFalse(any("/datasets/mabaku/porky-" in v for v in paths.values()))
        self.assertEqual(paths["frozen_json"], "/kaggle/input/datasets/mabaku/pkyevitch-banc-gel/frozen.json")
        # kept under another name in the code dataset, so that the pilot finds sources.json exactly once
        self.assertFalse((liaison.parent / "sources.json").exists())

    def test_child_sees_one_gpu(self):
        # first launch: two T4 visible, nt_run requires exactly one (single_visible_T4_required)
        src = (Path(__file__).resolve().parents[1] / "scripts" / "kaggle_nt_run.py").read_text()
        env_line = src[src.index("    env = dict(os.environ"):src.index("    for name in (\"HF_TOKEN\"")]
        self.assertIn('CUDA_VISIBLE_DEVICES="0"', env_line)
        self.assertIn('"gpus_seen_by_pilot": torch.cuda.device_count()', src)
        self.assertLess(src.index('CUDA_VISIBLE_DEVICES="0"'), src.index("record = run_child(cmd, env"))
        run = (Path(__file__).resolve().parents[1] / "scripts" / "nt_run.py").read_text()
        self.assertIn("torch.cuda.device_count() == 1", run)  # the child's own gate, unchanged


if __name__ == "__main__":
    unittest.main(verbosity=2)
