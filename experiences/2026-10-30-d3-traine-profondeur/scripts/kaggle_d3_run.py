# Kaggle T4 driver for d3_run.py (porkyevitch-maths, experiences/2026-10-30-d3-traine-profondeur). No network needed.
# Inputs: a dataset with scripts/ and ENCODAGE_TRAIN_V3.json (P9-A, pinned sha), the full output of
# caypollard-encode-cradio v3, and the output of kernel mabaku/porky-diag-run v3 mounted as kernel_source.
# STAGE = "blanc" first; "complet" needs the reviewed blanc.json, whose sha is set here by a reviewed commit.
import glob, hashlib, os, subprocess, sys, time

STAGE = "blanc"
BLANK_SHA256 = None
W = "/kaggle/working"
SCRIPTS = {"d3_run.py": "050d00309ea7f05141b30e80bf3212c15faa35a928d7aec8f205b1d1256d51b9", "d3_core.py": "10805ec7cce6495529d2fa3ca1a83c47c3417c96e5f2c1883b2649a1bfeb236a"}
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
script = find("d3_run.py")
inventory = find("ENCODAGE_TRAIN_V3.json", INVENTORY)
diag = [os.path.dirname(p) for p in find("diagnostic.json", DIAG)]
enc = [os.path.dirname(os.path.dirname(p)) for p in find("full/grid/train-00000-of-00011.json")]
if STAGE not in ("blanc", "complet") or not all(len(x) == 1 for x in (script, inventory, diag, enc)):
    fail(f"inputs not found exactly once: {STAGE} {script} {inventory} {diag} {enc}")
root = os.path.dirname(script[0])
for name, want in SCRIPTS.items():
    if sha(os.path.join(root, name)) != want:
        fail(f"{name}: sha256 is not the reviewed one")
cmd = [sys.executable, "-I", script[0], "--stage", STAGE, "--encoder", enc[0], "--inventory", inventory[0],
       "--diag", diag[0], "--out", f"{W}/d3-{STAGE}"]
if STAGE == "complet":
    blank = find("blanc.json", BLANK_SHA256)
    if BLANK_SHA256 is None or len(blank) != 1:
        fail("reviewed blanc.json not found")
    cmd += ["--blank", blank[0], "--blank-sha256", BLANK_SHA256]
import numpy  # noqa: E402
log(f"stage {STAGE} python {sys.version.split()[0]} numpy {numpy.__version__}")
with open(f"{W}/d3.log", "w") as f:
    r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONHASHSEED="0"))
if r.returncode != 0:
    fail(f"d3 exit {r.returncode}")
log(f"CHAIN DONE d3 {STAGE} ok")
