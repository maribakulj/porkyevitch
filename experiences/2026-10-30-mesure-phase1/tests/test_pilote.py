"""Pilot amendment: the dev archive of the test stage (no Kaggle, no real data). Run: python3 -I tests/test_pilote.py"""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
import kaggle_mesure_run as pilot  # noqa: E402


def add_bytes(tar, name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def archive(extra=None, scripts=True):
    """mesure-dev/ (dev.json, MANIFEST_DEV.json, planches/), recu_planches.json and the two reviewed scripts."""
    path = Path(tempfile.mkdtemp()) / "mesure-dev.bin"
    with tarfile.open(path, "w") as tar:  # uncompressed
        add_bytes(tar, "mesure-dev/dev.json", b"{}")
        add_bytes(tar, "mesure-dev/MANIFEST_DEV.json", b"{}")
        add_bytes(tar, "mesure-dev/planches/T-H-T_star.html", b"<html></html>")
        add_bytes(tar, "recu_planches.json", json.dumps({"stage": "planches_dev_regardees"}).encode())
        if scripts:
            for name in ("mesure_phase1.py", "mesure_metrics.py"):
                add_bytes(tar, f"scripts/{name}", (HERE / "scripts" / name).read_bytes())
        if extra:
            extra(tar)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


class PilotTest(unittest.TestCase):
    def dest(self):
        return Path(tempfile.mkdtemp()) / "dev-in"

    def test_valid_archive_extracts_and_finds_inputs_in_dev_in_only(self):
        path, digest = archive()
        dev_in = pilot.safe_extract(path, digest, self.dest())
        dev, receipt, script = pilot.test_inputs(dev_in)
        self.assertTrue(dev.endswith("mesure-dev") and receipt.endswith("recu_planches.json"))
        self.assertTrue(Path(script).is_relative_to(dev_in))

    def test_wrong_or_missing_sha_refused_before_writing(self):
        path, _ = archive()
        dest = self.dest()
        for digest in ("0" * 64, None):
            with self.assertRaises(RuntimeError):
                pilot.safe_extract(path, digest, dest)
        self.assertFalse(dest.exists())

    def test_dotdot_member_refused(self):
        path, digest = archive(lambda t: add_bytes(t, "mesure-dev/../../evil.txt", b"x"))
        dest = self.dest()
        with self.assertRaises(RuntimeError):
            pilot.safe_extract(path, digest, dest)
        self.assertFalse(dest.exists())
        self.assertFalse((dest.parent.parent / "evil.txt").exists())

    def test_absolute_member_refused(self):
        path, digest = archive(lambda t: add_bytes(t, "/tmp/evil.txt", b"x"))
        with self.assertRaises(RuntimeError):
            pilot.safe_extract(path, digest, self.dest())

    def test_symlink_and_hardlink_refused(self):
        def sym(t):
            info = tarfile.TarInfo("mesure-dev/link")
            info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
            t.addfile(info)

        def hard(t):
            info = tarfile.TarInfo("mesure-dev/hard")
            info.type, info.linkname = tarfile.LNKTYPE, "recu_planches.json"
            t.addfile(info)
        for maker in (sym, hard):
            path, digest = archive(maker)
            dest = self.dest()
            with self.assertRaises(RuntimeError):
                pilot.safe_extract(path, digest, dest)
            self.assertFalse(dest.exists())

    def test_special_member_refused(self):
        def fifo(t):
            info = tarfile.TarInfo("mesure-dev/pipe")
            info.type = tarfile.FIFOTYPE
            t.addfile(info)
        path, digest = archive(fifo)
        with self.assertRaises(RuntimeError):
            pilot.safe_extract(path, digest, self.dest())

    def test_duplicate_or_wrong_script_refused(self):
        path, digest = archive(lambda t: add_bytes(t, "other/MANIFEST_DEV.json", b"{}"))
        with self.assertRaises(RuntimeError):
            pilot.test_inputs(pilot.safe_extract(path, digest, self.dest()))
        def bad(t):
            add_bytes(t, "scripts/mesure_phase1.py", b"print('changed')")
            add_bytes(t, "scripts/mesure_metrics.py", b"")
        path, digest = archive(bad, scripts=False)
        with self.assertRaises(RuntimeError):
            pilot.test_inputs(pilot.safe_extract(path, digest, self.dest()))

    def test_existing_dev_in_refused(self):
        path, digest = archive()
        dest = self.dest()
        dest.mkdir(parents=True)
        with self.assertRaises(RuntimeError):
            pilot.safe_extract(path, digest, dest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
