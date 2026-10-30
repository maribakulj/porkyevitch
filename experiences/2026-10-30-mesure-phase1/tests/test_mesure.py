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


class EndToEndTest(unittest.TestCase):
    """Fake seal with patched constants: the dev stage must work with unreadable test files, the test stage needs a
    receipt, writes verdicts before measures and opens TK-niv only when TK and T-niv are retained."""

    def build(self, tk_good):
        rng = np.random.default_rng(1)
        root = Path(tempfile.mkdtemp())
        codes = ["11H", "11H(JEROME)", "25F", "25F23", "31A", "7", "71A"]
        icai_truth = [[str(c) for c in rng.choice(codes, 2, replace=False)] for _ in range(788)]
        icai_truth[5] = ["86(x)"]  # one image with an empty projected truth
        md5 = [f"{i:032x}" for i in range(788)]
        def comp_items(n, comps):
            return [{"pid": f"p{i:04d}", "component": int(i % comps), "support": ["print", "painting", "drawing"][i % 3],
                     "truth": [str(c) for c in rng.choice(codes, 2, replace=False)], "iiif": "https://x/full/!800,800/0/default.jpg",
                     "image_sha256": "0" * 64, "width": 10, "height": 10} for i in range(n)]
        dev, test = comp_items(30, 12), comp_items(60, 25)
        for it in dev + test:
            it["truth_projected"] = list(dict.fromkeys(mm.drop86(it["truth"])))
        frozen_sha = write(root / "frozen.json", {"dev": {"items": dev, "components": []}, "test": {"items": test, "components": []}})
        def noisy(truths, good):
            out = []
            for t in truths:
                p = list(mm.drop86(t)) if rng.random() < good else [str(rng.choice(codes))]
                out.append(p)
            return out
        quality = {"T0": 0.3, "T_star": 0.5, "TK": 0.9 if tk_good else 0.2, "T-niv": 0.9 if tk_good else 0.5,
                   "TK-niv": 0.95, "T-H": 0.4, "T-Z": 0.5, "T-D": 0.5}
        seal, files = root / "seal", {}
        for s, q in quality.items():
            for bank, rows in (("icai_test", [{"index": j, "md5": md5[j], "codes": c} for j, c in enumerate(noisy(icai_truth, q))]),
                               ("rijks_dev", [{"pid": it["pid"], "codes": c} for it, c in zip(dev, noisy([i["truth"] for i in dev], q))]),
                               ("rijks_test", [{"pid": it["pid"], "codes": c} for it, c in zip(test, noisy([i["truth"] for i in test], q))])):
                name = f"predictions__{bank}__{s}.json"
                if bank != "rijks_dev":
                    (seal).mkdir(parents=True, exist_ok=True)
                    content = json.dumps({"bank": bank, "system": s, "rows": rows})
                    (seal / name).write_text(content)
                    files[name] = {"sha256": hashlib.sha256(content.encode()).hexdigest(), "rows": len(rows)}
                else:
                    files[name] = {"sha256": write(seal / name, {"bank": bank, "system": s, "rows": rows}), "rows": len(rows)}
        self.test_names = [n for n in files if "rijks_dev" not in n]
        seal_sha = write(seal / "MANIFEST.json", {"predictions_frozen": True, "mode": "freeze", "technical_pass": True,
                         "systems": mp.SYSTEMS, "family": [list(x) for x in mm.FAMILY], "frozen_bench_sha256": frozen_sha,
                         "vocabulary_sha256": "v", "files": files})
        enc = root / "enc"
        (enc / "feats").mkdir(parents=True)
        lab_sha = write(enc / "grid" / f"{mp.TEST}.json", {"labels": icai_truth})
        np.savez(enc / "feats" / f"{mp.TEST}.npz", md5=np.array(md5))
        vec_sha = hashlib.sha256((enc / "feats" / f"{mp.TEST}.npz").read_bytes()).hexdigest()
        entrees_sha = write(root / "entrees.json", {"frozen_sha256": frozen_sha, "architecture_protocol_sha256": mp.PROTOCOL_SHA256,
                            "shards": {mp.TEST: {"grid_json_sha256": lab_sha, "vec_sha256": vec_sha}}})
        keep = [g for g in (list(dict.fromkeys(mm.drop86(t))) for t in icai_truth) if g]
        t0 = json.loads((seal / "predictions__icai_test__T0.json").read_text())["rows"]
        t0_mean = np.mean([mm.hier_f1(g, r["codes"]) for g, r in zip((list(dict.fromkeys(mm.drop86(t))) for t in icai_truth), t0) if g])
        patch = {"SEAL_SHA256": seal_sha, "FROZEN_SHA256": frozen_sha, "VOCABULARY_SHA256": "v", "ENTREES_SHA256": entrees_sha,
                 "ICAI_T0_HIST": float(t0_mean)}
        return root, patch, len(keep)

    def run_stage(self, root, patch, stage, out, **extra):
        old = {k: getattr(mp, k) for k in patch}
        old_fetch, old_dict, old_counts = mp.fetch_image, mp.dictionary, mp.training_counts
        try:
            for k, v in patch.items():
                setattr(mp, k, v)
            mp.fetch_image = lambda it, folder: "img.jpg"
            mp.dictionary = lambda root: {}
            mp.training_counts = lambda enc, entrees: ({"11H": 10, "25F": 50, "7": 200}, ["11H", "25F", "7"])
            a = type("A", (), dict(stage=stage, seal=str(root / "seal"), frozen=str(root / "frozen.json"),
                                   inputs=str(root / "entrees.json"), encoder=str(root / "enc"), iconclass=".",
                                   out=str(out), **extra))
            mp.main(a)
        finally:
            for k, v in old.items():
                setattr(mp, k, v)
            mp.fetch_image, mp.dictionary, mp.training_counts = old_fetch, old_dict, old_counts

    def test_dev_never_parses_test_files_and_test_needs_receipt(self):
        root, patch, kept = self.build(tk_good=True)
        # Make every test prediction file unparsable while keeping its sha in the manifest: dev must not care.
        manifest = json.loads((root / "seal" / "MANIFEST.json").read_text())
        backup = {}
        for n in self.test_names:
            backup[n] = (root / "seal" / n).read_bytes()
            (root / "seal" / n).write_bytes(b"\x00not json")
            manifest["files"][n]["sha256"] = hashlib.sha256(b"\x00not json").hexdigest()
        patch["SEAL_SHA256"] = write(root / "seal" / "MANIFEST.json", manifest)
        self.run_stage(root, patch, "dev", root / "dev")
        dev = json.loads((root / "dev" / "dev.json").read_text())
        self.assertEqual(len(dev["plates"]), 7)
        self.assertTrue(dev["plates"]["TK-niv-T_star"]["conditional"])
        self.assertTrue(all(len(v["images"]) == 12 for v in dev["plates"].values()))
        # restore the real test files and manifest
        for n, b in backup.items():
            (root / "seal" / n).write_bytes(b)
            manifest["files"][n]["sha256"] = hashlib.sha256(b).hexdigest()
        patch["SEAL_SHA256"] = write(root / "seal" / "MANIFEST.json", manifest)
        bad = write(root / "receipt_bad.json", {"stage": "planches_dev_regardees", "viewer": "x", "viewed_at": "t",
                                                "dev_manifest_sha256": "0"})
        with self.assertRaises(RuntimeError):
            self.run_stage(root, patch, "test", root / "t1", dev=str(root / "dev"), receipt=str(root / "receipt_bad.json"))
        good = hashlib.sha256((root / "dev" / "MANIFEST_DEV.json").read_bytes()).hexdigest()
        write(root / "receipt.json", {"stage": "planches_dev_regardees", "viewer": "wA:p1", "viewed_at": "t",
                                      "dev_manifest_sha256": good})
        self.run_stage(root, patch, "test", root / "t2", dev=str(root / "dev"), receipt=str(root / "receipt.json"))
        v = json.loads((root / "t2" / "verdicts.json").read_text())
        self.assertEqual(v["denominators"]["icai_test"], kept)
        self.assertEqual(v["denominators"]["icai_excluded_empty_projected_truth"], 1)
        self.assertTrue(v["verdicts"]["TK"]["retained"] and v["verdicts"]["T-niv"]["retained"])
        self.assertIn("delta_icai", v["verdicts"]["TK-niv"])  # activated
        self.assertFalse(v["verdicts"]["T-H"]["retained"])
        self.assertTrue((root / "t2" / "mesures_test.json").exists())

    def test_tk_niv_not_opened_when_condition_fails(self):
        root, patch, _ = self.build(tk_good=False)
        self.run_stage(root, patch, "dev", root / "dev")
        good = hashlib.sha256((root / "dev" / "MANIFEST_DEV.json").read_bytes()).hexdigest()
        write(root / "receipt.json", {"stage": "planches_dev_regardees", "viewer": "wA:p1", "viewed_at": "t",
                                      "dev_manifest_sha256": good})
        self.run_stage(root, patch, "test", root / "t", dev=str(root / "dev"), receipt=str(root / "receipt.json"))
        v = json.loads((root / "t" / "verdicts.json").read_text())
        self.assertFalse(v["verdicts"]["TK-niv"]["executed"])
        m = json.loads((root / "t" / "mesures_test.json").read_text())
        self.assertNotIn("TK-niv", m["icai_test"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
