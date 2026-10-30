"""One CPU-only remote stage, independent of the already reviewed P9-A pilot."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(8 << 20):
            h.update(b)
    return h.hexdigest()


def require(ok):
    if not ok:
        raise RuntimeError("image_cache_pilot_binding")


def bound(path):
    p = Path(path).resolve(strict=True)
    require(Path("/kaggle/input") in p.parents)
    return p


def main(args):
    cfg_path = bound(args.config)
    cfg = json.loads(cfg_path.read_text())
    root = bound(cfg["experiment_root"])
    helper = root / "images_initiales"
    manifest = bound(helper / "CODE_SHA256.json")
    require(sha(manifest) == cfg["helper_manifest_sha256"])
    code = json.loads(manifest.read_text())
    require(set(code["files"]) == {"p9a_image_cache.py", "kaggle_p9a_images_run.py"})
    for name, expected in code["files"].items():
        require(sha(bound(helper / name)) == expected)
    require(Path(__file__).resolve() == (helper / "kaggle_p9a_images_run.py").resolve())
    require(sha(bound(root / "CODE_SHA256.json")) == code["parent_manifest_sha256"])
    parent = json.loads((root / "CODE_SHA256.json").read_text())
    for relative in ("scripts/p9a_common.py", "ENCODAGE_TRAIN_V3.json", "PREINSCRIPTION.md"):
        require(sha(bound(root / relative)) == parent["files"][relative])
    binding = bound(cfg["binding"])
    require(sha(binding) == cfg["binding_sha256"])
    require(set(cfg["approved_versions"]) == {"numpy", "huggingface-hub", "pyarrow", "psutil"})
    require({p: importlib.metadata.version(p) for p in cfg["approved_versions"]} == cfg["approved_versions"])
    for key in ("grok_p2_report", "codex_p4_report", "remote_slot"):
        require(bool(cfg["approval"][key]) and "REPLACE" not in cfg["approval"][key])
    out = Path(cfg["output"]).resolve()
    require(Path("/kaggle/working") in out.parents and not out.exists())
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", P9A_REVIEWED_STAGE="image_cache",
               P9A_CONFIG_SHA256=sha(cfg_path), HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    # This stage intentionally needs anonymous HF dataset downloads, no credential.
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        env.pop(key, None)
    cmd = [sys.executable, "-u", str(helper / "p9a_image_cache.py"), "--binding", str(binding),
           "--inventory", str(root / "ENCODAGE_TRAIN_V3.json"), "--out", str(out)]
    child = subprocess.Popen(cmd, env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        status = child.wait(timeout=3600)
    except BaseException:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=10)
        raise
    require(status == 0)
    result = json.loads((out / "manifest.json").read_text())
    require(result["technical_only"] is True and result["no_model_or_scores"] is True and len(result["rows"]) == 12)
    for row in result["rows"]:
        path = out / row["file"]
        require(path.name == row["md5"] + ".image" and sha(path) == row["sha256"])
    print("P9A_INITIAL_IMAGE_CACHE_READY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    try:
        main(parser.parse_args())
    except Exception:
        print("P9A_IMAGE_CACHE_PILOT_FAILED", file=sys.stderr)
        sys.exit(1)
