# Kaggle driver for e0_reference.py (porkyevitch, experiences/2026-10-25-iconclass-architecture).
# MODE is "smoke" (E0_SMOKE=2, technical only) or "full" (E0_SMOKE=0), set before each push; no automatic chaining to the full run.
# Inputs: dataset porky-e0-entree (e0_reference.py), dataset caypollard-iconclass-t0 (head.pt) and the output of kernel
# caypollard-encode-cradio, which must be its version 3 (encode_cradio.py c3f12bb7..., full run, T0 control passed).
import glob, hashlib, json, os, subprocess, sys, time

MODE = "smoke"
assert MODE in ("smoke", "full"), MODE
W = "/kaggle/working"
SCRIPT_SHA256 = "TO_FILL_AFTER_REVIEW"  # sha256 of e0_reference.py as reviewed
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
script = glob.glob("/kaggle/input/**/e0_reference.py", recursive=True)
t0 = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/head.pt", recursive=True) if "caypollard-iconclass-t0" in p]
enc = [os.path.dirname(os.path.dirname(p)) for p in glob.glob("/kaggle/input/**/full/feats/test-00000-of-00001.npz", recursive=True)]
if len(script) != 1 or len(t0) != 1 or len(enc) != 1:
    fail(f"inputs not found exactly once: {script} {t0} {enc}")
script, t0, enc = script[0], t0[0], enc[0]
if sha(script) != SCRIPT_SHA256:
    fail(f"script sha256 {sha(script)} is not the reviewed one")
run = json.load(open(f"{enc}/run.json"))
ctrl = json.load(open(f"{enc}/controle.json"))
if run.get("script_sha256") != ENCODER_SCRIPT or run.get("smoke") != 0 or ctrl.get("passed") is not True:
    fail("the mounted encoder output is not version 3 (full run, control passed)")
log(f"inputs {script} {t0} {enc}")
freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
open(f"{W}/pip_freeze.txt", "w").write(freeze.stdout)
out = f"{W}/{MODE}"
with open(f"{W}/{MODE}.log", "w") as f:
    r = subprocess.run([sys.executable, script, out, enc, t0], env=dict(os.environ, E0_SMOKE="2" if MODE == "smoke" else "0"),
                       stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"e0 exit {r.returncode} ({MODE})")
if not json.load(open(f"{out}/run.json")).get("gpu"):
    fail("no GPU recorded in run.json: not a valid run")
for need in ("tenseurs.json", "e0.json", "t_long.pt", "journal_t_long.jsonl", "budget.json"):
    if not os.path.exists(f"{out}/{need}"):
        fail(f"missing output {need}")
log(f"CHAIN DONE {MODE} ok")
