# Kaggle driver for tirage_pilote.py (porkyevitch, experiences/2026-10-29-graphes-gemini). CPU is enough.
# Inputs: dataset porky-graphes-entree (tirage_pilote.py) and the output of kernel caypollard-encode-cradio v3 (full run).
import glob, hashlib, os, subprocess, sys, time

W = "/kaggle/working"
SCRIPT_SHA256 = "42e6efc46daabdc22acbc919d624ef802e390815cc721abab73ea0dba1c540b5"  # tirage_pilote.py as reviewed


def log(m):
    with open(f"{W}/chain.log", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")
    print(m, flush=True)


def fail(m):
    log(f"FAILED: {m}")
    sys.exit(1)


open(f"{W}/chain.log", "w").close()
script = glob.glob("/kaggle/input/**/tirage_pilote.py", recursive=True)
enc = [os.path.dirname(os.path.dirname(p)) for p in glob.glob("/kaggle/input/**/full/feats/train-00000-of-00011.npz", recursive=True)]
if len(script) != 1 or len(enc) != 1:
    fail(f"inputs not found exactly once: {script} {enc}")
if hashlib.sha256(open(script[0], "rb").read()).hexdigest() != SCRIPT_SHA256:
    fail("script sha256 is not the reviewed one")
log(f"inputs {script[0]} {enc[0]}")
with open(f"{W}/tirage.log", "w") as f:
    r = subprocess.run([sys.executable, script[0], enc[0], f"{W}/pilote"], stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"tirage exit {r.returncode}")
log("CHAIN DONE tirage ok")
