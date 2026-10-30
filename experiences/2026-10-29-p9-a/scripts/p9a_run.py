"""P9-A scientific runner. Four explicit stages, each launched by the reviewed pilot kaggle_p9a_science.py:

  devis    (T4, short)  real timings of every step of a seed, extrapolated cost; no score kept, no choice
  seed     (T4)         ten paired epochs of the four arms, V-reglage grid of 571 candidates, sealed selection,
                        then frozen validation predictions; no aggregate measure of a new head
  planches (CPU, net)   12 validation images per arm after the freeze, original Brillfull bytes (md5 checked)
  mesures  (CPU)        only after the plate viewing receipt: H/E/F_R, tranches, bootstrap 10 000 by md5 groups,
                        verdicts G then R, local-nesting mechanism on V-diagnostic

Recipes reused unchanged from the reviewed blank: TrainData, Head, optimizer, update, probability_pass,
invariants, load_preparation, extract. Preregistration sha 25f1040f..., sections 6 to 11.
"""
import argparse
import gc
import hashlib
import html
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p9a_common import (ARMS, B_H, PREREG_SHA, TRAIN, Budget, alpha_zero, drop86, hier_f1, input_path,  # noqa: E402
                        object_hash, output_dir, predictions, read_json, require, runtime_gate, sha, write_json)
import p9a_science as sc  # noqa: E402

MICRO, EFFECTIVE = 64, 64          # fixed by the blank (chosen_common_micro_batch = 64), all four arms
BLANC2_SHA256 = "a850389e41608c44dc663b9dc669735674ea82d6bc33e9f0f4f92ca2244ee82e"
UPDATES_PER_EPOCH = -(-81951 // EFFECTIVE)  # last batch kept


class Sampled:
    """The reviewed Budget, sampled every `every` calls so a ten-epoch run keeps a bounded event log."""
    def __init__(self, budget, every):
        self.inner, self.every, self.n = budget, every, 0

    def check(self, phase, gpu=False):
        self.n += 1
        if self.n % self.every == 0:
            return self.inner.check(phase, gpu)


def deterministic_t4():
    import torch
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1 and
            "T4" in torch.cuda.get_device_name(), "one visible T4 required; CPU fallback forbidden")
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    require(os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8", "deterministic cuBLAS environment missing")


def check_blank(path):
    blank = read_json(input_path(path))
    require(sha(input_path(path)) == BLANC2_SHA256 and blank["passed"] is True and
            blank["chosen_common_micro_batch"] == MICRO and blank["scientific_verdict"] is None, "blank 2 identity")
    return blank


def intensity_pass(model, data, rows, budget, phase):
    """Each arm's own intensity L^h (F/G/A: aggregated intensity; C: -log1p(-p) as computed by the head)."""
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for start in range(0, len(rows), MICRO):
            _, intensity, _ = model(data.batch(rows[start:start + MICRO]).cuda(), return_fields=True)
            require(bool(torch.isfinite(intensity).all()) and bool((intensity >= 0).all()), "invalid intensity")
            out.append(intensity.float().cpu().numpy())
            budget.check(f"{phase}/{start}", gpu=True)
    return np.concatenate(out)


def reference_b(data, binding, budget):
    """B reproduced on the whole validation (integrity exception), alpha=0 identity, envelope intensities."""
    import torch
    from p9a_heads import Baseline
    from p9a_inputs import baseline_checkpoint
    from p9a_smoke import probability_pass, seed_all
    checkpoint = baseline_checkpoint(binding, data)
    seed_all(0)
    baseline = Baseline(len(data.vocab)).cuda().eval()
    baseline.load_state_dict(checkpoint["state"], strict=True)
    require(sum(p.numel() for p in baseline.parameters()) == 18301667, "baseline architecture")
    bprob, seconds = probability_pass(baseline, data, data.val, 256, budget, "B_full_validation_integrity_only")
    bpred = predictions(bprob, data.vocab, sc.B_THRESHOLD)
    eligible = [j for j, i in enumerate(data.val) if drop86(data.labels[i])]
    hf1 = float(np.mean([hier_f1(drop86(data.labels[data.val[j]]), bpred[j]) for j in eligible]))
    require(len(eligible) == 4241 and abs(hf1 - B_H) <= 1e-6, "B does not reproduce historical H-F1")
    require(alpha_zero(bpred, 0, 0.65) is bpred, "alpha=0 does not return frozen B directly")
    del baseline
    gc.collect()
    torch.cuda.empty_cache()
    LB64 = sc.envelope(bprob, data.parents, data.levels)
    # Section 7: the envelope with its clipping must give B's sets at alpha=0 (checked in float64, never used then).
    require(sc.predict(-np.expm1(-LB64), data.vocab, sc.B_THRESHOLD) == bpred, "envelope at alpha=0 does not reproduce B")
    LB = LB64.astype(np.float32)
    del LB64
    return bprob, bpred, LB, {"H_F1": hf1, "eligible": len(eligible), "seconds": seconds}


def setup(args, budget):
    from p9a_inputs import TrainData
    from p9a_smoke import load_preparation
    binding_path, inventory = input_path(args.binding), input_path(args.inventory)
    binding = read_json(binding_path)
    data = TrainData(binding, inventory, budget)
    prototypes, preparation = load_preparation(args, data, inventory, binding_path)
    return data, binding, prototypes, preparation


def positions(data):
    pos = {int(i): k for k, i in enumerate(data.val)}
    reg = [pos[int(i)] for i in data.reg]
    diag = [pos[int(i)] for i in data.diag]
    return reg, diag


def permutations(seed):
    rng = np.random.default_rng(seed)
    return np.stack([rng.permutation(81951) for _ in range(sc.EPOCHS)])


def initial_w(seed):
    import torch
    return torch.randn(128, 1024, generator=torch.Generator(device="cpu").manual_seed(seed)) / 32.0


def train_epoch(model, opt, scaler, data, rows, budget, phase):
    from p9a_smoke import update
    stats = {"ASL": [], "grad_norm_before_clip": [], "wall_s": 0.0}
    for start in range(0, len(rows), EFFECTIVE):
        u = update(model, opt, scaler, data, rows[start:start + EFFECTIVE], MICRO, budget, phase)
        stats["ASL"].append(u["ASL"])
        stats["grad_norm_before_clip"].append(u["grad_norm_before_clip"])
        stats["wall_s"] += u["wall_s"]
    require(len(stats["ASL"]) == UPDATES_PER_EPOCH, "updates per epoch")
    return {"ASL_mean": float(np.mean(stats["ASL"])), "ASL_last": stats["ASL"][-1],
            "grad_norm_max": float(np.max(stats["grad_norm_before_clip"])), "updates": len(stats["ASL"]),
            "train_wall_s": stats["wall_s"], "regularization_last": u["regularization"]}


def atomic_torch(obj, path):
    import torch
    tmp = path.with_suffix(".tmp")
    torch.save(obj, tmp)
    os.replace(tmp, path)
    return sha(path)


# ---------------------------------------------------------------- devis
def stage_devis(args):
    import torch
    from p9a_heads import Head, optimizer
    from p9a_smoke import seed_all, update
    runtime_gate("devis")
    deterministic_t4()
    check_blank(args.blank)
    out = output_dir(args.out)
    budget = Budget(out, 3500)
    t0 = time.monotonic()
    data, binding, prototypes, _ = setup(args, budget)
    t_setup = time.monotonic() - t0
    t0 = time.monotonic()
    bprob, bpred, LB, ref = reference_b(data, binding, budget)
    t_b = time.monotonic() - t0
    reg, _ = positions(data)
    truth = sc.Truth([data.labels[i] for i in data.val])
    perms = permutations(args.seed)
    arms = {}
    for arm in sc.ARM_ORDER[args.seed]:
        seed_all(args.seed)
        model = Head(arm, data, prototypes, initial_w(args.seed)).cuda()
        opt, scaler = optimizer(model), torch.amp.GradScaler("cuda")
        rows = data.fit[perms[0]]
        walls = [update(model, opt, scaler, data, rows[k * 64:(k + 1) * 64], MICRO, budget, f"devis/{arm}")["wall_s"]
                 for k in range(21)]
        t0 = time.monotonic()
        Lh = intensity_pass(model, data, data.val[reg], budget, f"devis/{arm}/Vreg")
        t_vreg = time.monotonic() - t0
        t0 = time.monotonic()
        sc.epoch_grid(LB[reg], Lh, data.vocab, truth, reg, 1)  # timing only, scores discarded (technical)
        t_grid = time.monotonic() - t0
        t0 = time.monotonic()
        atomic_torch({"state": model.state_dict(), "optimizer": opt.state_dict(), "scaler": scaler.state_dict()},
                     out / f"devis_{arm}.pt")
        t_ckpt = time.monotonic() - t0
        size_ckpt = (out / f"devis_{arm}.pt").stat().st_size
        (out / f"devis_{arm}.pt").unlink()
        t0 = time.monotonic()
        intensity_pass(model, data, data.val, budget, f"devis/{arm}/full_val")
        t_full = time.monotonic() - t0
        warm = float(np.mean(walls[1:]))
        arms[arm] = {"warm_update_s_mean": warm, "cold_update_s": walls[0],
                     "train_s": warm * UPDATES_PER_EPOCH * sc.EPOCHS,
                     "per_epoch_selection_s": t_vreg + t_grid + 2 * t_ckpt,
                     "Vreg_pass_s": t_vreg, "grid_57_s": t_grid, "checkpoint_s": t_ckpt, "checkpoint_bytes": size_ckpt,
                     "freeze_pass_s": t_full, "peak_allocated_bytes": torch.cuda.max_memory_allocated()}
        del model, opt, scaler, Lh
        gc.collect()
        torch.cuda.empty_cache()
    per_arm = {a: v["train_s"] + sc.EPOCHS * v["per_epoch_selection_s"] + v["freeze_pass_s"] for a, v in arms.items()}
    seed_total = t_setup + t_b + sum(per_arm.values())
    disk = sum(v["checkpoint_bytes"] * (sc.EPOCHS + 1) for v in arms.values())
    # CPU measures stage: one table and one block of 500 draws on B's own frozen sets (integrity exception, no new
    # head), times 5 systems and 20 blocks. Values discarded.
    groups = sorted({data.md5[i] for i in data.val})
    gi = {m: k for k, m in enumerate(groups)}
    group_of = [gi[data.md5[i]] for i in data.val]
    t0 = time.monotonic()
    table = sc.group_tables(truth, bpred, list(range(len(data.val))), group_of, len(groups), data.rare)
    t_table = time.monotonic() - t0
    t0 = time.monotonic()
    counts = next(sc.group_draws(len(groups)))
    sc.draw_stats(table, counts)
    sc.draw_stats(table, counts)
    t_block = time.monotonic() - t0
    mesures_s = 5 * t_table + 20 * 5 * t_block
    result = {"technical_only": True, "seed": args.seed, "scores_kept": False, "setup_s": t_setup, "B_s": t_b,
              "arms": arms, "per_arm_total_s": per_arm, "seed_estimate_hours": seed_total / 3600,
              "mesures_cpu_bootstrap_estimate_hours": mesures_s / 3600,
              "disk_estimate_bytes": disk, "B_reference": ref,
              "status": "AMENDMENT_REQUIRED" if seed_total > 12 * 3600 else "WITHIN_12H",
              "note": "Extrapolation from 20 warm updates, one V-reglage pass and one 57-candidate grid per arm; "
                      "not a mathematical bound. The CPU measures stage is budgeted by its own timings."}
    write_json(out / "devis.json", result)
    budget.check("devis_finished", gpu=True)


# ---------------------------------------------------------------- seed
def load_resume(resume_dir, arm, identity, out):
    """Section 10.3: continue an arm only from its own end-of-epoch state with the same identity; the epoch
    weights are copied after their sha is checked. Without such a state the arm restarts from initialisation."""
    import shutil
    import torch
    rdir = input_path(resume_dir)
    if not (rdir / f"{arm}_seed.json").exists() or not (rdir / f"{arm}_resume.pt").exists():
        return None
    record = read_json(rdir / f"{arm}_seed.json")
    require(record["identity"] == identity, "resume identity differs: restart from initialisation instead")
    record["weights_sha256"] = {int(k): v for k, v in record["weights_sha256"].items()}
    state = torch.load(rdir / f"{arm}_resume.pt", map_location="cpu", weights_only=False)  # own earlier output
    k = state["epoch"]
    require(state["arm"] == arm and all(state[key] == value for key, value in identity.items()) and
            len(record["epochs"]) == k and len(record["grid"]) == 57 * k and set(record["weights_sha256"]) ==
            set(range(1, k + 1)), "resume state incomplete")
    for e in range(1, k + 1):
        src = rdir / f"{arm}_epoch{e:02d}_weights.pt"
        require(sha(src) == record["weights_sha256"][e], "resume weights changed")
        shutil.copyfile(src, out / src.name)
    return record, state


def stage_seed(args):
    import torch
    from p9a_heads import Head, optimizer
    from p9a_smoke import invariants, seed_all
    runtime_gate("seed")
    deterministic_t4()
    check_blank(args.blank)
    devis = read_json(input_path(args.devis))
    require(sha(input_path(args.devis)) == args.devis_sha256 and devis["status"] == "WITHIN_12H" and
            devis["seed"] == args.seed, "reviewed estimate missing or over 12 h")
    out = output_dir(args.out)
    raw_budget = Budget(out, args.wall_seconds)
    budget = Sampled(raw_budget, 2000)
    data, binding, prototypes, preparation = setup(args, raw_budget)
    write_json(out / "donnees.json", data.manifest())
    data_sha = sha(out / "donnees.json")
    bprob, bpred, LB, ref = reference_b(data, binding, raw_budget)
    write_json(out / "B_predictions_validation.json", {"identities": data.identities(data.val), "predictions": bpred})
    reference = {**ref, "frozen_predictions_sha256": sha(out / "B_predictions_validation.json")}
    del bprob
    reg, diag = positions(data)
    truth = sc.Truth([data.labels[i] for i in data.val])
    perms = permutations(args.seed)
    np.save(out / "permutations.npy", perms)
    perms_sha = sha(out / "permutations.npy")
    identity = {"seed": args.seed, "data_sha256": data_sha, "permutations_sha256": perms_sha,
                "preparation_sha256": args.preparation_sha256, "prereg_sha256": PREREG_SHA, "micro": MICRO}
    LB_reg = LB[reg]
    first_outputs, arms = {}, {}
    for arm in sc.ARM_ORDER[args.seed]:
        seed_all(args.seed)
        model = Head(arm, data, prototypes, initial_w(args.seed)).cuda()
        opt, scaler = optimizer(model), torch.amp.GradScaler("cuda")
        with torch.no_grad():
            first = model(data.batch(data.fit[:2]).cuda()).cpu()  # before any resume: initial outputs
        if arm in ("A", "controle_global"):
            other = first_outputs.get("A" if arm == "controle_global" else "controle_global")
            if other is not None:
                require(float((first - other).abs().max()) <= 1e-6, "initial A != G")
            first_outputs[arm] = first
        resumed = load_resume(args.resume, arm, identity, out) if args.resume else None
        if resumed is None:
            record = {"identity": identity, "checks_initial": invariants(model, data, raw_budget), "epochs": [],
                      "grid": [], "weights_sha256": {}}
        else:
            from p9a_smoke import restore_rng
            record, state = resumed
            model.load_state_dict(state["state"])
            opt.load_state_dict(state["optimizer"])
            scaler.load_state_dict(state["scaler"])
            restore_rng(state["rng"])
            record.setdefault("resumed_after_epoch", []).append(state["epoch"])
            del state
        for epoch in range(len(record["epochs"]) + 1, sc.EPOCHS + 1):
            rows = data.fit[perms[epoch - 1]]
            record["epochs"].append(train_epoch(model, opt, scaler, data, rows, budget, f"{arm}/epoch{epoch}"))
            wpath = out / f"{arm}_epoch{epoch:02d}_weights.pt"
            record["weights_sha256"][epoch] = atomic_torch(model.state_dict(), wpath)
            atomic_torch({"state": model.state_dict(), "optimizer": opt.state_dict(), "scaler": scaler.state_dict(),
                          "rng": __import__("p9a_smoke").rng_state(), "epoch": epoch, "arm": arm, **identity},
                         out / f"{arm}_resume.pt")
            Lh = intensity_pass(model, data, data.val[reg], raw_budget, f"{arm}/epoch{epoch}/Vreg")
            record["grid"] += sc.epoch_grid(LB_reg, Lh, data.vocab, truth, reg, epoch)
            del Lh
            write_json(out / f"{arm}_seed.json", record)
            raw_budget.check(f"{arm}/epoch{epoch}/done", gpu=True)
        record["checks_final"] = invariants(model, data, raw_budget)
        record["epochs_done"] = len(record["epochs"])
        require(record["epochs_done"] == sc.EPOCHS and len(record["grid"]) == 570, "incomplete arm")
        write_json(out / f"{arm}_seed.json", record)
        arms[arm] = record
        del model, opt, scaler
        gc.collect()
        torch.cuda.empty_cache()
    # Selection on V-reglage only, the four arms, sealed before any V-diagnostic inference of a new head.
    h_b = sc.mean_h(truth, reg, [bpred[i] for i in reg])
    selection = {}
    for arm, record in arms.items():
        candidates = [{"alpha": 0, "epoch": None, "theta": sc.B_THRESHOLD, "H_Vreg": h_b}] + record["grid"]
        chosen = sc.select(candidates)
        selection[arm] = {"chosen": chosen, "candidates": len(candidates),
                          "weights_sha256": None if chosen["alpha"] == 0 else record["weights_sha256"][chosen["epoch"]]}
    write_json(out / "selection.json", {"seed": args.seed, "rule": "max H on V-reglage; ties alpha, epoch, theta",
                                       "reference_H_Vreg": h_b, "arms": selection, "identity": identity})
    selection_sha = sha(out / "selection.json")
    # Freeze: chosen candidate of each arm on the whole validation; alpha=0 returns frozen B.
    frozen = {}
    for arm, s in selection.items():
        c = s["chosen"]
        if c["alpha"] == 0:
            preds = bpred
        else:
            seed_all(args.seed)
            model = Head(arm, data, prototypes, initial_w(args.seed)).cuda()
            wpath = out / f"{arm}_epoch{c['epoch']:02d}_weights.pt"
            require(sha(wpath) == s["weights_sha256"], "chosen weights changed")
            model.load_state_dict(torch.load(wpath, map_location="cuda", weights_only=True))
            Lh = intensity_pass(model, data, data.val, raw_budget, f"{arm}/freeze")
            preds = sc.predict(sc.mix(LB, Lh, c["alpha"]), data.vocab, c["theta"])
            del model, Lh
            gc.collect()
            torch.cuda.empty_cache()
        path = out / f"predictions_validation_{arm}.json"
        write_json(path, {"arm": arm, "seed": args.seed, "chosen": c, "identities": data.identities(data.val),
                          "predictions": preds})
        frozen[arm] = sha(path)
    write_json(out / "gel.json", {"seed": args.seed, "selection_sha256": selection_sha, "predictions_sha256": frozen,
                                  "B_reference": reference, "identity": identity, "scientific_measures": None,
                                  "next": "planches (after freeze) then viewing receipt then mesures"})
    raw_budget.check("seed_finished", gpu=True)


# ---------------------------------------------------------------- planches
def stage_planches(args):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images_initiales"))
    from p9a_image_cache import extract
    from p9a_prepare import descriptions
    from p9a_inputs import TrainData
    runtime_gate("planches")
    out = output_dir(args.out)
    budget = Budget(out, 3500)
    binding = read_json(input_path(args.binding))
    data = TrainData(binding, input_path(args.inventory), budget)
    gel_dir = input_path(args.gel)
    gel = read_json(gel_dir / "gel.json")
    require(sha(gel_dir / "gel.json") == args.gel_sha256, "gel identity")
    truth = sc.Truth([data.labels[i] for i in data.val])
    bpred = read_json(gel_dir / "B_predictions_validation.json")["predictions"]
    require(sha(gel_dir / "B_predictions_validation.json") == gel["B_reference"]["frozen_predictions_sha256"], "B frozen")
    texts, _, _ = descriptions(binding["iconclass_root"], set(data.vocab))
    where = [data.where[i] for i in data.val]
    plates, wanted = {}, {}
    for arm in ARMS:
        path = gel_dir / f"predictions_validation_{arm}.json"
        require(sha(path) == gel["predictions_sha256"][arm], f"frozen predictions {arm}")
        preds = read_json(path)["predictions"]
        chosen = sc.plate_rows(truth, preds, bpred, where)
        plates[arm] = [{"position": i, "shard": TRAIN[where[i][0]], "row": where[i][1], "md5": data.md5[data.val[i]],
                        "H_arm": sc.fast_h(truth, i, preds[i]), "H_B": sc.fast_h(truth, i, bpred[i]),
                        "truth": truth.y[i], "arm": preds[i], "B": bpred[i]} for i in chosen]
        for r in plates[arm]:
            wanted[(r["shard"], r["row"])] = {"shard": r["shard"], "row": r["row"], "md5": r["md5"],
                                              "file": r["md5"] + ".image"}
    (out / "images").mkdir()
    sources = extract(list(wanted.values()), out / "images", budget)
    describe = lambda c: html.escape(f"{c} — {texts.get(c, '(pas de texte propre)')}")
    for arm, rows in plates.items():
        blocks = []
        for r in rows:
            blocks.append(f"<section><h3>{r['shard']} · ligne {r['row']} · H bras {r['H_arm']:.3f} · H B {r['H_B']:.3f}</h3>"
                          f"<img src='images/{r['md5']}.image' style='max-width:480px'>"
                          + "".join(f"<p><b>{t}</b><br>" + "<br>".join(map(describe, codes or ['(vide)'])) + "</p>"
                                    for t, codes in (("Vérité projetée", r["truth"]), ("B", r["B"]), (arm, r["arm"])))
                          + "</section>")
        (out / f"planche_{arm}.html").write_text(
            f"<!doctype html><meta charset='utf-8'><title>P9-A {arm}</title><h1>P9-A, {arm} contre B : 12 images de "
            f"validation, |ΔH| décroissant (égalités : fragment, ligne). Champs de preuve non montrés : ils demanderaient "
            f"une nouvelle inférence.</h1>" + "".join(blocks))
    write_json(out / "planches.json", {"gel_sha256": args.gel_sha256, "plates": plates, "sources": sources})
    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "MANIFEST_PLANCHES.json")
    write_json(out / "MANIFEST_PLANCHES.json", {"files": {str(p.relative_to(out)): sha(p) for p in files}})
    budget.check("planches_finished")


# ---------------------------------------------------------------- mesures
def stage_mesures(args):
    from p9a_inputs import TrainData
    runtime_gate("mesures")
    out = output_dir(args.out)
    budget = Budget(out, 7000)
    receipt = read_json(input_path(args.receipt))
    plates = input_path(args.planches) / "MANIFEST_PLANCHES.json"
    require(receipt.get("stage") == "planches_p9a_regardees" and receipt.get("viewer") and receipt.get("viewed_at")
            and receipt.get("manifest_sha256") == sha(plates), "plates not viewed")
    binding = read_json(input_path(args.binding))
    data = TrainData(binding, input_path(args.inventory), budget)
    gel_dir = input_path(args.gel)
    require(sha(gel_dir / "gel.json") == args.gel_sha256, "gel identity")
    gel = read_json(gel_dir / "gel.json")
    selection = read_json(gel_dir / "selection.json")
    require(sha(gel_dir / "selection.json") == gel["selection_sha256"], "selection identity")
    truth = sc.Truth([data.labels[i] for i in data.val])
    bpred = read_json(gel_dir / "B_predictions_validation.json")["predictions"]
    require(sha(gel_dir / "B_predictions_validation.json") == gel["B_reference"]["frozen_predictions_sha256"], "B frozen")
    preds = {"B": bpred}
    for arm in ARMS:
        path = gel_dir / f"predictions_validation_{arm}.json"
        require(sha(path) == gel["predictions_sha256"][arm], f"frozen predictions {arm}")
        preds[arm] = read_json(path)["predictions"]
    reg, diag = positions(data)
    every = list(range(len(data.val)))
    sub = lambda rows: sc.Truth([data.labels[data.val[i]] for i in rows])
    full = {k: sc.measures(truth, p, data.rare, data.universe, data.raw, data.vocab) for k, p in preds.items()}
    t_diag = sub(diag)
    vdiag = {k: sc.measures(t_diag, [p[i] for i in diag], data.rare, data.universe, data.raw, data.vocab)
             for k, p in preds.items()}
    budget.check("measures")
    verdicts = {arm: sc.verdict(full[arm], full["B"], selection["arms"][arm]["chosen"]["alpha"]) for arm in ARMS}
    rare_set = set(data.rare)
    occ = sum(1 for i in diag for c in set(truth.y[i]) if c in rare_set)
    mech = sc.mechanism(verdicts["A"], vdiag, occ)
    # Paired bootstrap by md5 groups, same draws for B and the four arms.
    groups = sorted({data.md5[i] for i in data.val})
    gi = {m: k for k, m in enumerate(groups)}
    group_of = [gi[data.md5[i]] for i in data.val]
    diag_groups = np.zeros(len(groups), dtype=bool)
    diag_groups[[group_of[i] for i in diag]] = True
    tables = {k: sc.group_tables(truth, p, every, group_of, len(groups), data.rare) for k, p in preds.items()}
    draws = {k: {"H": [], "E": [], "F_R": []} for k in preds}
    dg = {k: {"H": [], "F_R": []} for k in preds}
    for counts in sc.group_draws(len(groups)):
        for k, t in tables.items():
            s = sc.draw_stats(t, counts)
            for m in ("H", "E", "F_R"):
                draws[k][m].append(s[m])
            s2 = sc.draw_stats(t, counts * diag_groups)
            for m in ("H", "F_R"):
                dg[k][m].append(s2[m])
        budget.check("bootstrap_block")
    cat = lambda d: {k: {m: np.concatenate(v) for m, v in x.items()} for k, x in d.items()}
    draws, dg = cat(draws), cat(dg)
    boot = {f"{arm}-B": {m: sc.summarise(draws[arm][m] - draws["B"][m]) for m in ("H", "E", "F_R")} for arm in ARMS}
    boot_mech = {f"A-{o}_Vdiag": {m: sc.summarise(dg["A"][m] - dg[o][m]) for m in ("H", "F_R")}
                 for o in ("controle_global", "F", "C")}
    write_json(out / "verdicts.json", {"seed": gel["seed"], "verdicts": verdicts, "mechanism": mech,
               "exploratory": True, "rules": "preregistration 9.1-9.3", "gel_sha256": args.gel_sha256})
    write_json(out / "mesures.json", {"full_validation": full, "V_diagnostic": vdiag,
               "bootstrap": {"seed": sc.BOOT_SEED, "draws": sc.BOOT_DRAWS, "unit": "md5 group", "groups": len(groups),
                             "full_validation": boot, "mechanism_Vdiag": boot_mech},
               "denominators": {"validation": len(data.val), "eligible": len(truth.eligible), "R": len(data.rare),
                                "Vreg": len(reg), "Vdiag": len(diag)}})
    budget.check("mesures_finished")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("devis", "seed", "planches", "mesures"), required=True)
    for name in ("binding", "inventory", "out"):
        p.add_argument("--" + name, required=True)
    for name in ("prepared", "preparation-sha256", "viewing-receipt", "blank", "devis", "devis-sha256", "gel",
                 "gel-sha256", "planches", "receipt", "resume"):
        p.add_argument("--" + name)
    p.add_argument("--seed", type=int, default=0, choices=(0, 1, 2))
    p.add_argument("--wall-seconds", type=int, default=42000)
    a = p.parse_args()
    {"devis": stage_devis, "seed": stage_seed, "planches": stage_planches, "mesures": stage_mesures}[a.stage](a)
