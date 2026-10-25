# Kaggle driver for filtres_distances.py (porkyevitch, experiences/2026-10-25-banc-rijksmuseum).
# MODE is "smoke" (RIJKS_SMOKE=16, technical only) or "full" (RIJKS_SMOKE=0), set before each push; no automatic chaining to the full run.
# Inputs: dataset rijks-filtres-entree (filtres_distances.py, eligibles.jsonl) and the output of kernel caypollard-encode-cradio,
# which must be its version 3 (full run of encode_cradio.py c3f12bb7..., T0 control passed). Stops at the first failure, non-zero.
import glob, hashlib, json, os, subprocess, sys, time

MODE = "smoke"
assert MODE in ("smoke", "full"), MODE
W = "/kaggle/working"
SCRIPT_SHA256 = "TO_FILL_AFTER_REVIEW"  # sha256 of filtres_distances.py as reviewed
ELIG_SHA256 = "TO_FILL"  # sha256 of eligibles.jsonl (smoke: the dry-run list; full: the list of the complete collection)
ENCODER_SCRIPT = "c3f12bb71deda0b96bf3b8d015d9a79f4db666c234ad8edb0ff04633bd2bf1ca"


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
entree = glob.glob("/kaggle/input/**/eligibles.jsonl", recursive=True)
feats = [os.path.dirname(os.path.dirname(p)) for p in glob.glob("/kaggle/input/**/full/feats/test-00000-of-00001.npz", recursive=True)]
if len(entree) != 1 or len(feats) != 1:
    fail(f"inputs not found exactly once: {entree} {feats}")
elig, feats = entree[0], feats[0]
script = os.path.join(os.path.dirname(elig), "filtres_distances.py")
if sha(script) != SCRIPT_SHA256:
    fail(f"script sha256 {sha(script)} is not the reviewed one")
if sha(elig) != ELIG_SHA256:
    fail(f"eligibles.jsonl sha256 {sha(elig)} is not the expected one")
run = json.load(open(f"{feats}/run.json"))
ctrl = json.load(open(f"{feats}/controle.json"))
if run.get("script_sha256") != ENCODER_SCRIPT or run.get("smoke") != 0 or ctrl.get("passed") is not True:
    fail("the mounted encoder output is not version 3 (full run, control passed)")
log(f"inputs {elig} {feats} {sorted(os.listdir(feats))}")
r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "open-clip-torch", "einops"])
if r.returncode != 0:
    fail(f"pip exit {r.returncode}")
freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
open(f"{W}/pip_freeze.txt", "w").write(freeze.stdout)
env = dict(os.environ, RIJKS_SMOKE="16" if MODE == "smoke" else "0", RIJKS_HF_CACHE="/tmp/rijks_hf")
out = f"{W}/{MODE}"
with open(f"{W}/{MODE}.log", "w") as f:
    r = subprocess.run([sys.executable, script, out, feats, elig], env=env, stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"filters exit {r.returncode} ({MODE})")
for need in ("run.json", "resume.json", "budget.json", "controle_encodeur.json", "voisins.jsonl", "internes.jsonl", "rijks.json"):
    if not os.path.exists(f"{out}/{need}"):
        fail(f"missing output {need}")
log(f"CHAIN DONE {MODE} ok")
