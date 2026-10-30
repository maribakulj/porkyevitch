# Kaggle driver for planche_images.py (porkyevitch, experiences/2026-10-25-banc-rijksmuseum). CPU is enough.
# Inputs: dataset rijks-planche-entree (planche_images.py and planche.json, or planche_repli.json) and the output of kernel
# rijks-filtres-run, which must be its full run (filtres_distances.py at the reviewed sha, RIJKS_SMOKE=0). Stops at the first failure.
import glob, hashlib, json, os, subprocess, sys, time

W = "/kaggle/working"
SCRIPT_SHA256 = "0e13c7214a636a7c0b6d198c433884c14bbd01e6cb589d6a2174af123c11ec17"  # planche_images.py as reviewed
PLANCHE = "planche.json"  # or planche_repli.json, set before the push
PLANCHE_SHA256 = "d7292419c0edd92c5796d4fbea2c8985900f9129707d001f35b8b7c5cb16efcf"  # sha256 of that file, written by composantes_reserve.py
FILTRES_SCRIPT = "e0fb13ff2fa1b4747a4cc02d1a31589761e83f0266a7133c81f7bb5de2beaa25"  # sha256 of filtres_distances.py of the full run


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
pl = glob.glob(f"/kaggle/input/**/{PLANCHE}", recursive=True)
full = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/full/voisins.jsonl", recursive=True)]
if len(pl) != 1 or len(full) != 1:
    fail(f"inputs not found exactly once: {pl} {full}")
pl, full = pl[0], full[0]
script = os.path.join(os.path.dirname(pl), "planche_images.py")
if sha(script) != SCRIPT_SHA256:
    fail(f"script sha256 {sha(script)} is not the reviewed one")
if sha(pl) != PLANCHE_SHA256:
    fail(f"{PLANCHE} sha256 {sha(pl)} is not the expected one")
run = json.load(open(f"{full}/run.json"))
if run.get("script_sha256") != FILTRES_SCRIPT or run.get("smoke") != 0:
    fail("the mounted filter output is not the reviewed full run")
log(f"inputs {pl} {full}")
out = f"{W}/planche"
with open(f"{W}/planche.log", "w") as f:
    r = subprocess.run([sys.executable, script, out, full, pl], env=dict(os.environ, PLANCHE_HF_CACHE="/tmp/planche_hf"),
                       stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"assembler exit {r.returncode}")
if not os.path.exists(f"{out}/index.json"):
    fail("missing output index.json")
log("CHAIN DONE planche ok")
