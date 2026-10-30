"""Freeze eight prediction systems for the seven predeclared comparisons.

No test/development measure, threshold search, selection or verdict exists here.
Smoke consumes ICAI validation and Rijks dev only, never either test bank.
"""
import argparse
import gc
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import torch

from gel_common import (FEATURE_CONFIG, FROZEN_SHA, FULL_BANKS, GRID_CONFIG, RADIO, REVISION,
                        SMOKE_BANKS, SYSTEMS, Monitor, bound, fresh_or_resumable_output, object_sha,
                        projected_predictions, read_json, require, sha, write_json)
from gel_data import (Downloader, TrainingReference, encode, frozen_image_rows, icai_test_bank,
                      metadata, verify_radio)
from gel_models import (SpatialPooling, ancestor_pairs, load_checkpoint, ml_decoder,
                        probabilities, vector_head)


def rijks_features(rows, model, processor, out, monitor, mode):
    """Durable owned cache until the final prediction seal, then removed in full."""
    workspace = out / ".work"
    cache_dir = workspace / "image_features"
    cache_dir.mkdir(exist_ok=True)
    downloader = Downloader()
    result = {}
    for split, items in rows.items():
        vectors, grids = [], []
        for start in range(0, len(items), 32):
            chunk = items[start:start + 32]
            key = object_sha({"rows": chunk, "frozen_sha256": FROZEN_SHA, "feature_config": FEATURE_CONFIG,
                              "grid_config": GRID_CONFIG})
            file = cache_dir / f"{split}_{start:05d}.npz"
            side = file.with_suffix(".json")
            if side.exists():
                cache = read_json(side)
                require(cache["key"] == key and file.exists() and sha(file) == cache["sha256"], "encoded_cache_changed")
                with np.load(file, allow_pickle=False) as z:
                    v, g = z["vectors"], z["grids"]
            else:
                images = [downloader.image(row) for row in chunk]
                v, g = encode(model, processor, images)
                if mode == "smoke" and start == 0:
                    again_v, again_g = encode(model, processor, images)
                    require(np.array_equal(v, again_v) and np.array_equal(g, again_g), "encoder_repeat_not_identical")
                for image in images:
                    image.close()
                tmp = file.with_name(file.stem + ".tmp.npz")
                np.savez(tmp, vectors=v, grids=g)
                os.replace(tmp, file)
                write_json(side, {"key": key, "sha256": sha(file), "verified_image_bytes": True})
            require(v.shape == (len(chunk), 4096) and v.dtype == np.float16 and
                    g.shape == (len(chunk), 64, 1024) and g.dtype == np.float16 and
                    np.isfinite(v).all() and np.isfinite(g).all(), "encoded_cache_shape")
            vectors.append(v)
            grids.append(g)
            monitor.check("rijks_image_hash_and_encoding")
        name = "rijks_" + split + ("_smoke" if mode == "smoke" else "")
        result[name] = {"vectors": np.concatenate(vectors).astype(np.float32), "grids": np.concatenate(grids),
                        "identities": [{"index": j, "id": row["pid"], "image_sha256": row["image_sha256"]}
                                       for j, row in enumerate(items)]}
    return result


@torch.no_grad()
def votes(training, query, classes, monitor):
    reference = torch.from_numpy(training.x).cuda()
    result = np.zeros((len(query), classes), dtype=np.float32)
    # Exact E1 operations, batch, topk ordering, clipping and accumulation order.
    for start in range(0, len(query), 1024):
        q = torch.from_numpy(query[start:start + 1024]).cuda()
        weight, indices = (q @ reference.T).topk(20, dim=1)
        weight, indices = weight.clamp(min=0).cpu().numpy(), indices.cpu().numpy()
        for row in range(len(weight)):
            total = max(float(weight[row].sum()), 1e-9)
            for w, i in zip(weight[row], indices[row], strict=True):
                result[start + row, training.ancestor_indices[i]] += w / total
        monitor.check("training_neighbour_vote")
    del reference
    torch.cuda.empty_cache()
    require(np.isfinite(result).all(), "invalid_neighbour_vote")
    return result


def thresholds_by_depth(values, vocab):
    return np.array([values["1-2" if len(ancestors_for_depth(c)) <= 2 else
                            "3-4" if len(ancestors_for_depth(c)) <= 4 else "5+"] for c in vocab])


def ancestors_for_depth(code):
    # Sole notation parser; this wrapper has no access to image annotations.
    from gel_common import ancestors
    return ancestors(code)


def publish(out, bank_name, system, bank, prediction, recipe, weights, files):
    require(len(prediction) == len(bank["identities"]), "prediction_row_count")
    filename = f"predictions__{bank_name}__{system}.json"
    rows = [{**identity, "codes": codes} for identity, codes in zip(bank["identities"], prediction, strict=True)]
    require(not any(c.strip().startswith("86") for row in rows for c in row["codes"]), "chapter_86_projection")
    obj = {"bank": bank_name, "system": system, "parameters_frozen_on_validation": recipe,
           "weights_sha256": weights, "prediction_order": "threshold_then_most_specific_then_drop86",
           "rows": rows}
    write_json(out / filename, obj)
    files[filename] = {"sha256": sha(out / filename), "bank": bank_name, "system": system,
                       "rows": len(rows), "identity_order_sha256": object_sha(bank["identities"])}


def all_predictions(out, banks, training, recipe, paths, inventory, vocab, binding, monitor, mode):
    files = {}
    controls = {"TK_alpha1_identity": True,
                "head_repeat_identity": True if mode == "smoke" else "checked_in_approved_smoke"}
    # Two global heads; T* probabilities are reused by all E1 decisions.
    star_prob, star_pred = {}, {}
    for system in ("T0", "T_star"):
        ck = load_checkpoint(paths[system], inventory["weights"][system], vocab,
                             recipe[system]["epoch"], recipe[system]["threshold"], spatial=False)
        model = vector_head(len(vocab)).cuda().eval()
        model.load_state_dict(ck["state"], strict=True)
        del ck
        for name, bank in banks.items():
            p = probabilities(model, bank["vectors"], None, 4096)
            pred = projected_predictions(p, vocab, recipe[system]["threshold"])
            if mode == "smoke":
                repeat = probabilities(model, bank["vectors"], None, 4096)
                require(pred == projected_predictions(repeat, vocab, recipe[system]["threshold"]), "global_head_repeat")
            publish(out, name, system, bank, pred, recipe[system], inventory["weights"][system], files)
            if system == "T_star":
                star_prob[name], star_pred[name] = p, pred
        del model
        gc.collect()
        torch.cuda.empty_cache()
        monitor.check("global_head_inference")
    for name, bank in banks.items():
        p = star_prob[name]
        vote = votes(training, bank["vectors"], len(vocab), monitor)
        require(projected_predictions(1.0 * p + 0.0 * vote, vocab, recipe["T_star"]["threshold"]) == star_pred[name],
                "TK_alpha1_not_identical")
        for system in ("TK", "T-niv", "TK-niv"):
            spec = recipe[system]
            s = p if system == "T-niv" else spec["alpha"] * p + (1 - spec["alpha"]) * vote
            threshold = spec["threshold"] if system == "TK" else thresholds_by_depth(spec["thresholds"], vocab)
            pred = projected_predictions(s, vocab, threshold)
            publish(out, name, system, bank, pred, spec, inventory["weights"]["T_star"], files)
        monitor.check("frozen_E1_decisions")
    del star_prob, star_pred
    pairs = ancestor_pairs(vocab)
    for system in ("T-H", "T-Z", "T-D"):
        spec = recipe[system]
        spatial = system != "T-H"
        ck = load_checkpoint(paths[system], inventory["weights"][system], vocab, spec["epoch"], spec["threshold"], spatial)
        if system == "T-H":
            model = vector_head(len(vocab))
            require(ck["constraint"] == "max over descendants (ancestors() of the notation)", "TH_constraint_identity")
        elif system == "T-Z":
            model = SpatialPooling(len(vocab))
        else:
            model = ml_decoder(binding["mldec_py"], inventory["mldec_sha256"], len(vocab), ck)
        model.load_state_dict(ck["state"], strict=True)
        if system == "T-D":
            require(np.array_equal(model.slot_of_class.cpu().numpy(), ck["slot_of_class"]), "loaded_decoder_permutation")
        del ck
        model = model.cuda().eval()
        for name, bank in banks.items():
            p = probabilities(model, bank["vectors"], bank["grids"] if spatial else None,
                              256 if spatial else 1024, constrained=system == "T-H", pairs=pairs)
            pred = projected_predictions(p, vocab, spec["threshold"])
            if mode == "smoke":
                repeated = probabilities(model, bank["vectors"], bank["grids"] if spatial else None,
                                         256 if spatial else 1024, constrained=system == "T-H", pairs=pairs)
                require(pred == projected_predictions(repeated, vocab, spec["threshold"]), "spatial_or_constraint_head_repeat")
            publish(out, name, system, bank, pred, spec, inventory["weights"][system], files)
        del model
        gc.collect()
        torch.cuda.empty_cache()
        monitor.check("spatial_or_constraint_head_inference")
    return files, controls


def main(args):
    require(os.environ.get("PHASE1_REVIEWED_MODE") == args.mode and os.environ.get("PHASE1_CODE_SHA256"),
            "use_reviewed_pilot")
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1 and
            "T4" in torch.cuda.get_device_name(), "single_visible_T4_required")
    # Preserve E0-E3 inference precision; do not introduce AMP into frozen heads.
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(0)
    np.random.seed(0)
    binding_path, inventory_path = bound(args.binding), bound(args.inventory)
    binding, inventory = read_json(binding_path), read_json(inventory_path)
    require(inventory["frozen_sha256"] == FROZEN_SHA, "inventory_bench_identity")
    identity = {"mode": args.mode, "binding_sha256": sha(binding_path), "inventory_sha256": sha(inventory_path),
                "code_manifest_sha256": os.environ["PHASE1_CODE_SHA256"],
                "versions": read_json(bound(args.versions))["approved_versions"],
                "feature_config": FEATURE_CONFIG, "grid_config": GRID_CONFIG}
    out, already_sealed = fresh_or_resumable_output(args.out, identity)
    if already_sealed:
        return
    monitor = Monitor(out, 3500 if args.mode == "smoke" else 14300)
    recipe, paths = metadata(binding, inventory)
    # All checkpoint/doc hashes verified before any test or frozen image is consumed.
    t0 = torch.load(bound(paths["T0"]), map_location="cpu", weights_only=False)
    vocab = list(t0["vocab"])
    require(len(vocab) == 7907 and len(set(vocab)) == 7907, "historical_vocabulary")
    del t0
    training = TrainingReference(binding["encoder_root"], inventory, vocab, monitor)
    radio_sources = verify_radio(binding["radio_hf_cache"], inventory)
    rows = frozen_image_rows(binding["frozen_json"], args.mode)
    from transformers import AutoModel, CLIPImageProcessor
    model = AutoModel.from_pretrained(RADIO, revision=REVISION, code_revision=REVISION, trust_remote_code=True,
                                     cache_dir=str(bound(binding["radio_hf_cache"])), local_files_only=True,
                                     use_safetensors=True, token=False).cuda().eval()
    processor = CLIPImageProcessor.from_pretrained(RADIO, revision=REVISION,
                                                   cache_dir=str(bound(binding["radio_hf_cache"])),
                                                   local_files_only=True, token=False)
    banks = rijks_features(rows, model, processor, out, monitor, args.mode)
    del model, processor, rows
    gc.collect()
    torch.cuda.empty_cache()
    if args.mode == "smoke":
        banks["icai_validation_smoke"] = training.smoke_bank(inventory)
    else:
        banks["icai_test"] = icai_test_bank(binding["encoder_root"], inventory)
    expected_banks = SMOKE_BANKS if args.mode == "smoke" else FULL_BANKS
    require(set(banks) == set(expected_banks), "prediction_bank_allowlist")
    files, controls = all_predictions(out, banks, training, recipe, paths, inventory, vocab, binding, monitor, args.mode)
    require({(info["bank"], info["system"]) for info in files.values()} ==
            {(bank, system) for bank in expected_banks for system in SYSTEMS}, "incomplete_prediction_family")
    for filename, info in files.items():
        require(sha(out / filename) == info["sha256"], "prediction_changed_before_seal")
    monitor.check("before_prediction_seal")
    result = {"schema": "architecture-predictions/v1", "run_identity": identity,
              "mode": args.mode, "predictions_frozen": args.mode == "freeze", "technical_pass": True,
              "scope": "predictions_only_no_measures_no_verdicts", "files": files,
              "systems": list(SYSTEMS), "banks": list(expected_banks), "recipes": recipe,
              "source_documents_sha256": inventory["documents"], "weights_sha256": inventory["weights"],
              "frozen_bench_sha256": FROZEN_SHA, "vocabulary_sha256": object_sha(vocab),
              "training_neighbour_order_sha256": training.fit_order_sha, "radio_files_sha256": radio_sources,
              "controls": controls, "resources": monitor.events, "gpu": torch.cuda.get_device_name(),
              "family": [["T_star", "T0"]] + [[s, "T_star"] for s in ("TK", "T-niv", "TK-niv", "T-H", "T-Z", "T-D")],
              "TK_niv_activation": "deferred_to_unopened_verdicts_TK_and_Tniv_both_retained",
              "input_rows_kept_without_truth_filtering": True}
    # ONLY prediction files and the final manifest survive a successful run.
    shutil.rmtree(out / ".work")
    require({p.name for p in out.iterdir()} == set(files), "unexpected_final_output")
    write_json(out / "MANIFEST.json", result)  # seal is published last, atomically


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binding", "inventory", "versions", "out"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--mode", choices=("smoke", "freeze"), required=True)
    try:
        main(parser.parse_args())
    except Exception:
        # No traceback: a network/decoder exception may contain a frozen image URL.
        print("PHASE1_PREDICTION_FREEZE_FAILED", file=sys.stderr)
        sys.exit(1)
