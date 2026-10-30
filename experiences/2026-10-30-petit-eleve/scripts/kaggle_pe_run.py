# Kaggle T4 driver for pe_kaggle.py (porkyevitch-maths, experiences/2026-10-30-petit-eleve). Internet on (model weights).
# Inputs: dataset with scripts/, listes.json, noms.json, images/, graphes/, s1b/ (no closed set), and the full output of
# kernel caypollard-encode-cradio v3. STAGE = "smoke" for the blank; the full run needs a reviewed commit that pins the
# OWLv2 / Florence-2 revisions in pe_kaggle.py (so its sha changes) and sets STAGE = "full".
# Amendment (30/10, wA:p1): the current Kaggle image lacks open_clip, which the C-RADIO remote code imports; the pilot
# installs the pinned open_clip_torch before the subprocess and logs its version (torch must stay unchanged).
# Amendment (30/10, before the full run): ultralytics pinned for YOLOE-v8-S, installed and checked the same way; stage
# "mesures" (CPU) runs only on the sealed predictions of the full run (MANIFEST_PREDICTIONS.json) with the plate receipt
# (recu_planche_pe.json), each found exactly once under /kaggle/input, and installs nothing.
# Amendment D11 (30/10): Kaggle deleted the porky-* datasets (name, or the drawn nudes: cause unsure). The inputs, images
# included, now come in ONE uncompressed tar renamed pe-entrees.bin (pinned ENTREES_SHA256), extracted safely into
# /tmp/pkyevitch/pe-in (NOT /kaggle/working, which Kaggle publishes as the kernel output: the images must not reappear
# there); listes.json and the scripts are looked for there only. If the sealed folder of the full run
# must be re-uploaded too (its 12 plates are JPEG), it comes as pe-scelle.bin, extracted into /tmp/pkyevitch, with a sha
# pinned by a reviewed commit (SCELLE_SHA256); otherwise the full run's kernel output is mounted as before.
# pe_kaggle.py and pe_common.py are unchanged (their sha is checked here and by the seal of the full run).
import glob, hashlib, importlib.metadata, os, subprocess, sys, tarfile, time
from pathlib import Path

STAGE = "full"  # after smoke 2 (Grok p3 CONFORME), revisions, MobileCLIP and CLIP tokenizer pinned in pe_kaggle.py
OPEN_CLIP = "open_clip_torch==3.3.0"
ULTRALYTICS = "ultralytics==8.4.177"  # YOLOE-v8-S witness (D8), smoke and full only
W = "/kaggle/working"
EXTRACT = "/tmp/pkyevitch"  # not persisted by Kaggle
SCRIPT_SHA256 = {"pe_kaggle.py": "91996fe00a615496529f1035d437d30caab6d27f0ea880ab9e28e7bb660af22a", "pe_common.py": "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af"}
ENTREES_SHA256 = "b48cb32c9880c35dd2bc55cfb5b791e2de7437a736463b78c50e93ad37b90608"  # pe-entrees.bin built by outils/construire_entrees_bin.py
SCELLE_SHA256 = None  # pe-scelle.bin, only if the sealed folder of the full run has to be re-uploaded


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


def safe_extract(archive, expected_sha, dest):
    """Uncompressed tar only; sha checked first; every member must be a regular file or a directory with a relative
    path without '..'; absolute names, links and special files are refused before anything is written.
    (The reviewed function of the phase-1 measure pilot, kaggle_mesure_run.py, unchanged.)"""
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


def only(pattern, root="/kaggle/input"):
    return glob.glob(f"{root}/**/{pattern}", recursive=True)


def entries(work=EXTRACT, mounted="/kaggle/input"):
    """Exactly one pe-entrees.bin under the mounts, extracted into work/pe-in; listes.json exactly once, there."""
    archive = only("pe-entrees.bin", mounted)
    if len(archive) != 1:
        raise RuntimeError(f"pe-entrees.bin not found exactly once: {archive}")
    root = safe_extract(archive[0], ENTREES_SHA256, Path(work) / "pe-in")
    listes = only("listes.json", str(root))
    if len(listes) != 1 or Path(listes[0]).parent != root:
        raise RuntimeError(f"listes.json must be at the root of pe-in, once: {listes}")
    for name, want in SCRIPT_SHA256.items():
        if sha(root / "scripts" / name) != want:
            raise RuntimeError(f"{name}: sha256 is not the reviewed one")
    return root


def sealed_predictions(work=EXTRACT, mounted="/kaggle/input"):
    """The sealed folder of the full run: from pe-scelle.bin if one is mounted (sha pinned), else the kernel output."""
    archive = only("pe-scelle.bin", mounted)
    if archive:
        if len(archive) != 1 or SCELLE_SHA256 is None:
            raise RuntimeError(f"pe-scelle.bin needs a pinned sha and must be unique: {archive}")
        root = safe_extract(archive[0], SCELLE_SHA256, Path(work) / "pe-scelle-in")
        sealed = only("MANIFEST_PREDICTIONS.json", str(root))
    else:
        sealed = only("MANIFEST_PREDICTIONS.json", mounted)
    if len(sealed) != 1:
        raise RuntimeError(f"the sealed predictions must be found exactly once: {sealed}")
    return os.path.dirname(sealed[0])


def main():
    open(f"{W}/chain.log", "w").close()
    enc = [os.path.dirname(os.path.dirname(p)) for p in only("full/grid/train-00000-of-00011.npy")]
    if STAGE not in ("smoke", "full", "mesures") or len(enc) != 1:
        fail(f"inputs not found exactly once: {STAGE} {enc}")
    try:
        root = entries()
    except RuntimeError as e:
        fail(str(e))
    log(f"stage {STAGE} inputs {root} (pe-entrees.bin {ENTREES_SHA256}) {enc[0]}")
    extra = []
    if STAGE == "mesures":
        receipt = only("recu_planche_pe.json")
        try:
            predictions = sealed_predictions()
        except RuntimeError as e:
            fail(str(e))
        if len(receipt) != 1:
            fail(f"mesures needs the plate receipt exactly once: {receipt}")
        extra = ["--predictions", predictions, "--receipt", receipt[0]]
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
                            "--inputs", str(root), "--encoder", enc[0], "--out", f"{W}/petit-eleve-{STAGE}"] + extra,
                           stdout=f, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        fail(f"petit eleve exit {r.returncode}")
    log(f"CHAIN DONE petit eleve {STAGE} ok")


if __name__ == "__main__":
    main()
