"""Synthetic tests of the pilot's seal protection (Codex p4 B1). No model, no data, no network.

The reviewed pilot is copied into a fake /kaggle tree and loaded from there; the child process,
psutil, package versions and disk usage are simulated. Run: python3 -I tests/test_pilot_seal.py
"""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
FILES = ("ENTREES_GELEES.json", "scripts/gel_common.py", "scripts/gel_models.py", "scripts/gel_data.py",
         "scripts/gel_predictions.py", "scripts/kaggle_gel_run.py")
SYSTEMS = ("T0", "T_star", "TK", "T-niv", "TK-niv", "T-H", "T-Z", "T-D")
BANKS = {"smoke": ("icai_validation_smoke", "rijks_dev_smoke"), "freeze": ("icai_test", "rijks_dev", "rijks_test")}
VERSIONS = {p: "0" for p in ("torch", "torchvision", "transformers", "tokenizers", "timm", "open-clip-torch",
                              "einops", "numpy", "Pillow", "huggingface-hub", "safetensors", "psutil")}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): sha_bytes(p.read_bytes()) for p in sorted(folder.rglob("*")) if p.is_file()}


def write_seal(out, mode, identity="A", files=None):
    # A coherent synthetic seal with the expected family, as gel_predictions.py would publish it.
    out.mkdir(parents=True, exist_ok=True)
    entries = {}
    for bank in BANKS[mode]:
        for system in SYSTEMS if files is None else files:
            name = f"{bank}__{system}.json"
            data = json.dumps({"bank": bank, "system": system, "rows": []}).encode()
            (out / name).write_bytes(data)
            entries[name] = {"bank": bank, "system": system, "sha256": sha_bytes(data)}
    manifest = {"run_identity": identity, "mode": mode, "predictions_frozen": mode == "freeze",
                "technical_pass": True, "files": entries}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True))
    return manifest


class FakeChild:
    def __init__(self, returncode):
        self.pid, self.returncode = 0, returncode

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


class PilotSealTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.input, self.working = base / "kaggle" / "input", base / "kaggle" / "working"
        self.root = self.input / "code"
        for name in FILES:
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(HERE / name, self.root / name)
        manifest = {"files": {n: sha_bytes((self.root / n).read_bytes()) for n in FILES}}
        (self.root / "CODE_SHA256.json").write_text(json.dumps(manifest))
        self.binding = self.input / "binding.json"
        self.binding.write_text("{}")
        self.working.mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("pilot", self.root / "scripts/kaggle_gel_run.py")
        self.pilot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.pilot)
        self.pilot.KAGGLE_INPUT, self.pilot.KAGGLE_WORKING = self.input.resolve(), self.working.resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, mode, out, smoke_reviewed=True):
        approval = {"grok_p2_code_review": "p2", "codex_p4_code_review": "p4", "slot_id": "slot-1",
                    "slot_granted_by": "wA:p1", "grok_p2_smoke_review": "p2s" if smoke_reviewed else "",
                    "codex_p4_smoke_review": "p4s" if smoke_reviewed else ""}
        config = {"mode": mode, "code_root": str(self.root), "binding": str(self.binding),
                  "code_manifest_sha256": sha_bytes((self.root / "CODE_SHA256.json").read_bytes()),
                  "binding_sha256": sha_bytes(self.binding.read_bytes()), "approved_versions": VERSIONS,
                  "approval": approval, "output": str(out)}
        if mode == "freeze":
            smoke = self.input / "smoke_manifest.json"
            smoke.write_text(json.dumps({"mode": "smoke", "predictions_frozen": False, "technical_pass": True,
                                         "run_identity": {"code_manifest_sha256": config["code_manifest_sha256"],
                                                          "versions": VERSIONS,
                                                          "binding_sha256": config["binding_sha256"]}}))
            config.update(smoke_manifest=str(smoke), smoke_manifest_sha256=sha_bytes(smoke.read_bytes()))
        path = self.input / f"config-{mode}.json"
        path.write_text(json.dumps(config))
        return path

    def run_pilot(self, mode, out, child, smoke_reviewed=True):
        """child(out) simulates gel_predictions.py and returns its exit code."""
        config = self.config(mode, out, smoke_reviewed)
        launched = []

        def popen(*a, **k):
            launched.append(True)
            return FakeChild(child(out))

        psutil = types.SimpleNamespace(
            Process=lambda pid: None, NoSuchProcess=Exception,
            virtual_memory=lambda: types.SimpleNamespace(available=1 << 40))
        usage = collections.namedtuple("usage", "total used free")(1 << 40, 0, 1 << 40)
        with mock.patch.dict(sys.modules, {"psutil": psutil}), \
                mock.patch.object(self.pilot.subprocess, "Popen", popen), \
                mock.patch.object(self.pilot.shutil, "disk_usage", lambda p: usage), \
                mock.patch.object(self.pilot.importlib.metadata, "version", lambda p: VERSIONS[p]):
            try:
                self.pilot.main(types.SimpleNamespace(config=str(config), mode=mode))
                ok = True
            except RuntimeError:
                ok = False
        return ok, bool(launched)

    # --- B1: an earlier seal survives every refusal, byte for byte ---

    def test_prior_seal_identity_changed_child_refuses_bytes_kept(self):
        out = self.working / "gel"
        write_seal(out, "freeze")
        before = snapshot(out)
        ok, launched = self.run_pilot("freeze", out, lambda o: 1)  # child: sealed_run_identity_changed
        self.assertTrue(launched)
        self.assertFalse(ok)
        self.assertEqual(snapshot(out), before)

    def test_prior_seal_other_mode_refused_bytes_kept(self):
        out = self.working / "gel"
        write_seal(out, "freeze")
        before = snapshot(out)
        ok, _ = self.run_pilot("smoke", out, lambda o: 1)
        self.assertFalse(ok)
        self.assertEqual(snapshot(out), before)

    def test_prior_seal_same_identity_verification_only(self):
        out = self.working / "gel"
        write_seal(out, "freeze")
        before = snapshot(out)
        ok, _ = self.run_pilot("freeze", out, lambda o: 0)  # child: already sealed, returns after SHA checks
        self.assertTrue(ok)
        self.assertEqual(snapshot(out), before)

    def test_prior_seal_final_control_fails_bytes_kept(self):
        # Refusal in the pilot's final controls (former lines 125-133) must not erase an earlier seal.
        out = self.working / "gel"
        write_seal(out, "freeze")
        (out / "stray.json").write_text("{}")
        before = snapshot(out)
        ok, _ = self.run_pilot("freeze", out, lambda o: 0)
        self.assertFalse(ok)
        self.assertEqual(snapshot(out), before)

    def test_prior_seal_rewritten_by_attempt_is_refused(self):
        out = self.working / "gel"
        write_seal(out, "freeze")

        def child(o):
            m = json.loads((o / "MANIFEST.json").read_text())
            m["technical_pass"] = True
            (o / "MANIFEST.json").write_text(json.dumps(m, indent=1))  # same content, other bytes
            return 0
        ok, _ = self.run_pilot("freeze", out, child)
        self.assertFalse(ok)
        self.assertTrue((out / "MANIFEST.json").exists())

    # --- current attempt: no failed seal is ever accepted ---

    def test_fresh_success_accepted(self):
        out = self.working / "smoke"
        ok, _ = self.run_pilot("smoke", out, lambda o: write_seal(o, "smoke") and 0)
        self.assertTrue(ok)
        self.assertTrue((out / "MANIFEST.json").exists())

    def test_fresh_child_fails_after_publishing_manifest_retracted(self):
        out = self.working / "smoke"
        ok, _ = self.run_pilot("smoke", out, lambda o: write_seal(o, "smoke") and 1)
        self.assertFalse(ok)
        self.assertFalse((out / "MANIFEST.json").exists())

    def test_fresh_incomplete_family_retracted_by_final_controls(self):
        out = self.working / "smoke"
        ok, _ = self.run_pilot("smoke", out, lambda o: write_seal(o, "smoke", files=SYSTEMS[:-1]) and 0)
        self.assertFalse(ok)
        self.assertFalse((out / "MANIFEST.json").exists())

    def test_fresh_corrupted_prediction_retracted(self):
        out = self.working / "smoke"

        def child(o):
            write_seal(o, "smoke")
            (o / "rijks_dev_smoke__T-Z.json").write_text("changed")
            return 0
        ok, _ = self.run_pilot("smoke", out, child)
        self.assertFalse(ok)
        self.assertFalse((out / "MANIFEST.json").exists())

    def test_fresh_child_fails_without_manifest(self):
        out = self.working / "smoke"
        ok, _ = self.run_pilot("smoke", out, lambda o: 1)
        self.assertFalse(ok)
        self.assertFalse((out / "MANIFEST.json").exists())

    # --- unchanged guard: no freeze without a reviewed smoke ---

    def test_freeze_without_smoke_review_refused_before_launch(self):
        out = self.working / "gel"
        ok, launched = self.run_pilot("freeze", out, lambda o: 0, smoke_reviewed=False)
        self.assertFalse(ok)
        self.assertFalse(launched)


if __name__ == "__main__":
    unittest.main(verbosity=2)
