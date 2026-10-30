"""Synthetic tests of the phase 1 measure script. No real truth, prediction or image. Run: python3 -I tests/test_mesure.py"""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mesure_metrics as mm  # noqa: E402
import mesure_phase1 as mp  # noqa: E402

GEL = Path.home() / "porkyevitch/experiences/2026-10-29-gel-phase1/scripts/gel_common.py"
E3 = Path.home() / "porkyevitch/experiences/2026-10-25-iconclass-architecture/scripts/e3_spatial.py"
CODES = ["1", "11", "11H", "11H(JEROME)", "11H(JEROME)3", "25F23(LION)", "25F23(LION)(+12)", "31A:25F", "86(Amor)",
         "73D82", "7", "0:49D3", "bad code", "11H(PAUL)"]


def extract(path, names):
    tree = ast.parse(path.read_text())
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names) or
            (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in {"PART", "TOKEN", "_anc"} for t in n.targets))]
    ns = {"re": re}
    exec(compile(ast.Module(keep, []), str(path), "exec"), ns)
    return ns


class MetricsTest(unittest.TestCase):
    @unittest.skipUnless(GEL.is_file() and E3.is_file(), "historical scripts absent")
    def test_parity_with_the_freeze_and_e3(self):
        g, e = extract(GEL, {"ancestors"}), extract(E3, {"ancestors", "hier_f1", "drop86"})
        rng = np.random.default_rng(0)
        for c in CODES:
            self.assertEqual(mm.ancestors(c), set(g["ancestors"](c)))
        for _ in range(300):
            a, b = list(rng.choice(CODES, rng.integers(0, 4))), list(rng.choice(CODES, rng.integers(0, 4)))
            self.assertEqual(mm.hier_f1(a, b), e["hier_f1"](a, b))
            self.assertEqual(mm.drop86(a), e["drop86"](a))

    def test_exact_is_pooled_micro_f1(self):
        r = mm.exact([["a", "b"], ["c"]], [["a"], ["c", "d"]])
        self.assertAlmostEqual(r["precision"], 2 / 3)
        self.assertAlmostEqual(r["recall"], 2 / 3)
        self.assertAlmostEqual(r["f1"], 2 / 3)

    def test_component_bootstrap_is_ratio_over_drawn_images(self):
        f_b, f_r = [1.0, 0.0, 0.5, 0.5, 1.0], [0.0, 0.0, 0.5, 0.0, 0.0]
        unit = np.array([0, 0, 1, 2, 2])
        counts = mm.unit_draws(3, draws=50, seed=0)
        d = mm.bootstrap_delta(f_b, f_r, unit, counts)
        for k in range(50):
            imgs = [i for u in range(3) for _ in range(counts[k, u]) for i in np.nonzero(unit == u)[0]]
            self.assertAlmostEqual(d[k], np.mean([f_b[i] for i in imgs]) - np.mean([f_r[i] for i in imgs]))
        self.assertTrue(np.array_equal(counts, mm.unit_draws(3, draws=50, seed=0)))  # same draws for every system

    def test_level_and_lower_bound(self):
        self.assertAlmostEqual(mm.LEVEL, 1 - 0.05 / 7)
        s = mm.summarise(0.1, np.arange(10000) / 10000)
        self.assertAlmostEqual(s["lower_one_sided_99_29"], np.quantile(np.arange(10000) / 10000, 0.05 / 7))

    def test_retention_rule_strict_on_both_banks(self):
        self.assertTrue(mm.retained(0.001, -0.009))
        self.assertFalse(mm.retained(0.0, 0.5))
        self.assertFalse(mm.retained(0.2, -0.01))
        self.assertFalse(mm.retained(0.2, -0.02))

    def test_tk_niv_activation(self):
        self.assertTrue(mm.tk_niv_active({"TK": {"retained": True}, "T-niv": {"retained": True}}))
        self.assertFalse(mm.tk_niv_active({"TK": {"retained": True}, "T-niv": {"retained": False}}))

    def test_planche_order_and_ties(self):
        ids = ["c", "a", "b", "d"]
        self.assertEqual(mm.planche(ids, [0.5, 0.0, 0.0, 0.1], [0.0, 0.5, 0.0, 0.1], n=3), ["a", "c", "b"])

    def test_depth_f1_and_recall(self):
        g, p = [["11H(JEROME)"]], [["11H"]]
        out = mm.depth_f1(g, p)
        self.assertEqual(out["1-2"]["f1"], 1.0)                 # 1, 11
        self.assertEqual(out["3-4"]["f1"], 2 * 1 / (2 + 1))     # truth {11H, 11H(JEROME)}, pred {11H}
        self.assertIsNone(out["5+"]["f1"])
        self.assertEqual(mm.ancestor_recall_by_tranche(g, p)["3-4"]["recall"], 0.5)

    def test_rare_recall_uses_prediction_ancestors(self):
        r = mm.rare_recall([["11H", "7"]], [["11H(JEROME)"]], rare={"11H", "7"})
        self.assertEqual((r["recall"], r["pairs"]), (0.5, 2))

    def test_frequency_and_coverage(self):
        out = mm.f1_by_frequency([["a", "b"]], [["a", "c"]], {"a": 10, "b": 50, "c": 500})
        self.assertEqual((out["5-20"]["tp"], out["21-100"]["fn"], out[">100"]["fp"]), (1, 1, 1))
        cov = mm.coverage([["a", "z"], ["a"]], ["a"])
        self.assertEqual((cov["per_image_mean"], cov["distinct_outside"]), (0.25, 1))


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


class EndToEndTest(unittest.TestCase):
    """Fake seal in the REAL schema of the freeze (gel_predictions.py / gel_data.py), constants patched."""

    def build(self, tk_good=True):
        rng = np.random.default_rng(1)
        root = Path(tempfile.mkdtemp())
        codes = ["11H", "11H(JEROME)", "25F", "25F23", "31A", "7", "71A"]
        icai_truth = [[str(c) for c in rng.choice(codes, 2, replace=False)] for _ in range(788)]
        icai_truth[5] = ["86(x)"]  # one image with an empty projected truth
        md5 = [f"{i:032x}" for i in range(788)]

        def items(n, comps, tag):
            out = []
            for i in range(n):
                t = [str(c) for c in rng.choice(codes, 2, replace=False)]
                out.append({"pid": f"https://id.rijksmuseum.nl/{tag}{i:04d}", "component": int(i % comps),
                            "support": ["print", "painting", "drawing"][i % 3], "truth": t,
                            "truth_projected": list(dict.fromkeys(mm.drop86(t))),
                            "iiif": "https://iiif.micr.io/x/full/!800,800/0/default.jpg",
                            "image_sha256": sha_bytes(f"{tag}{i}".encode()), "width": 10, "height": 10})
            return out
        dev, test = items(30, 12, "d"), items(60, 25, "t")
        self.frozen_sha = write(root / "frozen.json", {"dev": {"items": dev, "components": []},
                                                       "test": {"items": test, "components": []}})

        def noisy(truths, good):
            return [list(mm.drop86(t)) if rng.random() < good else [str(rng.choice(codes))] for t in truths]
        quality = {"T0": 0.3, "T_star": 0.5, "TK": 0.9 if tk_good else 0.2, "T-niv": 0.9 if tk_good else 0.5,
                   "TK-niv": 0.95, "T-H": 0.4, "T-Z": 0.5, "T-D": 0.5}
        seal, files = root / "seal", {}
        seal.mkdir()
        rijks_ids = lambda its: [{"index": j, "id": it["pid"], "image_sha256": it["image_sha256"]} for j, it in enumerate(its)]
        icai_ids = [{"index": j, "shard": mp.TEST, "row": j, "md5": m} for j, m in enumerate(md5)]
        for s, q in quality.items():
            for bank, ids, truths in (("icai_test", icai_ids, icai_truth), ("rijks_dev", rijks_ids(dev), [i["truth"] for i in dev]),
                                      ("rijks_test", rijks_ids(test), [i["truth"] for i in test])):
                rows = [{**ident, "codes": c} for ident, c in zip(ids, noisy(truths, q))]
                name = f"predictions__{bank}__{s}.json"
                files[name] = {"sha256": write(seal / name, {"bank": bank, "system": s, "rows": rows}), "rows": len(rows),
                               "bank": bank, "system": s, "identity_order_sha256": mp.object_sha(ids)}
        self.files = files
        enc = root / "enc"
        (enc / "feats").mkdir(parents=True)
        lab_sha = write(enc / "grid" / f"{mp.TEST}.json", {"labels": icai_truth})
        np.savez(enc / "feats" / f"{mp.TEST}.npz", md5=np.array(md5))
        vec_sha = hashlib.sha256((enc / "feats" / f"{mp.TEST}.npz").read_bytes()).hexdigest()
        entrees_sha = write(root / "entrees.json", {"frozen_sha256": self.frozen_sha,
                            "architecture_protocol_sha256": mp.PROTOCOL_SHA256,
                            "shards": {mp.TEST: {"grid_json_sha256": lab_sha, "vec_sha256": vec_sha}}})
        t0 = json.loads((seal / "predictions__icai_test__T0.json").read_text())["rows"]
        proj = [list(dict.fromkeys(mm.drop86(t))) for t in icai_truth]
        t0_mean = np.mean([mm.hier_f1(g, r["codes"]) for g, r in zip(proj, t0) if g])
        self.root = root
        self.patch = {"FROZEN_SHA256": self.frozen_sha, "VOCABULARY_SHA256": "v", "ENTREES_SHA256": entrees_sha,
                      "ICAI_T0_HIST": float(t0_mean)}
        self.reseal()
        return sum(1 for g in proj if g)

    def reseal(self):
        self.patch["SEAL_SHA256"] = write(self.root / "seal" / "MANIFEST.json", {
            "predictions_frozen": True, "mode": "freeze", "technical_pass": True, "systems": mp.SYSTEMS,
            "family": [list(x) for x in mm.FAMILY], "frozen_bench_sha256": self.frozen_sha,
            "vocabulary_sha256": "v", "files": self.files})

    def run_stage(self, stage, out, **extra):
        old = {k: getattr(mp, k) for k in self.patch}
        old_fetch, old_dict, old_counts = mp.fetch_image, mp.dictionary, mp.training_counts

        def fake_fetch(it, folder):
            name = hashlib.sha256(it["pid"].encode()).hexdigest()[:16] + ".jpg"
            (folder / name).write_bytes(b"jpg")
            return name
        try:
            for k, v in self.patch.items():
                setattr(mp, k, v)
            mp.fetch_image, mp.dictionary = fake_fetch, (lambda root: {})
            mp.training_counts = lambda enc, entrees: ({"11H": 10, "25F": 50, "7": 200}, ["11H", "25F", "7"])
            a = type("A", (), dict(stage=stage, seal=str(self.root / "seal"), frozen=str(self.root / "frozen.json"),
                                   inputs=str(self.root / "entrees.json"), encoder=str(self.root / "enc"),
                                   iconclass=".", out=str(out), **extra))
            mp.main(a)
        finally:
            for k, v in old.items():
                setattr(mp, k, v)
            mp.fetch_image, mp.dictionary, mp.training_counts = old_fetch, old_dict, old_counts

    def receipt(self, dev, name="recu.json", looks=("wA:p1", "Grok p2")):
        m = json.loads((dev / "MANIFEST_DEV.json").read_text())
        return str(self.root / name), write(self.root / name, {
            "stage": "planches_dev_regardees",
            "dev_manifest_sha256": sha_bytes((dev / "MANIFEST_DEV.json").read_bytes()),
            "regards": [{"viewer": v, "viewed_at": "t"} for v in looks],
            "plates_html_sha256": {c: m["files"][p["html"]] for c, p in m["plates"].items()}})

    def refused(self, dev, receipt, code):
        with self.assertRaises(RuntimeError) as e:
            self.run_stage("test", Path(tempfile.mkdtemp()) / "t", dev=str(dev), receipt=receipt)
        self.assertEqual(str(e.exception), code)

    def test_dev_ignores_unparsable_test_predictions(self):
        self.build()
        for n in [n for n in self.files if "rijks_dev" not in n]:
            (self.root / "seal" / n).write_bytes(b"\x00not json")
            self.files[n]["sha256"] = sha_bytes(b"\x00not json")
        self.reseal()
        self.run_stage("dev", self.root / "dev")
        dev = json.loads((self.root / "dev" / "dev.json").read_text())
        self.assertEqual(len(dev["plates"]), 7)
        self.assertTrue(dev["plates"]["TK-niv-T_star"]["conditional"])
        self.assertTrue(all(len(v["images"]) == 12 for v in dev["plates"].values()))

    def test_wrong_rijks_order_is_refused(self):
        self.build()
        name = "predictions__rijks_dev__T0.json"
        obj = json.loads((self.root / "seal" / name).read_text())
        obj["rows"][0], obj["rows"][1] = obj["rows"][1], obj["rows"][0]
        self.files[name]["sha256"] = write(self.root / "seal" / name, obj)
        self.reseal()
        with self.assertRaises(RuntimeError) as e:
            self.run_stage("dev", self.root / "dev")
        self.assertEqual(str(e.exception), "rijks_order")

    def test_full_run_and_every_refusal_before_test_truths(self):
        kept = self.build(tk_good=True)
        dev = self.root / "dev"
        self.run_stage("dev", dev)
        good, _ = self.receipt(dev)
        # refusals, each before any test truth is read
        (self.root / "empty").mkdir()
        write(self.root / "empty" / "MANIFEST_DEV.json", {})
        self.refused(self.root / "empty", good, "dev_manifest_identity")
        self.refused(dev, self.receipt(dev, "r1.json", looks=("wA:p1",))[0], "both_looks_required")
        m = json.loads((dev / "MANIFEST_DEV.json").read_text())
        plate = dev / m["plates"]["TK-T_star"]["html"]
        original = plate.read_bytes()
        plate.write_bytes(b"changed")
        self.refused(dev, good, "dev_file_missing_or_changed")
        plate.write_bytes(original)
        img = dev / m["plates"]["T-H-T_star"]["image_files"][0]
        img_bytes = img.read_bytes()
        img.unlink()
        self.refused(dev, good, "dev_file_missing_or_changed")
        img.write_bytes(img_bytes)
        broken = json.loads(json.dumps(m))
        del broken["plates"]["T-D-T_star"]
        (self.root / "dev2").mkdir()
        for rel in m["files"]:
            (self.root / "dev2" / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / "dev2" / rel).write_bytes((dev / rel).read_bytes())
        write(self.root / "dev2" / "MANIFEST_DEV.json", broken)
        self.refused(self.root / "dev2", self.receipt(self.root / "dev2", "r2.json")[0], "dev_plates_incomplete")
        self.refused(dev, self.receipt(self.root / "dev2", "r3.json")[0], "plates_not_viewed")  # receipt of another dev
        # the real run
        self.run_stage("test", self.root / "t2", dev=str(dev), receipt=good)
        v = json.loads((self.root / "t2" / "verdicts.json").read_text())
        self.assertEqual(v["denominators"]["icai_test"], kept)
        self.assertEqual(v["denominators"]["icai_excluded_empty_projected_truth"], 1)
        self.assertTrue(v["verdicts"]["TK"]["retained"] and v["verdicts"]["T-niv"]["retained"])
        self.assertIn("delta_icai", v["verdicts"]["TK-niv"])
        self.assertFalse(v["verdicts"]["T-H"]["retained"])
        self.assertTrue((self.root / "t2" / "mesures_test.json").exists())

    def test_dev_manifest_of_another_seal_is_refused(self):
        self.build()
        dev = self.root / "dev"
        self.run_stage("dev", dev)
        m = json.loads((dev / "MANIFEST_DEV.json").read_text())
        m["seal_sha256"] = "0" * 64
        write(dev / "MANIFEST_DEV.json", m)
        self.refused(dev, self.receipt(dev)[0], "dev_manifest_identity")

    def test_tk_niv_not_opened_when_condition_fails(self):
        self.build(tk_good=False)
        dev = self.root / "dev"
        self.run_stage("dev", dev)
        self.run_stage("test", self.root / "t", dev=str(dev), receipt=self.receipt(dev)[0])
        v = json.loads((self.root / "t" / "verdicts.json").read_text())
        self.assertFalse(v["verdicts"]["TK-niv"]["executed"])
        self.assertNotIn("TK-niv", json.loads((self.root / "t" / "mesures_test.json").read_text())["icai_test"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
