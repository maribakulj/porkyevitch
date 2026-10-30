# Kaggle CPU driver for mesure_phase1.py (porkyevitch-maths, experiences/2026-10-30-mesure-phase1). Internet on for the
# dev plates (IIIF images of the Rijksmuseum dev, sha checked). STAGE = "dev" first; "test" only after the plates are viewed,
# with the dev output and the viewing receipt mounted as inputs. The only change allowed between the two runs is STAGE.
import glob, hashlib, os, subprocess, sys, time

STAGE = "dev"
W = "/kaggle/working"
SCRIPTS = {"mesure_phase1.py": "e5f073f5be5a54d216d97ad2177b5e33d914383d92b686272e3b5c71d46eda08", "mesure_metrics.py": "9a9d452676e7dd7717d4fab0aa00d11c2a1da5169913d03a80e0ccb5416df895"}
SEAL = "3c468faa7bec5ac7a98104a4ac47d3f7be24ec9ef76e0855f49b42aad12fad0c"
FROZEN = "2424b778d0a3e7c36e0aeea7ce5db60fcc52bc1eaa6c52a057fd957b142de0ca"
ENTREES = "6bde822932f9a288d9bd764cc950e160e16e1c78fb5456df28b51bfd6acd6604"


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
    hits = glob.glob(f"/kaggle/input/**/{pattern}", recursive=True)
    return [p for p in hits if digest is None or sha(p) == digest]


open(f"{W}/chain.log", "w").close()
script = find("mesure_phase1.py")
seal = find("MANIFEST.json", SEAL)
frozen = find("frozen.json", FROZEN)
entrees = find("ENTREES_GELEES.json", ENTREES)
enc = [os.path.dirname(os.path.dirname(p)) for p in find("full/grid/train-00000-of-00011.json")]
icon = [os.path.dirname(os.path.dirname(os.path.dirname(p))) for p in find("txt/en/txt_en_keys.txt")]
if STAGE not in ("dev", "test") or not all(len(x) == 1 for x in (script, seal, frozen, entrees, enc, icon)):
    fail(f"inputs not found exactly once: {STAGE} {script} {seal} {frozen} {entrees} {enc} {icon}")
root = os.path.dirname(script[0])
for name, want in SCRIPTS.items():
    if sha(os.path.join(root, name)) != want:
        fail(f"{name}: sha256 is not the reviewed one")
cmd = [sys.executable, "-I", script[0], "--stage", STAGE, "--seal", os.path.dirname(seal[0]), "--frozen", frozen[0],
       "--inputs", entrees[0], "--encoder", enc[0], "--iconclass", icon[0], "--out", f"{W}/mesure-{STAGE}"]
if STAGE == "test":
    dev = [os.path.dirname(p) for p in find("MANIFEST_DEV.json")]
    receipt = find("recu_planches.json")
    if len(dev) != 1 or len(receipt) != 1:
        fail(f"test stage needs the dev output and the receipt exactly once: {dev} {receipt}")
    cmd += ["--dev", dev[0], "--receipt", receipt[0]]
log(f"stage {STAGE}")
with open(f"{W}/mesure.log", "w") as f:
    r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
if r.returncode != 0:
    fail(f"mesure exit {r.returncode}")
log(f"CHAIN DONE mesure {STAGE} ok")
