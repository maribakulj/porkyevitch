# Kaggle CPU driver for a1_run.py (porkyevitch-maths, experiences/2026-10-29-a1). One thread, no network needed.
# Inputs: a dataset with scripts/ and ENCODAGE_TRAIN_V3.json (P9-A, pinned sha), the full output of
# caypollard-encode-cradio v3, and the output of kernel mabaku/porky-diag-run v3 mounted as kernel_source.
# STAGE = "blanc" first; "reglage" needs the reviewed blanc.json (and its sha below); "diagnostic" needs the reglage
# output and the plate receipt. Changing STAGE and BLANK_SHA256 is the only edit allowed between runs.
import glob, hashlib, os, subprocess, sys, time

STAGE = "blanc"
BLANK_SHA256 = None  # sha of the reviewed blanc.json, set by a reviewed commit before "reglage"
W = "/kaggle/working"
SCRIPTS = {"a1_run.py": "78b1ed982ae9b2e59624a30b83675703e156b92a1d45309b6089162c9dcee597", "a1_core.py": "177ef54243fd6dfed0aa557561aa365f41b2c992379aef6d4fab4c5e27ab205a"}
DIAG = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
INVENTORY = "ff424e6453192f6465e23e3cdf9acf29aa5827d84565deb329de4c1b891a65d9"


def log(m):
    with open(f"{W}/chain.log", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")
    print(m, flush=True)


def fail(m):
    log(f"FAILED: {m}")
    sys.exit(1)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def find(pattern, digest=None):
    return [p for p in glob.glob(f"/kaggle/input/**/{pattern}", recursive=True) if digest is None or sha(p) == digest]


open(f"{W}/chain.log", "w").close()
script = find("a1_run.py")
inventory = find("ENCODAGE_TRAIN_V3.json", INVENTORY)
diag = [os.path.dirname(p) for p in find("diagnostic.json", DIAG)]
enc = [os.path.dirname(os.path.dirname(p)) for p in find("full/grid/train-00000-of-00011.json")]
if STAGE not in ("blanc", "reglage", "diagnostic") or not all(len(x) == 1 for x in (script, inventory, diag, enc)):
    fail(f"inputs not found exactly once: {STAGE} {script} {inventory} {diag} {enc}")
root = os.path.dirname(script[0])
for name, want in SCRIPTS.items():
    if sha(os.path.join(root, name)) != want:
        fail(f"{name}: sha256 is not the reviewed one")
cmd = [sys.executable, "-I", script[0], "--stage", STAGE, "--encoder", enc[0], "--inventory", inventory[0],
       "--diag", diag[0], "--out", f"{W}/a1-{STAGE}"]
if STAGE in ("reglage", "diagnostic"):
    blank = find("blanc.json", BLANK_SHA256)
    if BLANK_SHA256 is None or len(blank) != 1:
        fail("reviewed blanc.json not found")
    cmd += ["--blank", blank[0], "--blank-sha256", BLANK_SHA256]
if STAGE == "diagnostic":
    reg = [os.path.dirname(p) for p in find("MANIFEST_REGLAGE.json")]
    receipt = find("recu_planche_a1.json")
    if len(reg) != 1 or len(receipt) != 1:
        fail(f"diagnostic needs the reglage output and the receipt exactly once: {reg} {receipt}")
    cmd += ["--reglage", reg[0], "--receipt", receipt[0]]
env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="0")
import numpy  # noqa: E402
log(f"stage {STAGE} python {sys.version.split()[0]} numpy {numpy.__version__}")
with open(f"{W}/a1.log", "w") as f:
    r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env)
if r.returncode != 0:
    fail(f"a1 exit {r.returncode}")
log(f"CHAIN DONE a1 {STAGE} ok")
