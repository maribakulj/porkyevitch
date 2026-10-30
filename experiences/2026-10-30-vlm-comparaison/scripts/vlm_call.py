"""VLM comparison, calls (PREINSCRIPTION-v2.2.md sections 2, 3.4, 5, 6). Computes NO score.

One image per call, a fresh session per call, in a new temporary folder (outside the home folder) that holds only the image.
Every attempt is appended to journal/<stage>.jsonl with its raw output (raw/<id>.<attempt>.txt), state, time, cost or usage
and its budget charge; a call already final in the journal is never repeated (resume).

Caps, checked before each attempt (v2.2): attempts issued <= CAP_FACTOR x the planned calls of the selected systems; S1
wall time, cumulated across resumptions (wall_S1.json), < S1_WALL_SECONDS; cumulated Claude budget charges (all stages)
< BUDGET_USD, which stops H and O only; at most CLAUDE_IN_FLIGHT Claude calls at once (H and O together). At a cap the
stage stops and status_<stage>.json says it is incomplete.

S1 needs a complete S0: the extrapolation rule (vlm_core.plan_s1) is applied to the S0 journal, written to plan_S1.json
(checked again on every resumption), and S1 runs in blocks: dev, Opus slice, V-diagnostic (kept groups), graphs.

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

TIMEOUT = {"claude": 900, "agy": 900}
STAGES = ("S0", "S1", "R")
S1_BLOCKS = ("dev", "opus", "vdiag", "graphes")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(cond, what):
    if not cond:
        raise SystemExit(f"REFUSED: {what}")


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


def claude_command(model, prompt):
    return ["claude", "-p", prompt, "--model", model, "--system-prompt", vc.SYSTEM_CLAUDE, "--tools", "Read",
            "--allowedTools", "Read", "--setting-sources", "", "--output-format", "stream-json", "--verbose",
            "--no-session-persistence"]


def agy_command(model, prompt, timeout):
    return ["agy", "-p", prompt, "--model", model, "--output-format", "json", "--print-timeout", f"{timeout - 60}s"]


def one_attempt(spec, image_src, vocab, history):
    """One call in a fresh folder; returns the journal record (no score)."""
    model = vc.MODELS[spec["system"]]
    work = Path(tempfile.mkdtemp(prefix="vlm-"))
    try:
        image = work / Path(image_src).name
        shutil.copyfile(image_src, image)
        if spec["system"] in vc.CLAUDE_SYSTEMS:
            require(vc.claude_isolation_ok(work), "claude_isolation (user CLAUDE.md present or work folder under home)")
            out, seconds, timed_out = run(claude_command(model, vc.prompt_claude(spec["kind"], vocab, str(image.resolve()))),
                                          work, TIMEOUT["claude"])
            parsed = vc.parse_claude_stream(out, image)
            state, payload = ("echec_technique", None) if timed_out else vc.claude_state(spec["kind"], parsed)
            extra = {"cost_usd": parsed["cost_usd"], "usage": parsed["usage"], "duration_ms": parsed["duration_ms"],
                     "model_reported": parsed["model"], "image_read": parsed["image_read"],
                     "read_errors": parsed["read_errors"]}
        else:
            out, seconds, timed_out = run(agy_command(model, vc.prompt_agy(spec["kind"], vocab, image.name), TIMEOUT["agy"]),
                                          work, TIMEOUT["agy"])
            parsed = vc.parse_agy(out, image, history)
            state, payload = ("echec_technique", None) if timed_out else vc.agy_state(spec["kind"], parsed)
            extra = {"cost_usd": None, "usage": parsed["usage"], "status": parsed["status"],
                     "conversation_id": parsed["conversation_id"], "image_read": parsed["image_read"]}
        return {"state": state, "payload": payload, "seconds": round(seconds, 3), "timed_out": timed_out, "raw": out, **extra}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def read_journal(path):
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


class Journal:
    def __init__(self, root, stage):
        self.path = root / "journal" / f"{stage}.jsonl"
        self.raw = root / "raw"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.raw.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self.records = read_journal(self.path)

    def attempts(self, call_id):
        return [r for r in self.records if r["id"] == call_id]

    def final(self, call_id):
        rs = self.attempts(call_id)
        return bool(rs) and (rs[-1]["state"] not in vc.RETRYABLE or len(rs) >= 2)

    def append(self, call_id, attempt, rec):
        raw = rec.pop("raw")
        name = f"{call_id.replace(':', '_')}.{attempt}.txt"
        with self.lock:
            (self.raw / name).write_text(raw)
            rec = {"id": call_id, "attempt": attempt, "raw_file": name, "raw_sha256": sha(self.raw / name),
                   "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **rec}
            with self.path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.records.append(rec)
        return rec


def all_records(root):
    return [r for p in sorted((root / "journal").glob("*.jsonl")) for r in read_journal(p)]


def claude_spent(root):
    """Cumulated budget charges of every Claude attempt, all stages (v2.2: prudent charge when no cost was reported)."""
    return sum(r.get("budget_charge_usd", 0.0) for r in all_records(root) if r.get("system") in vc.CLAUDE_SYSTEMS)


class Caps:
    def __init__(self, root, stage, planned, journal):
        self.root, self.stage, self.journal = root, stage, journal
        self.max_attempts = math.ceil(vc.CAP_FACTOR * planned)
        self.issued = len(journal.records)  # attempts already in this stage's journal count against the cap
        self.wall_file = root / "wall_S1.json"
        self.wall_base = json.loads(self.wall_file.read_text())["seconds"] if self.wall_file.exists() else 0.0
        self.started = time.time()
        self.lock = threading.Lock()
        self.stopped = None  # stops the whole stage (attempt cap, S1 wall time)
        self.claude_stopped = False  # the Claude budget stops H and O only; Gemini goes on
        self.spent = claude_spent(root)
        self.observed = {s: [r["cost_usd"] for r in all_records(root) if r.get("system") == s
                             and isinstance(r.get("cost_usd"), (int, float))] for s in vc.CLAUDE_SYSTEMS}
        self.claude_slots = threading.BoundedSemaphore(vc.CLAUDE_IN_FLIGHT)
        self.gemini_slots = threading.BoundedSemaphore(vc.PARALLEL)

    def wall(self):
        return self.wall_base + (time.time() - self.started)

    def save_wall(self):
        if self.stage == "S1":
            with self.lock:
                self.wall_file.write_text(json.dumps({"seconds": self.wall()}) + "\n")

    def allow(self, system):
        """Reserves one attempt (atomically) when no cap forbids it."""
        with self.lock:
            if not self.stopped and self.issued >= self.max_attempts:
                self.stopped = "plafond d'essais"
            if not self.stopped and self.stage == "S1" and self.wall() >= vc.S1_WALL_SECONDS:
                self.stopped = "temps réel de S1"
            if self.stopped:
                return False
            if system in vc.CLAUDE_SYSTEMS and self.spent >= vc.BUDGET_USD:
                self.claude_stopped = True
                return False
            self.issued += 1
            return True

    def charge(self, system, cost):
        """Budget charge of a Claude attempt (v2.2); None for Gemini."""
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
            if not caps.allow(spec["system"]):
                return
            slots = caps.claude_slots if spec["system"] in vc.CLAUDE_SYSTEMS else caps.gemini_slots
            with slots:
                attempt = len(journal.attempts(spec["id"]))
                rec = attempt_fn(spec, image_path(prep, root, spec), vocab, history)
            charge = caps.charge(spec["system"], rec.get("cost_usd"))
            journal.append(spec["id"], attempt, {"system": spec["system"], "model": vc.MODELS[spec["system"]],
                                                 "kind": spec["kind"], "bank": spec["bank"], "item": spec["item"],
                                                 "block": spec.get("block"), "budget_charge_usd": charge, **rec})
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


def s1_plan(root, prep):
    """The extrapolation rule applied to the S0 journal (v2.2); written once, then checked on each resumption."""
    st0 = root / "status_S0.json"
    require(st0.exists() and json.loads(st0.read_text())["complete"], "S1_after_complete_S0")
    s0 = read_journal(root / "journal" / "S0.jsonl")
    calls = prep["calls"]["S1"]
    count = lambda block, system: sum(c["block"] == block and c["system"] == system for c in calls)  # noqa: E731
    sizes = {"n_dev": count("dev", "H"), "n_repeat": sum(c["system"] == "H" for c in prep["calls"]["R"]),
             "n_graphs": count("graphes", "H"), "n_opus": count("opus", "O")}
    spent_s0 = sum(r.get("budget_charge_usd", 0.0) for r in s0 if r.get("system") in vc.CLAUDE_SYSTEMS)
    plan = {"sizes": sizes, "spent_S0_usd": spent_s0,
            **vc.plan_s1(s0, sizes, [tuple(x) for x in prep["samples"]["vdiag_groups_order"]], spent_s0)}
    path = root / "plan_S1.json"
    if path.exists():
        require(json.loads(path.read_text()) == json.loads(json.dumps(plan)), "plan_S1_changed")
    else:
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n")
    require(plan["launch"], "S1_not_launched: predicted cost above the budget even without V-diagnostic (Marcel decides)")
    return plan


def stage_run(root, stage, systems, attempt_fn=one_attempt, history=vc.AGY_HISTORY):
    root = Path(root)
    prep = json.loads((root / "prep.json").read_text())
    for name, want in prep["code_sha256"].items():  # frozen code: the preparation seal names it
        require(sha(HERE / name) == want, f"code_changed_{name}")
    require(vc.prompts_sha256(prep["vocabulary"]) == prep["prompts_sha256"], "prompts_changed")
    require(set(vc.CLAUDE_SYSTEMS) & set(systems) == set() or not vc.USER_CLAUDE_MD.exists(), "user_CLAUDE_md_present")
    if stage == "R":
        require((root / "status_S1.json").exists() and json.loads((root / "status_S1.json").read_text())["complete"],
                "repeat_after_complete_S1")
    specs = [c for c in prep["calls"][stage] if c["system"] in systems]
    plan = None
    if stage == "S1":
        plan = s1_plan(root, prep)
        kept = set(plan["vdiag_groups_kept"])
        groups = {x["key"]: x["group"] for x in prep["banks"]["icai_vdiag"]}
        specs = [c for c in specs if c["bank"] != "icai_vdiag" or groups[c["item"]] in kept]
    journal = Journal(root, stage)
    caps = Caps(root, stage, len(specs), journal)
    blocks = S1_BLOCKS if stage == "S1" else (None,)
    for block in blocks:
        mine = [c for c in specs if block is None or c["block"] == block]
        run_block(mine, prep, root, journal, caps, history, attempt_fn, systems)
    caps.save_wall()
    done = sum(journal.final(c["id"]) for c in specs)
    status = {"stage": stage, "systems": list(systems), "planned": len(specs), "final": done,
              "complete": done == len(specs) and caps.stopped_by() is None, "stopped_by": caps.stopped_by(),
              "attempts": len(journal.records), "claude_charged_usd": round(claude_spent(root), 6),
              "s1_wall_seconds": round(caps.wall(), 1) if stage == "S1" else None,
              "vdiag_reduced": plan["reduced"] if plan else None,
              "journal_sha256": sha(journal.path) if journal.path.exists() else None}
    (root / f"status_{stage}.json").write_text(json.dumps(status, ensure_ascii=False, indent=1) + "\n")
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
