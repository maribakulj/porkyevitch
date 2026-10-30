# Kaggle CPU driver for mesure_phase1.py (porkyevitch-maths, experiences/2026-10-30-mesure-phase1). Internet on for the
# dev plates (IIIF images of the Rijksmuseum dev, sha checked). STAGE = "dev" first; "test" only after the plates are viewed.
# Amendment (30/10, wA:p1), test stage only: Kaggle deletes any dataset holding the dev plate images, so the dev output,
# the receipt and the two scripts come in ONE uncompressed tar renamed mesure-dev.bin (pinned sha DEV_ARCHIVE_SHA256),
# extracted safely into /kaggle/working/dev-in; MANIFEST_DEV.json, recu_planches.json and the scripts are then looked for
# in dev-in only, never in /kaggle/input. The dev stage is unchanged. The changes allowed between runs: STAGE, and
# DEV_ARCHIVE_SHA256 set by a reviewed commit before the test stage.
import glob, hashlib, os, subprocess, sys, tarfile, time
from pathlib import Path

STAGE = "dev"
DEV_ARCHIVE_SHA256 = "8281e5810e5bcb938085175e9dffffb4e937c659c958b6127fa9676b0a583a09"  # mesure-dev.bin given by wA:p1 (30/10)
W = "/kaggle/working"
SCRIPTS = {"mesure_phase1.py": "76f2643ae369faf5cb8b581af3b3c092ccf569355acb76d7f8c35e669fd7eb3b", "mesure_metrics.py": "9a9d452676e7dd7717d4fab0aa00d11c2a1da5169913d03a80e0ccb5416df895"}
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


def find(pattern, digest=None, root="/kaggle/input"):
    hits = glob.glob(f"{root}/**/{pattern}", recursive=True)
    return [p for p in hits if digest is None or sha(p) == digest]


def safe_extract(archive, expected_sha, dest):
    """Uncompressed tar only; sha checked first; every member must be a regular file or a directory with a relative
    path without '..'; absolute names, links and special files are refused before anything is written."""
    if expected_sha is None or sha(archive) != expected_sha:
        raise RuntimeError("dev archive sha is not the pinned one")
    dest = Path(dest)
    if dest.exists():
        raise RuntimeError("dev-in already exists")
    with tarfile.open(archive, mode="r:") as tar:
        members = tar.getmembers()
        for m in members:
            parts = Path(m.name).parts
            if m.name.startswith(("/", "\\")) or Path(m.name).is_absolute() or ".." in parts or not parts:
                raise RuntimeError(f"unsafe member path: {m.name!r}")
            if not (m.isfile() or m.isdir()):
                raise RuntimeError(f"link or special member refused: {m.name!r}")
            target = (dest / m.name).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                raise RuntimeError(f"member escapes dev-in: {m.name!r}")
        dest.mkdir(parents=True)
        for m in members:
            if m.isdir():
                (dest / m.name).mkdir(parents=True, exist_ok=True)
            else:
                (dest / m.name).parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(m) as src, open(dest / m.name, "wb") as out:
                    out.write(src.read())
    return dest


def test_inputs(dev_in):
    """MANIFEST_DEV.json, recu_planches.json and both scripts, each exactly once, in dev-in only; scripts' sha checked."""
    dev = [os.path.dirname(p) for p in find("MANIFEST_DEV.json", root=str(dev_in))]
    receipt = find("recu_planches.json", root=str(dev_in))
    script = find("mesure_phase1.py", root=str(dev_in))
    if len(dev) != 1 or len(receipt) != 1 or len(script) != 1:
        raise RuntimeError(f"dev-in must hold the dev output, the receipt and the script exactly once: {dev} {receipt} {script}")
    check_scripts(os.path.dirname(script[0]))
    return dev[0], receipt[0], script[0]


def check_scripts(root):
    for name, want in SCRIPTS.items():
        if sha(os.path.join(root, name)) != want:
            raise RuntimeError(f"{name}: sha256 is not the reviewed one")


def main():
    open(f"{W}/chain.log", "w").close()
    seal = find("MANIFEST.json", SEAL)
    frozen = find("frozen.json", FROZEN)
    entrees = find("ENTREES_GELEES.json", ENTREES)
    enc = [os.path.dirname(os.path.dirname(p)) for p in find("full/grid/train-00000-of-00011.json")]
    icon = [os.path.dirname(os.path.dirname(os.path.dirname(p))) for p in find("txt/en/txt_en_keys.txt")]
    if STAGE not in ("dev", "test") or not all(len(x) == 1 for x in (seal, frozen, entrees, enc, icon)):
        fail(f"inputs not found exactly once: {STAGE} {seal} {frozen} {entrees} {enc} {icon}")
    try:
        if STAGE == "dev":
            script = find("mesure_phase1.py")
            if len(script) != 1:
                fail(f"script not found exactly once: {script}")
            check_scripts(os.path.dirname(script[0]))
            script, extra = script[0], []
        else:
            archive = find("mesure-dev.bin")
            if len(archive) != 1:
                fail(f"mesure-dev.bin not found exactly once: {archive}")
            dev_in = safe_extract(archive[0], DEV_ARCHIVE_SHA256, f"{W}/dev-in")
            dev, receipt, script = test_inputs(dev_in)
            extra = ["--dev", dev, "--receipt", receipt]
    except RuntimeError as e:
        fail(str(e))
    cmd = [sys.executable, "-I", script, "--stage", STAGE, "--seal", os.path.dirname(seal[0]), "--frozen", frozen[0],
           "--inputs", entrees[0], "--encoder", enc[0], "--iconclass", icon[0], "--out", f"{W}/mesure-{STAGE}"] + extra
    import numpy  # noqa: E402
    log(f"stage {STAGE} python {sys.version.split()[0]} numpy {numpy.__version__}")
    with open(f"{W}/mesure.log", "w") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        fail(f"mesure exit {r.returncode}")
    log(f"CHAIN DONE mesure {STAGE} ok")


if __name__ == "__main__":
    main()
