# Kaggle driver for e1_decision.py (porkyevitch, experiences/2026-10-25-iconclass-architecture).
# MODE is "smoke" (E1_SMOKE=2, technical only) or "full" (E1_SMOKE=0), set before each push; no automatic chaining to the full run.
# Inputs: dataset porky-e1-entree (e1_decision.py), the output of kernel caypollard-encode-cradio (version 3: vectors) and the output
# of kernel porky-e0-run (version 2: full/t_long.pt and full/e0.json, T* of reference.json).
import glob, hashlib, json, os, subprocess, sys, time

MODE = "full"
assert MODE in ("smoke", "full"), MODE
W = "/kaggle/working"
SCRIPT_SHA256 = "f33681ea1bbec2fe9a5eda3b9ae00b3720b136d276489ecbfbacdc58a654f227"  # sha256 of e1_decision.py as reviewed
ENCODER_SCRIPT = "c3f12bb71deda0b96bf3b8d015d9a79f4db666c234ad8edb0ff04633bd2bf1ca"
TSTAR_SHA256 = "5a1b3041c0d9aab0e3403182b0881272a02f395542fe8414dc54b4fc7fa045ea"


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
script = glob.glob("/kaggle/input/**/e1_decision.py", recursive=True)
enc = [os.path.dirname(os.path.dirname(p)) for p in glob.glob("/kaggle/input/**/full/feats/test-00000-of-00001.npz", recursive=True)]
tstar = [os.path.dirname(p) for p in glob.glob("/kaggle/input/**/full/t_long.pt", recursive=True)]
if len(script) != 1 or len(enc) != 1 or len(tstar) != 1:
    fail(f"inputs not found exactly once: {script} {enc} {tstar}")
script, enc, tstar = script[0], enc[0], tstar[0]
if sha(script) != SCRIPT_SHA256:
    fail(f"script sha256 {sha(script)} is not the reviewed one")
run = json.load(open(f"{enc}/run.json"))
if run.get("script_sha256") != ENCODER_SCRIPT or run.get("smoke") != 0 or json.load(open(f"{enc}/controle.json")).get("passed") is not True:
    fail("the mounted encoder output is not version 3 (full run, control passed)")
if sha(f"{tstar}/t_long.pt") != TSTAR_SHA256 or json.load(open(f"{tstar}/e0.json")).get("T_star") != "T-long":
    fail("the mounted E0 output is not the one of reference.json")
log(f"inputs {script} {enc} {tstar}")
freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
open(f"{W}/pip_freeze.txt", "w").write(freeze.stdout)
out = f"{W}/{MODE}"
with open(f"{W}/{MODE}.log", "w") as f:
    r = subprocess.run([sys.executable, script, out, enc, tstar], env=dict(os.environ, E1_SMOKE="2" if MODE == "smoke" else "0"),
                       stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"e1 exit {r.returncode} ({MODE})")
if not json.load(open(f"{out}/run.json")).get("gpu"):
    fail("no GPU recorded in run.json: not a valid run")
e1 = json.load(open(f"{out}/e1.json"))
if not e1.get("controls", {}).get("passed"):
    fail("E1 controls not passed")
for need in ("e1.json", "budget.json"):
    if not os.path.exists(f"{out}/{need}"):
        fail(f"missing output {need}")
log(f"CHAIN DONE {MODE} ok")
