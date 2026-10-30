# Kaggle driver for extraire_confiants_absents.py (porkyevitch-maths, experiences/2026-10-30-diagnostic-tete). CPU, internet on.
# Inputs: a dataset holding the script and diagnostic.json (full run), the Iconclass data repository (txt/en/), and the
# output of kernel caypollard-encode-cradio v3 (full run, md5 field only).
import glob, hashlib, os, subprocess, sys, time

W = "/kaggle/working"
SCRIPT_SHA256 = "1caedaf493a00a7c30687a12ebce338e7c5db6612f8294940f9d75274ddf3e80"  # extraire_confiants_absents.py as reviewed
DIAG_SHA256 = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"


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
script = glob.glob("/kaggle/input/**/extraire_confiants_absents.py", recursive=True)
diag = [p for p in glob.glob("/kaggle/input/**/diagnostic.json", recursive=True) if sha(p) == DIAG_SHA256]
icon = [os.path.dirname(os.path.dirname(os.path.dirname(p))) for p in glob.glob("/kaggle/input/**/txt/en/txt_en_keys.txt", recursive=True)]
enc = [os.path.dirname(os.path.dirname(p)) for p in glob.glob("/kaggle/input/**/full/feats/train-00000-of-00011.npz", recursive=True)]
if len(script) != 1 or len(diag) != 1 or len(icon) != 1 or len(enc) != 1:
    fail(f"inputs not found exactly once: {script} {diag} {icon} {enc}")
if sha(script[0]) != SCRIPT_SHA256:
    fail("script sha256 is not the reviewed one")
log(f"inputs {script[0]} {diag[0]} {icon[0]} {enc[0]}")
with open(f"{W}/extraction.log", "w") as f:
    r = subprocess.run([sys.executable, "-I", script[0], diag[0], enc[0], icon[0], f"{W}/confiants_absents"],
                       stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"extraction exit {r.returncode}")
log("CHAIN DONE extraction ok")
