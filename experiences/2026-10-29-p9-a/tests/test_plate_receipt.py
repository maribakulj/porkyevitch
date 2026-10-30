"""Plate receipt of the measures stage (no data). Run: python -I tests/test_plate_receipt.py"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import p9a_run as run  # noqa: E402
from p9a_common import ARMS  # noqa: E402

h = lambda b: hashlib.sha256(b).hexdigest()


def plates(gel="g"):
    d = Path(tempfile.mkdtemp())
    (d / "images").mkdir()
    index = {"gel_sha256": gel, "plates": {}}
    for arm in ARMS:
        rows = [{"shard": "train-00000-of-00011", "row": k, "md5": f"{arm}{k:030d}"[:32]} for k in range(12)]
        index["plates"][arm] = rows
        (d / f"planche_{arm}.html").write_text(f"<html>{arm}</html>")
        for r in rows:
            (d / "images" / f"{r['md5']}.image").write_bytes(b"img")
    (d / "planches.json").write_text(json.dumps(index))
    files = {str(p.relative_to(d)): h(p.read_bytes()) for p in sorted(d.rglob("*")) if p.is_file()}
    (d / "MANIFEST_PLANCHES.json").write_text(json.dumps({"files": files}))
    return d, files


def receipt(d, files, looks=(("wA:p1", "t"), ("Grok p2", "t"))):
    r = d / "recu.json"
    r.write_text(json.dumps({"stage": "planches_p9a_regardees",
                             "manifest_sha256": h((d / "MANIFEST_PLANCHES.json").read_bytes()),
                             "regards": [{"viewer": v, "viewed_at": t} for v, t in looks],
                             "plates_html_sha256": {a: files[f"planche_{a}.html"] for a in ARMS}}))
    return r


class ReceiptTest(unittest.TestCase):
    def test_valid(self):
        d, files = plates()
        self.assertEqual(run.check_plate_receipt(d, receipt(d, files), "g")["stage"], "planches_p9a_regardees")

    def test_one_look_or_missing_date_refused(self):
        d, files = plates()
        for looks in ((("wA:p1", "t"),), (("Grok p2", "t"),), (("wA:p1", "t"), ("Grok p2", ""))):
            with self.assertRaises(RuntimeError):
                run.check_plate_receipt(d, receipt(d, files, looks), "g")

    def test_other_freeze_changed_file_missing_arm_refused(self):
        d, files = plates()
        with self.assertRaises(RuntimeError):
            run.check_plate_receipt(d, receipt(d, files), "other")
        (d / "planche_A.html").write_text("changed")
        with self.assertRaises(RuntimeError):
            run.check_plate_receipt(d, receipt(d, files), "g")
        d, files = plates()
        index = json.loads((d / "planches.json").read_text())
        del index["plates"]["C"]
        (d / "planches.json").write_text(json.dumps(index))
        files["planches.json"] = h((d / "planches.json").read_bytes())
        (d / "MANIFEST_PLANCHES.json").write_text(json.dumps({"files": files}))
        with self.assertRaises(RuntimeError):
            run.check_plate_receipt(d, receipt(d, files), "g")


if __name__ == "__main__":
    unittest.main(verbosity=2)
