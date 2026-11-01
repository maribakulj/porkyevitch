# Kaggle CPU driver for a1_run.py (porkyevitch-maths, experiences/2026-10-29-a1). One thread, no network needed.
# Inputs: a dataset with scripts/ and ENCODAGE_TRAIN_V3.json (P9-A, pinned sha), the full output of
# caypollard-encode-cradio v3, and the output of kernel mabaku/porky-diag-run v3 mounted as kernel_source.
# STAGE = "blanc" first; "reglage" needs the reviewed blanc.json (and its sha below); "diagnostic" needs the reglage
# output and the plate receipt. Changing STAGE and BLANK_SHA256 is the only edit allowed between runs.
# Amendment (30/10, Codex p4 B1): a global monitor like kaggle_gel_run.py. Wall time counted from the pilot start
# (blanc <= 20 min, preregistration section 7), RAM of the process group <= 8 GB, outputs <= 1 GB, free disk; at any
# breach the whole process group is stopped, driver.json says "failed" and a blanc.json written by that run is renamed
# blanc.REFUSED.json, so a failed blank can never be found by the reglage stage. The per-MILP limits are unchanged.
# B3 (Codex p4, 30/10): a non-empty output folder or an earlier driver.json is refused before the child starts,
# writing and renaming nothing; only a blanc.json created by the failed run itself is ever renamed.
import glob, hashlib, json, os, shutil, signal, subprocess, sys, time

STAGE = "diagnostic"
BLANK_SHA256 = "81003a86f64818b6e2a0d9af1fa5380ee8ef7d4d17f97b34cea9094487643eef"  # reviewed blanc.json (Grok p3 CONFORME, 30/10)
W = "/kaggle/working"
SCRIPTS = {"a1_run.py": "78b1ed982ae9b2e59624a30b83675703e156b92a1d45309b6089162c9dcee597", "a1_core.py": "177ef54243fd6dfed0aa557561aa365f41b2c992379aef6d4fab4c5e27ab205a"}
DIAG = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
INVENTORY = "ff424e6453192f6465e23e3cdf9acf29aa5827d84565deb329de4c1b891a65d9"
# blanc: section 7 (<= 20 min CPU); reglage and diagnostic: the series is <= 2 h, so neither stage may exceed it
WALL_SECONDS = {"blanc": 1200, "reglage": 7200, "diagnostic": 4387}  # diagnostic: series <= 7200 s - blanc 87 s - reglage 2726 s = 4387 s
RAM_BYTES = 8_000_000_000      # section 7: RAM <= 8 Go (decimal, the stricter reading)
OUTPUT_BYTES = 1_000_000_000   # section 7: outputs <= 1 Go, everything under /kaggle/working
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
    """(group RSS, bytes under work, free bytes of work's disk)."""
    return group_rss(pid), tree_bytes(work), shutil.disk_usage(work).free


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
            rss, size, free = measure(child.pid, work)
            peak = {"rss_bytes": max(peak["rss_bytes"], rss), "output_bytes": max(peak["output_bytes"], size)}
            if rss > RAM_BYTES:
                failure = "RAM ceiling exceeded"
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


def run_child(cmd, env, out, start, wall, work, clock=time.monotonic, sleep=time.sleep, measure=usage):
    """Start the stage in its own process group, monitor it, write driver.json; return the record."""
    record = {"stage": STAGE, "wall_limit_seconds": wall, "ram_limit_bytes": RAM_BYTES, "output_limit_bytes": OUTPUT_BYTES,
              "status": "running", "no_automatic_continuation": True}
    # B3 (Codex p4, 30/10): refuse before Popen, write nothing and rename nothing, so earlier paths and bytes stay intact
    found = preexisting(out, work)
    if found:
        return {**record, "status": "failed", "failure": f"output not empty before start: {found}", "exit_code": None,
                "started": False}
    blank_existed = os.path.lexists(os.path.join(out, "blanc.json"))
    with open(os.path.join(work, "a1.log"), "w") as f:
        child = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        failure, peak = monitor(child, start, wall, work, clock, sleep, measure)
    if failure is None and child.returncode != 0:
        failure = f"a1 exit {child.returncode}"
    record.update({"exit_code": child.returncode, "elapsed_s": clock() - start, "failure": failure, "peak": peak,
                   "status": "failed" if failure else "passed", "started": True})
    if failure:
        refuse_outputs(out, blank_existed)
    with open(os.path.join(work, "driver.json"), "w") as f:
        json.dump(record, f, indent=2, allow_nan=False)
        f.write("\n")
    return record


def main():
    start = time.monotonic()
    open(f"{W}/chain.log", "w").close()
    script = find("a1_run.py")
    inventory = find("ENCODAGE_TRAIN_V3.json", INVENTORY)
    diag = [os.path.dirname(p) for p in find("diagnostic.json", DIAG)]
    enc = [os.path.dirname(os.path.dirname(p)) for p in find("full/grid/train-00000-of-00011.json")]
    if STAGE not in ("blanc", "reglage", "diagnostic") or not all(len(x) == 1 for x in (script, inventory, diag, enc)):
        fail(f"inputs not found exactly once: {STAGE} {script} {inventory} {diag} {enc}")
    root = os.path.dirname(script[0])
    for name, want in SCRIPTS.items():
        if sha(os.path.join(root, name)) != want:
            fail(f"{name}: sha256 is not the reviewed one")
    out = f"{W}/a1-{STAGE}"
    cmd = [sys.executable, "-I", script[0], "--stage", STAGE, "--encoder", enc[0], "--inventory", inventory[0],
           "--diag", diag[0], "--out", out]
    if STAGE in ("reglage", "diagnostic"):
        blank = find("blanc.json", BLANK_SHA256)
        if BLANK_SHA256 is None or len(blank) != 1:
            fail("reviewed blanc.json not found")
        cmd += ["--blank", blank[0], "--blank-sha256", BLANK_SHA256]
    if STAGE == "diagnostic":
        reg = [os.path.dirname(p) for p in find("MANIFEST_REGLAGE.json")]
        receipt = find("recu_planche_a1.json")
        if len(reg) != 1 or len(receipt) != 1:
            fail(f"diagnostic needs the reglage output and the receipt exactly once: {reg} {receipt}")
        cmd += ["--reglage", reg[0], "--receipt", receipt[0]]
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONHASHSEED="0")
    import numpy  # noqa: E402
    log(f"stage {STAGE} python {sys.version.split()[0]} numpy {numpy.__version__} wall limit {WALL_SECONDS[STAGE]} s")
    record = run_child(cmd, env, out, start, WALL_SECONDS[STAGE], W)
    if record["status"] != "passed":
        fail(f"{record['failure']} after {record['elapsed_s']:.0f} s; see driver.json")
    log(f"CHAIN DONE a1 {STAGE} ok in {record['elapsed_s']:.0f} s")


if __name__ == "__main__":
    main()
