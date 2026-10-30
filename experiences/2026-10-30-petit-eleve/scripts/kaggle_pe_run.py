# Kaggle T4 driver for pe_kaggle.py (porkyevitch-maths, experiences/2026-10-30-petit-eleve). Internet on (model weights).
# Inputs: dataset with scripts/, listes.json, noms.json, images/, graphes/, s1b/ (no closed set), and the full output of
# kernel caypollard-encode-cradio v3. STAGE = "smoke" for the blank; the full run needs a reviewed commit that pins the
# OWLv2 / Florence-2 revisions in pe_kaggle.py (so its sha changes) and sets STAGE = "full".
# Amendment (30/10, wA:p1): the current Kaggle image lacks open_clip, which the C-RADIO remote code imports; the pilot
# installs the pinned open_clip_torch before the subprocess and logs its version (torch must stay unchanged).
# Amendment (30/10, before the full run): ultralytics pinned for YOLOE-v8-S, installed and checked the same way; stage
# "mesures" (CPU) runs only on the sealed predictions of the full run (MANIFEST_PREDICTIONS.json) with the plate receipt
# (recu_planche_pe.json), each found exactly once under /kaggle/input, and installs nothing.
import glob, hashlib, importlib.metadata, os, subprocess, sys, time

STAGE = "smoke"
OPEN_CLIP = "open_clip_torch==3.3.0"
ULTRALYTICS = "ultralytics==8.4.177"  # YOLOE-v8-S witness (D8), smoke and full only
W = "/kaggle/working"
SCRIPT_SHA256 = {"pe_kaggle.py": "e494a49db9b3fdba5ac0e7f3b1f4e9140e1c769d965da5c9618e5df66c589520", "pe_common.py": "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af"}


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
listes = glob.glob("/kaggle/input/**/listes.json", recursive=True)
enc = [os.path.dirname(os.path.dirname(p)) for p in glob.glob("/kaggle/input/**/full/grid/train-00000-of-00011.npy", recursive=True)]
if STAGE not in ("smoke", "full", "mesures") or len(listes) != 1 or len(enc) != 1:
    fail(f"inputs not found exactly once: {STAGE} {listes} {enc}")
root = os.path.dirname(listes[0])
for name, want in SCRIPT_SHA256.items():
    if sha(os.path.join(root, "scripts", name)) != want:
        fail(f"{name}: sha256 is not the reviewed one")
log(f"stage {STAGE} inputs {root} {enc[0]}")
extra = []
if STAGE == "mesures":
    sealed = glob.glob("/kaggle/input/**/MANIFEST_PREDICTIONS.json", recursive=True)
    receipt = glob.glob("/kaggle/input/**/recu_planche_pe.json", recursive=True)
    if len(sealed) != 1 or len(receipt) != 1:
        fail(f"mesures needs the sealed predictions and the plate receipt exactly once: {sealed} {receipt}")
    extra = ["--predictions", os.path.dirname(sealed[0]), "--receipt", receipt[0]]
else:
    torch_before = importlib.metadata.version("torch")
    for package in (OPEN_CLIP, ULTRALYTICS):
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", package], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
        if r.returncode != 0:
            fail(f"pip install {package} exit {r.returncode}: {r.stdout[-2000:]}")
    versions = {n: importlib.metadata.version(n) for n in ("open_clip_torch", "ultralytics", "torch")}
    if (versions["open_clip_torch"] != OPEN_CLIP.split("==")[1] or versions["ultralytics"] != ULTRALYTICS.split("==")[1]
            or versions["torch"] != torch_before):
        fail(f"installed versions differ: {versions} torch before {torch_before}")
    log(f"installed {OPEN_CLIP} {ULTRALYTICS}: versions {versions}")
with open(f"{W}/petit_eleve.log", "w") as f:
    r = subprocess.run([sys.executable, "-I", os.path.join(root, "scripts", "pe_kaggle.py"), "--stage", STAGE,
                        "--inputs", root, "--encoder", enc[0], "--out", f"{W}/petit-eleve-{STAGE}"] + extra,
                       stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"petit eleve exit {r.returncode}")
log(f"CHAIN DONE petit eleve {STAGE} ok")
