# Kaggle driver for encode_cradio.py (porkyevitch, experiences/2026-10-25-iconclass-architecture). MODE: smoke or full.
import glob, os, subprocess, sys, time

MODE = "smoke"
W = "/kaggle/working"


def log(m):
    with open(f"{W}/chain.log", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")
    print(m, flush=True)


open(f"{W}/chain.log", "w").close()
pe = glob.glob("/kaggle/input/**/caypollard-iconclass-pe", recursive=True)[0]
t0 = glob.glob("/kaggle/input/**/caypollard-iconclass-t0", recursive=True)[0]
log(f"inputs {pe} {sorted(os.listdir(pe))} {t0} {sorted(os.listdir(t0))}")
ext = "/tmp/ext"
os.makedirs(ext, exist_ok=True)
for name, src in (("candidates.jsonl", f"{pe}/candidates.jsonl"), ("near256.json", f"{pe}/near256.json"),
                  ("images", f"{pe}/ext_images/images"), ("gel2", f"{t0}/gel2")):
    if not os.path.exists(f"{ext}/{name}"):
        os.symlink(src, f"{ext}/{name}")
r = subprocess.run("pip install -q open-clip-torch einops && pip freeze | grep -i -E "
                   "'^(torch|transformers|timm|open.clip|einops|numpy|pyarrow|huggingface)' > /kaggle/working/versions.txt",
                   shell=True)
log(f"pip exit {r.returncode}")
env = dict(os.environ, HF_HOME="/tmp/hf", **({"ENC_SMOKE": "64"} if MODE == "smoke" else {}))
out = f"{W}/{MODE}"
r = subprocess.run([sys.executable, f"{t0}/scripts/encode_cradio.py", out, ext, t0], env=env,
                   stdout=open(f"{W}/{MODE}.log", "w"), stderr=subprocess.STDOUT)
log(f"exit {r.returncode} ({MODE})")
log("CHAIN DONE")
