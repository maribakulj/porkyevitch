"""B1 (Codex p4, 30/10): the D3 pilot's global monitor on fictitious processes and clocks (no 2-hour wait)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kaggle_d3_run as k  # noqa: E402

SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]
WRITES_BLANK = [sys.executable, "-c", "import sys, time; open(sys.argv[1], 'w').write('{}'); time.sleep(60)"]
SHORT = lambda s: time.sleep(0.05)


class FakeClock:
    def __init__(self, step, t=0.0):
        self.t, self.step = t, step

    def __call__(self):
        self.t += self.step
        return self.t


def calm(pid, work):
    return 1 << 20, 0, 1 << 40, 1 << 40


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = self.tmp.name
        self.out = os.path.join(self.work, "d3-blanc")
        os.mkdir(self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def test_wall_breach_stops_group_and_refuses_blank(self):
        cmd = WRITES_BLANK + [os.path.join(self.out, "blanc.json")]
        rec = k.run_child(cmd, dict(os.environ), self.out, 0.0, 7200, self.work, {"device": {"gpu": "fake"}},
                          FakeClock(600.0), SHORT, calm)
        self.assertEqual((rec["status"], rec["failure"]), ("failed", "wall time ceiling exceeded"))
        self.assertFalse(os.path.exists(os.path.join(self.out, "blanc.json")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "blanc.REFUSED.json")))
        driver = json.loads(Path(self.work, "driver.json").read_text())
        self.assertEqual((driver["status"], driver["device"]), ("failed", {"gpu": "fake"}))

    def test_setup_time_counts_against_the_wall(self):
        rec = k.run_child(SLEEPER, dict(os.environ), self.out, 0.0, 7200, self.work, None,
                          FakeClock(1.0, 7199.5), lambda s: None, calm)
        self.assertEqual(rec["failure"], "wall time ceiling exceeded")

    def test_machine_and_output_guards(self):
        cases = {"system RAM exhausted": lambda pid, w: (0, 0, 1 << 40, k.MIN_AVAILABLE_RAM - 1),
                 "output ceiling exceeded": lambda pid, w: (0, k.OUTPUT_BYTES + 1, 1 << 40, 1 << 40),
                 "disk exhausted": lambda pid, w: (0, 0, k.MIN_FREE_BYTES - 1, 1 << 40)}
        for reason, measure in cases.items():
            child = subprocess.Popen(SLEEPER, start_new_session=True)
            failure, _ = k.monitor(child, 0.0, 7200, self.work, FakeClock(1.0), lambda s: None, measure)
            self.assertEqual(failure, reason)
            self.assertIsNotNone(child.poll())

    def test_late_finish_error_and_success(self):
        clock = FakeClock(0.0)

        def late(s):
            clock.t = 9000.0
            time.sleep(0.2)

        rec = k.run_child([sys.executable, "-c", "pass"], dict(os.environ), self.out, 0.0, 7200, self.work, None,
                          clock, late, calm)
        self.assertEqual(rec["status"], "failed")
        fresh = lambda: tempfile.mkdtemp(dir=self.work)
        w = fresh()
        rec = k.run_child([sys.executable, "-c", "raise SystemExit(2)"], dict(os.environ), os.path.join(w, "o"), 0.0,
                          7200, w, None, FakeClock(0.0), SHORT, calm)
        self.assertEqual(rec["failure"], "d3 exit 2")
        w = fresh()
        rec = k.run_child([sys.executable, "-c", "pass"], dict(os.environ), os.path.join(w, "o"), 0.0, 7200, w, None,
                          FakeClock(0.0), SHORT, calm)
        self.assertEqual((rec["status"], rec["exit_code"]), ("passed", 0))

    def test_preexisting_blank_is_never_touched(self):
        # same flaw as A1 B3 (Codex p4): an earlier blanc.json in the output folder, then a failing run
        old = b'{"earlier": "reviewed bytes"}'
        Path(self.out, "blanc.json").write_bytes(old)
        Path(self.work, "driver.json").write_bytes(b"earlier driver")
        marker = os.path.join(self.work, "child_started")
        cmd = [sys.executable, "-c", "import sys; open(sys.argv[1], 'w'); raise SystemExit(1)", marker]
        rec = k.run_child(cmd, dict(os.environ), self.out, 0.0, 7200, self.work, None, FakeClock(0.0),
                          lambda s: None, calm)
        self.assertEqual((rec["status"], rec["started"]), ("failed", False))
        self.assertIn("output not empty before start", rec["failure"])
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(Path(self.out, "blanc.json").read_bytes(), old)
        self.assertFalse(Path(self.out, "blanc.REFUSED.json").exists())
        self.assertEqual(Path(self.work, "driver.json").read_bytes(), b"earlier driver")

    def test_pins_and_limits(self):
        here = Path(__file__).resolve().parents[1] / "scripts"
        import hashlib
        for name, want in k.SCRIPTS.items():
            self.assertEqual(hashlib.sha256((here / name).read_bytes()).hexdigest(), want)
        self.assertEqual(k.WALL_SECONDS, {"blanc": 7200, "complet": 7200})
        self.assertEqual(k.OUTPUT_BYTES, 200_000_000)
        self.assertEqual(k.CPU_TEST_FLAG, __import__("d3_run").CPU_TEST_FLAG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
