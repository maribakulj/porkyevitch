"""AMP skip amendment (30/10, after devis-0): update_amp on a tiny CPU model, inf injected in the gradients by a hook.
Run: python -I tests/test_amp_skip.py"""
from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import p9a_run as run  # noqa: E402


class TinyHead(torch.nn.Module):
    arm = "controle_global"

    def __init__(self):
        super().__init__()
        g = torch.Generator().manual_seed(0)
        self.W = torch.nn.Parameter(torch.randn(4, 3, generator=g) * 0.1)
        self.b = torch.nn.Parameter(torch.zeros(3))

    def forward(self, x):
        return torch.sigmoid(x @ self.W + self.b)

    def regularization(self):
        return 1e-4 * self.W.square().sum()


class TinyData:
    def __init__(self):
        g = torch.Generator().manual_seed(1)
        self.x = torch.randn(256, 4, generator=g)
        self.y = (torch.rand(256, 3, generator=g) > 0.7).float()

    def batch(self, rows):
        return self.x[rows]

    def targets(self, rows):
        return self.y[rows]


class NoBudget:
    def check(self, *a, **k):
        pass


def setup(init_scale=2.0 ** 16):
    model = TinyHead()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-2)
    scaler = torch.amp.GradScaler("cpu", init_scale=init_scale)
    return model, opt, scaler, TinyData(), run.SkipLog()


def poison(param, when):
    """Gradient of param becomes +inf at the calls listed in when (a set of call indices, or None for always)."""
    calls = {"n": 0}

    def hook(g):
        k = calls["n"]
        calls["n"] += 1
        return g * float("inf") if when is None or k in when else g
    param.register_hook(hook)


def step(model, opt, scaler, data, skips, k):
    return run.update_amp(model, opt, scaler, data, list(range(k * 64, (k + 1) * 64)), 64, NoBudget(), "test", skips,
                          model.arm, 1, k)


class AmpSkipTest(unittest.TestCase):
    def test_legitimate_inf_is_skipped_weights_unchanged_then_training_resumes(self):
        model, opt, scaler, data, skips = setup()
        poison(model.W, {0})  # only the first backward overflows, as an fp16 overflow would
        before = [p.detach().clone() for p in model.parameters()]
        u = step(model, opt, scaler, data, skips, 0)
        self.assertTrue(u["skipped"])
        self.assertIsNone(u["grad_norm_before_clip"])
        self.assertTrue(all(torch.equal(a, p.detach()) for a, p in zip(before, model.parameters())))
        self.assertEqual(scaler.get_scale(), 2.0 ** 15)
        r = skips.records[0]
        self.assertEqual((r["arm"], r["epoch"], r["step"], r["scale_before"]), ("controle_global", 1, 0, 2.0 ** 16))
        self.assertEqual(r["most_affected_parameter"], "W")
        self.assertGreater(r["n_inf"] + r["n_nan"], 0)
        u = step(model, opt, scaler, data, skips, 1)  # finite again: the reviewed path, weights move
        self.assertFalse(u["skipped"])
        self.assertIsNotNone(u["grad_norm_before_clip"])
        self.assertFalse(torch.equal(before[0], model.W.detach()))
        self.assertEqual(skips.summary("controle_global")["skips"], 1)

    def test_divergence_scale_below_one_stops(self):
        model, opt, scaler, data, skips = setup(init_scale=4.0)
        poison(model.W, None)  # every backward non-finite: the scale halves 4 -> 2 -> 1 -> 0.5
        step(model, opt, scaler, data, skips, 0)
        step(model, opt, scaler, data, skips, 1)
        with self.assertRaisesRegex(RuntimeError, "divergence"):
            step(model, opt, scaler, data, skips, 2)
        self.assertEqual(len(skips.records), 3)

    def test_one_percent_cap_stops(self):
        self.assertEqual(run.UPDATES_PER_EPOCH, 1281)
        self.assertAlmostEqual(run.MAX_SKIPS_PER_EPOCH, 12.81)
        model, opt, scaler, data, skips = setup(init_scale=2.0 ** 30)  # scale stays >= 1 over 13 halvings
        poison(model.W, None)
        for k in range(12):
            step(model, opt, scaler, data, skips, k % 4)
        with self.assertRaisesRegex(RuntimeError, "amendment required"):
            step(model, opt, scaler, data, skips, 0)
        self.assertEqual(skips.per_arm_epoch[("controle_global", 1)], 13)
        self.assertGreaterEqual(scaler.get_scale(), 1.0)

    def test_cap_is_per_arm_and_epoch(self):
        skips = run.SkipLog()
        for k in range(12):
            skips.add({"arm": "A", "epoch": 1, "step": k}, 2.0)
        skips.add({"arm": "A", "epoch": 2, "step": 0}, 2.0)       # another epoch: its own count
        skips.add({"arm": "C", "epoch": 1, "step": 0}, 2.0)       # another arm: its own count
        with self.assertRaises(RuntimeError):
            skips.add({"arm": "A", "epoch": 1, "step": 12}, 2.0)

    def test_finite_path_matches_plain_recipe(self):
        # without any overflow, update_amp is the reviewed recipe: same weights as a hand-written AMP step
        model, opt, scaler, data, skips = setup()
        ref, ropt, rscaler, _, _ = setup()
        step(model, opt, scaler, data, skips, 0)
        from p9a_heads import asymmetric_loss
        rows = list(range(64))
        ropt.zero_grad(set_to_none=True)
        rscaler.scale(asymmetric_loss(ref(data.batch(rows)), data.targets(rows))).backward()
        rscaler.scale(ref.regularization()).backward()
        rscaler.unscale_(ropt)
        torch.nn.utils.clip_grad_norm_(ref.parameters(), 5, error_if_nonfinite=True)
        rscaler.step(ropt)
        rscaler.update()
        self.assertTrue(all(torch.allclose(a, b, atol=0, rtol=0) for a, b in zip(model.parameters(), ref.parameters())))
        self.assertEqual(skips.records, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
