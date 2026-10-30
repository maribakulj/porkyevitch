"""A1-dev on Kaggle T4 (PREINSCRIPTION.md, D17): the frozen q-threshold rule of A1's secondary analysis (K 16, tau 0.02,
eta 1, pi0 0.25, t 0.3, sealed in reglage.json) measured ONCE on the Rijksmuseum dev, against B = T-Z (main) and T* (frozen
reference). Reuses unchanged: a1_run.Data / Image and a1_core.threshold_control (A1, pinned), the reviewed freeze code
(gel_*.py, pinned) for the dev encoding and the two heads, and D10's dev-only decoding of frozen.json. Five identity
controls come before any measure. No test file is opened, nothing is tuned.

Usage: a1dev_run.py --gel-code DIR --binding sources.json --gel-inventory ENTREES_GELEES.json --a1-inventory
       ENCODAGE_TRAIN_V3.json --encoder ENC --diag DIAG --seal DIR --out OUT
"""
import argparse
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a1_core as a1  # noqa: E402
import a1_run as a1r  # noqa: E402
import a1dev_core as dc  # noqa: E402

RULE = {"K": 16, "tau": 0.02, "eta": 1, "pi0": 0.25, "t": 0.3}  # reglage.json secondary_threshold_control (8f75d500)
VALIDATION_H = 0.6101628934369521  # diagnostic.json H.threshold_own_q (6adb2404)
GEL_INVENTORY_SHA256 = "6bde822932f9a288d9bd764cc950e160e16e1c78fb5456df28b51bfd6acd6604"
SEAL_SHA256 = "3c468faa7bec5ac7a98104a4ac47d3f7be24ec9ef76e0855f49b42aad12fad0c"
DEV_KEY = b'\n "dev": '


def dev_items(path, sha, require):
    """D10's nt_run.dev_items, unchanged: the "dev" member of frozen.json decoded alone; the test member, which precedes
    it, is never JSON-decoded nor UTF-8-decoded; the value must end exactly at the next top-level key."""
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
        require(it["truth_projected"] == list(dict.fromkeys(a1.drop86(it["truth"]))) and it["truth_projected"],
                "dev_projection")
    return items


def nt_frozen_sha():
    from gel_common import FROZEN_SHA
    return FROZEN_SHA


class DevData(a1r.Data):
    """A1's Data, unchanged, keeping the unit training vectors that its __init__ passes to neighbours() so that the dev
    queries get their neighbours by the very same function."""
    def neighbours(self, xf, xv, nf, nv, kmax=64):
        self.xf_unit, self.nf_train = xf, nf
        return super().neighbours(xf, xv, nf, nv, kmax)


def dev_view(data, p_b, b_pred, xd):
    """The attributes a1_run.Image reads, for the dev queries: B's probabilities and sets, neighbours and cosines by
    a1_run.Data.neighbours on unit float32 vectors, the training footprints, the vocabulary."""
    xd = np.asarray(xd, dtype=np.float32)
    nd = np.linalg.norm(xd, axis=1)
    xd = xd / nd[:, None]
    ns = SimpleNamespace()
    overlap = a1r.Data.neighbours(ns, data.xf_unit, xd, data.nf_train, nd)
    return SimpleNamespace(pb=p_b, b_pred=b_pred, nn=ns.nn, cos=ns.cos, footprint=data.footprint, vi=data.vi,
                           vocab=data.vocab), overlap


def rule_sets(view, rows, pi0=RULE["pi0"]):
    return [a1.threshold_control(a1r.Image(view, k, RULE["K"]).set_q(RULE["tau"], RULE["eta"], pi0), RULE["t"])
            for k in rows]


def jsonable(obj):
    if isinstance(obj, dict):
        return {k if isinstance(k, str) else str(jsonable(k)): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def main(a):
    import torch
    from gel_common import Monitor, bound, read_json, require, sha, write_json, projected_predictions, object_sha
    from gel_data import metadata, verify_radio
    from gel_models import SpatialPooling, load_checkpoint, probabilities, vector_head
    from gel_predictions import rijks_features
    require(os.environ.get("A1DEV_REVIEWED_STAGE") == "dev", "use_reviewed_pilot")
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1 and "T4" in torch.cuda.get_device_name(),
            "single_visible_T4_required")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    out = Path(a.out).resolve()
    require(Path("/kaggle/working") in out.parents and not out.exists(), "fresh_output_required")
    (out / ".work").mkdir(parents=True)
    monitor = Monitor(out, 3400)
    binding_path, gel_inv = bound(a.binding), bound(a.gel_inventory)
    require(sha(gel_inv) == GEL_INVENTORY_SHA256, "gel_inventory_identity")
    binding, inventory = read_json(binding_path), read_json(gel_inv)
    recipe, paths = metadata(binding, inventory)

    # (control 4) A1's data and the frozen rule on V-diagnostic: reproduce 0.6101628934369521
    data = DevData(a.encoder, a.a1_inventory, a.diag)
    monitor.check("a1dev_data")
    rows = [k for k in data.diag if data.truth[k]]
    h_val = float(np.mean([a1.hier_f1(data.truth[k], s) for k, s in zip(rows, rule_sets(data, rows), strict=True)]))
    require(abs(h_val - VALIDATION_H) <= 1e-12, "control4_validation_rule_not_reproduced")
    monitor.check("a1dev_control4")

    # (control 1) the dev only, re-encoded with the freeze recipe (vectors and grids)
    items = dev_items(bound(binding["frozen_json"]), sha, require)
    radio = verify_radio(binding["radio_hf_cache"], inventory)
    from transformers import AutoModel, CLIPImageProcessor
    from gel_common import RADIO, REVISION
    cache = str(bound(binding["radio_hf_cache"]))
    model = AutoModel.from_pretrained(RADIO, revision=REVISION, code_revision=REVISION, trust_remote_code=True,
                                      cache_dir=cache, local_files_only=True, use_safetensors=True, token=False).cuda().eval()
    processor = CLIPImageProcessor.from_pretrained(RADIO, revision=REVISION, cache_dir=cache, local_files_only=True,
                                                   token=False)
    rows_dev = {"dev": [{k: it[k] for k in ("pid", "iiif", "image_sha256", "width", "height")} for it in items]}
    dev = rijks_features(rows_dev, model, processor, out, monitor, "freeze")["rijks_dev"]
    del model, processor
    torch.cuda.empty_cache()
    require(list(data.vocab) == list(torch.load(bound(paths["T0"]), map_location="cpu", weights_only=False)["vocab"]),
            "vocabulary_identity")

    # (controls 2, 3) B = T-Z on the grids and T* on the vectors reproduce the sealed dev predictions exactly
    seal = Path(bound(a.seal))
    require(sha(seal / "MANIFEST.json") == SEAL_SHA256, "seal_identity")
    files = read_json(seal / "MANIFEST.json")["files"]
    sealed = {}
    for system in ("T-Z", "T_star"):
        name = f"predictions__rijks_dev__{system}.json"  # only these two dev files of the seal are opened
        info = files[name]
        require(info["bank"] == "rijks_dev" and info["system"] == system and sha(seal / name) == info["sha256"],
                "sealed_dev_file")
        r = read_json(seal / name)["rows"]
        require([{k: x[k] for k in ("index", "id", "image_sha256")} for x in r] == dev["identities"] and
                object_sha(dev["identities"]) == info["identity_order_sha256"], "dev_identity_order")
        sealed[system] = [x["codes"] for x in r]
    vocab = list(data.vocab)
    ck = load_checkpoint(paths["T-Z"], inventory["weights"]["T-Z"], vocab, recipe["T-Z"]["epoch"], recipe["T-Z"]["threshold"],
                         spatial=True)
    tz = SpatialPooling(len(vocab))
    tz.load_state_dict(ck["state"], strict=True)
    del ck
    p_b = probabilities(tz.cuda().eval(), dev["vectors"], dev["grids"], 256)
    del tz
    ck = load_checkpoint(paths["T_star"], inventory["weights"]["T_star"], vocab, recipe["T_star"]["epoch"],
                         recipe["T_star"]["threshold"], spatial=False)
    head = vector_head(len(vocab)).cuda().eval()
    head.load_state_dict(ck["state"], strict=True)
    del ck
    p_star = probabilities(head, dev["vectors"], None, 4096)
    del head
    torch.cuda.empty_cache()
    controls = {}
    for system, mine in (("T-Z", projected_predictions(p_b, vocab, recipe["T-Z"]["threshold"])),
                         ("T_star", projected_predictions(p_star, vocab, recipe["T_star"]["threshold"]))):
        differ = sum(sorted(s) != sorted(m) for s, m in zip(sealed[system], mine, strict=True))
        controls[system] = {"images": len(mine), "differing": differ}
        require(differ == 0, f"control_{system}_dev_not_reproduced_{differ}")
    b_pred = a1.project(np.asarray(p_b, dtype=np.float32), vocab, 0.65)  # A1's own projection of B (float32 threshold)
    require(all(sorted(x) == sorted(y) for x, y in zip(b_pred, sealed["T-Z"], strict=True)), "A1_projection_of_B_differs")
    monitor.check("a1dev_controls_2_3")

    # (control 5) pi0 = 1 gives exactly B on the dev; then the frozen rule, once
    view, overlap = dev_view(data, np.asarray(p_b, dtype=np.float32), b_pred, dev["vectors"])
    k_dev = list(range(len(items)))
    require(all(s == sorted(b) for s, b in zip(rule_sets(view, k_dev, pi0=1.0), b_pred, strict=True)),
            "control5_pi0_one_not_B")
    rule = rule_sets(view, k_dev)
    monitor.check("a1dev_rule")

    truth = [it["truth_projected"] for it in items]
    require(all(truth), "dev_truth_empty")  # every dev image is evaluable (bench rule); the denominator is fixed
    h = {"rule": [a1.hier_f1(t, s) for t, s in zip(truth, rule)],
         "B": [a1.hier_f1(t, s) for t, s in zip(truth, sealed["T-Z"])],
         "T_star": [a1.hier_f1(t, s) for t, s in zip(truth, sealed["T_star"])]}
    h["rule_minus_B"] = list(np.subtract(h["rule"], h["B"]))
    h["rule_minus_T_star"] = list(np.subtract(h["rule"], h["T_star"]))
    components = [it["component"] for it in items]
    boot = dc.component_bootstrap(h, components)
    exact = {k: float(np.mean([a1.exact_e(t, x) for t, x in zip(truth, s, strict=True)])) for k, s in
             (("rule", rule), ("B", sealed["T-Z"]), ("T_star", sealed["T_star"]))}  # E, per-image exact F1, mean
    near = ["cos >= 0.95" if view.cos[k, 0] >= 0.95 else "cos < 0.95" for k in k_dev]
    write_json(out / "dev.json", jsonable({
        "stage": "a1_dev_rijksmuseum", "exploratory": True, "test_rows": 0, "rule": RULE,
        "population": {"images": len(items), "evaluable": len(truth), "components": len(set(components))},
        "H": {k: float(np.mean(v)) for k, v in h.items() if k in ("rule", "B", "T_star")},
        "main_contrast_rule_minus_B": {**boot["contrasts"]["rule_minus_B"], **dc.reading(boot["contrasts"]["rule_minus_B"])},
        "reference_contrast_rule_minus_T_star": boot["contrasts"]["rule_minus_T_star"],
        "bootstrap": {k: v for k, v in boot.items() if k != "contrasts"},
        "gains_losses_vs_B": dc.gains_losses(h["rule"], h["B"]),
        "by_support_descriptive": {k: dc.strata(h[k], [it["support"] for it in items]) for k in ("rule", "B", "T_star")},
        "proximity_descriptive": {"rule_minus_B": dc.strata(h["rule_minus_B"], near),
                                  "read_as": "strong proximity, not proof of copying"},
        "exact_f1_descriptive": exact,
        "identity_controls": {"validation_rule_H": h_val, "dev": controls, "A1_projection_of_B": True,
                              "pi0_one_gives_B_on_dev": True},
        "neighbour_top20_overlap_with_TK_dot": overlap,
        "inputs": {"seal_sha256": SEAL_SHA256, "gel_inventory_sha256": GEL_INVENTORY_SHA256, "radio_files_sha256": radio,
                   "frozen_sha256": nt_frozen_sha()},
        "versions": {**a1r.versions(), "torch": torch.__version__}}))
    import shutil
    shutil.rmtree(out / ".work" / "image_features", ignore_errors=True)
    monitor.check("a1dev_done")
    print("A1DEV_DONE_EXPLORATORY")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("gel-code", "binding", "gel-inventory", "a1-inventory", "encoder", "diag", "seal", "out"):
        p.add_argument(f"--{k}", required=True)
    args = p.parse_args()
    sys.path.insert(0, str(Path(args.gel_code).resolve()))
    try:
        main(args)
    except RuntimeError as e:
        print(f"A1DEV_FAILED {e}", file=sys.stderr)
        sys.exit(1)
