"""B1 (Codex p4, 30/10): the pilot's global monitor, on fictitious processes and clocks (no 20-minute wait)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import kaggle_a1_run as k  # noqa: E402

SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]
WRITES_BLANK = [sys.executable, "-c", "import sys, time; open(sys.argv[1], 'w').write('{}'); time.sleep(60)"]


class FakeClock:
    def __init__(self, step):
        self.t, self.step = 0.0, step

    def __call__(self):
        self.t += self.step
        return self.t


def calm(pid, work):
    return 1 << 20, 0, 1 << 40


def alive(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = self.tmp.name
        self.out = os.path.join(self.work, "a1-blanc")
        os.mkdir(self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def read_driver(self):
        return json.loads(Path(self.work, "driver.json").read_text())

    def test_wall_breach_stops_group_and_refuses_blank(self):
        cmd = WRITES_BLANK + [os.path.join(self.out, "blanc.json")]
        clock = FakeClock(100.0)  # every reading advances 100 s: the 1200 s wall is crossed after a few polls
        sleep = lambda s: __import__("time").sleep(0.05)
        rec = k.run_child(cmd, dict(os.environ), self.out, 0.0, 1200, self.work, clock, sleep, calm)
        self.assertEqual(rec["status"], "failed")
        self.assertEqual(rec["failure"], "wall time ceiling exceeded")
        self.assertNotEqual(rec["exit_code"], 0)
        self.assertFalse(os.path.exists(os.path.join(self.out, "blanc.json")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "blanc.REFUSED.json")))
        self.assertEqual(self.read_driver()["status"], "failed")

    def test_setup_time_counts_against_the_wall(self):
        clock = FakeClock(1.0)
        clock.t = 1199.5  # the pilot already used almost all of its 20 minutes before the child starts
        rec = k.run_child(SLEEPER, dict(os.environ), self.out, 0.0, 1200, self.work, clock, lambda s: None, calm)
        self.assertEqual(rec["failure"], "wall time ceiling exceeded")

    def test_ram_output_and_disk_ceilings(self):
        cases = {"RAM ceiling exceeded": lambda pid, w: (k.RAM_BYTES + 1, 0, 1 << 40),
                 "output ceiling exceeded": lambda pid, w: (0, k.OUTPUT_BYTES + 1, 1 << 40),
                 "disk exhausted": lambda pid, w: (0, 0, k.MIN_FREE_BYTES - 1)}
        for reason, measure in cases.items():
            child = subprocess.Popen(SLEEPER, start_new_session=True)
            failure, _ = k.monitor(child, 0.0, 1200, self.work, FakeClock(1.0), lambda s: None, measure)
            self.assertEqual(failure, reason)
            self.assertIsNotNone(child.poll())
            self.assertFalse(alive(child.pid))

    def test_late_finish_is_a_failure(self):
        # the child ends normally, but the clock read after its end is past the wall: still refused
        cmd = [sys.executable, "-c", "pass"]
        clock = FakeClock(0.0)

        def sleep(s):
            clock.t = 5000.0
            __import__("time").sleep(0.2)

        rec = k.run_child(cmd, dict(os.environ), self.out, 0.0, 1200, self.work, clock, sleep, calm)
        self.assertEqual(rec["status"], "failed")

    def test_child_error_and_success(self):
        rec = k.run_child([sys.executable, "-c", "raise SystemExit(3)"], dict(os.environ), self.out, 0.0, 1200,
                          self.work, FakeClock(0.0), lambda s: __import__("time").sleep(0.05), calm)
        self.assertEqual((rec["status"], rec["failure"]), ("failed", "a1 exit 3"))
        work2 = tempfile.mkdtemp(dir=self.work)
        out2 = os.path.join(work2, "a1-blanc")
        cmd = [sys.executable, "-c", "import os, sys; os.mkdir(sys.argv[1]); open(sys.argv[1] + '/blanc.json', 'w')", out2]
        rec = k.run_child(cmd, dict(os.environ), out2, 0.0, 1200, work2, FakeClock(0.0),
                          lambda s: __import__("time").sleep(0.05), calm)
        self.assertEqual((rec["status"], rec["failure"], rec["exit_code"]), ("passed", None, 0))
        self.assertTrue(Path(out2, "blanc.json").exists())

    def test_preexisting_blank_is_never_touched(self):
        # B3 reproduced by Codex p4: an earlier blanc.json in the output folder, then a failing run
        old = b'{"earlier": "reviewed bytes"}'
        Path(self.out, "blanc.json").write_bytes(old)
        Path(self.work, "driver.json").write_bytes(b"earlier driver")
        marker = os.path.join(self.work, "child_started")
        cmd = [sys.executable, "-c", "import sys; open(sys.argv[1], 'w'); raise SystemExit(1)", marker]
        rec = k.run_child(cmd, dict(os.environ), self.out, 0.0, 1200, self.work, FakeClock(0.0),
                          lambda s: None, calm)
        self.assertEqual((rec["status"], rec["started"]), ("failed", False))
        self.assertIn("output not empty before start", rec["failure"])
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(Path(self.out, "blanc.json").read_bytes(), old)
        self.assertFalse(Path(self.out, "blanc.REFUSED.json").exists())
        self.assertEqual(Path(self.work, "driver.json").read_bytes(), b"earlier driver")
        self.assertEqual(sorted(os.listdir(self.out)), ["blanc.json"])
        # an earlier driver.json alone (empty output folder) is refused the same way
        os.remove(os.path.join(self.out, "blanc.json"))
        rec = k.run_child(cmd, dict(os.environ), self.out, 0.0, 1200, self.work, FakeClock(0.0), lambda s: None, calm)
        self.assertFalse(rec["started"])
        self.assertFalse(os.path.exists(marker))

    def test_real_usage_reads_this_tree(self):
        Path(self.work, "x.bin").write_bytes(b"0" * 1000)
        rss, size, free = k.usage(os.getpid(), self.work)
        self.assertGreater(rss, 0)
        self.assertGreaterEqual(size, 1000)
        self.assertGreater(free, 0)

    def test_limits_match_preregistration(self):
        self.assertEqual(k.WALL_SECONDS["blanc"], 1200)
        self.assertEqual((k.RAM_BYTES, k.OUTPUT_BYTES), (8_000_000_000, 1_000_000_000))
        self.assertEqual(k.SCRIPTS, {"a1_run.py": "78b1ed982ae9b2e59624a30b83675703e156b92a1d45309b6089162c9dcee597",
                                     "a1_core.py": "177ef54243fd6dfed0aa557561aa365f41b2c992379aef6d4fab4c5e27ab205a"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
