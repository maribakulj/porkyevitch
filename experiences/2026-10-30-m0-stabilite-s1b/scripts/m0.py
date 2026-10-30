"""M0, DESCRIPTIVE ONLY: agreement of the two S1b passes on the 60 internal-validation images, at the level of the
targets the student learns (super-categories, boxes matched at IoU 0.5, relations v0). No gate, no decision: no arm
depends on M0 (note notes/2026-10-30-tranche300-devis-v2.md, section 1). CPU, seconds; scipy for the Hungarian
sensitivity.

Usage: m0.py --pass1 DIR --pass2 DIR --tirage tirage.json --params PARAMETRES.json --out OUT
  DIR      folders of graphs tNNN.json ({objects: [{id, name, box}], relations: [[s, p, o]]}), boxes in thousandths
  tirage   tirage.json of the 300-image draw (pinned sha): the 60 rows with role validation_interne
  params   PARAMETRES.json: IoU threshold (0.5, fixed) and bootstrap settings; it holds no gate
Matching, fixed: per image, pairs (object of pass 1, object of pass 2) with IoU >= 0.5, under two rules, "joint" (same
super-category too) and "iou" (IoU alone). Main matcher: greedy by decreasing IoU (ties: pass-1 order, then pass-2
order), the usual measure of agreement between two annotations. Sensitivity: Hungarian, maximum total IoU over the
admissible pairs. The rules of names and relations are the student's (pe_common.py, pinned sha), unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

PE = Path(__file__).resolve().parents[2] / "2026-10-30-petit-eleve" / "scripts"
sys.path.insert(0, str(PE))
import pe_common as pc  # noqa: E402

PE_COMMON_SHA256 = "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af"
TIRAGE_SHA256 = "5be1c117754c84774fc26884dac1a7e5689fc3069986c58d9a0426cdc6165992"
REL_NAMES = pc.RELATIONS + [pc.AUTRE_RELATION]


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path):
    """Objects with a valid box (degenerate ones dropped and counted), super-category, relations between kept objects."""
    g = json.loads(Path(path).read_text())
    objs, index, dropped = [], {}, 0
    for o in g["objects"]:
        b = pc.clean_box(o["box"])
        if b is None:
            dropped += 1
            continue
        index[o["id"]] = len(objs)
        objs.append({"name": o["name"].strip().lower(), "box": b, "cat": pc.categorie(o["name"])[0]})
    rels = []
    for r in g["relations"]:
        s, p, o = r if isinstance(r, list) else (r["subject"], r["predicate"], r["object"])
        if s in index and o in index and s != o:
            rels.append((index[s], pc.relation_class(p), index[o], " ".join(str(p).lower().split())))
    return {"objects": objs, "relations": rels, "dropped": dropped}


def match(a, b, same_category=True, thr=0.5, hungarian=False):
    """Greedy by decreasing IoU, ties by (index in a, index in b); or Hungarian, maximum total IoU over admissible
    pairs (inadmissible pairs weigh 0 and are dropped). Returns {i_a: i_b}."""
    iou = pc.iou_matrix([o["box"] for o in a], [o["box"] for o in b])
    ok = lambda i, j: iou[i, j] >= thr and (not same_category or a[i]["cat"] == b[j]["cat"])
    if hungarian:
        if not len(a) or not len(b):
            return {}
        from scipy.optimize import linear_sum_assignment
        weight = np.array([[iou[i, j] if ok(i, j) else 0.0 for j in range(len(b))] for i in range(len(a))])
        rows, cols = linear_sum_assignment(-weight)
        return {int(i): int(j) for i, j in zip(rows, cols) if ok(i, j)}
    cand = [(-iou[i, j], i, j) for i in range(len(a)) for j in range(len(b)) if ok(i, j)]
    used_a, used_b, out = set(), set(), {}
    for _, i, j in sorted(cand):
        if i not in used_a and j not in used_b:
            out[i] = j
            used_a.add(i)
            used_b.add(j)
    return out


def image_stats(g1, g2, hungarian=False):
    o1, o2 = g1["objects"], g2["objects"]
    m = match(o1, o2, hungarian=hungarian)
    m_iou = match(o1, o2, same_category=False, hungarian=hungarian)
    same_cat = sum(o1[i]["cat"] == o2[j]["cat"] for i, j in m_iou.items())
    # relations v0 on jointly matched pairs: (matched subject, class, matched object)
    t1 = {(m[s], c, m[o]) for s, c, o, _ in g1["relations"] if s in m and o in m}
    inv = {j: i for i, j in m.items()}
    t2 = {(s, c, o) for s, c, o, _ in g2["relations"] if s in inv and o in inv}
    # raw, recomputed here (names and named triplets per image); may differ from the journal's computation
    n1, n2 = {o["name"] for o in o1}, {o["name"] for o in o2}
    r1 = {(o1[s]["name"], p, o1[o]["name"]) for s, _, o, p in g1["relations"]}
    r2 = {(o2[s]["name"], p, o2[o]["name"]) for s, _, o, p in g2["relations"]}
    jac = lambda x, y: len(x & y) / len(x | y) if x | y else None
    return {"n1": len(o1), "n2": len(o2), "matched": len(m), "iou_matched": len(m_iou),
            "iou_matched_same_category": same_cat, "rel_inter": len(t1 & t2), "rel_union": len(t1 | t2),
            "raw_names_jaccard": jac(n1, n2), "raw_relations_jaccard": jac(r1, r2),
            "dropped": g1["dropped"] + g2["dropped"]}


def rates(m, n1, n2):
    """Recall of each pass, Dice 2m/(n1+n2), Jaccard m/(n1+n2-m); None when undefined."""
    return {"recall_pass1": m / n1 if n1 else None, "recall_pass2": m / n2 if n2 else None,
            "dice": 2 * m / (n1 + n2) if n1 + n2 else None, "jaccard": m / (n1 + n2 - m) if n1 + n2 - m else None}


def mean_defined(values):
    v = [x for x in values if x is not None]
    return float(np.mean(v)) if v else None


def pooled(stats, idx=None):
    idx = list(range(len(stats))) if idx is None else list(idx)
    s = lambda k: sum(stats[i][k] for i in idx)
    out = {}
    for rule, key in (("joint", "matched"), ("iou", "iou_matched")):
        micro = rates(s(key), s("n1"), s("n2"))
        per_image = [rates(stats[i][key], stats[i]["n1"], stats[i]["n2"]) for i in idx]
        out[rule] = {"micro": micro, "mean_per_image": {k: mean_defined([r[k] for r in per_image]) for k in micro}}
    out["category_agreement_iou_matched"] = s("iou_matched_same_category") / s("iou_matched") if s("iou_matched") else None
    out["relations_v0_jaccard_matched_pairs"] = s("rel_inter") / s("rel_union") if s("rel_union") else None
    out["relations_v0_jaccard_mean_per_image"] = mean_defined(
        [stats[i]["rel_inter"] / stats[i]["rel_union"] if stats[i]["rel_union"] else None for i in idx])
    out["objects_per_image"] = {"pass1": s("n1") / len(idx), "pass2": s("n2") / len(idx)}
    return out


def bootstrap(stats, draws, seed):
    rng = np.random.default_rng(seed)
    get = {"joint_dice": lambda p: p["joint"]["micro"]["dice"], "iou_dice": lambda p: p["iou"]["micro"]["dice"],
           "category_agreement_iou_matched": lambda p: p["category_agreement_iou_matched"],
           "relations_v0_jaccard_matched_pairs": lambda p: p["relations_v0_jaccard_matched_pairs"]}
    vals = {k: [] for k in get}
    for _ in range(draws):
        p = pooled(stats, rng.integers(0, len(stats), len(stats)))
        for k, f in get.items():
            if f(p) is not None:
                vals[k].append(f(p))
    return {k: [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if v else None for k, v in vals.items()}


def main(a):
    require(sha(Path(pc.__file__)) == PE_COMMON_SHA256, "student_rules_changed")
    require(sha(a.tirage) == TIRAGE_SHA256, "tirage_sha")
    params = json.loads(Path(a.params).read_text())
    require(params["iou_appariement"] == 0.5, "matching_threshold_fixed_at_0.5")
    require(not any(k.startswith("porte") for k in params), "M0 is descriptive: no gate allowed")
    tirage = json.loads(Path(a.tirage).read_text())
    names = sorted(p["name"] for p in tirage["picks"] if p["role"] == "validation_interne")
    require(len(names) == 60, "sixty_internal_validation_images")
    missing = [n for n in names if not (Path(a.pass1) / f"{n}.json").is_file() or not (Path(a.pass2) / f"{n}.json").is_file()]
    kept = [n for n in names if n not in missing]
    graphs = [(load(Path(a.pass1) / f"{n}.json"), load(Path(a.pass2) / f"{n}.json")) for n in kept]
    stats = [image_stats(g1, g2) for g1, g2 in graphs]
    stats_h = [image_stats(g1, g2, hungarian=True) for g1, g2 in graphs]
    result = pooled(stats)
    raw = {k: float(np.mean([s[k] for s in stats if s[k] is not None])) for k in ("raw_names_jaccard", "raw_relations_jaccard")}
    out = {"images": len(stats), "missing_graphs_kept_out_and_counted": missing,
           "descriptive_only": True, "pooled_greedy": result, "pooled_hungarian_sensitivity": pooled(stats_h),
           "ci95_by_image": bootstrap(stats, params["bootstrap"]["tirages"], params["bootstrap"]["graine"]),
           "raw_recomputed": raw, "raw_journal": {"names": 0.52, "relations": 0.34},
           "dropped_degenerate_boxes": sum(s["dropped"] for s in stats),
           "per_image": dict(zip(kept, stats)),
           "params_sha256": sha(a.params), "pe_common_sha256": PE_COMMON_SHA256, "tirage_sha256": TIRAGE_SHA256}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("M0_DONE_DESCRIPTIVE", json.dumps(result["joint"]["micro"]))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("pass1", "pass2", "tirage", "params", "out"):
        p.add_argument(f"--{k}", required=True)
    try:
        main(p.parse_args())
    except RuntimeError as e:
        print(f"M0_FAILED {e}", file=sys.stderr)
        sys.exit(1)
