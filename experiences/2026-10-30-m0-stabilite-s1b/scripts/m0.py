"""M0: agreement of the two S1b passes on the 60 internal-validation images, at the level of the targets the student
learns (super-categories, boxes matched at IoU 0.5, relations v0). CPU, seconds. Note notes/2026-10-30-tranche300-devis.md.

Usage: m0.py --pass1 DIR --pass2 DIR --tirage tirage.json --params PARAMETRES.json --out OUT
  DIR      folders of graphs tNNN.json ({objects: [{id, name, box}], relations: [[s, p, o]]}), boxes in thousandths
  tirage   tirage.json of the 300-image draw (pinned sha): the 60 rows with role validation_interne
  params   PARAMETRES.json: the gates, null until fixed after review; null gates give no decision
Matching rule, fixed: per image, pairs (object of pass 1, object of pass 2) with the same super-category and IoU >= 0.5,
taken greedily by decreasing IoU (ties: pass-1 order, then pass-2 order). The rules of names and relations are the
student's (pe_common.py, pinned sha), unchanged.
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


def match(a, b, same_category=True, thr=0.5):
    """Greedy by decreasing IoU; ties by (index in a, index in b). Returns {i_a: i_b}."""
    iou = pc.iou_matrix([o["box"] for o in a], [o["box"] for o in b])
    cand = [(-iou[i, j], i, j) for i in range(len(a)) for j in range(len(b))
            if iou[i, j] >= thr and (not same_category or a[i]["cat"] == b[j]["cat"])]
    used_a, used_b, out = set(), set(), {}
    for _, i, j in sorted(cand):
        if i not in used_a and j not in used_b:
            out[i] = j
            used_a.add(i)
            used_b.add(j)
    return out


def image_stats(g1, g2):
    m = match(g1["objects"], g2["objects"])
    m_iou = match(g1["objects"], g2["objects"], same_category=False)
    same_cat = sum(g1["objects"][i]["cat"] == g2["objects"][j]["cat"] for i, j in m_iou.items())
    # relations v0 on matched pairs: a triplet (pair of matched subjects, class, pair of matched objects)
    t1 = {(m[s], c, m[o]) for s, c, o, _ in g1["relations"] if s in m and o in m}
    inv = {j: i for i, j in m.items()}
    t2 = {(s, c, o) for s, c, o, _ in g2["relations"] if s in inv and o in inv}
    # raw, recomputed here (names and named triplets per image); may differ from the journal's computation
    n1, n2 = {o["name"] for o in g1["objects"]}, {o["name"] for o in g2["objects"]}
    r1 = {(g1["objects"][s]["name"], p, g1["objects"][o]["name"]) for s, _, o, p in g1["relations"]}
    r2 = {(g2["objects"][s]["name"], p, g2["objects"][o]["name"]) for s, _, o, p in g2["relations"]}
    jac = lambda x, y: len(x & y) / len(x | y) if x | y else None
    return {"n1": len(g1["objects"]), "n2": len(g2["objects"]), "matched": len(m), "iou_matched": len(m_iou),
            "iou_matched_same_category": same_cat, "rel_inter": len(t1 & t2), "rel_union": len(t1 | t2),
            "raw_names_jaccard": jac(n1, n2), "raw_relations_jaccard": jac(r1, r2),
            "dropped": g1["dropped"] + g2["dropped"]}


def pooled(stats, idx=None):
    idx = range(len(stats)) if idx is None else idx
    s = lambda k: sum(stats[i][k] for i in idx)
    n = s("n1") + s("n2")
    return {"objects_matched_share": 2 * s("matched") / n if n else None,
            "objects_matched_share_pass1": s("matched") / s("n1") if s("n1") else None,
            "objects_matched_share_pass2": s("matched") / s("n2") if s("n2") else None,
            "category_agreement_iou_matched": s("iou_matched_same_category") / s("iou_matched") if s("iou_matched") else None,
            "relations_v0_jaccard_matched_pairs": s("rel_inter") / s("rel_union") if s("rel_union") else None}


def bootstrap(stats, draws, seed):
    rng = np.random.default_rng(seed)
    keys = ("objects_matched_share", "category_agreement_iou_matched", "relations_v0_jaccard_matched_pairs")
    vals = {k: [] for k in keys}
    for _ in range(draws):
        p = pooled(stats, rng.integers(0, len(stats), len(stats)))
        for k in keys:
            if p[k] is not None:
                vals[k].append(p[k])
    return {k: [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] if v else None for k, v in vals.items()}


def decide(result, params):
    """The rule of the note, with the gates read from PARAMETRES.json; null gates give no decision."""
    go, gr = params["porte_objets_apparies_min"], params["porte_relations_jaccard_v0_cible_dure_min"]
    if go is None or gr is None:
        return {"decision": None, "reason": "gates not fixed in PARAMETRES.json: no decision"}
    obj, rel = result["objects_matched_share"], result["relations_v0_jaccard_matched_pairs"]
    return {"objects": "cibles_dures_passe_1" if obj is not None and obj >= go else "cibles_douces_seconde_passe_240",
            "relations": ("cible_dure_possible" if rel is not None and rel >= gr
                          else "pas_de_cible_dure_relations_douces_ou_exclues"),
            "gates": {"objects": go, "relations": gr}}


def main(a):
    require(sha(Path(pc.__file__)) == PE_COMMON_SHA256, "student_rules_changed")
    require(sha(a.tirage) == TIRAGE_SHA256, "tirage_sha")
    params = json.loads(Path(a.params).read_text())
    require(params["iou_appariement"] == 0.5, "matching_threshold_fixed_at_0.5")
    tirage = json.loads(Path(a.tirage).read_text())
    names = sorted(p["name"] for p in tirage["picks"] if p["role"] == "validation_interne")
    require(len(names) == 60, "sixty_internal_validation_images")
    missing = [n for n in names if not (Path(a.pass1) / f"{n}.json").is_file() or not (Path(a.pass2) / f"{n}.json").is_file()]
    stats = [image_stats(load(Path(a.pass1) / f"{n}.json"), load(Path(a.pass2) / f"{n}.json"))
             for n in names if n not in missing]
    result = pooled(stats)
    raw = {k: float(np.mean([s[k] for s in stats if s[k] is not None])) for k in ("raw_names_jaccard", "raw_relations_jaccard")}
    out = {"images": len(stats), "missing_graphs_kept_out_and_counted": missing,
           "pooled": result, "ci95_by_image": bootstrap(stats, params["bootstrap"]["tirages"], params["bootstrap"]["graine"]),
           "raw_recomputed": raw, "raw_journal": {"names": 0.52, "relations": 0.34},
           "dropped_degenerate_boxes": sum(s["dropped"] for s in stats),
           "decision": decide(result, params), "per_image": dict(zip([n for n in names if n not in missing], stats)),
           "params_sha256": sha(a.params), "pe_common_sha256": PE_COMMON_SHA256, "tirage_sha256": TIRAGE_SHA256}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("M0_DONE", json.dumps(result), json.dumps(out["decision"]))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("pass1", "pass2", "tirage", "params", "out"):
        p.add_argument(f"--{k}", required=True)
    try:
        main(p.parse_args())
    except RuntimeError as e:
        print(f"M0_FAILED {e}", file=sys.stderr)
        sys.exit(1)
