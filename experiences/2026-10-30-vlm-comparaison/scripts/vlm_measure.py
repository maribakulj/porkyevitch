"""VLM comparison, measures (PREINSCRIPTION-v2.3.md sections 3.5, 3.6, 4, 5). Runs only after the plate receipt.

The receipt (recu.json) names the SHA-256 of the journals of S1 and R and of status_S1.json, and at least two distinct looks;
every raw output must still match the SHA-256 written in its journal record. Nothing is measured otherwise. V-diagnostic is
measured on the groups kept by plan_S1.json (extrapolation rule, v2.2).
The call kept for each image is the final attempt of S1 (the repeat stage R only feeds the repeatability table). An image
whose final state is not "reponse" counts with an empty set (H-F1 0) and stays in the denominator.

Usage: vlm_measure.py --prep OUT --receipt recu.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a1_core as a1  # noqa: E402
import pe_common as pc  # noqa: E402
import vlm_core as vc  # noqa: E402
from vlm_call import require, sha  # noqa: E402


def vm_read(path):
    return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []


def final_records(root, stage):
    path = root / "journal" / f"{stage}.jsonl"
    last = {}
    for line in path.read_text().splitlines() if path.exists() else []:
        r = json.loads(line)
        last[r["id"]] = r
    return last


def codes_of(rec, vocab_set):
    """Valid codes (drop86) and chain counts of a final record; empty set when the state is not 'reponse'."""
    if rec is None or rec["state"] != "reponse":
        return [], {"valide": 0, "hors_V": 0, "invalide": 0}
    valid, counts = vc.classify(rec["payload"], vocab_set)
    return a1.drop86(valid), counts


def states(records):
    out = {}
    for r in records.values():
        out[r["state"]] = out.get(r["state"], 0) + 1
    return out


def bank_measure(prep, last, bank, systems, keys=None):
    rows = [x for x in prep["banks"][bank] if keys is None or x["key"] in keys]
    vocab_set = set(prep["vocabulary"])
    truth = [x["truth"] for x in rows]
    per = {"B": [a1.hier_f1(t, x["B"]) for t, x in zip(truth, rows)],
           "T_star": [a1.hier_f1(t, x["T_star"]) for t, x in zip(truth, rows)]}
    exact = {"B": [a1.exact_e(t, x["B"]) for t, x in zip(truth, rows)],
             "T_star": [a1.exact_e(t, x["T_star"]) for t, x in zip(truth, rows)]}
    info = {}
    for s in systems:
        recs = [last.get(f"S1:{s}:{bank}:{x['key']}") for x in rows]
        preds, counts = zip(*(codes_of(r, vocab_set) for r in recs)) if rows else ((), ())
        per[s] = [a1.hier_f1(t, p) for t, p in zip(truth, preds)]
        exact[s] = [a1.exact_e(t, p) for t, p in zip(truth, preds)]
        tot = {k: sum(c[k] for c in counts) for k in ("valide", "hors_V", "invalide")}
        info[s] = {"missing_records": sum(r is None for r in recs), "states": states({i: r for i, r in enumerate(recs) if r}),
                   "commands_executed": sum(1 for r in recs if r and r["state"] == "commande_executee"),
                   "refusals_without_image_read": sum(1 for r in recs if r and r["state"] == "refus" and not r.get("image_read")),
                   "chains": tot, "invalid_rate": vc.invalid_rate(tot),
                   "cardinality_mean": float(np.mean([len(p) for p in preds])) if preds else None}
    groups = [x["group"] for x in rows]
    contrasts = {f"{s}-{ref}": np.array(per[s]) - np.array(per[ref]) for s in systems for ref in ("T_star", "B")}
    contrasts.update({f"O-{s}": np.array(per["O"]) - np.array(per[s]) for s in ("H", "G") if "O" in systems and s in per})
    boot = vc.paired_bootstrap(contrasts, groups) if rows else None
    return {"images": len(rows), "groups": len(set(groups)),
            "H_F1": {k: float(np.mean(v)) for k, v in per.items()},
            "exact_F1": {k: float(np.mean(v)) for k, v in exact.items()}, "systems": info, "bootstrap": boot}


def repeatability(prep, s1, r, systems):
    vocab_set, out = set(prep["vocabulary"]), {}
    truth = {x["key"]: x["truth"] for x in prep["banks"]["rijks_dev"]}
    for s in systems:
        jac, dh = [], []
        for key in prep["samples"]["repeat"]:
            a = codes_of(s1.get(f"S1:{s}:rijks_dev:{key}"), vocab_set)[0]
            b = codes_of(r.get(f"R:{s}:rijks_dev:{key}"), vocab_set)[0]
            jac.append(vc.jaccard(a, b))
            dh.append(a1.hier_f1(truth[key], b) - a1.hier_f1(truth[key], a))
        out[s] = {"images": len(jac), "jaccard_mean": float(np.mean(jac)), "delta_H_mean": float(np.mean(dh)),
                  "delta_H_abs_mean": float(np.mean(np.abs(dh)))}
    return out


def graphs(prep, last, systems):
    rows = prep["banks"]["pe_eval"]
    refs = {"gemini": [vc.graph_boxes(x["gemini_graph"], pc.clean_box) for x in rows],
            "s1b": [vc.graph_boxes(x["s1b_graph"], pc.clean_box) for x in rows]}
    for x in rows:
        require(sha(x["gemini_graph"]) == x["gemini_graph_sha256"] and sha(x["s1b_graph"]) == x["s1b_graph_sha256"],
                f"graph_changed_{x['name']}")
    out = {}
    for s in systems:
        recs = [last.get(f"S1:{s}:pe_eval:{x['name']}") for x in rows]
        boxes = []
        for r in recs:
            raw = r["payload"] if r and r["state"] == "reponse" else []
            boxes.append([b for b in (pc.clean_box(v) if v is not None else None for v in raw) if b is not None])
        res = {"states": states({i: r for i, r in enumerate(recs) if r}), "missing_records": sum(r is None for r in recs),
               "boxes_mean": float(np.mean([len(b) for b in boxes]))}
        for name, gts in refs.items():
            imgs = [(b, [-k for k in range(len(b))], g) for b, g in zip(boxes, gts)]  # rank as score
            res[f"recall_at_30_vs_{name}"] = pc.pooled_recall(pc.recall_counts(imgs, vc.MAX_BOXES))
        out[s] = res
    out["circularity"] = "G contre le juge Gemini : circulaire, déclaré (section 4)"
    return out


def costs(root):
    out = {}
    for p in sorted((root / "journal").glob("*.jsonl")):
        for line in p.read_text().splitlines():
            r = json.loads(line)
            o = out.setdefault(r["system"], {"attempts": 0, "seconds": [], "cost_usd": 0.0, "cost_missing": 0, "usage": []})
            o["attempts"] += 1
            o["seconds"].append(r["seconds"])
            if isinstance(r.get("cost_usd"), (int, float)):
                o["cost_usd"] += r["cost_usd"]
            else:
                o["cost_missing"] += 1
            o["usage"].append(r.get("usage"))
    for o in out.values():
        s = np.array(o.pop("seconds"))
        o["seconds_median"], o["seconds_p90"] = float(np.median(s)), float(np.percentile(s, 90))
        o["usage_records"] = sum(u is not None for u in o.pop("usage"))
    out["fast_model"] = "absent ici : T4-chrono en préinscription séparée (v2.1)"
    return out


def main(a):
    root = Path(a.prep)
    prep = json.loads((root / "prep.json").read_text())
    for name, want in prep["code_sha256"].items():
        require(sha(HERE / name) == want, f"code_changed_{name}")
    receipt = json.loads(Path(a.receipt).read_text())
    for stage in ("S1", "R"):
        require(receipt["journals_sha256"][stage] == sha(root / "journal" / f"{stage}.jsonl"), f"receipt_journal_{stage}")
    require(receipt["status_S1_sha256"] == sha(root / "status_S1.json"), "receipt_status")
    require(len(set(receipt.get("regards", []))) >= 2, "receipt_two_distinct_looks")
    for stage in ("S0", "S1", "R"):
        for rec in vm_read(root / "journal" / f"{stage}.jsonl"):
            require(sha(root / "raw" / rec["raw_file"]) == rec["raw_sha256"], f"raw_changed_{rec['raw_file']}")
    plan = json.loads((root / "plan_S1.json").read_text())
    kept = set(plan["vdiag_groups_kept"])
    s1, r = final_records(root, "S1"), final_records(root, "R")
    status = json.loads((root / "status_S1.json").read_text())
    dev = bank_measure(prep, s1, "rijks_dev", vc.MAIN_SYSTEMS)
    family = {s: {**dev["bootstrap"]["contrasts"][f"{s}-T_star"],
                  "reading": vc.reading(dev["bootstrap"]["contrasts"][f"{s}-T_star"])} for s in vc.MAIN_SYSTEMS}
    out = {"preinscription": prep["preinscription"], "complete": status["complete"], "stopped_by": status["stopped_by"],
           "family_dev_vs_T_star": family,
           "family_level": "Bonferroni bilatéral sur 2 : q1_25 / q98_75 ; q2_5 / q97_5 = IC95 non corrigé, descriptif",
           "plan_S1": plan,
           "rijks_dev": dev, "icai_vdiag": bank_measure(prep, s1, "icai_vdiag", vc.MAIN_SYSTEMS,
                                      keys={x["key"] for x in prep["banks"]["icai_vdiag"] if x["group"] in kept}),
           "opus_slice_descriptive": bank_measure(prep, s1, "rijks_dev", ("H", "G", "O"), keys=set(prep["samples"]["opus"])),
           "repeatability": repeatability(prep, s1, r, vc.MAIN_SYSTEMS), "graphs": graphs(prep, s1, vc.MAIN_SYSTEMS),
           "costs_and_time": costs(root), "test_rows": 0}
    if not status["complete"]:
        out["incomplete"] = "S1 incomplet : publié comme tel, aucun sous-ensemble choisi après coup"
    (root / "mesures.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    print(json.dumps(family, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", required=True)
    ap.add_argument("--receipt", required=True)
    main(ap.parse_args())
