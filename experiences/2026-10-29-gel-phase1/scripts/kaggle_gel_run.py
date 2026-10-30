"""Kaggle pilot for prediction-only phase-1 seal. Never submits a kernel.

Only a reviewed, explicitly selected smoke or freeze stage can be run. stdout
and stderr of inference are suppressed: never print a frozen ID, URL or truth.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

KAGGLE_INPUT = Path("/kaggle/input")
KAGGLE_WORKING = Path("/kaggle/working")


def require(ok):
    if not ok:
        raise RuntimeError("phase1_pilot_control")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while data := f.read(8 << 20):
            h.update(data)
    return h.hexdigest()


def bound(path):
    p = Path(path).resolve(strict=True)
    require(KAGGLE_INPUT in p.parents)
    return p


def retract(out, prior_seal):
    # A seal that existed before this attempt is never touched, whatever the refusal point.
    # Only a manifest published by this attempt, in a folder that was not sealed, is revoked.
    if prior_seal is None:
        (out / "MANIFEST.json").unlink(missing_ok=True)


def accept(out, mode, prior_seal):
    if prior_seal is not None:
        require(sha(out / "MANIFEST.json") == prior_seal)  # resume = verification only, no rewrite
    final = json.loads((out / "MANIFEST.json").read_text())
    expected_banks = {"icai_validation_smoke", "rijks_dev_smoke"} if mode == "smoke" else {"icai_test", "rijks_dev", "rijks_test"}
    systems = {"T0", "T_star", "TK", "T-niv", "TK-niv", "T-H", "T-Z", "T-D"}
    require(final["mode"] == mode and final["predictions_frozen"] == (mode == "freeze"))
    require({(v["bank"], v["system"]) for v in final["files"].values()} ==
            {(bank, system) for bank in expected_banks for system in systems})
    require({p.name for p in out.iterdir()} == set(final["files"]) | {"MANIFEST.json"})
    for filename, info in final["files"].items():
        require(sha(out / filename) == info["sha256"])


def main(args):
    start = time.monotonic()
    config_path = bound(args.config)
    config = json.loads(config_path.read_text())
    require(config["mode"] == args.mode)
    root = bound(config["code_root"])
    manifest_path = bound(root / "CODE_SHA256.json")
    require(sha(manifest_path) == config["code_manifest_sha256"])
    code = json.loads(manifest_path.read_text())
    expected = {"ENTREES_GELEES.json", "scripts/gel_common.py", "scripts/gel_models.py", "scripts/gel_data.py",
                "scripts/gel_predictions.py", "scripts/kaggle_gel_run.py"}
    require(set(code["files"]) == expected)
    for filename, digest in code["files"].items():
        p = bound(root / filename)
        require(p.is_relative_to(root) and sha(p) == digest)
    require(Path(__file__).resolve() == (root / "scripts/kaggle_gel_run.py").resolve())
    binding = bound(config["binding"])
    require(sha(binding) == config["binding_sha256"])
    packages = {"torch", "torchvision", "transformers", "tokenizers", "timm", "open-clip-torch", "einops",
                "numpy", "Pillow", "huggingface-hub", "safetensors", "psutil"}
    require(set(config["approved_versions"]) == packages)
    require({p: importlib.metadata.version(p) for p in packages} == config["approved_versions"])
    approval = config["approval"]
    for name in ("grok_p2_code_review", "codex_p4_code_review", "slot_id"):
        require(isinstance(approval[name], str) and bool(approval[name]) and "REPLACE" not in approval[name])
    require(approval["slot_granted_by"] == "wA:p1")
    if args.mode == "freeze":
        for name in ("grok_p2_smoke_review", "codex_p4_smoke_review"):
            require(bool(approval[name]) and "REPLACE" not in approval[name])
        smoke_path = bound(config["smoke_manifest"])
        require(sha(smoke_path) == config["smoke_manifest_sha256"])
        smoke = json.loads(smoke_path.read_text())
        require(smoke["mode"] == "smoke" and smoke["predictions_frozen"] is False and smoke["technical_pass"] is True)
        require(smoke["run_identity"]["code_manifest_sha256"] == config["code_manifest_sha256"] and
                smoke["run_identity"]["versions"] == config["approved_versions"] and
                smoke["run_identity"]["binding_sha256"] == config["binding_sha256"])
    out = Path(config["output"]).resolve()
    require(KAGGLE_WORKING in out.parents)
    require(shutil.disk_usage(KAGGLE_WORKING).free >= 6_000_000_000)
    # Ownership of the seal is fixed before launch: an existing seal belongs to an earlier run.
    seal = out / "MANIFEST.json"
    require(not seal.is_symlink())
    prior_seal = sha(seal) if seal.exists() else None
    workspace = out / ".work"
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="0", PYTHONHASHSEED="0", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4",
               PHASE1_REVIEWED_MODE=args.mode, PHASE1_CODE_SHA256=config["code_manifest_sha256"],
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
               TOKENIZERS_PARALLELISM="false", HF_HOME=str(workspace / "hf-home"),
               HF_MODULES_CACHE=str(workspace / "hf-modules"))
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "KAGGLE_KEY"):
        env.pop(name, None)
    command = [sys.executable, "-u", str(root / "scripts/gel_predictions.py"), "--mode", args.mode,
               "--binding", str(binding), "--inventory", str(root / "ENTREES_GELEES.json"),
               "--versions", str(config_path), "--out", str(out)]
    limit = 3600 if args.mode == "smoke" else 4 * 3600
    import psutil
    child = subprocess.Popen(command, cwd=str(root / "scripts"), env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failed = False
    try:
        while child.poll() is None:
            if time.monotonic() - start >= limit:
                failed = True
                break
            try:
                process = psutil.Process(child.pid)
                processes = [process] + process.children(recursive=True)
                rss = sum(p.memory_info().rss for p in processes if p.is_running())
                if rss >= 15 * (1 << 30) or psutil.virtual_memory().available <= 512 * (1 << 20):
                    failed = True
                    break
            except psutil.NoSuchProcess:
                if child.poll() is not None:
                    break
            if out.exists():
                size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
                if size > 5_000_000_000 or shutil.disk_usage(out).free < 256 * (1 << 20):
                    failed = True
                    break
            time.sleep(2)
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=10)
    try:
        require(not failed and child.returncode == 0 and time.monotonic() - start <= limit)
        accept(out, args.mode, prior_seal)
    except Exception:
        retract(out, prior_seal)  # never accept a failed pilot's seal, never erase an earlier one
        raise
    print("PHASE1_TECHNICAL_SMOKE_COMPLETE" if args.mode == "smoke" else "PHASE1_PREDICTIONS_FROZEN_NO_MEASURES")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", choices=("smoke", "freeze"), required=True)
    try:
        main(parser.parse_args())
    except Exception:
        print("PHASE1_PILOT_FAILED", file=sys.stderr)
        sys.exit(1)
