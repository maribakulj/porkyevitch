# Kaggle driver for tirage_300.py (porkyevitch-maths, experiences/2026-10-30-tirage-300). CPU is enough.
# Inputs: a dataset holding tirage_300.py and the pilot tirage.json, and the output of kernel caypollard-encode-cradio v3.
# STAGE is "plan" for the blank (no image read); the only change allowed for the full run is STAGE = "full".
import glob, hashlib, os, subprocess, sys, time

STAGE = "plan"
W = "/kaggle/working"
SCRIPT_SHA256 = "d1fd87c19ae6637c8952e4d1aba59e94f7a1e71b2b901985c16cdaf97ea9d74c"  # tirage_300.py as reviewed
PILOT_SHA256 = "6f618135db479c6842b36fc6fb7a4b20ee7543e8bcc6b11d77847c3d04836749"  # graphes-gemini tirage/tirage.json


def log(m):
    with open(f"{W}/chain.log", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")
    print(m, flush=True)


def fail(m):
    log(f"FAILED: {m}")
    sys.exit(1)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


open(f"{W}/chain.log", "w").close()
script = glob.glob("/kaggle/input/**/tirage_300.py", recursive=True)
pilot = [p for p in glob.glob("/kaggle/input/**/tirage.json", recursive=True) if sha(p) == PILOT_SHA256]
enc = [os.path.dirname(os.path.dirname(p)) for p in glob.glob("/kaggle/input/**/full/feats/train-00000-of-00011.npz", recursive=True)]
if STAGE not in ("plan", "full") or len(script) != 1 or len(pilot) != 1 or len(enc) != 1:
    fail(f"inputs not found exactly once: {STAGE} {script} {pilot} {enc}")
if sha(script[0]) != SCRIPT_SHA256:
    fail("script sha256 is not the reviewed one")
log(f"stage {STAGE} inputs {script[0]} {pilot[0]} {enc[0]}")
with open(f"{W}/tirage.log", "w") as f:
    r = subprocess.run([sys.executable, "-I", script[0], "--stage", STAGE, enc[0], pilot[0], f"{W}/tranche300"],
                       stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"tirage exit {r.returncode}")
log(f"CHAIN DONE tirage {STAGE} ok")
