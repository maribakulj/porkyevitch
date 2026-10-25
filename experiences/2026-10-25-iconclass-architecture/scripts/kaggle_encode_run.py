# Kaggle driver for encode_cradio.py (porkyevitch, experiences/2026-10-25-iconclass-architecture).
# MODE is "smoke" (ENC_SMOKE=64, technical only) or "full" (ENC_SMOKE=0), set before each push; no automatic chaining to the full run.
# Stops at the first failure and exits non-zero, so that Kaggle marks the run as failed.
import glob, hashlib, os, subprocess, sys, time

MODE = "smoke"
assert MODE in ("smoke", "full"), MODE
W = "/kaggle/working"
SCRIPT_SHA256 = "c3f12bb71deda0b96bf3b8d015d9a79f4db666c234ad8edb0ff04633bd2bf1ca"  # sha256 of encode_cradio.py as reviewed


def log(m):
    with open(f"{W}/chain.log", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")
    print(m, flush=True)


def fail(m):
    log(f"FAILED: {m}")
    sys.exit(1)


open(f"{W}/chain.log", "w").close()
pe = glob.glob("/kaggle/input/**/caypollard-iconclass-pe", recursive=True)
t0 = glob.glob("/kaggle/input/**/caypollard-iconclass-t0", recursive=True)
if len(pe) != 1 or len(t0) != 1:
    fail(f"inputs not found exactly once: {pe} {t0}")
pe, t0 = pe[0], t0[0]
script = f"{t0}/scripts/encode_cradio.py"
got = hashlib.sha256(open(script, "rb").read()).hexdigest()
if got != SCRIPT_SHA256:
    fail(f"script sha256 {got} is not the reviewed one")
log(f"inputs {pe} {sorted(os.listdir(pe))} {t0} {sorted(os.listdir(t0))}")
ext = "/tmp/ext"
os.makedirs(ext, exist_ok=True)
for name, src in (("candidates.jsonl", f"{pe}/candidates.jsonl"), ("near256.json", f"{pe}/near256.json"),
                  ("images", f"{pe}/ext_images/images"), ("gel2", f"{t0}/gel2")):
    if not os.path.exists(src):
        fail(f"missing {src}")
    if not os.path.exists(f"{ext}/{name}"):
        os.symlink(src, f"{ext}/{name}")
r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "open-clip-torch", "einops"])
if r.returncode != 0:
    fail(f"pip exit {r.returncode}")
freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
open(f"{W}/pip_freeze.txt", "w").write(freeze.stdout)
env = dict(os.environ, ENC_SMOKE="64" if MODE == "smoke" else "0", ENC_HF_CACHE="/tmp/enc_hf")
out = f"{W}/{MODE}"
with open(f"{W}/{MODE}.log", "w") as f:
    r = subprocess.run([sys.executable, script, out, ext, t0], env=env, stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"encoder exit {r.returncode} ({MODE})")
for need in ("run.json", "budget.json", "controle.json", "emb.json"):
    if not os.path.exists(f"{out}/{need}"):
        fail(f"missing output {need}")
log(f"CHAIN DONE {MODE} ok")
