"""VLM comparison on fictitious data: no network, no model call (fake claude/agy executables). Run: python -I tests/test_vlm.py"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
import threading
import time
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import a1_core as a1  # noqa: E402
import vlm_call as call  # noqa: E402
import vlm_core as vc  # noqa: E402
import vlm_measure as vm  # noqa: E402
import vlm_prepare as prep  # noqa: E402

VOCAB_FILE = Path.home() / "porkyevitch-donnees/sauvegardes-kaggle/porky-diag-run/diag-full/vocabulaire.json"
VOCAB = ["1", "11", "11H", "11H(JEROME)", "2", "25", "25F", "25F2", "31A", "31A2"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class NotationTest(unittest.TestCase):
    @unittest.skipUnless(VOCAB_FILE.exists(), "vocabulary file not on this machine")
    def test_all_7907_codes_are_well_formed(self):
        v = json.loads(VOCAB_FILE.read_text())
        self.assertEqual(len(v), 7907)
        self.assertEqual([c for c in v if not vc.NOTATION.match(c)], [])

    def test_free_text_and_broken_brackets_are_invalid(self):
        for s in ("Saint Jerome", "11H(JEROME", "", "31A 24", "1.2", "11H(JEROME)}", "lion"):
            self.assertIsNone(vc.NOTATION.match(s), s)
        for s in ("11H(JEROME)", "61B:31A2212(+1)", "25F23(LION)(+12)", "86()"):
            self.assertIsNotNone(vc.NOTATION.match(s), s)

    def test_classify(self):
        valid, counts = vc.classify([" 11H ", "11H", "25F9", "a lion", 7, "31A"], set(VOCAB))
        self.assertEqual(valid, ["11H", "31A"])
        self.assertEqual(counts, {"valide": 3, "hors_V": 1, "invalide": 2})
        self.assertAlmostEqual(vc.invalid_rate(counts), 0.5)


class AnswerTest(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(vc.parse_answer("codes", '```json\n{"codes": ["11H", "2"]}\n```'), ("reponse", ["11H", "2"]))
        self.assertEqual(vc.parse_answer("codes", 'Voici : {"codes": []} fin'), ("reponse", []))
        self.assertEqual(vc.parse_answer("codes", '{"refus": "nudité"}'), ("refus", "nudité"))
        self.assertEqual(vc.parse_answer("codes", "IMAGE_ABSENTE"), ("image_non_lue", None))
        self.assertEqual(vc.parse_answer("codes", "je ne sais pas"), ("illisible", None))
        self.assertEqual(vc.parse_answer("codes", '{"codes": "11H"}'), ("illisible", None))

    def test_boxes_rank_and_cap(self):
        objs = [{"nom": "a", "boite": [0, 0, 10, 10]}, {"nom": "b", "boite": [1, 2]}, {"nom": "c", "boite": [5, 5, 50, 60]}]
        objs += [{"nom": "x", "boite": [0, 0, 1, 1]}] * 40
        state, boxes = vc.parse_answer("boites", json.dumps({"objets": objs}))
        self.assertEqual(state, "reponse")
        self.assertEqual(len(boxes), 30)
        self.assertEqual(boxes[:3], [[0, 0, 10, 10], None, [5, 5, 50, 60]])

    def test_prompts_frozen(self):
        p = vc.prompt_claude("codes", VOCAB, "/tmp/x.jpg")
        self.assertIn("11H(JEROME)\n2", p)
        self.assertIn("IMAGE_ABSENTE", p)
        self.assertIn("@x.jpg", vc.prompt_agy("codes", VOCAB, "x.jpg"))
        self.assertEqual(vc.prompts_sha256(VOCAB), vc.prompts_sha256(list(VOCAB)))
        self.assertNotEqual(vc.prompts_sha256(VOCAB), vc.prompts_sha256(VOCAB[:-1]))


def claude_stream(image, read_path=None, text='{"codes": ["11H"]}', stop="end_turn", cost=0.01):
    ev = [{"type": "system", "subtype": "init"}]
    if read_path:
        ev.append({"type": "assistant", "message": {"model": "claude-haiku-5-5", "stop_reason": "tool_use",
                   "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": str(read_path)}}]}})
        ev.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": False}]}})
    ev.append({"type": "assistant", "message": {"model": "claude-haiku-5-5", "stop_reason": stop,
               "content": [{"type": "text", "text": text}]}})
    ev.append({"type": "result", "subtype": "success", "result": text, "total_cost_usd": cost,
               "usage": {"input_tokens": 100, "output_tokens": 10}, "duration_ms": 1234, "is_error": False})
    return "\n".join(json.dumps(e) for e in ev)


def agy_db(history, cid, opened):
    history.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(history / f"{cid}.db") as con:
        con.execute("CREATE TABLE steps (step_payload BLOB)")
        for p in opened:
            con.execute("INSERT INTO steps VALUES (?)", (json.dumps({"view_file": {"AbsolutePath": str(p)}}, separators=(",", ":")).encode(),))  # agy's compact form


class CallerParsingTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.img = self.d / "a.jpg"
        self.img.write_bytes(b"jpg")

    def test_claude_image_read_cost_and_states(self):
        p = vc.parse_claude_stream(claude_stream(self.img, read_path=self.img), self.img)
        self.assertTrue(p["image_read"])
        self.assertEqual((p["cost_usd"], p["duration_ms"]), (0.01, 1234))
        self.assertEqual(vc.claude_state("codes", p), ("reponse", ["11H"]))
        other = vc.parse_claude_stream(claude_stream(self.img, read_path=self.d / "b.jpg"), self.img)
        self.assertEqual(vc.claude_state("codes", other)[0], "image_non_lue")
        refused = vc.parse_claude_stream(claude_stream(self.img, read_path=self.img, stop="refusal"), self.img)
        self.assertEqual(vc.claude_state("codes", refused)[0], "refus")
        self.assertEqual(vc.claude_state("codes", vc.parse_claude_stream("", self.img))[0], "echec_technique")

    def test_agy_sqlite_guard(self):
        hist = self.d / "hist"
        agy_db(hist, "c1", [self.img.resolve()])
        env = json.dumps({"response": '{"codes": ["2"]}', "status": "SUCCESS", "usage": {"t": 1}, "conversation_id": "c1"})
        p = vc.parse_agy(env, self.img, hist)
        self.assertTrue(p["image_read"])
        self.assertEqual(vc.agy_state("codes", p), ("reponse", ["2"]))
        agy_db(hist, "c2", [self.d / "other.jpg"])
        p2 = vc.parse_agy(env.replace("c1", "c2"), self.img, hist)
        self.assertEqual(vc.agy_state("codes", p2)[0], "image_non_lue")
        p3 = vc.parse_agy(json.dumps({"response": "partiel", "status": "ERROR", "conversation_id": "c1"}), self.img, hist)
        self.assertEqual(vc.agy_state("codes", p3)[0], "echec_technique")
        p4 = vc.parse_agy(json.dumps({"response": "", "status": "BLOCKED", "conversation_id": "c1"}), self.img, hist)
        self.assertEqual(vc.agy_state("codes", p4)[0], "refus")


class SampleTest(unittest.TestCase):
    def test_vdiag_rows_is_a1_partition(self):
        md5 = [hashlib.md5(str(i).encode()).hexdigest() for i in range(400)]
        rows = vc.vdiag_rows(md5)
        self.assertEqual(rows, [k for k in range(400) if hashlib.sha256((vc.SALT + md5[k]).encode()).digest()[0] >= 128])

    def test_whole_groups_deterministic(self):
        g = {f"c{i}": list(range(i % 4 + 1)) for i in range(50)}
        a, b = vc.draw_whole_groups(g, 20, 1), vc.draw_whole_groups(g, 20, 1)
        self.assertEqual(a, b)
        n = sum(len(g[x]) for x in a)
        self.assertGreaterEqual(n, 20)
        self.assertLess(n - len(g[a[-1]]), 20)
        with self.assertRaises(ValueError):
            vc.draw_whole_groups({"x": [1]}, 5, 0)


class BootstrapTest(unittest.TestCase):
    def test_reading_and_determinism(self):
        groups = [i // 2 for i in range(40)]
        up = vc.paired_bootstrap({"d": np.full(40, 0.02) + np.linspace(0, 0.01, 40)}, groups, draws=500)
        self.assertEqual(up, vc.paired_bootstrap({"d": np.full(40, 0.02) + np.linspace(0, 0.01, 40)}, groups, draws=500))
        self.assertEqual(vc.reading(up["contrasts"]["d"]), "dépasse T* sur le dev, en accord de catalogue")
        down = vc.paired_bootstrap({"d": -np.full(40, 0.02)}, groups, draws=500)["contrasts"]["d"]
        self.assertEqual(vc.reading(down), "sous T* sur le dev")
        mixed = vc.paired_bootstrap({"d": np.array([0.1, -0.1] * 20)}, list(range(40)), draws=500)["contrasts"]["d"]
        self.assertEqual(vc.reading(mixed), "pas de différence établie")
        self.assertEqual(up["groups"], 20)


class PrepareGuardsTest(unittest.TestCase):
    def test_pins(self):
        prep.check_pins()
        self.assertEqual(sha(ROOT / "scripts/a1_core.py"),
                         sha(Path.home() / "porkyevitch/experiences/2026-10-29-a1/scripts/a1_core.py"))
        self.assertEqual(sha(ROOT / "scripts/pe_common.py"),
                         sha(Path.home() / "porkyevitch/experiences/2026-10-30-petit-eleve/scripts/pe_common.py"))

    def test_never_a_test_shard(self):
        self.assertTrue(prep.shard_path("train-00003-of-00011").endswith("data/train-00003-of-00011.parquet"))
        with self.assertRaises(SystemExit):
            prep.shard_path("test-00000-of-00001")

    def test_dev_items_never_decodes_the_test_member(self):
        dev = {"identities": [], "items": [{"pid": f"p{i}", "truth": ["11H", "86A"], "truth_projected": ["11H"],
                                            "component": i // 3} for i in range(300)]}
        raw = b'{\n "test": "\xff\xfe not utf-8",\n "dev": ' + json.dumps(dev).encode() + b',\n "end": 1\n}'
        f = Path(tempfile.mkdtemp()) / "frozen.json"
        f.write_bytes(raw)
        old = prep.FROZEN_SHA
        prep.FROZEN_SHA = hashlib.sha256(raw).hexdigest()
        try:
            _, items = prep.dev_items(f)
        finally:
            prep.FROZEN_SHA = old
        self.assertEqual(len(items), 300)

    def test_plan_counts(self):
        calls = prep.plan_calls([f"v{i}" for i in range(200)], [f"r{i}" for i in range(301)], [f"r{i}" for i in range(50)],
                                [f"r{i}" for i in range(20)], [f"p{i:03d}" for i in range(26)])
        self.assertEqual({k: len(v) for k, v in calls.items()}, {"S0": 19, "S1": 1104, "R": 40})
        self.assertEqual(len(calls["S1"]) + len(calls["R"]), 1144)
        self.assertEqual({c["system"] for c in calls["S1"] if c["bank"] == "pe_eval"}, {"H", "G"})


def fake_prep(root, n_dev=6):
    """A preparation folder on a 10-code vocabulary: 4 V-diag images (2 groups), n_dev dev images (components of 2),
    2 graph images."""
    (root / "images/icai").mkdir(parents=True)
    (root / "images/rijks").mkdir()
    (root / "images/pe").mkdir()
    g = root / "graphs"
    g.mkdir()
    icai = [{"key": f"v{i}", "image": f"icai/v{i}.jpg", "truth": ["11H"], "group": f"m{i // 2}", "draw_rank": i // 2,
             "B": ["11"], "T_star": ["11H"]} for i in range(4)]
    rijks = [{"key": f"r{i}", "image": f"rijks/r{i}.jpg", "truth": ["25F2"], "group": str(i // 2), "B": ["25"],
              "T_star": ["25F"]} for i in range(n_dev)]
    pe = []
    for i in range(2):
        name = f"p{i:03d}"
        (root / f"images/pe/{name}.jpg").write_bytes(b"pe" + bytes([i]))
        for kind in ("gemini", "s1b"):
            (g / f"{kind}{i}.json").write_text(json.dumps({"objects": [{"id": 0, "name": "x", "box": [0, 0, 100, 100]}],
                                                           "relations": []}))
        pe.append({"name": name, "image": f"{name}.jpg", "gemini_graph": str(g / f"gemini{i}.json"),
                   "gemini_graph_sha256": sha(g / f"gemini{i}.json"), "s1b_graph": str(g / f"s1b{i}.json"),
                   "s1b_graph_sha256": sha(g / f"s1b{i}.json")})
    for x in icai + rijks:
        (root / "images" / x["image"]).write_bytes(x["key"].encode())
    opus, repeat = [x["key"] for x in rijks[:4]], [x["key"] for x in rijks[:2]]
    calls = prep.plan_calls([x["key"] for x in icai], [x["key"] for x in rijks], opus, repeat, [x["name"] for x in pe])
    p = {"preinscription": "PREINSCRIPTION-v2.2.md", "vocabulary": VOCAB, "prompts_sha256": vc.prompts_sha256(VOCAB),
         "code_sha256": {n: sha(ROOT / "scripts" / n) for n in prep.CODE},
         "banks": {"icai_vdiag": icai, "rijks_dev": rijks, "pe_eval": pe},
         "samples": {"opus": opus, "repeat": repeat, "vdiag_groups_order": [["m0", 2], ["m1", 2]]},
         "calls": calls, "image_sha256": {str(q.relative_to(root / "images")): sha(q)
                                          for q in sorted((root / "images").rglob("*")) if q.is_file()}}
    (root / "prep.json").write_text(json.dumps(p))
    return p


def scripted(answers, delay=0.0, probe=None):
    """attempt_fn returning, per call id, the next scripted (state, payload, cost); probe tracks concurrency."""
    seen = {}

    def fn(spec, image, vocab, history):
        k = seen.get(spec["id"], 0)
        seen[spec["id"]] = k + 1
        if probe is not None:
            probe.enter(spec["system"])
        time.sleep(delay)
        if probe is not None:
            probe.leave(spec["system"])
        state, payload, cost = answers(spec, k)
        return {"state": state, "payload": payload, "seconds": 1.0, "timed_out": False, "raw": f"{state}",
                "cost_usd": cost if spec["system"] in vc.CLAUDE_SYSTEMS else None, "usage": {"t": 1}, "image_read": True}
    fn.seen = seen
    return fn


class Probe:
    def __init__(self):
        self.lock, self.now, self.max = threading.Lock(), {"claude": 0, "gemini": 0}, {"claude": 0, "gemini": 0}

    def _k(self, system):
        return "claude" if system in vc.CLAUDE_SYSTEMS else "gemini"

    def enter(self, system):
        with self.lock:
            k = self._k(system)
            self.now[k] += 1
            self.max[k] = max(self.max[k], self.now[k])

    def leave(self, system):
        with self.lock:
            self.now[self._k(system)] -= 1


OK = lambda spec, k: ("reponse", [[0, 0, 100, 100]] if spec["kind"] == "boites" else ["25F"], 0.001)  # noqa: E731


class StageTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        fake_prep(self.root)

    def s0(self, answers=OK):
        return call.stage_run(self.root, "S0", ("H", "G", "O"), attempt_fn=scripted(answers))

    def test_s1_needs_s0_and_runs_in_blocks(self):
        with self.assertRaises(SystemExit):
            call.stage_run(self.root, "S1", ("H", "G", "O"), attempt_fn=scripted(OK))
        self.s0()
        st = call.stage_run(self.root, "S1", ("H", "G", "O"), attempt_fn=scripted(OK))
        self.assertTrue(st["complete"])
        order = [call.S1_BLOCKS.index(json.loads(l)["block"]) for l in (self.root / "journal/S1.jsonl").read_text().splitlines()]
        self.assertEqual(order, sorted(order))  # dev, then Opus, then V-diagnostic, then graphs
        self.assertFalse(json.loads((self.root / "plan_S1.json").read_text())["reduced"])

    def test_retry_once_refusal_final_resume(self):
        self.s0()

        def answers(spec, k):
            if spec["item"] == "r0":
                return ("illisible", None, 0.01) if k == 0 else ("reponse", ["25F2"], 0.01)
            if spec["item"] == "r1":
                return "refus", "x", 0.01
            return OK(spec, k)
        fn = scripted(answers)
        st = call.stage_run(self.root, "S1", ("H", "G", "O"), attempt_fn=fn)
        self.assertTrue(st["complete"])
        self.assertEqual(fn.seen["S1:H:rijks_dev:r0"], 2)
        self.assertEqual(fn.seen["S1:H:rijks_dev:r1"], 1)
        again = scripted(answers)
        call.stage_run(self.root, "S1", ("H", "G", "O"), attempt_fn=again)
        self.assertEqual(again.seen, {})  # resume: nothing repeated

    def test_budget_stops_claude_not_gemini_and_charges_missing_costs(self):
        old = vc.BUDGET_USD
        vc.BUDGET_USD = 0.05
        try:
            st = call.stage_run(self.root, "S0", ("H", "G", "O"),
                                attempt_fn=scripted(lambda s, k: ("echec_technique", None, None) if s["item"] == "r0"
                                                    else ("reponse", ["25F"], 0.02)))
        finally:
            vc.BUDGET_USD = old
        self.assertEqual(st["stopped_by"], "budget Claude")
        recs = [json.loads(l) for l in (self.root / "journal/S0.jsonl").read_text().splitlines()]
        planned_g = sum(c["system"] == "G" for c in json.loads((self.root / "prep.json").read_text())["calls"]["S0"])
        g_final = {r["id"] for r in recs if r["system"] == "G"}
        self.assertEqual(len(g_final), planned_g)  # Gemini goes on
        for r in recs:
            if r["system"] in vc.CLAUDE_SYSTEMS and r["cost_usd"] is None:
                self.assertGreater(r["budget_charge_usd"], 0)  # prudent charge, never free

    def test_at_most_three_claude_calls_in_flight(self):
        probe = Probe()
        call.stage_run(self.root, "S0", ("H", "G", "O"), attempt_fn=scripted(OK, delay=0.05, probe=probe))
        self.assertLessEqual(probe.max["claude"], vc.CLAUDE_IN_FLIGHT)
        self.assertLessEqual(probe.max["gemini"], vc.PARALLEL)

    def test_s1_wall_is_cumulative(self):
        self.s0()
        (self.root / "wall_S1.json").write_text(json.dumps({"seconds": vc.S1_WALL_SECONDS + 1}))
        st = call.stage_run(self.root, "S1", ("H", "G", "O"), attempt_fn=scripted(OK))
        self.assertEqual(st["stopped_by"], "temps réel de S1")
        self.assertFalse(st["complete"])

    def test_extrapolation_reduces_vdiag_only(self):
        self.s0(lambda s, k: ("reponse", ["25F"], 0.5) if s["system"] in vc.CLAUDE_SYSTEMS else OK(s, k))
        sizes = {"n_dev": 6, "n_repeat": 2, "n_graphs": 2, "n_opus": 4}
        s0 = [json.loads(l) for l in (self.root / "journal/S0.jsonl").read_text().splitlines()]
        spent = sum(r["budget_charge_usd"] or 0 for r in s0)
        full = vc.plan_s1(s0, sizes, [("m0", 2), ("m1", 2)], spent, budget=100.0)
        self.assertFalse(full["reduced"])
        cut = vc.plan_s1(s0, sizes, [("m0", 2), ("m1", 2)], spent, budget=spent + 1.2 * 0.5 * (6 + 2 + 2 + 2 + 4) + 0.1)
        self.assertEqual((cut["vdiag_groups_kept"], cut["reduced"], cut["launch"]), (["m0"], True, True))
        none = vc.plan_s1(s0, sizes, [("m0", 2), ("m1", 2)], spent, budget=spent + 1.0)
        self.assertFalse(none["launch"])

    def test_repeat_requires_complete_s1_and_code_frozen(self):
        with self.assertRaises(SystemExit):
            call.stage_run(self.root, "R", ("H",), attempt_fn=scripted(OK))
        p = json.loads((self.root / "prep.json").read_text())
        p["code_sha256"]["vlm_core.py"] = "0" * 64
        (self.root / "prep.json").write_text(json.dumps(p))
        with self.assertRaises(SystemExit):
            call.stage_run(self.root, "S0", ("H",), attempt_fn=scripted(OK))

    def test_measure_after_receipt(self):
        def answers(spec, k):
            if spec["kind"] == "boites":
                return "reponse", [[0, 0, 100, 100], None], 0.01
            if spec["system"] == "G" and spec["item"] == "r0":
                return "refus", "x", None
            return "reponse", ["25F2", "zz", "99Z"], 0.01
        self.s0()
        call.stage_run(self.root, "S1", ("H", "G", "O"), attempt_fn=scripted(answers))
        call.stage_run(self.root, "R", ("H", "G"), attempt_fn=scripted(answers))
        rec = self.root / "recu.json"
        good = {"journals_sha256": {s: sha(self.root / f"journal/{s}.jsonl") for s in ("S1", "R")},
                "status_S1_sha256": sha(self.root / "status_S1.json"), "regards": ["wA:p1", "sonnet"]}
        args = type("A", (), {"prep": str(self.root), "receipt": str(rec)})
        for bad in ({**good, "status_S1_sha256": "bad"}, {**good, "regards": ["wA:p1", "wA:p1"]}):
            rec.write_text(json.dumps(bad))
            with self.assertRaises(SystemExit):
                vm.main(args)
        rec.write_text(json.dumps(good))
        raw = sorted((self.root / "raw").glob("S1_*"))[0]
        keep = raw.read_text()
        raw.write_text("altered")
        with self.assertRaises(SystemExit):
            vm.main(args)
        raw.write_text(keep)
        vm.main(args)
        m = json.loads((self.root / "mesures.json").read_text())
        dev = m["rijks_dev"]
        self.assertAlmostEqual(dev["H_F1"]["H"], 1.0)
        self.assertAlmostEqual(dev["H_F1"]["G"], 5 / 6)  # the refused image counts with an empty set
        self.assertAlmostEqual(dev["H_F1"]["T_star"], a1.hier_f1(["25F2"], ["25F"]))
        self.assertEqual(dev["systems"]["H"]["chains"], {"valide": 6, "hors_V": 6, "invalide": 6})
        self.assertIn("q1_25", m["family_dev_vs_T_star"]["H"])
        self.assertEqual(m["family_dev_vs_T_star"]["H"]["reading"], "dépasse T* sur le dev, en accord de catalogue")
        self.assertEqual(m["icai_vdiag"]["images"], 4)
        self.assertEqual(m["graphs"]["H"]["recall_at_30_vs_gemini"], 1.0)
        self.assertEqual(m["repeatability"]["H"]["jaccard_mean"], 1.0)
        self.assertIn("absent ici", m["costs_and_time"]["fast_model"])


class V22Test(unittest.TestCase):
    def test_bonferroni_bounds_drive_the_reading(self):
        c = {"mean": 0.01, "q1_25": -0.001, "q2_5": 0.001, "q97_5": 0.02, "q98_75": 0.021}
        self.assertEqual(vc.reading(c), "pas de différence établie")  # uncorrected 95 % would have said "dépasse"
        self.assertEqual(vc.reading({**c, "q1_25": 0.0005}), "dépasse T* sur le dev, en accord de catalogue")
        b = vc.paired_bootstrap({"d": np.linspace(-1, 1, 50)}, list(range(50)), draws=2000)["contrasts"]["d"]
        self.assertTrue(b["q1_25"] <= b["q2_5"] <= b["q97_5"] <= b["q98_75"])

    def test_errored_read_is_not_a_read(self):
        img = Path(tempfile.mkdtemp()) / "a.jpg"
        img.write_bytes(b"x")
        ev = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Read",
                                                             "input": {"file_path": str(img)}}]}},
              {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True}]}},
              {"type": "result", "result": '{"codes": ["11H"]}', "total_cost_usd": 0.01}]
        p = vc.parse_claude_stream("\n".join(json.dumps(e) for e in ev), img)
        self.assertEqual((p["image_read"], p["read_errors"]), (False, 1))
        self.assertEqual(vc.claude_state("codes", p)[0], "image_non_lue")
        ev[1]["message"]["content"][0]["is_error"] = False
        self.assertTrue(vc.parse_claude_stream("\n".join(json.dumps(e) for e in ev), img)["image_read"])

    def test_prudent_charge(self):
        self.assertEqual(vc.budget_charge(0.03, []), 0.03)
        self.assertEqual(vc.budget_charge(None, [0.01, 0.04]), 0.08)
        self.assertEqual(vc.budget_charge(None, []), vc.UNKNOWN_CHARGE_USD)

    def test_claude_isolation(self):
        d = Path(tempfile.mkdtemp())
        missing = d / "no-CLAUDE.md"
        self.assertTrue(vc.claude_isolation_ok(d, home=Path.home(), user_md=missing))
        self.assertFalse(vc.claude_isolation_ok(Path.home() / "x", home=Path.home(), user_md=missing))
        present = d / "CLAUDE.md"
        present.write_text("x")
        self.assertFalse(vc.claude_isolation_ok(d, home=Path.home(), user_md=present))
        cmd = call.claude_command("claude-haiku-5-5", "p")
        self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "")
        self.assertNotIn("--bare", cmd)

    def test_plan_order(self):
        calls = prep.plan_calls(["v1", "v0"], ["r0", "r1"], ["r0"], ["r1"], ["p000"])
        blocks = [c["block"] for c in calls["S1"]]
        self.assertEqual(blocks, sorted(blocks, key=call.S1_BLOCKS.index))
        self.assertEqual([c["item"] for c in calls["S1"] if c["block"] == "vdiag" and c["system"] == "H"], ["v1", "v0"])


class FakeExecutableTest(unittest.TestCase):
    """one_attempt end to end with fake `claude` and `agy` on PATH (no model, no network)."""
    def setUp(self):
        self.bin = Path(tempfile.mkdtemp())
        self.hist = Path(tempfile.mkdtemp())
        self.img = Path(tempfile.mkdtemp()) / "a.jpg"
        self.img.write_bytes(b"jpg")
        claude = f"""#!{sys.executable}
import json, os, sys
img = [l for l in sys.argv[2].splitlines() if l.startswith("Image : ")][0][8:]
ev = [{{"type": "assistant", "message": {{"stop_reason": "tool_use", "content": [{{"type": "tool_use", "id": "t1", "name": "Read", "input": {{"file_path": img}}}}]}}}},
      {{"type": "user", "message": {{"content": [{{"type": "tool_result", "tool_use_id": "t1", "is_error": False}}]}}}},
      {{"type": "result", "result": "{{\\"codes\\": [\\"11H\\"]}}", "total_cost_usd": 0.003, "usage": {{}}, "duration_ms": 5}}]
print("\\n".join(json.dumps(e) for e in ev))
"""
        agy = f"""#!{sys.executable}
import json, os, sqlite3, sys
cid = "conv1"
img = os.path.join(os.getcwd(), sys.argv[2].split("@")[1].split()[0])
with sqlite3.connect(os.path.join({str(self.hist)!r}, cid + ".db")) as con:
    con.execute("CREATE TABLE IF NOT EXISTS steps (step_payload BLOB)")
    con.execute("INSERT INTO steps VALUES (?)", (json.dumps({{"view_file": {{"AbsolutePath": img}}}}, separators=(",", ":")).encode(),))
print(json.dumps({{"response": "{{\\"codes\\": [\\"2\\"]}}", "status": "SUCCESS", "usage": {{"t": 3}}, "conversation_id": cid}}))
"""
        for name, body in (("claude", claude), ("agy", agy)):
            (self.bin / name).write_text(body)
            (self.bin / name).chmod((self.bin / name).stat().st_mode | stat.S_IEXEC)
        self.old = os.environ["PATH"]
        os.environ["PATH"] = f"{self.bin}:{self.old}"

    def tearDown(self):
        os.environ["PATH"] = self.old

    def test_claude_and_agy(self):
        r = call.one_attempt({"system": "H", "kind": "codes"}, self.img, VOCAB, self.hist)
        self.assertEqual((r["state"], r["payload"], r["cost_usd"], r["image_read"]), ("reponse", ["11H"], 0.003, True))
        g = call.one_attempt({"system": "G", "kind": "codes"}, self.img, VOCAB, self.hist)
        self.assertEqual((g["state"], g["payload"], g["image_read"]), ("reponse", ["2"], True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
