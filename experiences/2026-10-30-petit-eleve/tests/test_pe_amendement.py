"""Amendment of 30/10 before the full run (Codex p4 points 1-4, D8): padding offsets, sealed predictions and the plate
receipt, timing under no_grad, revisions pinned. CPU, synthetic only. Run: python -I tests/test_pe_amendement.py"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import warnings

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pe_kaggle as pk  # noqa: E402

SRC = (Path(__file__).resolve().parents[1] / "scripts" / "pe_kaggle.py").read_text()


def fake_preds(n, seed):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        boxes = [[float(x) for x in sorted(rng.uniform(0, 1000, 2))] * 2 for _ in range(pk.NQ)]
        boxes = [[b[0], b[1], b[0] + 50, b[1] + 60] for b in boxes]
        out.append({"boxes": boxes, "score": rng.uniform(0, 1, pk.NQ).tolist(), "cat": rng.integers(0, 9, pk.NQ).tolist(),
                    "cat_score": rng.uniform(0, 1, pk.NQ).tolist(), "pairs": pk.query_pairs(),
                    "rel": rng.uniform(0, 1, (pk.NQ * (pk.NQ - 1), pk.NREL)).astype(np.float32)})
    return out


class PaddingTest(unittest.TestCase):
    def test_odd_difference_uses_the_integer_padding(self):
        # 480 x 641: the image sits at x = 80 in its 641-pixel square (paste uses //2), not at 80.5
        self.assertEqual(pk.pad_offsets(480, 641), (80, 0))
        self.assertEqual(pk.pad_offsets(641, 480), (0, 80))
        self.assertAlmostEqual(pk.square_box([0, 0, 1000, 1000], 480, 641)[0], 80 / 641 * 1000, places=12)
        self.assertAlmostEqual(pk.square_box([0, 0, 1000, 1000], 641, 480)[1], 80 / 641 * 1000, places=12)
        for w, h in ((480, 641), (641, 480), (640, 480)):
            b = [123.0, 45.0, 678.0, 910.0]
            back = pk.unsquare_box(pk.square_box(b, w, h), w, h)
            self.assertLess(max(abs(u - v) for u, v in zip(back, b)), 1e-9)
        self.assertIn("c.paste(im, pad_offsets(im.width, im.height))", SRC)

    def test_square_pixels_match_square_box(self):
        from PIL import Image
        im = Image.new("RGB", (480, 641), (255, 255, 255))
        sq = pk.Encoder.square(im).resize((641, 641), Image.NEAREST)  # back to the square side for a pixel check
        row = np.asarray(sq)[320, :, 0]
        first_white = int(np.argmax(row > 200))
        expected = pk.square_box([0, 0, 1000, 1000], 480, 641)[0] / 1000 * 641
        self.assertLessEqual(abs(first_white - expected), 1.0)


PLANCHE = [f"p{k:03d}" for k in range(12)]
BOTH = [{"viewer": "wA:p1", "viewed_at": "2026-10-30T10:00:00Z"}, {"viewer": "Grok p2", "viewed_at": "2026-10-30T10:05:00Z"}]


class SealTest(unittest.TestCase):
    """B1 (Codex p4): the reader requires exactly the files the measures consume, the twelve plate names in order."""

    def build(self, florence=True, skip=(), extra=False, planche=PLANCHE):
        root = Path(tempfile.mkdtemp())
        (root / pk.PRED_DIR).mkdir()
        (root / "planche").mkdir()
        for n in PLANCHE:
            (root / "planche" / f"{n}.jpg").write_bytes(b"jpg " + n.encode())
        self.preds = fake_preds(3, 0)
        for key in pk.STUDENT_KEYS:
            pk.save_student(root, key, self.preds)
        for name in ("a_priori", "owlv2", "yoloe") + (("florence2",) if florence else ()):
            pk.write_json(root / pk.PRED_DIR / f"{name}.json", [])
        pk.write_json(root / "timing.json", {"D": 1.0})
        pk.write_json(root / "run.json", {"measures": None, "witnesses": {"florence2": None if florence else "unavailable: x"}})
        for rel in skip:
            (root / rel).unlink()
        if extra:
            (root / "planche" / "intrus.jpg").write_bytes(b"x")
        digest = pk.seal(root, {"stage": "predictions_sealed", "planche": planche, "script_sha256": {},
                                "listes_sha256": pk.LISTES_SHA256})
        return root, digest

    def receipt(self, root, digest, regards=BOTH):
        path = root / "recu.json"
        path.write_text(json.dumps({"stage": "planche_petit_eleve_regardee", "manifest_sha256": digest, "regards": regards}))
        return path

    def check(self, root, digest, **kw):
        return pk.check_receipt(root, self.receipt(root, digest, **kw), {"planche": PLANCHE})

    def test_complete_seal_and_both_looks(self):
        root, digest = self.build()
        manifest, _ = self.check(root, digest)
        self.assertTrue(manifest["florence_available"])
        with self.assertRaisesRegex(RuntimeError, "both_looks_required"):
            self.check(root, digest, regards=BOTH[:1])
        with self.assertRaisesRegex(RuntimeError, "plate_not_viewed"):
            self.check(root, "0" * 64)
        (root / "planche" / "p001.jpg").write_bytes(b"changed")
        with self.assertRaisesRegex(RuntimeError, "sealed_file_missing_or_changed"):
            self.check(root, digest)

    def test_florence_unavailable_must_not_be_sealed_nor_read(self):
        root, digest = self.build(florence=False)
        manifest, _ = self.check(root, digest)
        self.assertFalse(manifest["florence_available"])

    def test_codex_case_seal_without_the_consumed_files_is_refused(self):
        # Codex p4 reproduction: twelve plates sealed, but run/timing/predictions absent from the manifest
        root, digest = self.build(skip=["timing.json", f"{pk.PRED_DIR}/owlv2.json",
                                        f"{pk.PRED_DIR}/student_28x28_seed0_rel.npy"])
        with self.assertRaisesRegex(RuntimeError, "seal_incomplete_or_extra"):
            self.check(root, digest)
        root, digest = self.build(skip=["run.json"])
        with self.assertRaisesRegex(RuntimeError, "seal_incomplete"):
            self.check(root, digest)

    def test_empty_extra_or_wrong_plate_list_refused(self):
        root, digest = self.build(extra=True)
        with self.assertRaisesRegex(RuntimeError, "seal_incomplete_or_extra"):
            self.check(root, digest)
        root, digest = self.build(planche=[])
        with self.assertRaisesRegex(RuntimeError, "plate_names"):
            self.check(root, digest)
        root, digest = self.build(planche=list(reversed(PLANCHE)))
        with self.assertRaisesRegex(RuntimeError, "plate_names"):
            self.check(root, digest)
        root, _ = self.build()
        (root / "MANIFEST_PREDICTIONS.json").write_text(json.dumps({"stage": "predictions_sealed", "planche": PLANCHE,
                                                                     "listes_sha256": pk.LISTES_SHA256, "files": {}}))
        with self.assertRaises(RuntimeError):
            pk.check_receipt(root, self.receipt(root, hashlib.sha256((root / "MANIFEST_PREDICTIONS.json").read_bytes())
                                                .hexdigest()), {"planche": PLANCHE})

    def test_roundtrip_of_student_predictions(self):
        root, _ = self.build()
        back = pk.load_student(root, "student_28x28_seed0")
        for a, b in zip(self.preds, back):
            self.assertEqual({k: a[k] for k in ("boxes", "score", "cat", "cat_score")},
                             {k: b[k] for k in ("boxes", "score", "cat", "cat_score")})
            self.assertEqual(b["pairs"], pk.query_pairs())
            self.assertTrue(np.array_equal(a["rel"], b["rel"]))
        graph = {"objects": [{"box": self.preds[0]["boxes"][0], "cat": 0}, {"box": self.preds[0]["boxes"][1], "cat": 1}],
                 "relations": [(0, 2, 1)]}
        self.assertEqual(pk.relation_measures(self.preds[:1], [graph]), pk.relation_measures(back[:1], [graph]))

    def test_no_measure_before_the_receipt(self):
        full = SRC[SRC.index("def main(a):"):SRC.index("def versions():")]
        for word in ("pooled_recall(", "average_precision(", "pc.states(", "pc.issue(loc", "bootstrap("):
            self.assertNotIn(word, full.split('if not overfit["passed"]:')[1].split("save_student")[0] + full.split("(9) plate")[1])
        self.assertLess(SRC.index("manifest, receipt = check_receipt(root, a.receipt, listes)"),
                        SRC.index("counts_prior = pc.recall_counts"))
        self.assertNotIn("is_file() else None", SRC[SRC.index("def mesures(a):"):])


class TimingAndPinsTest(unittest.TestCase):
    def test_timed_student_runs_the_relation_head(self):
        # B2 (Codex p4): the 'full' column runs model.rel on the 870 ordered pairs of every image, as predict()
        model = pk.build_student(8, 0).eval()
        calls = []
        model.rel.register_forward_hook(lambda m, i, o: calls.append(i[0].shape[0]))

        class Enc:
            def tokens(self, px):
                return px, None
        tok = torch.randn(2, 64, 1024)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            outs, rel = pk.student_forward(model, Enc(), tokens=tok)
            self.assertEqual(calls, [pk.NQ * (pk.NQ - 1)] * 2)
            self.assertFalse(any(r.requires_grad for r in rel))
            calls.clear()
            pk.student_forward(model, Enc(), tokens=tok, relations=False)
            self.assertEqual(calls, [])
            calls.clear()
            pk.predict(model, tok, [(640, 480), (640, 480)])
            self.assertEqual(calls, [pk.NQ * (pk.NQ - 1)] * 2)

    def test_student_timed_without_graph(self):
        class Enc:
            def tokens(self, px):
                return px * 2, None
        layer = torch.nn.Linear(4, 2)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y = pk.student_forward(layer, Enc(), px=torch.ones(3, 4), relations=False)
            z = pk.student_forward(layer, Enc(), tokens=torch.ones(3, 4), relations=False)
        self.assertFalse(y.requires_grad or z.requires_grad)

    def test_pins(self):
        self.assertEqual(pk.OWL_REV, "cfd3195ba4ea9592eec887ded089f4c08eff231d")
        self.assertEqual(pk.FLO_SOURCE, ("microsoft/Florence-2-base", "5ca5edf5bd017b9919c05d08aebef5e4c7ac3bac"))
        self.assertEqual((pk.FLO_NATIVE_REPO, pk.FLO_REV),
                         ("florence-community/Florence-2-base", "00921df66db728a9ceb750f5eca43e5c203a2051"))
        self.assertEqual(pk.YOLOE_WEIGHTS[1], "ac2b90ed23011495a3e86d89caeb3432a15129cac8d849ba121293c8fc1e0536")
        self.assertEqual((pk.YOLOE_CONF, pk.YOLOE_IOU, pk.YOLOE_MAX_DET, pk.YOLOE_IMGSZ), (0.1, 0.5, 300, 640))
        self.assertEqual(pk.YOLOE_CONF, pk.OWL_THRESHOLD)
        self.assertEqual(pk.YOLOE_TEXT_SHA256, "a67804d1b0f07b8b9a20c1761ec0847f34660f5fa338ec70e8f3fce68ed95e54")
        self.assertEqual(pk.CLIP_TOKENIZER["commit_id"], "7ffa84b3bfa40c42ecc1c77147a855e69cb2dd40")
        self.assertEqual(pk.CLIP_TOKENIZER["version"], "1.0")
        self.assertEqual(pk.TESTED_ENV["torch"], "2.11.0+cu128")
        self.assertIn('require(versions() == TESTED_ENV, "environment_differs_from_the_reviewed_smoke")', SRC)
        self.assertIn('"clip_tokenizer_differs_from_the_reviewed_smoke"', SRC)
        self.assertIn("method linear", pk.QUANTILE_METHOD)
        self.assertIn('require(YOLOE_TEXT_SHA256 is not None, "yoloe_text_encoder_not_pinned_after_smoke")', SRC)
        self.assertNotIn("trust_remote_code=True,\n", SRC[SRC.index("def florence_detect"):SRC.index("def yoloe_load")])

    def test_failed_overfit_fails_the_smoke(self):
        smoke = SRC[SRC.index('if a.stage == "smoke":'):SRC.index('print("PETIT_ELEVE_SMOKE_DONE')]
        self.assertIn('require(overfit["passed"], "overfit_control_failed_technical_failure")', smoke)


if __name__ == "__main__":
    unittest.main(verbosity=2)
