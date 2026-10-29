"""Diagnostic « où la tête perd des points » on the ICAI VALIDATION only, for B = T-Z and T*. Kaggle CPU.

Reads existing outputs only: porky-e0-run (t_long.pt, e0.json, journal), porky-e3-run (t_z.pt, e3.json,
journal) and caypollard-encode-cradio v3 (eleven train-* fragments). Never opens a test fragment, the
Rijksmuseum bench, Emblematica or a PE-Spatial output. No training, no model choice. See PREINSCRIPTION.md.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

import diag_metrics as dm

TRAIN = tuple(f"train-{i:05d}-of-00011" for i in range(11))
DATASET = ["davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"]
FEATURE_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|square-grey128|448|bicubic|"
                  "autocast-fp16|summary+meanspatial|l2-each-then-l2")
GRID_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|square-grey128|448|bicubic|"
               "autocast-fp16|spatial28x28|adaptive-avg-8x8|fp16")
REPRODUCE_TOL = 1e-4  # CPU float32 against the historical T4 float32 run
GRID = [round(0.05 * k, 2) for k in range(1, 20)]
BUDGET_SECONDS = 2 * 3600
START = time.monotonic()


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def legacy_sha(obj):
    return hashlib.sha256(json.dumps(obj).encode()).hexdigest()


def bound(path):
    p = Path(path).resolve(strict=True)
    require(Path("/kaggle/input") in p.parents, "input_outside_kaggle_mount")
    require(not any(x.lower().startswith(("test-", "emb")) or "rijks" in x.lower() or "emblem" in x.lower()
                    or x.lower().endswith("-pe") for x in p.parts), "forbidden_input")
    return p


def budget(step):
    require(time.monotonic() - START <= BUDGET_SECONDS, f"budget_exceeded_at_{step}")


def write_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + "\n")
    os.replace(tmp, path)


def load_data(root, inventory):
    """E3 split (md5 groups, default_rng(0) < 0.05), training labels and validation vectors/grids."""
    root = bound(root)
    labels, md5s, where, vectors = [], [], [], []
    for shard, tag in enumerate(TRAIN):
        expected = inventory["shards"][tag]
        for sub, ext, key in (("feats", "npz", "vec_sha256"), ("feats", "json", "feats_json_sha256"),
                              ("grid", "json", "grid_json_sha256"), ("grid", "npy", "grid_sha256")):
            require(sha(bound(root / sub / f"{tag}.{ext}")) == expected[key], "train_source_sha")
        side = json.loads((root / "grid" / f"{tag}.json").read_text())
        manifest = json.loads((root / "feats" / f"{tag}.json").read_text())
        n = 8000 if shard < 10 else 6216
        require(side["manifest"] == manifest and manifest["dataset"] == DATASET and manifest["smoke"] == 0 and
                manifest["feature_config"] == FEATURE_CONFIG and side["grid_config"] == GRID_CONFIG and
                manifest["rows"] == n == side["rows"] and len(side["labels"]) == n, "train_source_alignment")
        require(legacy_sha(side["labels"]) == manifest["labels_sha256"], "train_annotation_sha")
        with np.load(root / "feats" / f"{tag}.npz", allow_pickle=False) as z:
            x, md5 = z["x"], z["md5"].tolist()
        require(x.shape == (n, 4096) and x.dtype == np.float16 and len(md5) == n and
                legacy_sha(md5) == side["md5_sha256"], "train_vector_alignment")
        vectors.append(x)
        labels.extend(side["labels"])
        md5s.extend(md5)
        where.extend((shard, row) for row in range(n))
        budget("load_shard")
    groups = sorted(set(md5s))
    gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
    val = np.array([m in gval for m in md5s])
    require(int(val.sum()) == 4265 and int((~val).sum()) == 81951, "historical_split")
    rows = np.flatnonzero(val)
    x_all = np.concatenate(vectors)
    vectors.clear()
    x_val = x_all[rows].astype(np.float32)
    del x_all
    grids = np.empty((len(rows), 64, 1024), dtype=np.float16)
    for shard, tag in enumerate(TRAIN):
        g = np.load(root / "grid" / f"{tag}.npy", mmap_mode="r", allow_pickle=False)
        require(g.shape == (8000 if shard < 10 else 6216, 64, 1024) and g.dtype == np.float16, "grid_shape")
        for k, i in enumerate(rows):
            if where[i][0] == shard:
                grids[k] = g[where[i][1]]
        del g
    require(np.isfinite(x_val).all() and np.isfinite(grids).all(), "non_finite_inputs")
    train_labels = [labels[i] for i in np.flatnonzero(~val)]
    val_labels = [labels[i] for i in rows]
    identities = [{"shard": TRAIN[where[i][0]], "row": int(where[i][1]), "md5": md5s[i]} for i in rows]
    return train_labels, val_labels, x_val, grids, identities


def load_head(path, expected_sha, vocab, epoch, threshold, spatial):
    import torch
    from torch import nn
    path = bound(path)
    require(sha(path) == expected_sha, "head_sha")
    ck = torch.load(path, map_location="cpu", weights_only=False)  # only after the SHA check (as the phase-1 seal)
    require(list(ck["vocab"]) == vocab and ck["epoch"] == epoch and ck["threshold"] == threshold,
            "head_vocabulary_epoch_threshold")
    require(ck["grid_config" if spatial else "feature_config"] == (GRID_CONFIG if spatial else FEATURE_CONFIG),
            "head_feature_configuration")
    classes = len(vocab)
    if spatial:
        class SpatialPooling(nn.Module):  # E3 T-Z, as gel_models.py
            def __init__(self):
                super().__init__()
                self.q = nn.Parameter(torch.empty(1024))
                self.mlp = nn.Sequential(nn.Linear(1024, 2048), nn.GELU(), nn.Dropout(0.2), nn.Linear(2048, classes))

            def forward(self, x):
                w = torch.softmax((x @ self.q) / 32.0, dim=1)
                return self.mlp((w.unsqueeze(-1) * x).sum(1))
        model = SpatialPooling()
    else:
        model = nn.Sequential(nn.Linear(4096, 2048), nn.GELU(), nn.Dropout(0.2), nn.Linear(2048, classes))
    model.load_state_dict(ck["state"], strict=True)
    return model.eval()


def probabilities(model, source, batch):
    import torch
    out = []
    with torch.no_grad():
        for start in range(0, len(source), batch):
            x = torch.from_numpy(np.array(source[start:start + batch], dtype=np.float32, copy=True))
            p = torch.sigmoid(model(x)).numpy()
            require(np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all(), "invalid_probability")
            out.append(p)
            budget("inference")
    return np.concatenate(out)


def journal_spread(path, last):
    # Not a seed spread: phase 1 trained one seed (0). Spread of validation H-F1 over the last epochs.
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    vals = [r["val"] for r in rows[-last:]]
    return {"epochs": [r["epoch"] for r in rows[-last:]], "val": vals, "range": max(vals) - min(vals),
            "label": "variation between epochs of one seed, NOT a seed spread"}


def main(args):
    import torch
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    out = Path(args.out).resolve()
    require(Path("/kaggle/working") in out.parents and (not out.exists() or not any(out.iterdir())), "output")
    out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent
    inventory = json.loads((here.parent / "ENTREES.json").read_text())
    binding = json.loads(bound(args.binding).read_text())
    docs = {}
    for name, key in (("e0", "e0/e0.json"), ("e3", "e3/e3.json")):
        p = bound(Path(binding[name + "_root"]) / f"{name}.json")
        require(sha(p) == inventory["documents"][key], "published_document_sha")
        docs[name] = json.loads(p.read_text())
    tstar, tz = docs["e0"]["validation"]["T-long"], docs["e3"]["T-Z"]
    require(docs["e0"]["T_star"] == "T-long" and docs["e0"]["t_long_sha256"] == inventory["weights"]["T_star"] and
            tz["sha256"] == inventory["weights"]["T-Z"], "reference_identity")

    train_labels, val_labels, x_val, grids, identities = load_data(binding["encoder_root"], inventory)
    n_brut = Counter(c for y in train_labels for c in set(y))
    vocab = sorted({a for c, n in n_brut.items() if n >= 5 for a in dm.ancestors(c)})
    require(len(vocab) == 7907, "historical_vocabulary")
    systems = {
        "T_star": (Path(binding["e0_root"]) / "t_long.pt", inventory["weights"]["T_star"], tstar, False, x_val, 1024),
        "B_TZ": (Path(binding["e3_root"]) / "t_z.pt", inventory["weights"]["T-Z"], tz, True, grids, 256)}
    gts_all = [dm.drop86(y) for y in val_labels]
    keep = [i for i, g in enumerate(gts_all) if g]
    require(len(keep) == 4241, "evaluable_validation_rows")
    gts = [gts_all[i] for i in keep]
    groups = [identities[i]["md5"] for i in keep]
    universe = sorted({c for c in n_brut if not c.strip().startswith("86")} | set(dm.drop86(vocab)) |
                      {c for g in gts_all for c in g})
    code_tranche = {c: dm.tranche(n_brut.get(c, 0)) for c in vocab}
    results = {"stage": "diagnostic_tete_validation", "population": {"validation_rows": len(gts_all),
               "evaluable": len(keep), "train_rows": len(train_labels), "vocabulary": len(vocab),
               "universe": len(universe),
               "truth_codes_outside_vocabulary": sum(1 for g in gts for c in g if c not in set(vocab)),
               "truth_codes": sum(len(set(g)) for g in gts)},
               "seeds": "not_available: phase 1 trained one seed (0) per head",
               "cradio_vs_pe_spatial": "not_available: no PE-Spatial validation predictions were saved; "
                                       "the saved PE predictions are on the closed ICAI test and are not opened",
               "systems": {}}
    probs, preds, per_image = {}, {}, {}
    for name, (path, digest, spec, spatial, source, batch) in systems.items():
        model = load_head(path, digest, vocab, spec["epoch"], spec["threshold"], spatial)
        p = probabilities(model, source, batch)
        del model
        pred_all = dm.project(p, vocab, spec["threshold"])
        pred = [pred_all[i] for i in keep]
        h = [dm.hier_f1(g, q) for g, q in zip(gts, pred, strict=True)]
        delta = float(np.mean(h)) - spec["val"]
        # Stop before any diagnostic if the historical validation score is not reproduced.
        require(abs(delta) <= REPRODUCE_TOL, f"{name}_historical_hf1_not_reproduced")
        probs[name], preds[name], per_image[name] = p, pred_all, h
        if args.stage == "smoke":
            results["systems"][name] = {"reproduced_hf1": float(np.mean(h)), "historical_hf1": spec["val"],
                                        "reproduction_delta": delta}
            continue
        e = [dm.exact_f1(g, q) for g, q in zip(gts, pred, strict=True)]
        results["systems"][name] = {
            "epoch": spec["epoch"], "threshold": spec["threshold"], "historical_hf1": spec["val"],
            "reproduced_hf1": float(np.mean(h)), "reproduction_delta": delta, "exact_f1": float(np.mean(e)),
            "codes_per_image": float(np.mean([len(q) for q in pred])),
            "empty_predictions": sum(1 for q in pred if not q),
            "tranches_exact_codes": dm.tranche_table(gts_all, pred_all, n_brut, universe),
            "depth_nodes": dm.node_depth_table(gts, pred),
            "stop_depth_of_missed_codes": dm.stop_depths(gts, pred),
            "confident_absent_p_ge_0.9": dm.confident_absent(p[keep], vocab, gts, [identities[i] for i in keep]),
            "tranche_threshold_upper_bound": dm.tranche_threshold_upper_bound(
                p[keep], vocab, code_tranche, gts, spec["threshold"], GRID),
            "global_threshold_grid": {str(t): dm.mean_hier(gts, dm.project(p[keep], vocab, t)) for t in GRID}}
        per_image[name + "_exact"] = e
        budget(f"measures_{name}")
    if args.stage == "smoke":
        # Blank: inputs, split, vocabulary and historical reproduction only; no diagnostic measure.
        results["stage"] = "smoke_reproduction_only"
        results["wall_seconds"] = time.monotonic() - START
        write_json(out / "blanc.json", results)
        print("DIAGNOSTIC_SMOKE_DONE_NO_MEASURE")
        return
    results["bootstrap_md5_groups"] = dm.group_bootstrap(
        {"hf1_T_star": per_image["T_star"], "hf1_B_TZ": per_image["B_TZ"],
         "hf1_B_minus_T_star": np.subtract(per_image["B_TZ"], per_image["T_star"]),
         "exact_T_star": per_image["T_star_exact"], "exact_B_TZ": per_image["B_TZ_exact"]}, groups)
    results["error_overlap_T_star_vs_B_TZ"] = dm.error_overlap(
        gts, [preds["T_star"][i] for i in keep], [preds["B_TZ"][i] for i in keep],
        per_image["T_star"], per_image["B_TZ"])
    results["epoch_spread"] = {"T_star": journal_spread(bound(Path(binding["e0_root"]) / "journal_t_long.jsonl"), 5),
                               "B_TZ": journal_spread(bound(Path(binding["e3_root"]) / "journal_t_z.jsonl"), 5)}
    # Validation probabilities kept for later reviewed work (A1 needs B's); fp16, rows = validation order.
    np.savez_compressed(out / "probabilites_validation.npz", **{k: v.astype(np.float16) for k, v in probs.items()})
    write_json(out / "identites_validation.json", identities)
    results["files_sha256"] = {f: sha(out / f) for f in ("probabilites_validation.npz", "identites_validation.json")}
    results["script_sha256"] = {f: sha(here / f) for f in ("kaggle_diagnostic.py", "diag_metrics.py")}
    results["versions"] = {"python": sys.version.split()[0], "numpy": np.__version__, "torch": torch.__version__}
    results["wall_seconds"] = time.monotonic() - START
    write_json(out / "diagnostic.json", results)
    print("DIAGNOSTIC_DONE_VALIDATION_ONLY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--stage", choices=("smoke", "full"), required=True)
    try:
        main(parser.parse_args())
    except RuntimeError as error:
        print(f"DIAGNOSTIC_FAILED {error}", file=sys.stderr)
        sys.exit(1)
