# Kaggle T4 driver for d3_run.py (porkyevitch-maths, experiences/2026-10-30-d3-traine-profondeur). No network needed.
# Inputs: a dataset with scripts/ and ENCODAGE_TRAIN_V3.json (P9-A, pinned sha), the full output of
# caypollard-encode-cradio v3, and the output of kernel mabaku/porky-diag-run v3 mounted as kernel_source.
# STAGE = "blanc" first; "complet" needs the reviewed blanc.json, whose sha is set here by a reviewed commit.
# Amendment (30/10, Codex p4 B1): one T4 is required and logged with torch before anything runs (no CPU fallback; the
# local-test flag is removed from the child's environment), and a global monitor like kaggle_gel_run.py enforces the
# 2 h session of preregistration section 5, counted from the pilot start, plus outputs < 200 MB and machine guards. At
# any breach the process group is stopped, driver.json says "failed" and a blanc.json written by that run is renamed
# blanc.REFUSED.json, so the complete stage can never find it.
import glob, hashlib, json, os, shutil, signal, subprocess, sys, time

STAGE = "blanc"
BLANK_SHA256 = None
W = "/kaggle/working"
SCRIPTS = {"d3_run.py": "2529107d7a16f08f2441bba81f5d7613e264b6232cc102f7cf783cbb25bf913a", "d3_core.py": "8a31d87b4364980bbf9e9ffb552c2bf622920ec03444cdadcb67f0dd3ab85039"}
DIAG = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
INVENTORY = "ff424e6453192f6465e23e3cdf9acf29aa5827d84565deb329de4c1b891a65d9"
WALL_SECONDS = {"blanc": 7200, "complet": 7200}  # section 5: one T4 session of 2 h at most, for each stage
OUTPUT_BYTES = 200_000_000   # section 5: outputs < 200 MB, everything under /kaggle/working
MIN_AVAILABLE_RAM = 512 << 20  # no RAM ceiling is preregistered: machine guard only, peak RSS published
MIN_FREE_BYTES = 256 << 20
CPU_TEST_FLAG = "D3_CPU_FOR_LOCAL_TESTS"
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


def refuse_outputs(out):
    """A failed run never leaves a blanc.json that a later stage could pick up."""
    blank = os.path.join(out, "blanc.json")
    if os.path.exists(blank):
        os.replace(blank, os.path.join(out, "blanc.REFUSED.json"))


def run_child(cmd, env, out, start, wall, work, extra=None, clock=time.monotonic, sleep=time.sleep, measure=usage):
    """Start the stage in its own process group, monitor it, write driver.json; return the record."""
    record = {"stage": STAGE, "wall_limit_seconds": wall, "output_limit_bytes": OUTPUT_BYTES, "status": "running",
              "no_automatic_continuation": True, **(extra or {})}
    with open(os.path.join(work, "d3.log"), "w") as f:
        child = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        failure, peak = monitor(child, start, wall, work, clock, sleep, measure)
    if failure is None and child.returncode != 0:
        failure = f"d3 exit {child.returncode}"
    record.update({"exit_code": child.returncode, "elapsed_s": clock() - start, "failure": failure, "peak": peak,
                   "status": "failed" if failure else "passed"})
    if failure:
        refuse_outputs(out)
    with open(os.path.join(work, "driver.json"), "w") as f:
        json.dump(record, f, indent=2, allow_nan=False)
        f.write("\n")
    return record


def t4_identity():
    """One visible T4, torch version and GPU name; any other device stops the pilot before the child starts."""
    import torch
    if not torch.cuda.is_available() or "T4" not in torch.cuda.get_device_name(0):
        fail("one T4 required, no CPU fallback")
    return {"torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0)}


def main():
    start = time.monotonic()
    open(f"{W}/chain.log", "w").close()
    script = find("d3_run.py")
    inventory = find("ENCODAGE_TRAIN_V3.json", INVENTORY)
    diag = [os.path.dirname(p) for p in find("diagnostic.json", DIAG)]
    enc = [os.path.dirname(os.path.dirname(p)) for p in find("full/grid/train-00000-of-00011.json")]
    if STAGE not in ("blanc", "complet") or not all(len(x) == 1 for x in (script, inventory, diag, enc)):
        fail(f"inputs not found exactly once: {STAGE} {script} {inventory} {diag} {enc}")
    root = os.path.dirname(script[0])
    for name, want in SCRIPTS.items():
        if sha(os.path.join(root, name)) != want:
            fail(f"{name}: sha256 is not the reviewed one")
    out = f"{W}/d3-{STAGE}"
    cmd = [sys.executable, "-I", script[0], "--stage", STAGE, "--encoder", enc[0], "--inventory", inventory[0],
           "--diag", diag[0], "--out", out]
    if STAGE == "complet":
        blank = find("blanc.json", BLANK_SHA256)
        if BLANK_SHA256 is None or len(blank) != 1:
            fail("reviewed blanc.json not found")
        cmd += ["--blank", blank[0], "--blank-sha256", BLANK_SHA256]
    gpu = t4_identity()
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.pop(CPU_TEST_FLAG, None)
    import numpy  # noqa: E402
    log(f"stage {STAGE} python {sys.version.split()[0]} numpy {numpy.__version__} torch {gpu['torch']} "
        f"cuda {gpu['cuda']} gpu {gpu['gpu']} wall limit {WALL_SECONDS[STAGE]} s")
    record = run_child(cmd, env, out, start, WALL_SECONDS[STAGE], W, extra={"device": gpu})
    if record["status"] != "passed":
        fail(f"{record['failure']} after {record['elapsed_s']:.0f} s; see driver.json")
    log(f"CHAIN DONE d3 {STAGE} ok in {record['elapsed_s']:.0f} s")


if __name__ == "__main__":
    main()
