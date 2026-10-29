"""P9-A technical smoke only: two primary updates per arm, no scientific run.

128 first canonical fit rows / 64 first canonical V-reg rows. The only full-val
inference is the historical B integrity exception. No epoch/alpha selection.
"""
import argparse
import copy
import gc
import hashlib
import os
from pathlib import Path
import random
import time

import numpy as np
import torch

from p9a_common import (ARMS, B_H, PREREG_SHA, Budget, alpha_zero, code_f1, drop86, hier_f1,
                       input_path, object_hash, output_dir, predictions, read_json, require, runtime_gate, sha, write_json)
from p9a_inputs import TrainData, baseline_checkpoint
from p9a_heads import Baseline, Head, Hierarchy, asymmetric_loss, optimizer


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def rng_state():
    return {"python": random.getstate(), "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all()}


def restore_rng(state):
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    torch.cuda.set_rng_state_all(state["cuda"])


def atomic_checkpoint(path, model, opt, scaler, rows, next_update, data_sha, micro):
    tmp = path.with_suffix(".tmp.pt")
    torch.save({"state": model.state_dict(), "optimizer": opt.state_dict(), "scaler": scaler.state_dict(),
                "rng": rng_state(), "seed": 0, "epoch": 0, "next_update": next_update,
                "canonical_smoke_rows": rows.tolist(), "permutation_position": next_update * 64,
                "data_sha256": data_sha, "micro_batch": micro, "effective_batch": 64,
                "arm": model.arm, "technical_only": True}, tmp)
    os.replace(tmp, path)
    return sha(path)


def update(model, opt, scaler, data, rows, micro, budget, phase):
    model.train()
    torch.cuda.synchronize()
    start = time.monotonic()
    opt.zero_grad(set_to_none=True)
    loss_value = 0.0
    for offset in range(0, len(rows), micro):
        part = rows[offset:offset + micro]
        x, y = data.batch(part).cuda(), data.targets(part).cuda()
        probability = model(x)
        require(bool(torch.isfinite(probability).all()), "nonfinite probability")
        loss = asymmetric_loss(probability, y)
        require(bool(torch.isfinite(loss)), "nonfinite ASL")
        scaler.scale(loss * (len(part) / len(rows))).backward()
        loss_value += float(loss.detach()) * len(part) / len(rows)
        del x, y, probability, loss
        budget.check(f"{phase}/micro{offset}", gpu=True)
    # Exactly once per effective update, independent of accumulation count.
    penalty = model.regularization()
    scaler.scale(penalty).backward()
    scaler.unscale_(opt)
    require(all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in model.parameters()),
            "nonfinite gradients")
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5, error_if_nonfinite=True)
    scaler.step(opt)
    scaler.update()
    require(all(bool(torch.isfinite(p).all()) for p in model.parameters()), "nonfinite model parameters")
    budget.check(f"{phase}/updated", gpu=True)
    torch.cuda.synchronize()
    return {"wall_s": time.monotonic() - start, "ASL": loss_value,
            "regularization": float(penalty.detach()), "grad_norm_before_clip": float(norm)}


@torch.no_grad()
def probability_pass(model, data, rows, micro, budget, phase):
    model.eval()
    outputs = []
    start = time.monotonic()
    for offset in range(0, len(rows), micro):
        p = model(data.batch(rows[offset:offset + micro]).cuda())
        require(bool(torch.isfinite(p).all()) and bool(((p >= 0) & (p <= 1)).all()), "invalid probabilities")
        outputs.append(p.cpu().numpy())
        budget.check(f"{phase}/{offset}", gpu=True)
    return np.concatenate(outputs), time.monotonic() - start


@torch.no_grad()
def invariants(model, data, budget):
    model.eval()
    x = data.batch(data.fit[:2]).cuda()
    p, intensity, fields = model(x, return_fields=True)
    result = {}
    if model.arm in ("A", "controle_global"):
        result["hierarchy_probability_violation"] = model.hierarchy.violation(p)
        result["hierarchy_intensity_violation"] = model.hierarchy.violation(intensity)
        require(max(result.values()) <= 1e-6, "hierarchy violation")
        if model.arm == "A":
            result["hierarchy_local_violation"] = model.hierarchy.violation(fields)
            require(result["hierarchy_local_violation"] <= 1e-6, "local hierarchy violation")
        duplicate = torch.cat((x[:, :1], x[:, :1], x[:, 1:]), dim=1)
        weights = torch.full((65,), 1 / 64, device="cuda", dtype=torch.float32)
        weights[:2] = 1 / 128
        result["weighted_cell_duplication_max_probability_error"] = float((model(duplicate, weights) - p).abs().max())
        require(result["weighted_cell_duplication_max_probability_error"] <= 1e-6, "mass conservation check")
        # Both software paths receive gates/root from these same real grid cells.
        z, scores = model.linear_scores(x)
        root = torch.nn.functional.softplus(torch.nn.functional.linear(
            z, model.w0.unsqueeze(0), model.b0.view(1)).squeeze(-1)) + 1e-8
        gates = torch.sigmoid(scores)
        shallow = Hierarchy([[] for _ in data.vocab], [list(range(len(data.vocab)))]).cuda()
        local = shallow(gates, root).mean(1)
        mu = root.mean(1)
        global_ = shallow((root.unsqueeze(-1) * gates).mean(1) / mu.unsqueeze(-1), mu)
        result["one_level_max_intensity_error"] = float((local - global_).abs().max())
        require(result["one_level_max_intensity_error"] <= 1e-6, "one-level A/G identity")
    budget.check(f"invariants/{model.arm}", gpu=True)
    return result


def load_preparation(args, data, inventory, binding):
    root = input_path(args.prepared)
    path = input_path(root / "preparation.json")
    require(sha(path) == args.preparation_sha256, "preparation artifact SHA differs from approved binding")
    meta = read_json(path)
    require(meta["prereg_sha256"] == PREREG_SHA and meta["no_new_head_inference"] is True, "preparation protocol")
    require(meta["binding_sha256"] == sha(binding) and meta["inventory_sha256"] == sha(inventory), "preparation inputs changed")
    for name, key in (("donnees.json", "donnees_sha256"), ("prototypes.npz", "prototypes_sha256"),
                      ("textes.json", "texts_sha256")):
        require(sha(input_path(root / name)) == meta[key], f"prepared artifact identity: {name}")
    require(read_json(root / "donnees.json") == data.manifest(), "prepared train/val metadata changed")
    board = input_path(root / "planche_initiale" / "manifest.json")
    require(sha(board) == meta["initial_board_manifest_sha256"], "board manifest changed")
    bm = read_json(board)
    require(sha(input_path(root / "planche_initiale" / "index.html")) == bm["html_sha256"], "board HTML changed")
    for row in bm["rows"]:
        require(sha(input_path(root / "planche_initiale" / row["thumbnail"])) == row["thumbnail_sha256"], "board image changed")
    receipt = read_json(input_path(args.viewing_receipt))
    require(receipt["stage"] == "initial_board_viewed" and bool(receipt["viewer"]) and bool(receipt["viewed_at"]),
            "initial material has not been viewed")
    require(receipt["preparation_sha256"] == sha(path) and receipt["manifest_sha256"] == sha(board),
            "viewing receipt belongs to another board")
    with np.load(root / "prototypes.npz", allow_pickle=False) as f:
        require(set(f.files) == {"e", "d"}, "prototype fields")
        e, d = f["e"], f["d"]
        require(e.shape == d.shape == (7907, 384) and e.dtype == d.dtype == np.float32
                and np.isfinite(e).all() and np.isfinite(d).all(), "prototype cache shape/dtype")
        rebuilt = e.copy()
        for c, ps in enumerate(data.parents):
            if ps:
                rebuilt[c] -= e[ps].mean(0)
        require(np.array_equal(rebuilt, d), "text residual parents mismatch")
    return d, meta


def paired_attempt(data, prototypes, initial_W, micro, directory, budget, data_sha):
    directory.mkdir()
    rows, validation = data.fit[:128], data.reg[:64]
    initial_global = None
    initial_W_sha = hashlib.sha256(initial_W.numpy().tobytes()).hexdigest()
    summaries = {}
    for arm in ARMS:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        seed_all(0)
        model = Head(arm, data, prototypes, initial_W).cuda()
        require(hashlib.sha256(model.W.detach().cpu().numpy().tobytes()).hexdigest() == initial_W_sha,
                "shared W initialization differs")
        opt = optimizer(model)
        scaler = torch.amp.GradScaler("cuda")
        with torch.no_grad():
            initial = model(data.batch(rows[:2]).cuda())
            prior_error = float((initial - model.prior).abs().max())
            if arm == "controle_global":
                initial_global = initial.cpu().clone()
            if arm == "A":
                require(float((initial.cpu() - initial_global).abs().max()) <= 1e-6, "initial A != G")
        checks = invariants(model, data, budget)
        first = update(model, opt, scaler, data, rows[:64], micro, budget, f"{arm}/cold_step1")
        cp = directory / f"{arm}_resume.pt"
        cp_sha = atomic_checkpoint(cp, model, opt, scaler, rows, 1, data_sha, micro)
        second = update(model, opt, scaler, data, rows[64:], micro, budget, f"{arm}/warm_step2")
        checks.update({"after_training/" + k: v for k, v in invariants(model, data, budget).items()})
        probability, val_s = probability_pass(model, data, validation, micro, budget, f"{arm}/technical_Vreg")
        # Save only compact CPU tensors for comparison; replay on the same device/model.
        expected_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        expected_scaler = copy.deepcopy(scaler.state_dict())
        require(sha(cp) == cp_sha, "resume checkpoint changed")
        checkpoint = torch.load(cp, map_location="cpu", weights_only=False)  # own atomic output, SHA verified above
        require(checkpoint["data_sha256"] == data_sha and checkpoint["canonical_smoke_rows"] == rows.tolist()
                and checkpoint["permutation_position"] == 64 and checkpoint["micro_batch"] == micro,
                "resume data/permutation position")
        model.load_state_dict(checkpoint["state"])
        opt.load_state_dict(checkpoint["optimizer"])
        scaler.load_state_dict(checkpoint["scaler"])
        restore_rng(checkpoint["rng"])
        del checkpoint
        replay = update(model, opt, scaler, data, rows[64:], micro, budget, f"{arm}/resume_replay_step2")
        resumed, _ = probability_pass(model, data, validation, micro, budget, f"{arm}/resumed_Vreg")
        require(float(np.abs(probability - resumed).max()) <= 1e-6, "resume probabilities differ")
        pred = predictions(probability, data.vocab, 0.65)  # fixed technical threshold, NOT selected
        require(pred == predictions(resumed, data.vocab, 0.65), "resume predicted sets differ")
        require(all(torch.equal(v.detach().cpu(), expected_state[k]) for k, v in model.state_dict().items()),
                "resume model state differs")
        require(scaler.state_dict() == expected_scaler, "resume scaler differs")
        truth = [drop86(data.labels[i]) for i in validation]
        rare = code_f1(truth, pred, data.rare)
        require(rare["codes"] == len(data.rare), "rare denominator changed with validation support")
        independent = []
        for c in data.rare:
            tp = sum(c in g and c in p for g, p in zip(truth, pred, strict=True))
            fp = sum(c not in g and c in p for g, p in zip(truth, pred, strict=True))
            fn = sum(c in g and c not in p for g, p in zip(truth, pred, strict=True))
            independent.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
        require(not independent or abs(float(np.mean(independent)) - rare["macro_F1"]) <= 1e-12,
                "rare independent calculation differs")
        np.save(directory / f"{arm}_technical_vreg.npy", probability)
        end_sha = atomic_checkpoint(directory / f"{arm}_after2.pt", model, opt, scaler, rows, 2, data_sha, micro)
        summaries[arm] = {"technical_only": True, "initial_prior_max_error": prior_error,
                          "initial_W_sha256": initial_W_sha,
                          "target_sha256": hashlib.sha256(data.targets(rows).numpy().tobytes()).hexdigest(),
                          "rows_sha256": object_hash(rows.tolist()), "cold_update": first, "warm_update": second,
                          "replay_update": replay, "technical_validation_seconds": val_s,
                          "technical_threshold_not_selected": 0.65, "rare_metric_control": rare,
                          "checks": checks, "resume_probability_max_error": float(np.abs(probability - resumed).max()),
                          "checkpoint_after2_sha256": end_sha,
                          "trainable_parameters": sum(p.numel() for p in model.parameters())}
        write_json(directory / f"{arm}_technical.json", summaries[arm])
        del model, opt, scaler, expected_state, probability, resumed
        gc.collect()
        torch.cuda.empty_cache()
    require(len({v["target_sha256"] for v in summaries.values()}) == 1, "unpaired targets")
    require(len({v["rows_sha256"] for v in summaries.values()}) == 1, "unpaired train rows")
    return summaries


def smoke(args):
    runtime_gate("smoke")
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1 and
            "T4" in torch.cuda.get_device_name(), "one visible T4 required; CPU fallback forbidden")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    require(os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8", "deterministic cuBLAS environment missing")
    out = output_dir(args.out)
    budget = Budget(out, 3550)  # external driver hard wall is <=3600 seconds, including startup
    binding_path, inventory = input_path(args.binding), input_path(args.inventory)
    binding = read_json(binding_path)
    data = TrainData(binding, inventory, budget)
    prototypes, preparation = load_preparation(args, data, inventory, binding_path)
    checkpoint = baseline_checkpoint(binding, data)
    seed_all(0)
    baseline = Baseline(len(data.vocab)).cuda().eval()
    baseline.load_state_dict(checkpoint["state"], strict=True)
    require(sum(p.numel() for p in baseline.parameters()) == 18301667, "baseline architecture")
    del checkpoint
    bprob, btime = probability_pass(baseline, data, data.val, 256, budget, "B_full_validation_integrity_only")
    bpred = predictions(bprob, data.vocab, 0.65)
    eligible = [j for j, i in enumerate(data.val) if drop86(data.labels[i])]
    hf1 = float(np.mean([hier_f1(drop86(data.labels[data.val[j]]), bpred[j]) for j in eligible]))
    require(len(eligible) == 4241 and abs(hf1 - B_H) <= 1e-6, "B does not reproduce historical H-F1")
    require(alpha_zero(bpred, 0, 0.65) is bpred, "alpha=0 does not return frozen B directly")
    rejected = False
    try:
        alpha_zero(bpred, 0, 0.60)
    except RuntimeError:
        rejected = True
    require(rejected, "alpha=0 permits retuning its threshold")
    np.save(out / "B_validation.npy", bprob)
    write_json(out / "B_predictions_validation.json", {"identities": data.identities(data.val), "predictions": bpred})
    write_json(out / "reference_validation.json", {"H_F1": hf1, "eligible": len(eligible), "threshold": 0.65,
               "seconds": btime, "frozen_predictions_sha256": sha(out / "B_predictions_validation.json"),
               "alpha_zero_identity": True, "integrity_exception_only": True})
    del baseline, bprob, bpred
    gc.collect()
    torch.cuda.empty_cache()
    n_diff = sum(data.raw.get(c, 0) != data.closed[c] for c in data.vocab)
    require(n_diff > 0, "raw/closed frequency distinction not exercised")
    manifest = data.manifest()
    write_json(out / "donnees.json", manifest)
    data_sha = sha(out / "donnees.json")
    generator = torch.Generator(device="cpu").manual_seed(0)
    initial_W = torch.randn(128, 1024, generator=generator) / 32.0
    attempts = []
    summary = None
    for micro in (64, 32, 16):
        gc.collect()
        torch.cuda.empty_cache()
        try:
            summary = paired_attempt(data, prototypes, initial_W, micro, out / f"micro{micro}", budget, data_sha)
            attempts.append({"micro_batch": micro, "status": "passed_all_four"})
            break
        except torch.cuda.OutOfMemoryError:
            # No scientific interpretation. Restart ALL heads from the same seed/rows.
            attempts.append({"micro_batch": micro, "status": "OOM_restart_all_four"})
            write_json(out / "memory_attempts.json", attempts)
            gc.collect()
            torch.cuda.empty_cache()
            budget.check(f"OOM/micro{micro}", gpu=True)
    require(summary is not None, "all predeclared micro-batches fail; amendment required")
    # A lower bound from two updates, NOT certification of the full grid search cost.
    train_estimate = sum(v["warm_update"]["wall_s"] for v in summary.values()) * int(np.ceil(81951 / 64)) * 10
    result = {"technical_only": True, "passed": True, "scientific_verdict": None,
              "no_full_runner_or_automatic_continuation": True, "seed": 0,
              "canonical_fit_rows": data.identities(data.fit[:128]),
              "canonical_Vreg_rows": data.identities(data.reg[:64]), "new_head_Vdiag_inferences": 0,
              "attempts": attempts, "chosen_common_micro_batch": micro, "effective_batch": 64,
              "arms": summary, "raw_closed_frequency_differences": n_diff,
              "train_only_timing_extrapolation_hours": train_estimate / 3600,
              "extrapolation_includes_selection_grid": False,
              "full_run_budget_status": "AMENDMENT_REQUIRED" if train_estimate > 12 * 3600 else "REVIEW_REQUIRED",
              "full_run_budget_note": "Training lower bound only; selection + full validation must be budgeted separately.",
              "preparation_sha256": args.preparation_sha256, "prereg_sha256": PREREG_SHA,
              "source_sha256": {p.name: sha(p) for p in Path(__file__).parent.glob("p9a_*.py")},
              "gpu": torch.cuda.get_device_name(), "torch": torch.__version__, "numpy": np.__version__}
    write_json(out / "blanc.json", result)
    budget.check("smoke_finished", gpu=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binding", "inventory", "prepared", "preparation-sha256", "viewing-receipt", "out"):
        parser.add_argument("--" + name, required=True)
    smoke(parser.parse_args())
