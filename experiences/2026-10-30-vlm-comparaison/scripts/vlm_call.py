"""VLM comparison, calls (PREINSCRIPTION-v2.4.md sections 2, 3.4, 5, 6). Computes NO score.

One image per call, a fresh session per call, in a new temporary folder (canonical path, outside the home folder) that holds
only the image.

Journal (v2.4, Codex B3): journal/<stage>.jsonl, append only, each line flushed and fsynced. A "started" line is written
BEFORE each call is sent and a "result" line after it (state, time, cost or usage, budget charge, raw output in
raw/<id>.<attempt>.txt, never overwritten). Attempts are counted from the "started" lines. On resumption, a "started" line
without result is closed by a result "interrompu" (retryable once, empty set) with the prudent budget charge for Claude.

Order of a call (v2.4, Codex B4): take a slot (at most CLAUDE_IN_FLIGHT Claude calls, H and O together; PARALLEL Gemini
calls), THEN, in ONE critical section, check the caps (attempt cap, S1 wall time, Claude budget) and write "started";
send, charge the
budget and write the result, and only then free the slot. The Claude budget stops H and O only; Gemini goes on.

S1 wall time: cumulated across resumptions (wall_S1.json, refreshed every HEARTBEAT seconds and after each call); a call is
not started with less than MIN_CALL_SECONDS left, and its time-out is the time left (v2.4).

Gates (v2.4): S1 needs a complete S0 on H, G and O; R needs a complete S1 on H, G and O. The extrapolation rule
(vlm_core.plan_s1) is applied to the S0 journal, written to plan_S1.json and checked again on every resumption; S1 runs in
blocks: dev, Opus slice, V-diagnostic (kept groups), graphs. The CLI versions are written in a "meta" line at each start.

Usage: vlm_call.py --prep OUT --stage S0|S1|R [--systems H,G,O]
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vlm_core as vc  # noqa: E402

TIMEOUT = 900
MIN_CALL_SECONDS = 120
HEARTBEAT = 15
STAGES = ("S0", "S1", "R")
S1_BLOCKS = ("dev", "opus", "vdiag", "graphes")
EXPECTED_SYSTEMS = {"S0": ("H", "G", "O"), "S1": ("H", "G", "O"), "R": ("H", "G")}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(cond, what):
    if not cond:
        raise SystemExit(f"REFUSED: {what}")


def now_utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def run(command, cwd, timeout):
    """Own process group, killed whole at the wall-clock deadline (region_agy.run_agy). Returns (stdout, seconds, timed_out)."""
    started = time.time()
    p = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         start_new_session=True)
    deadline = started + timeout
    try:
        while True:
            try:
                out, _ = p.communicate(timeout=min(30, max(1, deadline - time.time())))
                return out, time.time() - started, False
            except subprocess.TimeoutExpired:
                if time.time() >= deadline:
                    raise
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        return "", time.time() - started, True


def cli_versions():
    """Versions of the two CLIs (v2.4, Codex note 4)."""
    out = {}
    for name in ("claude", "agy"):
        try:
            r = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=60)
            text = (r.stdout or r.stderr).strip()
            out[name] = text.splitlines()[0] if text else None
        except (OSError, subprocess.TimeoutExpired):
            out[name] = None
    return out


def claude_command(model, prompt):
    return ["claude", "-p", prompt, "--model", model, "--system-prompt", vc.SYSTEM_CLAUDE, "--tools", "Read",
            "--allowedTools", "Read", "--setting-sources", "", "--output-format", "stream-json", "--verbose",
            "--no-session-persistence"]


def agy_command(model, prompt, timeout):
    return ["agy", "-p", prompt, "--model", model, "--output-format", "json", "--print-timeout", f"{max(60, timeout - 60)}s"]


def one_attempt(spec, image_src, vocab, history, timeout=TIMEOUT):
    """One call in a fresh folder; returns the result record (no score)."""
    model = vc.MODELS[spec["system"]]
    work = Path(tempfile.mkdtemp(prefix="vlm-", dir=os.path.realpath(tempfile.gettempdir())))  # canonical path
    try:
        image = work / Path(image_src).name
        shutil.copyfile(image_src, image)
        if spec["system"] in vc.CLAUDE_SYSTEMS:
            require(vc.claude_isolation_ok(work), "claude_isolation (user CLAUDE.md present or work folder under home)")
            out, seconds, timed_out = run(claude_command(model, vc.prompt_claude(spec["kind"], vocab, str(image.resolve()))),
                                          work, timeout)
            parsed = vc.parse_claude_stream(out, image)
            state, payload = ("echec_technique", None) if timed_out else vc.claude_state(spec["kind"], parsed)
            extra = {"cost_usd": parsed["cost_usd"], "usage": parsed["usage"], "duration_ms": parsed["duration_ms"],
                     "model_reported": parsed["model"], "image_read": parsed["image_read"],
                     "read_errors": parsed["read_errors"]}
        else:
            out, seconds, timed_out = run(agy_command(model, vc.prompt_agy(spec["kind"], vocab, image.name), timeout),
                                          work, timeout)
            parsed = vc.parse_agy(out, image, history)
            state, payload = ("echec_technique", None) if timed_out else vc.agy_state(spec["kind"], parsed)
            extra = {"cost_usd": None, "usage": parsed["usage"], "status": parsed["status"],
                     "conversation_id": parsed["conversation_id"], "image_read": parsed["image_read"],
                     "commands": parsed["commands"]}
        return {"state": state, "payload": payload, "seconds": round(seconds, 3), "timed_out": timed_out,
                "timeout_seconds": timeout, "raw": out, **extra}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def read_lines(path):
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def append_durable(path, record):
    with open(path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def write_durable(path, text):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class Journal:
    def __init__(self, root, stage):
        self.path = root / "journal" / f"{stage}.jsonl"
        self.raw = root / "raw"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.raw.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        lines = read_lines(self.path)
        self.starts = [l for l in lines if l.get("phase") == "started"]
        self.records = [l for l in lines if l.get("phase") == "result"]

    def attempts(self, call_id):
        return sum(1 for l in self.starts if l["id"] == call_id)

    def final(self, call_id):
        rs = [r for r in self.records if r["id"] == call_id]
        return bool(rs) and (rs[-1]["state"] not in vc.RETRYABLE or self.attempts(call_id) >= 2)

    def orphans(self):
        done = {(r["id"], r["attempt"]) for r in self.records}
        return [s for s in self.starts if (s["id"], s["attempt"]) not in done]

    def meta(self, info):
        with self.lock:
            append_durable(self.path, {"phase": "meta", "time_utc": now_utc(), **info})

    def start(self, spec):
        with self.lock:
            line = {"phase": "started", "id": spec["id"], "attempt": self.attempts(spec["id"]), "system": spec["system"],
                    "model": vc.MODELS[spec["system"]], "kind": spec["kind"], "bank": spec["bank"], "item": spec["item"],
                    "block": spec.get("block"), "time_utc": now_utc()}
            append_durable(self.path, line)
            self.starts.append(line)
            return line

    def result(self, started, rec):
        raw = rec.pop("raw", None)
        with self.lock:
            name = None
            if raw is not None:
                name = f"{started['id'].replace(':', '_')}.{started['attempt']}.txt"
                require(not (self.raw / name).exists(), f"raw_already_written_{name}")
                write_durable(self.raw / name, raw)
            line = {"phase": "result", **{k: started[k] for k in ("id", "attempt", "system", "model", "kind", "bank",
                                                                 "item", "block")},
                    "raw_file": name, "raw_sha256": sha(self.raw / name) if name else None, "time_utc": now_utc(), **rec}
            append_durable(self.path, line)
            self.records.append(line)
            return line


def all_lines(root):
    return [l for p in sorted((root / "journal").glob("*.jsonl")) for l in read_lines(p)]


def observed_costs(lines):
    return {s: [l["cost_usd"] for l in lines if l.get("phase") == "result" and l.get("system") == s
                and isinstance(l.get("cost_usd"), (int, float))] for s in vc.CLAUDE_SYSTEMS}


def claude_spent(root):
    """Budget charges of every Claude result, all stages, plus the prudent charge of any Claude start still without result."""
    lines = all_lines(root)
    obs = observed_costs(lines)
    total = sum(l.get("budget_charge_usd") or 0.0 for l in lines
                if l.get("phase") == "result" and l.get("system") in vc.CLAUDE_SYSTEMS)
    done = {(l["id"], l["attempt"]) for l in lines if l.get("phase") == "result"}
    for s in lines:
        if s.get("phase") == "started" and s["system"] in vc.CLAUDE_SYSTEMS and (s["id"], s["attempt"]) not in done:
            total += vc.budget_charge(None, obs[s["system"]])
    return total


class Caps:
    def __init__(self, root, stage, planned, journal):
        self.root, self.stage, self.journal = root, stage, journal
        self.max_attempts = math.ceil(vc.CAP_FACTOR * planned)
        self.wall_file = root / "wall_S1.json"
        self.wall_base = json.loads(self.wall_file.read_text())["seconds"] if self.wall_file.exists() else 0.0
        self.started = time.time()
        self.lock = threading.Lock()
        self.stopped = None  # stops the whole stage (attempt cap, S1 wall time)
        self.claude_stopped = False  # the Claude budget stops H and O only; Gemini goes on
        self.spent = claude_spent(root)
        self.observed = observed_costs(all_lines(root))
        self.claude_slots = threading.BoundedSemaphore(vc.CLAUDE_IN_FLIGHT)
        self.gemini_slots = threading.BoundedSemaphore(vc.PARALLEL)

    def wall(self):
        return self.wall_base + (time.time() - self.started)

    def left(self):
        return vc.S1_WALL_SECONDS - self.wall() if self.stage == "S1" else float("inf")

    def save_wall(self):
        if self.stage == "S1":
            with self.lock:
                write_durable(self.wall_file, json.dumps({"seconds": self.wall()}) + "\n")

    def allow(self, system):
        """Checks the caps (attempt cap, S1 wall time, Claude budget) without reserving anything."""
        with self.lock:
            return self._check(system)

    def reserve(self, spec):
        """v2.4 (Codex B4 residual): check AND reserve in one critical section. With the slot held, the caps are checked and
        the durable 'started' line is written under the same lock (lock order: Caps, then Journal), so that no two workers
        can both see the last free attempt. Returns the started line, or None when a cap forbids the call."""
        with self.lock:
            if not self._check(spec["system"]):
                return None
            return self.journal.start(spec)

    def _check(self, system):
        """Caller holds self.lock."""
        if not self.stopped and len(self.journal.starts) >= self.max_attempts:
            self.stopped = "plafond d'essais"
        if not self.stopped and self.left() < MIN_CALL_SECONDS:
            self.stopped = "temps réel de S1"
        if self.stopped:
            return False
        if system in vc.CLAUDE_SYSTEMS and self.spent >= vc.BUDGET_USD:
            self.claude_stopped = True
            return False
        return True

    def timeout(self):
        return int(min(TIMEOUT, self.left()))

    def charge(self, system, cost):
        """Budget charge of a Claude attempt; None for Gemini."""
        if system not in vc.CLAUDE_SYSTEMS:
            return None
        with self.lock:
            c = vc.budget_charge(cost, self.observed[system])
            if isinstance(cost, (int, float)):
                self.observed[system].append(float(cost))
            self.spent += c
            return c

    def stopped_by(self):
        return self.stopped or ("budget Claude" if self.claude_stopped else None)


def close_orphans(journal, caps):
    """B3: a start without result (interruption) is closed as 'interrompu', with the prudent charge for Claude. The charge
    was already counted in caps.spent by claude_spent; it is written now and not added twice."""
    for s in journal.orphans():
        charge = vc.budget_charge(None, caps.observed[s["system"]]) if s["system"] in vc.CLAUDE_SYSTEMS else None
        journal.result(s, {"state": "interrompu", "payload": None, "seconds": None, "timed_out": None,
                           "cost_usd": None, "budget_charge_usd": charge})


def image_path(prep, root, spec):
    bank = {x.get("key", x.get("name")): x for x in prep["banks"][spec["bank"]]}[spec["item"]]
    rel = bank["image"] if spec["bank"] != "pe_eval" else f"pe/{bank['image']}"
    path = root / "images" / rel
    require(sha(path) == prep["image_sha256"][rel], f"image_changed_{rel}")
    return path


def worker(specs, prep, root, journal, caps, history, attempt_fn):
    vocab = prep["vocabulary"]
    for spec in specs:
        while not journal.final(spec["id"]):
            slots = caps.claude_slots if spec["system"] in vc.CLAUDE_SYSTEMS else caps.gemini_slots
            with slots:  # B4: the caps are read only once the slot is held, right before sending
                image = image_path(prep, root, spec)
                started = caps.reserve(spec)  # B3 + B4: checked and written durably in one critical section
                if started is None:
                    return
                rec = attempt_fn(spec, image, vocab, history, timeout=caps.timeout())
                rec["budget_charge_usd"] = caps.charge(spec["system"], rec.get("cost_usd"))
                journal.result(started, rec)  # charged and written before the slot is freed
            caps.save_wall()


def run_block(specs, prep, root, journal, caps, history, attempt_fn, systems):
    with ThreadPoolExecutor(max_workers=vc.PARALLEL * len(systems)) as pool:
        futures = []
        for s in systems:
            mine = [c for c in specs if c["system"] == s]
            for k in range(vc.PARALLEL):
                if mine[k::vc.PARALLEL]:
                    futures.append(pool.submit(worker, mine[k::vc.PARALLEL], prep, root, journal, caps, history,
                                               attempt_fn))
        for f in futures:
            f.result()


def complete(root, stage):
    st = root / f"status_{stage}.json"
    if not st.exists():
        return False
    s = json.loads(st.read_text())
    return bool(s["complete"] and s["all_systems"])


def s1_plan(root, prep):
    """The extrapolation rule applied to the S0 journal (v2.2); written once, then checked on each resumption."""
    require(complete(root, "S0"), "S1_after_complete_S0_on_all_systems")
    s0 = [l for l in read_lines(root / "journal" / "S0.jsonl") if l.get("phase") == "result"]
    calls = prep["calls"]["S1"]
    count = lambda block, system: sum(c["block"] == block and c["system"] == system for c in calls)  # noqa: E731
    sizes = {"n_dev": count("dev", "H"), "n_repeat": sum(c["system"] == "H" for c in prep["calls"]["R"]),
             "n_graphs": count("graphes", "H"), "n_opus": count("opus", "O")}
    spent_s0 = sum(r.get("budget_charge_usd") or 0.0 for r in s0 if r.get("system") in vc.CLAUDE_SYSTEMS)
    plan = {"sizes": sizes, "spent_S0_usd": spent_s0,
            **vc.plan_s1(s0, sizes, [tuple(x) for x in prep["samples"]["vdiag_groups_order"]], spent_s0)}
    path = root / "plan_S1.json"
    if path.exists():
        require(json.loads(path.read_text()) == json.loads(json.dumps(plan)), "plan_S1_changed")
    else:
        write_durable(path, json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    require(plan["launch"], "S1_not_launched: predicted cost above the budget even without V-diagnostic (Marcel decides)")
    return plan


def stage_run(root, stage, systems, attempt_fn=one_attempt, history=vc.AGY_HISTORY, versions_fn=None):
    root = Path(root)
    prep = json.loads((root / "prep.json").read_text())
    for name, want in prep["code_sha256"].items():  # frozen code: the preparation seal names it
        require(sha(HERE / name) == want, f"code_changed_{name}")
    require(vc.prompts_sha256(prep["vocabulary"]) == prep["prompts_sha256"], "prompts_changed")
    require(set(vc.CLAUDE_SYSTEMS) & set(systems) == set() or not vc.USER_CLAUDE_MD.exists(), "user_CLAUDE_md_present")
    if stage == "R":
        require(complete(root, "S1"), "repeat_after_complete_S1_on_all_systems")
    specs = [c for c in prep["calls"][stage] if c["system"] in systems]
    plan = None
    if stage == "S1":
        plan = s1_plan(root, prep)
        kept = set(plan["vdiag_groups_kept"])
        groups = {x["key"]: x["group"] for x in prep["banks"]["icai_vdiag"]}
        specs = [c for c in specs if c["bank"] != "icai_vdiag" or groups[c["item"]] in kept]
    journal = Journal(root, stage)
    caps = Caps(root, stage, len(specs), journal)
    close_orphans(journal, caps)
    journal.meta({"systems": list(systems), "cli_versions": (versions_fn or cli_versions)()})
    stop = threading.Event()

    def heartbeat():
        while not stop.wait(HEARTBEAT):
            caps.save_wall()
    beat = threading.Thread(target=heartbeat, daemon=True)
    beat.start()
    try:
        for block in (S1_BLOCKS if stage == "S1" else (None,)):
            mine = [c for c in specs if block is None or c["block"] == block]
            run_block(mine, prep, root, journal, caps, history, attempt_fn, systems)
    finally:
        stop.set()
        beat.join()
        caps.save_wall()
    done = sum(journal.final(c["id"]) for c in specs)
    status = {"stage": stage, "systems": list(systems), "all_systems": set(systems) == set(EXPECTED_SYSTEMS[stage]),
              "planned": len(specs), "final": done, "complete": done == len(specs) and caps.stopped_by() is None,
              "stopped_by": caps.stopped_by(), "attempts_started": len(journal.starts),
              "claude_charged_usd": round(claude_spent(root), 6),
              "s1_wall_seconds": round(caps.wall(), 1) if stage == "S1" else None,
              "vdiag_reduced": plan["reduced"] if plan else None,
              "journal_sha256": sha(journal.path) if journal.path.exists() else None}
    write_durable(root / f"status_{stage}.json", json.dumps(status, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(status, ensure_ascii=False))
    return status


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", required=True)
    ap.add_argument("--stage", required=True, choices=STAGES)
    ap.add_argument("--systems", default="H,G,O")
    a = ap.parse_args()
    systems = tuple(s for s in a.systems.split(",") if s)
    require(set(systems) <= set(vc.MODELS), "unknown_system")
    stage_run(a.prep, a.stage, systems)
