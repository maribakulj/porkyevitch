"""Explicit, offline Kaggle pilot. PREPARE or SMOKE only; never submits a kernel.

The orchestrator fills the reviewed config in a separate input dataset after
Grok p2 / Codex p4 approval and assigns a GPU slot. No defaults start a run.
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


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while part := f.read(8 << 20):
            h.update(part)
    return h.hexdigest()


def bound(path):
    p = Path(path).resolve(strict=True)
    require(Path("/kaggle/input") in p.parents, f"input outside Kaggle mount: {p}")
    require(not any(x.lower().startswith(("test-", "emb")) or "rijksmuseum" in x.lower()
                    or x.lower() == "lermolieff" for x in p.parts), "forbidden binding path")
    return p


def dump(path, value):
    tmp = path.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def run(args):
    start = time.monotonic()
    config_path = bound(args.config)
    config = json.loads(config_path.read_text())
    require(config["stage"] == args.stage and args.stage in ("prepare", "smoke"), "explicit stage mismatch")
    approval = config["approval"]
    for name in ("grok_p2_report", "codex_p4_report", "slot_id"):
        require(isinstance(approval[name], str) and bool(approval[name]) and "REPLACE" not in approval[name],
                f"missing reviewed execution binding: {name}")
    require(approval["slot_granted_by"] == "wA:p1", "slot must be assigned by wA:p1")
    root = bound(config["experiment_root"])
    manifest_path = bound(root / "CODE_SHA256.json")
    require(sha(manifest_path) == config["source_manifest_sha256"], "reviewed code manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text())
    exact = {"PREINSCRIPTION.md", "ENCODAGE_TRAIN_V3.json", "scripts/p9a_common.py", "scripts/p9a_inputs.py",
             "scripts/p9a_heads.py", "scripts/p9a_prepare.py", "scripts/p9a_smoke.py", "scripts/kaggle_p9a_run.py"}
    require(set(manifest["files"]) == exact, "unexpected code manifest allowlist")
    for relative, expected in manifest["files"].items():
        p = bound(root / relative)
        require(p.is_relative_to(root) and sha(p) == expected, f"reviewed source changed: {relative}")
    require(Path(__file__).resolve() == (root / "scripts/kaggle_p9a_run.py").resolve(), "pilot path mismatch")
    binding = bound(config["binding"])
    require(sha(binding) == config["binding_sha256"], "bound inputs manifest SHA mismatch")
    packages = {"torch", "numpy", "transformers", "tokenizers", "huggingface-hub", "safetensors", "Pillow", "psutil"}
    require(set(config["approved_versions"]) == packages, "freeze all required package versions before review")
    versions = {p: importlib.metadata.version(p) for p in packages}
    require(versions == config["approved_versions"], "environment differs from audited versions")
    import psutil
    device = config["prepare_device"]
    require(device in ("cpu", "cuda"), "explicit prepare device required")
    limit = 1800 if args.stage == "prepare" and device == "cuda" else 3600
    out = Path(config["output"]).resolve()
    require(Path("/kaggle/working") in out.parents, "output outside /kaggle/working")
    require(shutil.disk_usage("/kaggle/working").free >= 6_000_000_000, "less than 6 GB free")
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="0", CUBLAS_WORKSPACE_CONFIG=":4096:8",
               PYTHONHASHSEED="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
               TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4",
               P9A_REVIEWED_STAGE=args.stage, P9A_CONFIG_SHA256=sha(config_path))
    # No credentials are needed; explicitly remove inherited tokens from this child.
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "KAGGLE_KEY"):
        env.pop(name, None)
    script = root / "scripts" / ("p9a_prepare.py" if args.stage == "prepare" else "p9a_smoke.py")
    command = [sys.executable, "-u", str(script), "--binding", str(binding),
               "--inventory", str(root / "ENCODAGE_TRAIN_V3.json"), "--out", str(out / args.stage)]
    if args.stage == "prepare":
        command += ["--device", device]
    else:
        command += ["--prepared", str(bound(config["prepared"])),
                    "--preparation-sha256", config["preparation_sha256"],
                    "--viewing-receipt", str(bound(config["viewing_receipt"]))]
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True,
                            timeout=30, env=env)
    (out / "pip_freeze.txt").write_text(freeze.stdout)
    record = {"stage": args.stage, "technical_only": True, "config_sha256": sha(config_path),
              "source_manifest_sha256": sha(manifest_path), "versions": versions, "approval": approval,
              "wall_limit_seconds": limit, "status": "running", "no_automatic_continuation": True}
    dump(out / "driver.json", record)
    samples = []
    failure = None
    with open(out / "execution.log", "w") as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env,
                                 cwd=str(root / "scripts"), start_new_session=True)
        try:
            while child.poll() is None:
                elapsed = time.monotonic() - start
                try:
                    processes = [psutil.Process(child.pid)]
                    processes += processes[0].children(recursive=True)
                    rss = sum(p.memory_info().rss for p in processes if p.is_running())
                except psutil.NoSuchProcess:
                    if child.poll() is not None:
                        break
                    continue
                size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
                samples.append({"elapsed_s": elapsed, "aggregate_rss_bytes": rss, "output_bytes": size})
                if elapsed > limit:
                    failure = "hard wall deadline exceeded"
                elif rss > 15 * (1 << 30) or psutil.virtual_memory().available < 512 * (1 << 20):
                    failure = "RAM ceiling exceeded"
                elif size > 5_000_000_000:
                    failure = "durable output ceiling exceeded"
                elif shutil.disk_usage(out).free < 256 * (1 << 20):
                    failure = "disk exhausted"
                if failure:
                    break
                time.sleep(2)
        except BaseException:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=10)
            raise
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
    elapsed = time.monotonic() - start
    record.update({"exit_code": child.returncode, "elapsed_s": elapsed, "failure": failure,
                   "status": "passed" if child.returncode == 0 and failure is None and elapsed <= limit else "failed",
                   "monitor_samples": samples})
    dump(out / "driver.json", record)
    require(record["status"] == "passed", "preparation/smoke failed; inspect driver.json and execution.log")
    expected = "preparation.json" if args.stage == "prepare" else "blanc.json"
    result = json.loads((out / args.stage / expected).read_text())
    require(result["technical_only"] is True, "unexpected scientific output")
    if args.stage == "smoke":
        require(result["passed"] is True and result["scientific_verdict"] is None, "smoke controls did not pass")
    print(f"P9-A {args.stage}: technical stage complete; STOP, review outputs before any further stage.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--stage", choices=("prepare", "smoke"), required=True)
    run(parser.parse_args())
