"""VLM comparison, calls (PREINSCRIPTION-v2.1.md sections 2, 3.4, 5, 6). Computes NO score.

One image per call, a fresh session per call, in a temporary folder that holds only the image. Every attempt is appended to
journal/<stage>.jsonl with its raw output (raw/<id>.<attempt>.txt), state, time, cost or usage; a call already final in the
journal is never repeated (resume). Caps, checked before each attempt: attempts <= CAP_FACTOR x planned calls of the stage;
cumulated Claude total_cost_usd (all stages) < BUDGET_USD; S1 wall time < S1_WALL_SECONDS. At a cap the stage stops and
status.json says "incomplet".

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
            "--allowedTools", "Read", "--output-format", "stream-json", "--verbose", "--no-session-persistence"]


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
            out, seconds, timed_out = run(claude_command(model, vc.prompt_claude(spec["kind"], vocab, str(image.resolve()))),
                                          work, TIMEOUT["claude"])
            parsed = vc.parse_claude_stream(out, image)
            state, payload = ("echec_technique", None) if timed_out else vc.claude_state(spec["kind"], parsed)
            extra = {"cost_usd": parsed["cost_usd"], "usage": parsed["usage"], "duration_ms": parsed["duration_ms"],
                     "model_reported": parsed["model"], "image_read": parsed["image_read"]}
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


class Journal:
    def __init__(self, root, stage):
        self.path = root / "journal" / f"{stage}.jsonl"
        self.raw = root / "raw"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.raw.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self.records = [json.loads(l) for l in self.path.read_text().splitlines()] if self.path.exists() else []

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


def claude_spent(root):
    """Cumulated total_cost_usd of every Claude attempt, all stages (v2.1 budget)."""
    total = 0.0
    for p in (root / "journal").glob("*.jsonl"):
        for l in p.read_text().splitlines():
            r = json.loads(l)
            if r.get("system") in vc.CLAUDE_SYSTEMS and isinstance(r.get("cost_usd"), (int, float)):
                total += r["cost_usd"]
    return total


class Caps:
    def __init__(self, root, stage, planned, journal):
        self.root, self.stage, self.journal = root, stage, journal
        self.max_attempts = math.ceil(vc.CAP_FACTOR * planned)
        self.started = time.time()
        self.lock = threading.Lock()
        self.stopped = None  # stops the whole stage (attempt cap, S1 wall time)
        self.claude_stopped = False  # the Claude budget stops H and O only; Gemini goes on (v2.1)
        self.spent = claude_spent(root)

    def allow(self, system):
        with self.lock:
            if self.stopped:
                return False
            if len(self.journal.records) >= self.max_attempts:
                self.stopped = "plafond d'essais"
            elif self.stage == "S1" and time.time() - self.started >= vc.S1_WALL_SECONDS:
                self.stopped = "temps réel de S1"
            if self.stopped:
                return False
            if system in vc.CLAUDE_SYSTEMS and self.spent >= vc.BUDGET_USD:
                self.claude_stopped = True
                return False
            return True

    def stopped_by(self):
        return self.stopped or ("budget Claude" if self.claude_stopped else None)

    def charge(self, rec):
        with self.lock:
            if isinstance(rec.get("cost_usd"), (int, float)):
                self.spent += rec["cost_usd"]


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
            attempt = len(journal.attempts(spec["id"]))
            rec = attempt_fn(spec, image_path(prep, root, spec), vocab, history)
            rec = journal.append(spec["id"], attempt, {"system": spec["system"], "model": vc.MODELS[spec["system"]],
                                                       "kind": spec["kind"], "bank": spec["bank"], "item": spec["item"],
                                                       **rec})
            caps.charge(rec)


def stage_run(root, stage, systems, attempt_fn=one_attempt, history=vc.AGY_HISTORY):
    root = Path(root)
    prep = json.loads((root / "prep.json").read_text())
    for name, want in prep["code_sha256"].items():  # frozen code: the preparation seal names it
        require(sha(HERE / name) == want, f"code_changed_{name}")
    require(vc.prompts_sha256(prep["vocabulary"]) == prep["prompts_sha256"], "prompts_changed")
    if stage == "R":
        require((root / "status_S1.json").exists() and json.loads((root / "status_S1.json").read_text())["complete"],
                "repeat_after_complete_S1")
    specs = [c for c in prep["calls"][stage] if c["system"] in systems]
    journal = Journal(root, stage)
    caps = Caps(root, stage, len(prep["calls"][stage]), journal)
    with ThreadPoolExecutor(max_workers=vc.PARALLEL * len(systems)) as pool:
        futures = []
        for s in systems:
            mine = [c for c in specs if c["system"] == s]
            for k in range(vc.PARALLEL):
                futures.append(pool.submit(worker, mine[k::vc.PARALLEL], prep, root, journal, caps, history, attempt_fn))
        for f in futures:
            f.result()
    done = sum(journal.final(c["id"]) for c in specs)
    status = {"stage": stage, "systems": list(systems), "planned": len(specs), "final": done,
              "complete": done == len(specs) and caps.stopped_by() is None, "stopped_by": caps.stopped_by(),
              "attempts": len(journal.records), "claude_spent_usd": round(claude_spent(root), 6),
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
