"""Torch parts of pe_kaggle on synthetic tokens (CPU, a few seconds). Needs torch and scipy.
Run: python -I tests/test_pe_torch.py"""
from pathlib import Path
import sys
import unittest

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pe_common as pc  # noqa: E402
import pe_kaggle as pk  # noqa: E402


def synthetic(n=4, side=8, seed=0):
    """Tokens whose cells encode where the boxes are, and teacher graphs with relations."""
    rng = np.random.default_rng(seed)
    data, graphs, sizes = [], [], []
    for i in range(n):
        tok = torch.from_numpy(rng.normal(0, 0.1, (side * side, 1024)).astype(np.float32))
        objs = []
        for k in range(3):
            x0, y0 = rng.uniform(0, 600, 2)
            box = [x0, y0, x0 + rng.uniform(100, 400), y0 + rng.uniform(100, 400)]
            objs.append({"box": pc.clean_box(box), "cat": int(rng.integers(0, pk.NCLS))})
            cx, cy = (box[0] + box[2]) / 2000, (box[1] + box[3]) / 2000
            tok[int(min(cy, 0.99) * side) * side + int(min(cx, 0.99) * side), k * 10:(k + 1) * 10] += 3.0
        g = {"objects": objs, "relations": [(0, 0, 1), (1, 8, 2)], "dropped_boxes": 0}
        w, h = (640, 480) if i % 2 else (500, 700)
        graphs.append(g)
        sizes.append((w, h))
        data.append((tok.half(), pk.make_target(g, w, h, "cpu")))
    return data, graphs, sizes


class TorchTest(unittest.TestCase):
    def test_box_conversions_roundtrip(self):
        b = [100.0, 200.0, 300.0, 900.0]
        back = pk.unsquare_box(pk.square_box(b, 640, 480), 640, 480)
        self.assertLess(max(abs(u - v) for u, v in zip(back, b)), 1e-9)
        xy = torch.tensor([[0.1, 0.2, 0.5, 0.9]])
        self.assertTrue(torch.allclose(pk.cxcywh_to_xyxy(pk.xyxy_to_cxcywh(xy)), xy))

    def test_hungarian_injective_and_losses_finite(self):
        data, _, _ = synthetic()
        model = pk.build_student(8, 0)
        outs = model(torch.stack([d[0] for d in data]))
        self.assertEqual(len(outs), pk.LAYERS)
        self.assertEqual(tuple(outs[-1][0].shape), (4, pk.NQ, pk.NCLS + 1))
        q, k = pk.hungarian(outs[-1][0][0], outs[-1][1][0], data[0][1])
        self.assertEqual(len(set(q.tolist())), 3)
        det, rel = pk.losses(model, outs, [d[1] for d in data], torch.Generator().manual_seed(0))
        self.assertTrue(torch.isfinite(det) and torch.isfinite(rel))
        (det + rel).backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))

    def test_overfit_loop_reduces_loss_and_predict_shapes(self):
        data, graphs, sizes = synthetic()
        model, history, checks = pk.train(8, 0, data, None, "cpu", steps=60)
        self.assertEqual(history, [])
        self.assertTrue(checks["grads_finite"])
        self.assertEqual(checks["zero_grad_params_at_step1"], [])
        self.assertLess(checks["last_loss"], checks["first_loss"])
        pred = pk.predict(model, torch.stack([d[0] for d in data]), sizes)
        self.assertEqual(len(pred[0]["boxes"]), pk.NQ)
        self.assertEqual(pred[0]["rel"].shape, (pk.NQ * (pk.NQ - 1), pk.NREL))
        rec = pc.pooled_recall(pc.recall_counts(pk.student_images(pred, graphs), 30))
        self.assertTrue(0 <= rec <= 1)
        rm = pk.relation_measures(pred, graphs)
        self.assertIn("triplet_recall_at_20", rm)
        prior = {"global": 0}
        pm = pk.relation_measures([{"boxes": [o["box"] for o in g["objects"]], "score": [1, 0.9, 0.8]} for g in graphs],
                                  graphs, prior=prior)
        self.assertEqual(pm["predicate_recall_at_1"]["left of"]["hits"], 4)  # perfect boxes, prior says left of

    def test_train_with_tuning_keeps_best_epoch(self):
        data, _, _ = synthetic()
        model, history, _ = pk.train(8, 1, data[:3], data[3:], "cpu", epochs=10)
        self.assertEqual([h["epoch"] for h in history], [5, 10])
        self.assertEqual(sum(1 for h in history if h.get("best")) >= 1, True)

    def test_graph_loader_cleans_and_keeps_teacher_relations(self):
        import json
        import tempfile
        g = {"objects": [{"id": "o1", "name": "man", "box": [500, 100, 100, 900]},
                         {"id": "o2", "name": "staff", "box": [10, 10, 10, 50]},
                         {"id": "o3", "name": "zeppelin", "box": [0, 0, 100, 100]}],
             "relations": [["o1", "holds", "o2"], ["o1", "kneels before", "o3"], ["o3", "above", "o1"]]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(g, f)
        out = pk.load_graph(f.name)
        self.assertEqual(out["dropped_boxes"], 1)
        self.assertEqual([o["cat"] for o in out["objects"]], [0, len(pc.CATEGORIES)])
        names = pc.RELATIONS + [pc.AUTRE_RELATION]
        self.assertEqual([(s, names[r], o) for s, r, o in out["relations"]],
                         [(0, pc.AUTRE_RELATION, 1), (1, "above", 0)])

    def test_json_cleaning(self):
        self.assertEqual(pk.clean({"a": float("nan"), "b": np.float32(1.5), "c": [np.int64(2), np.bool_(True)]}),
                         {"a": None, "b": 1.5, "c": [2, True]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
