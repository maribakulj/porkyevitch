# Kaggle T4 driver for pe_kaggle.py (porkyevitch-maths, experiences/2026-10-30-petit-eleve). Internet on (model weights).
# Inputs: dataset with scripts/, listes.json, noms.json, images/, graphes/, s1b/ (no closed set), and the full output of
# kernel caypollard-encode-cradio v3. STAGE = "smoke" for the blank; the full run needs a reviewed commit that pins the
# OWLv2 / Florence-2 revisions in pe_kaggle.py (so its sha changes) and sets STAGE = "full".
import glob, hashlib, os, subprocess, sys, time

STAGE = "smoke"
W = "/kaggle/working"
SCRIPT_SHA256 = {"pe_kaggle.py": "017f488863fc58b5f9e7457d354a714a0b04d48bfc5e5409c497563d0c626a91", "pe_common.py": "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af"}


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
if STAGE not in ("smoke", "full") or len(listes) != 1 or len(enc) != 1:
    fail(f"inputs not found exactly once: {STAGE} {listes} {enc}")
root = os.path.dirname(listes[0])
for name, want in SCRIPT_SHA256.items():
    if sha(os.path.join(root, "scripts", name)) != want:
        fail(f"{name}: sha256 is not the reviewed one")
log(f"stage {STAGE} inputs {root} {enc[0]}")
with open(f"{W}/petit_eleve.log", "w") as f:
    r = subprocess.run([sys.executable, "-I", os.path.join(root, "scripts", "pe_kaggle.py"), "--stage", STAGE,
                        "--inputs", root, "--encoder", enc[0], "--out", f"{W}/petit-eleve"],
                       stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"petit eleve exit {r.returncode}")
log(f"CHAIN DONE petit eleve {STAGE} ok")
