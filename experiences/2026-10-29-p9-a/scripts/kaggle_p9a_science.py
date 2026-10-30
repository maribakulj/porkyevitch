"""Explicit, offline Kaggle pilot of the P9-A scientific series: DEVIS, SEED, PLANCHES or MESURES; never submits a kernel.

Separate from kaggle_p9a_run.py (prepare/smoke, unchanged). The orchestrator fills a reviewed config per stage after
Grok p2 / Codex p4 approval and assigns the slot. No stage starts the next one. Seeds 1 and 2 need their own approval.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kaggle_p9a_run import bound, dump, require, sha  # noqa: E402  (reviewed helpers)

STAGES = {"devis": ("gpu", 3600), "seed": ("gpu", None), "planches": ("cpu", 3600), "mesures": ("cpu", 7200)}
ALLOWLIST = {"PREINSCRIPTION.md", "ENCODAGE_TRAIN_V3.json", "scripts/p9a_common.py", "scripts/p9a_inputs.py",
             "scripts/p9a_heads.py", "scripts/p9a_prepare.py", "scripts/p9a_smoke.py", "scripts/p9a_science.py",
             "scripts/p9a_run.py", "scripts/kaggle_p9a_science.py", "scripts/kaggle_p9a_run.py",
             "images_initiales/p9a_image_cache.py"}
PACKAGES = {"torch", "numpy", "scipy", "pyarrow", "huggingface-hub", "transformers", "tokenizers", "safetensors",
            "Pillow", "psutil"}


def run(args):
    import psutil
    start = time.monotonic()
    config_path = bound(args.config)
    config = json.loads(config_path.read_text())
    require(config["stage"] == args.stage and args.stage in STAGES, "explicit stage mismatch")
    approval = config["approval"]
    for name in ("grok_p2_report", "codex_p4_report", "slot_id"):
        require(isinstance(approval[name], str) and approval[name] and "REPLACE" not in approval[name],
                f"missing reviewed execution binding: {name}")
    require(approval["slot_granted_by"] == "wA:p1", "slot must be assigned by wA:p1")
    seed = int(config["seed"])
    require(seed in (0, 1, 2) and (seed == 0 or approval.get("seeds_1_2_decision")), "seeds 1/2 need their decision")
    root = bound(config["experiment_root"])
    manifest_path = bound(root / "CODE_SHA256_SCIENCE.json")
    require(sha(manifest_path) == config["source_manifest_sha256"], "reviewed code manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text())
    require(set(manifest["files"]) == ALLOWLIST, "unexpected code manifest allowlist")
    for relative, expected in manifest["files"].items():
        p = bound(root / relative)
        require(p.is_relative_to(root) and sha(p) == expected, f"reviewed source changed: {relative}")
    require(Path(__file__).resolve() == (root / "scripts/kaggle_p9a_science.py").resolve(), "pilot path mismatch")
    binding = bound(config["binding"])
    require(sha(binding) == config["binding_sha256"], "bound inputs manifest SHA mismatch")
    require(set(config["approved_versions"]) == PACKAGES, "freeze all required package versions before review")
    versions = {p: importlib.metadata.version(p) for p in PACKAGES}
    require(versions == config["approved_versions"], "environment differs from audited versions")
    device, limit = STAGES[args.stage]
    if limit is None:
        limit = int(config["wall_limit_seconds"])
        require(0 < limit <= 43000, "seed wall limit must be explicit and within one Kaggle session")
    out = Path(config["output"]).resolve()
    require(Path("/kaggle/working") in out.parents, "output outside /kaggle/working")
    require(shutil.disk_usage("/kaggle/working").free >= 6_000_000_000, "less than 6 GB free")
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, CUBLAS_WORKSPACE_CONFIG=":4096:8", PYTHONHASHSEED="0", HF_HUB_DISABLE_TELEMETRY="1",
               TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="4", MKL_NUM_THREADS="4",
               P9A_REVIEWED_STAGE=args.stage, P9A_CONFIG_SHA256=sha(config_path))
    if device == "gpu":
        env["CUDA_VISIBLE_DEVICES"] = "0"
    else:
        env["CUDA_VISIBLE_DEVICES"] = ""
    if args.stage != "planches":  # only the plates read original pixels from the pinned Brillfull revision
        env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "KAGGLE_KEY"):
        env.pop(name, None)
    command = [sys.executable, "-u", str(root / "scripts" / "p9a_run.py"), "--stage", args.stage,
               "--binding", str(binding), "--inventory", str(root / "ENCODAGE_TRAIN_V3.json"),
               "--out", str(out / args.stage), "--seed", str(seed)]
    if args.stage in ("devis", "seed"):
        command += ["--prepared", str(bound(config["prepared"])), "--preparation-sha256", config["preparation_sha256"],
                    "--viewing-receipt", str(bound(config["viewing_receipt"])), "--blank", str(bound(config["blank"]))]
    if args.stage == "seed":
        command += ["--devis", str(bound(config["devis"])), "--devis-sha256", config["devis_sha256"],
                    "--wall-seconds", str(limit - 300)]
        if config.get("resume"):
            command += ["--resume", str(bound(config["resume"]))]
    if args.stage in ("planches", "mesures"):
        command += ["--gel", str(bound(config["gel"])), "--gel-sha256", config["gel_sha256"]]
    if args.stage == "mesures":
        command += ["--planches", str(bound(config["planches"])), "--receipt", str(bound(config["plates_receipt"]))]
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True,
                            timeout=30, env=env)
    (out / "pip_freeze.txt").write_text(freeze.stdout)
    record = {"stage": args.stage, "seed": seed, "config_sha256": sha(config_path),
              "source_manifest_sha256": sha(manifest_path), "versions": versions, "python": sys.version.split()[0],
              "approval": approval, "wall_limit_seconds": limit, "status": "running", "no_automatic_continuation": True}
    dump(out / "driver.json", record)
    samples, failure = [], None
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
                if not samples or elapsed - samples[-1]["elapsed_s"] >= 60:
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
                time.sleep(5)
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
    elapsed = time.monotonic() - start
    record.update({"exit_code": child.returncode, "elapsed_s": elapsed, "failure": failure,
                   "status": "passed" if child.returncode == 0 and failure is None and elapsed <= limit else "failed",
                   "monitor_samples": samples})
    dump(out / "driver.json", record)
    require(record["status"] == "passed", "stage failed; inspect driver.json and execution.log")
    print(f"P9-A {args.stage}: stage complete; STOP, review outputs before any further stage.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--stage", choices=tuple(STAGES), required=True)
    run(parser.parse_args())
