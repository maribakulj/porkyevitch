"""Non-transfer diagnostic on Kaggle T4 (PREINSCRIPTION.md): Rijksmuseum dev (301 images) and ICAI validation (4 265 rows)
only. Reuses the reviewed phase-1 freeze code (gel_*.py, pinned) for the training reference, the C-RADIO encoding of the
dev images, the T* head and the TK vote; two identity controls (T* and TK on the re-encoded dev = the sealed dev
predictions, exactly) come before any measure. No test file is opened: the Rijksmuseum bench is decoded from its "dev"
member only (the test member, placed before it in the file, is never decoded), and only the two dev prediction files of
the seal are read. Descriptive: no choice, no threshold, no verdict.

Usage: nt_run.py --gel-code DIR --binding sources.json --inventory ENTREES_GELEES.json --seal DIR --diag DIR --out OUT
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nt_core as nt  # noqa: E402
import mesure_metrics as mm  # noqa: E402

INVENTORY_SHA256 = "6bde822932f9a288d9bd764cc950e160e16e1c78fb5456df28b51bfd6acd6604"
SEAL_SHA256 = "3c468faa7bec5ac7a98104a4ac47d3f7be24ec9ef76e0855f49b42aad12fad0c"
DIAG = {"probabilites_validation.npz": "c7df9d3dd28acea7454cf7609cf083fe961fa5ff5a7ef121a85fc1d7c2eedbe9",
        "identites_validation.json": "9ce6a35f4b82c237cb992b7c1106d7ab3ffe68045b8c54cae91f9c529df83312",
        "vocabulaire.json": "5e3f201c90f7ae38277e9915fff4c677e651bcfb75977405d1e3eff01ac89a19"}
STAR_VALIDATION_DECISIONS = "2d7140eeaa9e1d249985a63dd6048c35f84af825832fb41f36a90066df795531"
K, RANDOM_SEED, DRAWS = 20, 20261031, 10_000
BOOT_SEED = {"rijks_dev": 20261032, "icai_validation": 20261033}
DEV_KEY = b'\n "dev": '


def dev_items(path, sha, require):
    """The "dev" member of frozen.json, decoded alone. The file is hashed whole; the test member, which precedes "dev",
    is never JSON-decoded nor UTF-8-decoded. The decoded value must end exactly at the next top-level key."""
    raw = Path(path).read_bytes()
    require(sha(path) == nt_frozen_sha(), "rijks_frozen_sha")
    require(raw.count(DEV_KEY) == 1, "dev_member_not_unique")
    start = raw.index(DEV_KEY) + len(DEV_KEY)
    tail = raw[start:].decode("utf-8")
    dev, end = json.JSONDecoder().raw_decode(tail)
    require(tail[end:].startswith(',\n "'), "dev_member_boundary")
    del raw, tail
    items = dev["items"]
    require(300 <= len(items) <= 319 and len({it["pid"] for it in items}) == len(items), "dev_structure")
    for it in items:
        require(it["truth_projected"] == list(dict.fromkeys(mm.drop86(it["truth"]))) and it["truth_projected"],
                "dev_projection")
    return items


def nt_frozen_sha():
    from gel_common import FROZEN_SHA
    return FROZEN_SHA


def neighbours(training, query, monitor):
    """The 20 training neighbours exactly as gel_predictions.votes: same matmul, topk, clamp, batches of 1 024."""
    import torch
    reference = torch.from_numpy(training.x).cuda()
    weights, indices = [], []
    with torch.no_grad():
        for start in range(0, len(query), 1024):
            q = torch.from_numpy(query[start:start + 1024]).cuda()
            w, i = (q @ reference.T).topk(K, dim=1)
            weights.append(w.clamp(min=0).cpu().numpy())
            indices.append(i.cpu().numpy())
            monitor.check("nt_neighbours")
    del reference
    torch.cuda.empty_cache()
    return np.concatenate(weights), np.concatenate(indices)


def validation_rows(root, inventory, require, sha, legacy_sha, read_json):
    """Validation vectors, labels and identities in the historical order (same split as gel_data.TrainingReference),
    plus the raw per-image training counts n_brut and the training order."""
    from gel_common import TRAIN
    xs, labels, md5s, where = [], [], [], []
    for shard, tag in enumerate(TRAIN):
        expected = inventory["shards"][tag]
        for sub, ext, key in (("feats", "npz", "vec_sha256"), ("grid", "json", "grid_json_sha256")):
            require(sha(Path(root) / sub / f"{tag}.{ext}") == expected[key], "train_source_sha")
        side = read_json(Path(root) / "grid" / f"{tag}.json")
        with np.load(Path(root) / "feats" / f"{tag}.npz", allow_pickle=False) as z:
            x, md5 = z["x"], z["md5"].tolist()
        require(legacy_sha(md5) == side["md5_sha256"] and len(side["labels"]) == len(md5) == len(x), "train_alignment")
        xs.append(x)
        md5s.extend(md5)
        labels.extend(side["labels"])
        where.extend((tag, r) for r in range(len(md5)))
    groups = sorted(set(md5s))
    gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
    val = np.array([m in gval for m in md5s])
    require(int(val.sum()) == 4265 and int((~val).sum()) == 81951, "historical_split")
    counts = Counter(c for y, v in zip(labels, val, strict=True) if not v for c in set(y))
    rows = np.flatnonzero(val)
    x_val = np.concatenate(xs)[rows].astype(np.float32)
    ids = [{"shard": where[i][0], "row": int(where[i][1]), "md5": md5s[i]} for i in rows]
    fit_order = [[where[i][0], where[i][1], md5s[i]] for i in np.flatnonzero(~val)]
    return x_val, [labels[i] for i in rows], ids, counts, fit_order


def project32(prob, vocab, threshold):
    """The diagnostic's projection (threshold cast to the probabilities' dtype, most_specific, drop86)."""
    from gel_common import most_specific
    t = np.asarray(threshold, dtype=prob.dtype)
    return [mm.drop86(most_specific([vocab[j] for j in np.flatnonzero(row >= t)])) for row in prob]


def main(a):
    import torch
    from gel_common import Monitor, bound, legacy_sha, object_sha, read_json, require, sha, write_json, projected_predictions
    from gel_data import TrainingReference, metadata, verify_radio
    from gel_models import load_checkpoint, probabilities, vector_head
    from gel_predictions import rijks_features, votes
    require(os.environ.get("NT_REVIEWED_STAGE") == "diagnostic", "use_reviewed_pilot")
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1 and "T4" in torch.cuda.get_device_name(),
            "single_visible_T4_required")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    out = Path(a.out).resolve()
    require(Path("/kaggle/working") in out.parents and not out.exists(), "fresh_output_required")
    (out / ".work").mkdir(parents=True)
    monitor = Monitor(out, 3500)
    binding_path, inventory_path = bound(a.binding), bound(a.inventory)
    require(sha(inventory_path) == INVENTORY_SHA256, "inventory_identity")
    binding, inventory = read_json(binding_path), read_json(inventory_path)
    recipe, paths = metadata(binding, inventory)
    t0 = torch.load(bound(paths["T0"]), map_location="cpu", weights_only=False)
    vocab = list(t0["vocab"])
    del t0
    diag = Path(bound(a.diag))
    for f, want in DIAG.items():
        require(sha(diag / f) == want, f"diag_{f}")
    require(read_json(diag / "vocabulaire.json") == vocab and len(vocab) == 7907, "vocabulary_identity")
    training = TrainingReference(binding["encoder_root"], inventory, vocab, monitor)
    anc = [set(map(int, s)) for s in training.ancestor_indices]
    x_val, val_labels, val_ids, counts, fit_order = validation_rows(bound(binding["encoder_root"]), inventory, require,
                                                                    sha, legacy_sha, read_json)
    require(object_sha(fit_order) == training.fit_order_sha, "training_order_identity")
    require(read_json(diag / "identites_validation.json") == val_ids, "validation_order_identity")
    monitor.check("nt_inputs")

    # ---- ICAI validation: T* from the reviewed float32 cache, TK = alpha T* + (1 - alpha) vote (E1 recipe)
    with np.load(diag / "probabilites_validation.npz", allow_pickle=False) as z:
        p_val = z["T_star"]
    star_val = project32(p_val, vocab, recipe["T_star"]["threshold"])
    require(legacy_sha([sorted(q) for q in star_val]) == STAR_VALIDATION_DECISIONS, "tstar_validation_decisions")
    alpha, tk_t = recipe["TK"]["alpha"], recipe["TK"]["threshold"]
    w_val, i_val = neighbours(training, x_val, monitor)
    v_val = votes(training, x_val, len(vocab), monitor)
    s_val = alpha * p_val + (1 - alpha) * v_val
    tk_val = projected_predictions(s_val, vocab, tk_t)

    # ---- Rijksmuseum dev: decoded alone, re-encoded with the freeze recipe, two identity controls
    items = dev_items(bound(binding["frozen_json"]), sha, require)
    radio_sources = verify_radio(binding["radio_hf_cache"], inventory)
    from transformers import AutoModel, CLIPImageProcessor
    from gel_common import RADIO, REVISION
    cache = str(bound(binding["radio_hf_cache"]))
    model = AutoModel.from_pretrained(RADIO, revision=REVISION, code_revision=REVISION, trust_remote_code=True,
                                      cache_dir=cache, local_files_only=True, use_safetensors=True, token=False).cuda().eval()
    processor = CLIPImageProcessor.from_pretrained(RADIO, revision=REVISION, cache_dir=cache, local_files_only=True,
                                                   token=False)
    rows = {"dev": [{k: it[k] for k in ("pid", "iiif", "image_sha256", "width", "height")} for it in items]}
    dev = rijks_features(rows, model, processor, out, monitor, "freeze")["rijks_dev"]
    del model, processor
    torch.cuda.empty_cache()
    ck = load_checkpoint(paths["T_star"], inventory["weights"]["T_star"], vocab, recipe["T_star"]["epoch"],
                         recipe["T_star"]["threshold"], spatial=False)
    head = vector_head(len(vocab)).cuda().eval()
    head.load_state_dict(ck["state"], strict=True)
    del ck
    p_dev = probabilities(head, dev["vectors"], None, 4096)
    del head
    star_dev = projected_predictions(p_dev, vocab, recipe["T_star"]["threshold"])
    w_dev, i_dev = neighbours(training, dev["vectors"], monitor)
    v_dev = votes(training, dev["vectors"], len(vocab), monitor)
    s_dev = alpha * p_dev + (1 - alpha) * v_dev
    tk_dev = projected_predictions(s_dev, vocab, tk_t)
    seal = Path(bound(a.seal))
    require(sha(seal / "MANIFEST.json") == SEAL_SHA256, "seal_identity")
    files = read_json(seal / "MANIFEST.json")["files"]
    controls = {}
    for system, mine in (("T_star", star_dev), ("TK", tk_dev)):
        name = f"predictions__rijks_dev__{system}.json"
        info = files[name]  # only the two dev files of the seal are opened
        require(info["bank"] == "rijks_dev" and info["system"] == system and sha(seal / name) == info["sha256"],
                "sealed_dev_file")
        sealed = read_json(seal / name)["rows"]
        require([{k: r[k] for k in ("index", "id", "image_sha256")} for r in sealed] == dev["identities"] and
                object_sha(dev["identities"]) == info["identity_order_sha256"], "dev_identity_order")
        differ = sum(sorted(r["codes"]) != sorted(m) for r, m in zip(sealed, mine, strict=True))
        controls[system] = {"images": len(sealed), "differing": differ}
        require(differ == 0, f"{system}_dev_not_reproduced_{differ}")
    monitor.check("nt_dev_controls")

    # ---- the same pairs, the same measures on both banks
    rng = np.random.default_rng(RANDOM_SEED)
    n_fit = len(anc)
    rand_val = [rng.choice(n_fit, K, replace=False) for _ in range(len(val_ids))]
    rand_dev = [rng.choice(n_fit, K, replace=False) for _ in range(len(items))]
    vt = [list(dict.fromkeys(mm.drop86(y))) for y in val_labels]
    banks = {
        "rijks_dev": {"truths": [it["truth_projected"] for it in items], "star": star_dev, "star_prob": p_dev,
                      "tk": tk_dev, "tk_score": s_dev, "nn_weight": w_dev, "nn_index": i_dev, "rand_index": rand_dev,
                      "groups": [it["component"] for it in items], "vote": v_dev},
        "icai_validation": {"truths": vt, "star": star_val, "star_prob": p_val, "tk": tk_val, "tk_score": s_val,
                            "nn_weight": w_val, "nn_index": i_val, "rand_index": rand_val,
                            "groups": [r["md5"] for r in val_ids], "vote": v_val}}
    keep = [k for k, t in enumerate(vt) if t]  # 4 241 evaluable rows, as in every validation measure
    require(len(keep) == 4241, "validation_evaluable_rows")
    b = banks["icai_validation"]
    for key in ("truths", "star", "tk", "rand_index", "groups"):
        b[key] = [b[key][k] for k in keep]
    for key in ("star_prob", "tk_score", "nn_weight", "nn_index", "vote"):
        b[key] = b[key][keep]
    rec = {"alpha": alpha, "tk_threshold": tk_t, "star_threshold": recipe["T_star"]["threshold"]}
    reports, codes = {}, {}
    for name, bank in banks.items():
        records, rep = nt.bank_report(bank, vocab, counts, anc, rec, DRAWS, BOOT_SEED[name])
        vi = {c: j for j, c in enumerate(vocab)}
        gap = max((abs(r["vote"] - float(bank["vote"][r["image"]][vi[r["code"]]])) for r in records), default=0.0)
        require(gap <= 1e-5, "vote_recomputation")  # the per-pair vote equals the vote matrix of TK
        rep["vote_recomputation_max_gap"] = gap
        reports[name], codes[name] = rep, rep["per_code_main"]
        monitor.check(f"nt_measures_{name}")
    common = {e: nt.common_codes(codes["rijks_dev"], codes["icai_validation"], e)
              for e in ("head_closure", "head_exact", "vote_available")}
    allowed = {it["pid"] for it in items}
    write_json(out / "diagnostic.json", {
        "stage": "diagnostic_non_transfert", "descriptive_only": True, "test_rows": 0,
        "banks": reports, "common_codes_main_macro": {"a": "rijks_dev", "b": "icai_validation", **common},
        "identity_controls_dev": controls, "recipe": {"T_star": recipe["T_star"], "TK": recipe["TK"], "K": K},
        "random_control": {"seed": RANDOM_SEED, "per_query": K, "rule": "20 distinct training rows, uniform"},
        "inputs": {"inventory_sha256": INVENTORY_SHA256, "seal_sha256": SEAL_SHA256, "diag": DIAG,
                   "frozen_sha256": nt_frozen_sha(), "radio_files_sha256": radio_sources,
                   "training_order_sha256": training.fit_order_sha},
        "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "torch": torch.__version__},
        "dev_identifiers_only": sorted(allowed) == sorted(r["id"] for r in dev["identities"])})
    import shutil
    shutil.rmtree(out / ".work" / "image_features", ignore_errors=True)
    monitor.check("nt_done")
    print("NT_DIAGNOSTIC_DONE_DESCRIPTIVE")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("gel-code", "binding", "inventory", "seal", "diag", "out"):
        p.add_argument(f"--{k}", required=True)
    args = p.parse_args()
    sys.path.insert(0, str(Path(args.gel_code).resolve()))
    try:
        main(args)
    except RuntimeError as e:
        print(f"NT_FAILED {e}", file=sys.stderr)
        sys.exit(1)
