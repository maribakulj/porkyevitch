# Remote end-to-end check of lermolieff (image -> codes), both variants, installed in this fresh Kaggle environment.
# Compares the codes for the first 32 ICAI test images with the published predictions (resultats/icai788_<variant>_predictions.json).
# Rule fixed before the run: a variant passes if predict exits 0 and at least 30 of the 32 images get exactly the published codes;
# the script exits non-zero unless both variants pass.
import glob, json, os, shutil, subprocess, sys, time

W = "/kaggle/working"
src = glob.glob("/kaggle/input/**/lermolieff-smoke", recursive=True)[0]
shutil.copytree(f"{src}/lermolieff", "/tmp/lermolieff", dirs_exist_ok=True)
r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "/tmp/lermolieff[c-radio,pe-spatial,train]"])
assert r.returncode == 0
freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
keep = [l for l in freeze.splitlines() if l.split("==")[0].lower() in
        ("torch", "torchvision", "transformers", "timm", "open-clip-torch", "open_clip_torch", "einops", "numpy", "pillow",
         "huggingface-hub", "huggingface_hub", "pyarrow", "safetensors", "lermolieff")]
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

t = pq.read_table(hf_hub_download("davanstrien/iconclass-vlm-brillfull", "data/test-00000-of-00001.parquet",
                                  repo_type="dataset", revision="8045366ff092a06e8e1c4e47f1eb43cb2a54d732"))
imgs = t.column("image").to_pylist()[:32]
files = []
for i, x in enumerate(imgs):
    files.append(f"/tmp/icai_{i:03d}.jpg")
    open(files[-1], "wb").write(x["bytes"])
report = {"python": sys.version.split()[0], "versions": keep, "gpu": None}
import torch

report["gpu"] = torch.cuda.get_device_name() if torch.cuda.is_available() else None
for v in ("c-radio", "pe-spatial"):
    t0 = time.time()
    out = subprocess.run([sys.executable, "-m", "lermolieff.predict", "--head", f"{src}/head-{v}.pt", *files],
                         capture_output=True, text=True, cwd="/tmp")
    got = [json.loads(l)["codes"] for l in out.stdout.splitlines() if l.startswith("{")]
    pub = json.load(open(f"{src}/lermolieff/resultats/icai788_{v}_predictions.json"))["T_head"][:32]
    same = sum(sorted(a) == sorted(b) for a, b in zip(got, pub))
    report[v] = {"returncode": out.returncode, "images": len(got), "identical": same,
                 "passed": out.returncode == 0 and len(got) == 32 and same >= 30,
                 "seconds": round(time.time() - t0, 1), "stderr_tail": out.stderr[-1500:]}
json.dump(report, open(f"{W}/smoke_lermolieff.json", "w"), indent=1)
print(json.dumps(report, indent=1))
if not all(report[v]["passed"] for v in ("c-radio", "pe-spatial")):
    sys.exit(1)
