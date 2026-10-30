"""Phase 1 measures and verdicts on the sealed predictions (porkyevitch-maths, experiences/2026-10-30-mesure-phase1).
Kaggle CPU. Rules: architecture preregistration (sha 5115c3a5...), amendment 4; nothing is chosen here.

Usage:
  mesure_phase1.py --stage dev  --seal SEAL --frozen FROZEN --inputs ENTREES --encoder ENC --iconclass ICON --out OUT
  mesure_phase1.py --stage test --seal SEAL --frozen FROZEN --inputs ENTREES --encoder ENC --iconclass ICON --out OUT
                   --dev DEVOUT --receipt RECEIPT
  SEAL     the sealed freeze folder: MANIFEST.json (sha 3c468faa...) and its 24 prediction files
  FROZEN   Rijksmuseum frozen.json (sha 2424b778...): truths, components, supports
  ENTREES  ENTREES_GELEES.json of the freeze (sha below): pinned shard hashes
  ENC      full output of caypollard-encode-cradio v3 (train label sidecars; ICAI test labels in the test stage only)
  ICON     root of the Iconclass data repository (txt/en/*.txt, git blobs pinned) for the plates
dev  : Rijksmuseum dev only. Test prediction files are hashed, never parsed; no test truth is read. Writes the diagnostic
       D and the 12-image plates of every comparison, then dev/MANIFEST_DEV.json.
test : refuses to start without a viewing receipt of those plates. Opens ICAI test and Rijksmuseum test, computes the
       verdicts first (six comparisons, then TK-niv only if TK and T-niv are both retained), writes verdicts.json, then the
       descriptive measures and D on the tests.
"""
import argparse
from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesure_metrics as mm  # noqa: E402

SEAL_SHA256 = "3c468faa7bec5ac7a98104a4ac47d3f7be24ec9ef76e0855f49b42aad12fad0c"
FROZEN_SHA256 = "2424b778d0a3e7c36e0aeea7ce5db60fcc52bc1eaa6c52a057fd957b142de0ca"
ENTREES_SHA256 = "6bde822932f9a288d9bd764cc950e160e16e1c78fb5456df28b51bfd6acd6604"  # the freeze's ENTREES_GELEES.json
PROTOCOL_SHA256 = "5115c3a5654f303723161c1eed0bd0dc3dac98c54ba8a5f21df384a6337186cb"
VOCABULARY_SHA256 = "e410341477888d3b6b25642ff04c317b92377bd7b4d09a39a21d0b1d240435ae"
SYSTEMS = ["T0", "T_star", "TK", "T-niv", "TK-niv", "T-H", "T-Z", "T-D"]
TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
TEST = "test-00000-of-00001"
ICAI_T0_HIST = 0.5459  # preregistration: ICAI 787 images, T0 = 0.5459 (control, four decimals)
ENGLISH_BLOBS = {
    "txt/en/txt_en_0_1.txt": "4335f2fd430b656509916b6952e12e3f39af0b92",
    "txt/en/txt_en_2_3.txt": "7938c9017de7755d907e2c8a747abceb7f45ce4e",
    "txt/en/txt_en_4.txt": "7b524547b7f3b5594de6d5bdbdb275668e43c668",
    "txt/en/txt_en_5_6_7_8.txt": "321cb4b88e9401a91926e05d3e44ff00d7c6ffbd",
    "txt/en/txt_en_9.txt": "1015fa24c62e2c2f08cef2509908a9fcebd6d5a4",
    "txt/en/txt_en_keys.txt": "9df9e30fdd327b10d4c0bdfbed19ffaeb593e009",
    "txt/en/txt_en_shakespeare.txt": "dcd1cf8320ba1e40e2e723ae411b55aea4d2baee",
}


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def object_sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def legacy_sha(obj):
    return hashlib.sha256(json.dumps(obj).encode()).hexdigest()


def write_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- inputs
def check_seal(seal):
    require(sha(seal / "MANIFEST.json") == SEAL_SHA256, "seal_sha")
    m = json.loads((seal / "MANIFEST.json").read_text())
    require(m["predictions_frozen"] is True and m["mode"] == "freeze" and m["technical_pass"] is True, "seal_state")
    require(m["systems"] == SYSTEMS and [tuple(x) for x in m["family"]] == mm.FAMILY, "seal_family")
    require(m["frozen_bench_sha256"] == FROZEN_SHA256 and m["vocabulary_sha256"] == VOCABULARY_SHA256, "seal_sources")
    require(len(m["files"]) == 24, "seal_file_count")
    for name, meta in m["files"].items():
        require(sha(seal / name) == meta["sha256"], f"sealed_file_sha_{name}")  # hashed, not parsed
    return m


def read_predictions(seal, manifest, bank, system):
    name = f"predictions__{bank}__{system}.json"
    meta = manifest["files"][name]
    obj = json.loads((seal / name).read_text())
    require(obj["bank"] == bank and obj["system"] == system and len(obj["rows"]) == meta["rows"], "prediction_identity")
    require(not any(c.strip().startswith("86") for r in obj["rows"] for c in r["codes"]), "prediction_86")
    return obj["rows"], meta


def check_icai_rows(rows, meta, md5):
    """Sealed ICAI rows are {index, shard, row, md5, codes} (gel_data.py)."""
    for j, r in enumerate(rows):
        require(set(r) == {"index", "shard", "row", "md5", "codes"} and r["index"] == j and r["row"] == j and
                r["shard"] == TEST and r["md5"] == md5[j], "icai_prediction_schema_or_order")
    require(object_sha([{k: r[k] for k in ("index", "shard", "row", "md5")} for r in rows]) ==
            meta["identity_order_sha256"], "icai_identity_order_sha")


def training_counts(enc, entrees):
    """n(c) = training images (non validation) whose raw label holds c; V rebuilt and checked against the seal."""
    labels, md5s = [], []
    for tag in TRAIN:
        expected = entrees["shards"][tag]
        require(sha(enc / "grid" / f"{tag}.json") == expected["grid_json_sha256"], "train_label_sha")
        require(sha(enc / "feats" / f"{tag}.npz") == expected["vec_sha256"], "train_vector_sha")
        side = json.loads((enc / "grid" / f"{tag}.json").read_text())
        with np.load(enc / "feats" / f"{tag}.npz", allow_pickle=False) as z:
            md5 = [str(m) for m in z["md5"]]
        require(len(md5) == len(side["labels"]) and legacy_sha(md5) == side["md5_sha256"], "train_alignment")
        labels += side["labels"]
        md5s += md5
    groups = sorted(set(md5s))
    gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
    val = [m in gval for m in md5s]
    require(sum(val) == 4265 and len(val) - sum(val) == 81951, "historical_split")
    counts = Counter(c for y, v in zip(labels, val, strict=True) if not v for c in set(y))
    vocab = sorted({a for c, n in counts.items() if n >= 5 for a in mm.ancestors(c)})
    require(len(vocab) == 7907 and object_sha(vocab) == VOCABULARY_SHA256, "vocabulary_identity")
    return counts, vocab


def rijks_split(frozen, split):
    """Items of one split only; the other split is dropped at once (dev stage never keeps test truths)."""
    require(sha(frozen) == FROZEN_SHA256, "frozen_sha")
    doc = json.loads(Path(frozen).read_text())
    items = doc[split]["items"]
    del doc
    for it in items:
        require(it["truth_projected"] == list(dict.fromkeys(mm.drop86(it["truth"]))), "rijks_projection")
        require(len(it["truth_projected"]) > 0, "rijks_empty_projected_truth")
    return items


def align_rijks(rows, items, meta):
    """Sealed Rijksmuseum rows are {index, id, image_sha256, codes} (gel_predictions.py); the bench item key is pid."""
    require(len(rows) == len(items), "rijks_row_count")
    for j, (r, it) in enumerate(zip(rows, items)):
        require(set(r) == {"index", "id", "image_sha256", "codes"}, "rijks_prediction_schema")
        require(r["index"] == j and r["id"] == it["pid"] and r["image_sha256"] == it["image_sha256"], "rijks_order")
    require(object_sha([{k: r[k] for k in ("index", "id", "image_sha256")} for r in rows]) ==
            meta["identity_order_sha256"], "rijks_identity_order_sha")
    return [r["codes"] for r in rows]


def dictionary(root):
    texts = {}
    for relative, expected in ENGLISH_BLOBS.items():
        content = (root / relative).read_bytes()
        require(hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest() == expected, relative)
        for line in content.decode("utf-8-sig").splitlines():
            if line:
                code, _, text = line.partition("|")
                texts.setdefault(code, set()).add(text)
    return {c: t.pop() for c, t in texts.items() if len(t) == 1}


# ---------------------------------------------------------------- measures
def diagnostic(gts, preds, counts, vocab, supports=None, f=None):
    out = {"hier_f1": float(np.mean(f)) if f is not None else None, "exact": mm.exact(gts, preds),
           "depth_f1": mm.depth_f1(gts, preds), "D1_ancestor_recall": mm.ancestor_recall_by_tranche(gts, preds),
           "D2_f1_by_frequency": mm.f1_by_frequency(gts, preds, counts), "D3_coverage": mm.coverage(gts, vocab),
           "D4_codes_per_tranche": mm.codes_per_tranche(gts, preds),
           "D5_probabilities": "not_available: the seal holds predicted sets only, no probability per code",
           "rare_recall_5_20": mm.rare_recall(gts, preds, {c for c, n in counts.items() if 5 <= n <= 20})}
    if supports is not None:
        out["D6_by_support"] = mm.by_support(f, supports)
    return out


def plate_html(comp, brick, ref, chosen, items, preds, f, texts, image_files):
    by_pid = {it["pid"]: k for k, it in enumerate(items)}
    describe = lambda c: html.escape(f"{c} — {texts.get(c, '(no own text)')}")
    rows = []
    for pid in chosen:
        k = by_pid[pid]
        block = [f"<h3>{html.escape(pid)} · {items[k]['support']} · Δ = {f[brick][k] - f[ref][k]:+.3f}</h3>",
                 f"<img src='images/{image_files[pid]}' style='max-width:480px'>"]
        for title, codes in (("Vérité (projetée)", items[k]["truth_projected"]), (f"{ref} (H-F1 {f[ref][k]:.3f})",
                             preds[ref][k]), (f"{brick} (H-F1 {f[brick][k]:.3f})", preds[brick][k])):
            block.append(f"<p><b>{html.escape(title)}</b><br>" + "<br>".join(map(describe, codes or ["(vide)"])) + "</p>")
        rows.append("<section>" + "".join(block) + "</section>")
    return (f"<!doctype html><meta charset='utf-8'><title>Planche {html.escape(comp)}</title>"
            f"<h1>{html.escape(comp)} : 12 images du dev, |Δ H-F1| décroissant (égalités : identifiant)</h1>"
            + "".join(rows))


def fetch_image(it, folder):
    name = hashlib.sha256(it["pid"].encode()).hexdigest()[:16] + ".jpg"
    path = folder / name
    if not path.exists():
        with urllib.request.urlopen(urllib.request.Request(it["iiif"], headers={"User-Agent": "Mozilla/5.0"}),
                                    timeout=60) as r:
            data = r.read()
        require(hashlib.sha256(data).hexdigest() == it["image_sha256"], "dev_image_sha")
        path.write_bytes(data)
        time.sleep(1)
    return name


def stage_dev(a, seal, manifest, counts, vocab, out):
    items = rijks_split(a.frozen, "dev")
    preds = {}
    for system in SYSTEMS:
        rows, meta = read_predictions(seal, manifest, "rijks_dev", system)
        preds[system] = align_rijks(rows, items, meta)
    gts = [it["truth_projected"] for it in items]
    f = {s: [mm.hier_f1(g, p) for g, p in zip(gts, preds[s], strict=True)] for s in SYSTEMS}
    supports = [it["support"] for it in items]
    result = {"stage": "dev_only", "images": len(items), "components": len({it["component"] for it in items}),
              "systems": {s: diagnostic(gts, preds[s], counts, vocab, supports, f[s]) for s in SYSTEMS},
              "D_validation_icai": "not measured here for the bricks: the seal holds no validation predictions; "
                                   "the head diagnostic (porky-diag-run) covers T* and T-Z only", "plates": {}}
    texts = dictionary(Path(a.iconclass))
    (out / "planches" / "images").mkdir(parents=True)
    ids = [it["pid"] for it in items]
    for brick, ref in mm.FAMILY:
        comp = mm.comparison_name(brick, ref)
        chosen = mm.planche(ids, f[brick], f[ref])
        files = {pid: fetch_image(items[ids.index(pid)], out / "planches" / "images") for pid in chosen}
        (out / "planches" / f"{comp}.html").write_text(plate_html(comp, brick, ref, chosen, items, preds, f, texts, files))
        result["plates"][comp] = {"images": chosen, "conditional": brick == mm.CONDITIONAL,
                                  "html": f"planches/{comp}.html",
                                  "image_files": [f"planches/images/{files[pid]}" for pid in chosen]}
    write_json(out / "dev.json", result)
    files = sorted(p for p in out.rglob("*") if p.is_file())
    write_json(out / "MANIFEST_DEV.json", {"seal_sha256": SEAL_SHA256, "frozen_sha256": FROZEN_SHA256,
               "protocol_sha256": PROTOCOL_SHA256, "script_sha256": script_shas(),
               "versions": {"python": sys.version.split()[0], "numpy": np.__version__}, "plates": result["plates"], "files": {str(p.relative_to(out)): sha(p) for p in files}})
    print("PHASE1_DEV_DONE_NO_TEST_OPENED")


def script_shas():
    return {n: sha(Path(__file__).parent / n) for n in ("mesure_phase1.py", "mesure_metrics.py")}


def check_dev_and_receipt(dev_dir, receipt_path):
    """Before any test truth: the dev output of THIS seal, bench and scripts, its seven plates of twelve images with
    their files, and a receipt that records both looks (wA:p1 then Grok) on exactly these plates."""
    dev_dir = Path(dev_dir)
    path = dev_dir / "MANIFEST_DEV.json"
    m = json.loads(path.read_text())
    require(m.get("seal_sha256") == SEAL_SHA256 and m.get("frozen_sha256") == FROZEN_SHA256 and
            m.get("protocol_sha256") == PROTOCOL_SHA256, "dev_manifest_identity")
    require(m.get("script_sha256") == script_shas(), "dev_produced_by_other_scripts")
    files = m.get("files") or {}
    for rel, digest in files.items():
        require((dev_dir / rel).is_file() and sha(dev_dir / rel) == digest, "dev_file_missing_or_changed")
    require("dev.json" in files, "dev_json_missing")
    plates = m.get("plates") or {}
    expected = [mm.comparison_name(b, r) for b, r in mm.FAMILY]
    require(sorted(plates) == sorted(expected), "dev_plates_incomplete")
    dev = json.loads((dev_dir / "dev.json").read_text())
    require(dev.get("plates") == plates, "dev_json_plates_differ")
    for comp in expected:
        pl = plates[comp]
        require(len(pl["images"]) == 12 == len(set(pl["images"])) == len(pl["image_files"]), "plate_not_twelve_images")
        require(pl["html"] in files and all(f in files for f in pl["image_files"]), "plate_file_not_in_manifest")
    receipt = json.loads(Path(receipt_path).read_text())
    looks = receipt.get("regards") or []
    viewers = [x.get("viewer", "") for x in looks if x.get("viewed_at")]
    require(receipt.get("stage") == "planches_dev_regardees" and receipt.get("dev_manifest_sha256") == sha(path),
            "plates_not_viewed")
    require(any(v == "wA:p1" for v in viewers) and any(v.startswith("Grok") for v in viewers), "both_looks_required")
    require(receipt.get("plates_html_sha256") == {c: files[plates[c]["html"]] for c in expected}, "receipt_plates_differ")
    return receipt, sha(path)


def stage_test(a, seal, manifest, counts, vocab, out, entrees):
    receipt, dev_manifest_sha = check_dev_and_receipt(a.dev, a.receipt)
    # Order of opening: ICAI truths, Rijksmuseum test truths, then the six unconditional comparisons, then TK-niv.
    expected = entrees["shards"][TEST]
    require(sha(Path(a.encoder) / "grid" / f"{TEST}.json") == expected["grid_json_sha256"], "icai_test_label_sha")
    require(sha(Path(a.encoder) / "feats" / f"{TEST}.npz") == expected["vec_sha256"], "icai_test_vector_sha")
    side = json.loads((Path(a.encoder) / "grid" / f"{TEST}.json").read_text())
    with np.load(Path(a.encoder) / "feats" / f"{TEST}.npz", allow_pickle=False) as z:
        md5 = [str(m) for m in z["md5"]]
    labels = side["labels"]
    require(len(labels) == len(md5) == 788, "icai_test_rows")
    items = rijks_split(a.frozen, "test")
    comp_ids = sorted({it["component"] for it in items})
    unit_rijks = np.array([comp_ids.index(it["component"]) for it in items])
    gts_r = [it["truth_projected"] for it in items]
    gts_i_all = [list(dict.fromkeys(mm.drop86(y))) for y in labels]
    keep = [j for j, g in enumerate(gts_i_all) if g]
    require(len(keep) == 787, "icai_787")
    gts_i = [gts_i_all[j] for j in keep]

    def bank_preds(system):
        rows_i, meta_i = read_predictions(seal, manifest, "icai_test", system)
        check_icai_rows(rows_i, meta_i, md5)
        rows_r, meta_r = read_predictions(seal, manifest, "rijks_test", system)
        return [rows_i[j]["codes"] for j in keep], align_rijks(rows_r, items, meta_r)

    counts_i = mm.unit_draws(len(keep))           # ICAI: images, default_rng(0)
    counts_r = mm.unit_draws(len(comp_ids))       # Rijksmuseum: whole components, default_rng(0)
    preds, f = {}, {}

    def open_system(s):
        pi, pr = bank_preds(s)
        preds[s] = (pi, pr)
        f[s] = ([mm.hier_f1(g, p) for g, p in zip(gts_i, pi, strict=True)],
                [mm.hier_f1(g, p) for g, p in zip(gts_r, pr, strict=True)])

    verdicts = {}

    def verdict(brick, ref):
        for s in (brick, ref):
            if s not in f:
                open_system(s)
        di = mm.bootstrap_delta(f[brick][0], f[ref][0], np.arange(len(keep)), counts_i)
        dr = mm.bootstrap_delta(f[brick][1], f[ref][1], unit_rijks, counts_r)
        icai = mm.summarise(np.mean(f[brick][0]) - np.mean(f[ref][0]), di)
        rijks = mm.summarise(np.mean(f[brick][1]) - np.mean(f[ref][1]), dr)
        return {"brick": brick, "reference": ref, "delta_icai": icai, "delta_rijks": rijks,
                "retained": mm.retained(rijks["lower_one_sided_99_29"], icai["lower_one_sided_99_29"])}

    for brick, ref in mm.FAMILY:
        if brick != mm.CONDITIONAL:
            verdicts[brick] = verdict(brick, ref)
    t0 = float(np.mean(f["T0"][0]))
    require(abs(t0 - ICAI_T0_HIST) < 5e-5, "icai_T0_not_reproduced")
    if mm.tk_niv_active(verdicts):
        verdicts[mm.CONDITIONAL] = verdict(mm.CONDITIONAL, "T_star")
    else:
        verdicts[mm.CONDITIONAL] = {"brick": mm.CONDITIONAL, "reference": "T_star", "executed": False,
                                    "reason": "TK and T-niv not both retained; keeps its place in the family of seven"}
    write_json(out / "verdicts.json", {
        "protocol_sha256": PROTOCOL_SHA256, "seal_sha256": SEAL_SHA256, "family_size": 7, "level_one_sided": mm.LEVEL,
        "rule": "retained iff lower bound(Delta_Rijks) > 0 and lower bound(Delta_ICAI) > -0.01",
        "bootstrap": {"draws": mm.DRAWS, "seed": 0, "icai_unit": "image", "rijks_unit": "dependency component",
                      "paired": "same draws for every system of a bank"},
        "denominators": {"icai_test": len(keep), "icai_excluded_empty_projected_truth": 788 - len(keep),
                         "rijks_test_images": len(items), "rijks_test_components": len(comp_ids)},
        "icai_T0_control": {"measured": t0, "preregistered": ICAI_T0_HIST}, "verdicts": verdicts})
    # Descriptive measures and D on the tests, after the verdicts are written.
    supports = [it["support"] for it in items]
    described = [s for s in SYSTEMS if s != mm.CONDITIONAL or mm.tk_niv_active(verdicts)]
    for s in described:
        if s not in f:
            open_system(s)
    mesures = {"icai_test": {s: diagnostic(gts_i, preds[s][0], counts, vocab, None, f[s][0]) for s in described},
               "rijks_test": {s: diagnostic(gts_r, preds[s][1], counts, vocab, supports, f[s][1]) for s in described},
               "latency_T4": "not measured by this script: the seal holds predictions, not timings"}
    write_json(out / "mesures_test.json", mesures)
    files = sorted(p for p in out.rglob("*") if p.is_file())
    write_json(out / "MANIFEST_TEST.json", {"seal_sha256": SEAL_SHA256, "dev_manifest_sha256": dev_manifest_sha,
               "receipt": receipt, "script_sha256": script_shas(),
               "versions": {"python": sys.version.split()[0], "numpy": np.__version__},
               "files": {str(p.relative_to(out)): sha(p) for p in files}})
    print("PHASE1_TEST_DONE_VERDICTS_WRITTEN")


def main(a):
    seal, out = Path(a.seal), Path(a.out)
    require(not out.exists() or not any(out.iterdir()), "output_not_empty")
    out.mkdir(parents=True, exist_ok=True)
    require(sha(a.inputs) == ENTREES_SHA256, "entrees_sha")
    entrees = json.loads(Path(a.inputs).read_text())
    require(entrees["frozen_sha256"] == FROZEN_SHA256 and entrees["architecture_protocol_sha256"] == PROTOCOL_SHA256,
            "entrees_identity")
    manifest = check_seal(seal)
    counts, vocab = training_counts(Path(a.encoder), entrees)
    if a.stage == "dev":
        stage_dev(a, seal, manifest, counts, vocab, out)
    else:
        stage_test(a, seal, manifest, counts, vocab, out, entrees)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("dev", "test"), required=True)
    for k in ("seal", "frozen", "inputs", "encoder", "iconclass", "out"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--dev")
    p.add_argument("--receipt")
    args = p.parse_args()
    if args.stage == "test":
        require(args.dev and args.receipt, "test_stage_needs_dev_and_receipt")
    try:
        main(args)
    except RuntimeError as e:
        print(f"PHASE1_FAILED {e}", file=sys.stderr)
        sys.exit(1)
