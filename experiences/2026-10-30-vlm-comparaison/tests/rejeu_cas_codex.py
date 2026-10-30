"""Replays EVERY case of Codex's reproduction scripts (porkyevitch-vlm-cas-audit-codex.py, 0016904; and
porkyevitch-vlm-plafond-cas-codex.py, b8c221e) against the current code, each case isolated, on fictitious data only (no
model, no network, no real image). Codex's conversation ids ('mention', 'failed') are kept AND replayed as valid UUIDs, since
the current guard rejects malformed ids before anything else. Prints, per case, whether the defect still reproduces.
Run: python -I -B tests/rejeu_cas_codex.py  (exit status 1 if any defect reproduces)
"""
import concurrent.futures
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time

BASE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE / "scripts"), str(BASE / "tests")]
import vlm_call as call  # noqa: E402
import vlm_core as vc  # noqa: E402
import vlm_prepare as prep  # noqa: E402
import test_vlm as fixture  # noqa: E402

call.cli_versions = lambda: {"claude": "test", "agy": "test"}
UUIDS = {"mention": "aaaaaaaa-0000-0000-0000-000000000001", "failed": "aaaaaaaa-0000-0000-0000-000000000002"}
out = {}


def db(history, cid, rows):
    with sqlite3.connect(history / f"{cid}.db") as con:
        con.execute("CREATE TABLE IF NOT EXISTS steps(step_type INTEGER, status INTEGER, error_details TEXT, step_payload BLOB)")
        con.executemany("INSERT INTO steps VALUES(?,?,?,?)", rows)


with tempfile.TemporaryDirectory(prefix="rejeu-codex-") as tmp:
    root = Path(tmp)
    image = root / "a.jpg"
    image.write_bytes(b"image-fictive-non-decodee")
    history = root / "history"
    history.mkdir()
    # B1: a mention of the path, and a failed read, must not prove the image (both id forms)
    for name, typ, status, error, payload in [("mention", 15, 3, None, {"AbsolutePath": str(image)}),
                                              ("failed", 132, 2, "failed", {"view_file": {"AbsolutePath": str(image)}})]:
        for cid in (name, UUIDS[name]):
            db(history, cid, [(typ, status, error, json.dumps(payload, separators=(",", ":")).encode())])
            env = json.dumps({"status": "SUCCESS", "conversation_id": cid, "response": '{"codes":["2"]}'})
            parsed = vc.parse_agy(env, image, history)
            out[f"B1 {name} ({'uuid' if cid != name else 'id Codex'})"] = \
                parsed["image_read"] or vc.agy_state("codes", parsed)[0] == "reponse"
    # B2: run_command with Cwd before CommandLine, next to a valid image read
    cid = "aaaaaaaa-0000-0000-0000-000000000003"
    db(history, cid, [fixture.read_step(image.resolve()),
                      (132, 3, None, b"run_command" + json.dumps({"Cwd": "/tmp", "CommandLine": "echo fictif"},
                                                                  separators=(",", ":")).encode())])
    env = json.dumps({"status": "SUCCESS", "conversation_id": cid, "response": '{"codes":["2"]}'})
    p = vc.parse_agy(env, image, history)
    out["B2 Cwd avant CommandLine"] = vc.commands_requested(cid, history) == 0 or vc.agy_state("codes", p)[0] != "commande_executee"
    # B4 (budget): a worker waiting for a slot must not start once the budget is exhausted
    work = root / "queue"
    work.mkdir()
    pr = fixture.fake_prep(work)
    spec = next(c for c in pr["calls"]["S0"] if c["system"] == "H")
    journal = call.Journal(work, "S0")
    caps = call.Caps(work, "S0", 19, journal)
    for _ in range(3):
        caps.claude_slots.acquire()
    starts = []

    def attempt(spec, image, vocab, history, **kw):
        starts.append(caps.spent)
        return {"state": "reponse", "payload": [], "seconds": 0, "timed_out": False, "raw": "{}", "cost_usd": .1,
                "image_read": True}
    th = threading.Thread(target=call.worker, args=([spec], pr, work, journal, caps, history, attempt))
    th.start()
    time.sleep(0.2)
    caps.spent = 30.0
    for _ in range(3):
        caps.claude_slots.release()
    th.join(5)
    out["B4 appel en attente après le budget"] = bool(starts)
    # B3: an interruption after sending leaves a durable start, counted and charged at resumption
    work = root / "interruption"
    work.mkdir()
    pr = fixture.fake_prep(work)
    journal = call.Journal(work, "S0")
    caps = call.Caps(work, "S0", 19, journal)

    def interrupted(*a, **kw):
        raise RuntimeError("interruption fictive après envoi")
    try:
        call.worker([spec], pr, work, journal, caps, history, interrupted)
    except RuntimeError:
        pass
    again = call.Journal(work, "S0")
    resume = call.Caps(work, "S0", 19, again)
    out["B3 interruption perdue"] = not (len(again.starts) == 1 and resume.spent > 0)
    # B4 residual: 21 starts, cap 22, three workers past allow together
    work = root / "plafond"
    work.mkdir()
    pr = fixture.fake_prep(work)
    specs = prep.plan_calls([], ["r0", "r1", "r2", "r3", "r4"], ["r0", "r1", "r2", "r3", "r4"], [], ["p000", "p001"])["S0"]
    journal = call.Journal(work, "S0")

    def result(state):
        return {"state": state, "payload": [], "seconds": 0, "timed_out": False, "raw": "{}", "cost_usd": .001,
                "budget_charge_usd": .001, "image_read": True}
    for i, s in enumerate(specs[:16]):
        if i < 5:
            journal.result(journal.start(s), result("echec_technique"))
        journal.result(journal.start(s), result("reponse"))
    caps = call.Caps(work, "S0", 19, journal)
    barrier, original, sent = threading.Barrier(3), call.image_path, []

    def delayed(*a):
        barrier.wait(timeout=3)
        return original(*a)

    def fake(spec, image, vocab, history, **kw):
        sent.append(spec["id"])
        return result("reponse")
    call.image_path = delayed
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for f in [pool.submit(call.worker, [s], pr, work, journal, caps, None, fake) for s in specs[16:]]:
                f.result(timeout=5)
    finally:
        call.image_path = original
    out["B4 plafond non atomique (24 départs)"] = len(journal.starts) > caps.max_attempts or len(sent) != 1

for k, v in out.items():
    print(f"{'PRÉSENT' if v else 'levé  '}  {k}")
sys.exit(1 if any(out.values()) else 0)
