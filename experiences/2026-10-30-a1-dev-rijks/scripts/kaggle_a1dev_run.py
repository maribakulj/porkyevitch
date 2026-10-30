# Kaggle T4 driver for a1dev_run.py (porkyevitch-maths, experiences/2026-10-30-a1-dev-rijks, D17). Internet on (IIIF
# images of the Rijksmuseum dev, sha checked by the reviewed freeze downloader; open_clip_torch for the C-RADIO remote
# code). Each input is found exactly once under /kaggle/input and sha-checked here: this folder (a1dev_*.py and the
# pinned A1 modules), the reviewed freeze code (pkyevitch-gel-code), its binding (pkyevitch-gel-config/sources.json,
# D11), the freeze inventory and A1's inventory, the seal of the freeze (only its two dev prediction files are opened),
# the validation cache of porky-diag-run v3, and the C-RADIO encoding. One session of at most 3 600 s from the pilot
# start (Codex, D17), outputs <= 200 MB, machine guards, refusal of a non-empty output before the child starts, one
# visible GPU, one CPU thread (A1's sealed environment: Python 3.13.15, numpy 2.1.3, scipy 1.16.3, required here).
import glob, hashlib, importlib.metadata, json, os, shutil, signal, subprocess, sys, time

STAGE = "dev"
W = "/kaggle/working"
SCRIPTS = {"a1dev_run.py": "d26c4b0f3f7811740d7f96b93823835e6adb2b0def87f62a72526227c8e30247", "a1dev_core.py": "2da71468255293ba7dfb602c1bffd78cf5ee590d43afe9720f1490fcfdf8cc81",
           "a1_core.py": "177ef54243fd6dfed0aa557561aa365f41b2c992379aef6d4fab4c5e27ab205a",
           "a1_run.py": "78b1ed982ae9b2e59624a30b83675703e156b92a1d45309b6089162c9dcee597"}
GEL = {"gel_common.py": "e228e390f3d23fcb9ee6e31d2d85f6d89c6f8b5e0b835e2d8ccd3ab547276987",
       "gel_data.py": "cc0686d313f49ca489c9683ef919b551f65e27360795eff31e354d8bfeabd0cc",
       "gel_models.py": "f84ebc46cb5275792fd6fc02f77242815ed66d3a5fbf161119a255567aaacd4a",
       "gel_predictions.py": "0ac075adf74ff7bcd2abc80e031891ddcabff595188cac6a38956b4ef5c71af0"}
BINDING = "60d068998f7d93ab5fb379a8df9ea3fbd3bca6dfa42f7baa02cb2c5572ffb898"  # pkyevitch-gel-config/sources.json (D11)
GEL_INVENTORY = "6bde822932f9a288d9bd764cc950e160e16e1c78fb5456df28b51bfd6acd6604"
A1_INVENTORY = "ff424e6453192f6465e23e3cdf9acf29aa5827d84565deb329de4c1b891a65d9"
SEAL = "3c468faa7bec5ac7a98104a4ac47d3f7be24ec9ef76e0855f49b42aad12fad0c"
DIAG = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
A1_ENV = {"python": "3.13.15", "numpy": "2.1.3", "scipy": "1.16.3"}  # reglage.json versions (8f75d500)
OPEN_CLIP = "open_clip_torch==3.3.0"
WALL_SECONDS = {"dev": 3600}
OUTPUT_BYTES = 200_000_000
MIN_AVAILABLE_RAM = 512 << 20
MIN_FREE_BYTES = 256 << 20
POLL_SECONDS = 2


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


def tree_bytes(root):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, files in os.walk(root) for f in files
               if os.path.isfile(os.path.join(d, f)))


def group_rss(pid):
    import psutil
    try:
        parent = psutil.Process(pid)
        procs = [parent] + parent.children(recursive=True)
    except psutil.NoSuchProcess:
        return 0
    total = 0
    for p in procs:
        try:
            total += p.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return total


def usage(pid, work):
    """(group RSS, bytes under work, free bytes of work's disk, available system RAM)."""
    import psutil
    return group_rss(pid), tree_bytes(work), shutil.disk_usage(work).free, psutil.virtual_memory().available


def stop_group(child):
    if child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=10)


def monitor(child, start, wall, work, clock=time.monotonic, sleep=time.sleep, measure=usage):
    """Watch child (started with start_new_session=True) until it exits or a ceiling is breached; return the failure
    reason or None. start is the pilot's own start on the same clock, so setup time counts against the wall."""
    failure, peak = None, {"rss_bytes": 0, "output_bytes": 0}
    try:
        while child.poll() is None:
            if clock() - start > wall:
                failure = "wall time ceiling exceeded"
                break
            rss, size, free, available = measure(child.pid, work)
            peak = {"rss_bytes": max(peak["rss_bytes"], rss), "output_bytes": max(peak["output_bytes"], size)}
            if available < MIN_AVAILABLE_RAM:
                failure = "system RAM exhausted"
            elif size > OUTPUT_BYTES:
                failure = "output ceiling exceeded"
            elif free < MIN_FREE_BYTES:
                failure = "disk exhausted"
            if failure:
                break
            sleep(POLL_SECONDS)
    finally:
        stop_group(child)
    if failure is None and clock() - start > wall:
        failure = "wall time ceiling exceeded"
    return failure, peak


def refuse_outputs(out, blank_existed):
    """A failed run never leaves a blanc.json that a later stage could pick up; only a blanc.json created by this run
    is renamed, never one that existed before it started (run_child also refuses a non-empty output beforehand)."""
    blank = os.path.join(out, "blanc.json")
    if not blank_existed and os.path.exists(blank):
        os.replace(blank, os.path.join(out, "blanc.REFUSED.json"))


def preexisting(out, work):
    """Paths that a new run could overwrite or rename: a non-empty output folder, or an earlier driver.json."""
    found = []
    if os.path.lexists(out) and (not os.path.isdir(out) or os.listdir(out)):
        found.append(out)
    if os.path.lexists(os.path.join(work, "driver.json")):
        found.append(os.path.join(work, "driver.json"))
    return found


def run_child(cmd, env, out, start, wall, work, extra=None, clock=time.monotonic, sleep=time.sleep, measure=usage):
    """Start the stage in its own process group, monitor it, write driver.json; return the record."""
    record = {"stage": STAGE, "wall_limit_seconds": wall, "output_limit_bytes": OUTPUT_BYTES, "status": "running",
              "no_automatic_continuation": True, **(extra or {})}
    # B3 (Codex p4, 30/10): refuse before Popen, write nothing and rename nothing, so earlier paths and bytes stay intact
    found = preexisting(out, work)
    if found:
        return {**record, "status": "failed", "failure": f"output not empty before start: {found}", "exit_code": None,
                "started": False}
    blank_existed = os.path.lexists(os.path.join(out, "blanc.json"))
    with open(os.path.join(work, "a1dev.log"), "w") as f:
        child = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        failure, peak = monitor(child, start, wall, work, clock, sleep, measure)
    if failure is None and child.returncode != 0:
        failure = f"a1dev exit {child.returncode}"
    record.update({"exit_code": child.returncode, "elapsed_s": clock() - start, "failure": failure, "peak": peak,
                   "status": "failed" if failure else "passed", "started": True})
    if failure:
        refuse_outputs(out, blank_existed)
    with open(os.path.join(work, "driver.json"), "w") as f:
        json.dump(record, f, indent=2, allow_nan=False)
        f.write("\n")
    return record


def t4_identity():
    import torch
    if not torch.cuda.is_available() or "T4" not in torch.cuda.get_device_name(0):
        fail("one T4 required, no CPU fallback")
    return {"torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0),
            "gpus_seen_by_pilot": torch.cuda.device_count(), "child_visible_devices": "0"}


def one(pattern, digest=None):
    hits = [p for p in glob.glob(f"/kaggle/input/**/{pattern}", recursive=True) if digest is None or sha(p) == digest]
    if len(hits) != 1:
        fail(f"{pattern} not found exactly once: {hits}")
    return hits[0]


def main():
    start = time.monotonic()
    open(f"{W}/chain.log", "w").close()
    here = os.path.dirname(one("a1dev_run.py"))
    for name, want in SCRIPTS.items():
        if sha(os.path.join(here, name)) != want:
            fail(f"{name}: sha256 is not the reviewed one")
    gel = os.path.dirname(one("gel_predictions.py", GEL["gel_predictions.py"]))
    for name, want in GEL.items():
        if sha(os.path.join(gel, name)) != want:
            fail(f"{name}: sha256 is not the reviewed one")
    binding = one("sources.json", BINDING)
    gel_inventory = one("ENTREES_GELEES.json", GEL_INVENTORY)
    a1_inventory = one("ENCODAGE_TRAIN_V3.json", A1_INVENTORY)
    seal = os.path.dirname(one("MANIFEST.json", SEAL))
    diag = os.path.dirname(one("diagnostic.json", DIAG))
    enc = os.path.dirname(os.path.dirname(one("full/grid/train-00000-of-00011.json")))
    torch_before = importlib.metadata.version("torch")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", OPEN_CLIP], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        fail(f"pip install {OPEN_CLIP} exit {r.returncode}: {r.stdout[-2000:]}")
    versions = {n: importlib.metadata.version(n) for n in ("torch", "open_clip_torch", "transformers", "numpy", "scipy",
                                                            "timm", "einops", "Pillow", "psutil")}
    versions["python"] = sys.version.split()[0]
    if versions["open_clip_torch"] != OPEN_CLIP.split("==")[1] or versions["torch"] != torch_before:
        fail(f"installed versions differ: {versions} torch before {torch_before}")
    if {k: versions[k] for k in A1_ENV} != A1_ENV:
        fail(f"environment differs from A1's sealed one: {versions}")
    gpu = t4_identity()
    out = f"{W}/a1-dev"
    cmd = [sys.executable, "-I", os.path.join(here, "a1dev_run.py"), "--gel-code", gel, "--binding", binding,
           "--gel-inventory", gel_inventory, "--a1-inventory", a1_inventory, "--encoder", enc, "--diag", diag,
           "--seal", seal, "--out", out]
    env = dict(os.environ, PYTHONHASHSEED="0", A1DEV_REVIEWED_STAGE="dev", CUBLAS_WORKSPACE_CONFIG=":4096:8",
               CUDA_VISIBLE_DEVICES="0", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN", "KAGGLE_KEY"):
        env.pop(name, None)
    log(f"stage {STAGE} versions {json.dumps(versions)} gpu {gpu['gpu']} gpus seen by pilot {gpu['gpus_seen_by_pilot']} "
        f"child CUDA_VISIBLE_DEVICES=0 OMP 1 wall limit {WALL_SECONDS[STAGE]} s")
    record = run_child(cmd, env, out, start, WALL_SECONDS[STAGE], W, extra={"device": gpu, "versions": versions})
    if record["status"] != "passed":
        fail(f"{record['failure']} after {record['elapsed_s']:.0f} s; see driver.json")
    log(f"CHAIN DONE a1-dev ok in {record['elapsed_s']:.0f} s")


if __name__ == "__main__":
    main()
