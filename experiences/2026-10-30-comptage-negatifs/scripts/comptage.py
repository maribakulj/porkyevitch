"""Descriptive count, no gate: on the 26 evaluation images that have both a Gemini and an S1b graph, how many of the
negatives the student's loss draws from Gemini does S1b assert? (Grok p7, porkyevitch-etiquettes-manquantes-grok.md, 2.3.)

Usage: comptage.py --listes listes.json --gemini PILOT_GRAPHS --s1b S1B_DIR --out OUT
  listes   petit élève listes.json (pinned sha): the evaluation rows, with the sha of each Gemini and S1b graph
  gemini   ~/porkyevitch-donnees/graphes-gemini/pilote/graphes (pNNN/g.json);  s1b  .../systemes/evaluation/S1b (pNNN.json)
Negatives, as the student's loss sees them (petit élève v1, sections 2-3):
  pairs      ordered pairs of distinct Gemini objects with no Gemini relation at all (the relation head's negatives;
             the student draws them at 3 for 1, here all are counted, so the share is the expectation of the draw)
  predicates (pair, class v0) with the class absent from Gemini for that pair, the pair having a relation or not
             (multi-label sigmoid output: each absent class is a negative)
  objects    S1b objects with no Gemini object at IoU >= 0.5: what the student would learn as "no object"
S1b objects are matched to Gemini objects greedily by decreasing IoU >= 0.5 (ties: Gemini order, then S1b order), with
the rule "joint" (same super-category, the student's name table) and, for objects, also "IoU alone". A Gemini negative
is "comparable" when both its objects are matched to S1b objects; it is "asserted" when S1b states the relation (or the
class) between the two matched S1b objects.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

PE = Path(__file__).resolve().parents[2] / "2026-10-30-petit-eleve" / "scripts"
sys.path.insert(0, str(PE))
import pe_common as pc  # noqa: E402

PE_COMMON_SHA256 = "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af"
LISTES_SHA256 = "87e45b418ace7a4f1a15857456d3d40d107ee3a9c286962e9c19723ecfb065af"


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path):
    g = json.loads(Path(path).read_text())
    objs, index = [], {}
    for o in g["objects"]:
        b = pc.clean_box(o["box"])
        if b is None:
            continue
        index[o["id"]] = len(objs)
        objs.append({"box": b, "cat": pc.categorie(o["name"])[0]})
    rels = set()
    for r in g["relations"]:
        s, p, o = r if isinstance(r, list) else (r["subject"], r["predicate"], r["object"])
        if s in index and o in index and s != o:
            rels.add((index[s], pc.relation_class(p), index[o]))
    return {"objects": objs, "relations": rels}


def match(a, b, same_category=True, thr=0.5):
    iou = pc.iou_matrix([o["box"] for o in a], [o["box"] for o in b])
    cand = sorted((-iou[i, j], i, j) for i in range(len(a)) for j in range(len(b))
                  if iou[i, j] >= thr and (not same_category or a[i]["cat"] == b[j]["cat"]))
    out, ub = {}, set()
    for _, i, j in cand:
        if i not in out and j not in ub:
            out[i] = j
            ub.add(j)
    return out


def count(gem, s1b):
    m = match(gem["objects"], s1b["objects"])                        # Gemini index -> S1b index
    m_iou = match(gem["objects"], s1b["objects"], same_category=False)
    n = len(gem["objects"])
    related = {(s, o) for s, _, o in gem["relations"]}
    s1b_pairs = {(s, o) for s, _, o in s1b["relations"]}
    neg_pairs = [(i, j) for i in range(n) for j in range(n) if i != j and (i, j) not in related]
    comparable = [(i, j) for i, j in neg_pairs if i in m and j in m]
    asserted = [(i, j) for i, j in comparable if (m[i], m[j]) in s1b_pairs]
    by_class = {}
    for c in pc.RELATIONS + [pc.AUTRE_RELATION]:
        neg = [(i, j) for i in range(n) for j in range(n) if i != j and (i, c, j) not in gem["relations"]]
        comp = [(i, j) for i, j in neg if i in m and j in m]
        ass = [(i, j) for i, j in comp if (m[i], c, m[j]) in s1b["relations"]]
        by_class[c] = {"negatives": len(neg), "comparable": len(comp), "asserted_by_S1b": len(ass)}
    unmatched_joint = len(s1b["objects"]) - len(m)
    unmatched_iou = len(s1b["objects"]) - len(m_iou)
    return {"gemini_objects": n, "s1b_objects": len(s1b["objects"]), "matched_joint": len(m), "matched_iou": len(m_iou),
            "pairs": {"negatives": len(neg_pairs), "comparable": len(comparable), "asserted_by_S1b": len(asserted)},
            "predicates": by_class,
            "objects": {"s1b_unmatched_joint": unmatched_joint, "s1b_unmatched_iou": unmatched_iou}}


def total(per_image):
    t = {"images": len(per_image), "pairs": {"negatives": 0, "comparable": 0, "asserted_by_S1b": 0},
         "predicates": {}, "objects": {"s1b_objects": 0, "s1b_unmatched_joint": 0, "s1b_unmatched_iou": 0}}
    for r in per_image.values():
        for k in t["pairs"]:
            t["pairs"][k] += r["pairs"][k]
        for c, v in r["predicates"].items():
            d = t["predicates"].setdefault(c, {"negatives": 0, "comparable": 0, "asserted_by_S1b": 0})
            for k in d:
                d[k] += v[k]
        t["objects"]["s1b_objects"] += r["s1b_objects"]
        t["objects"]["s1b_unmatched_joint"] += r["objects"]["s1b_unmatched_joint"]
        t["objects"]["s1b_unmatched_iou"] += r["objects"]["s1b_unmatched_iou"]
    share = lambda a, b: a / b if b else None
    t["pairs"]["asserted_share_of_comparable"] = share(t["pairs"]["asserted_by_S1b"], t["pairs"]["comparable"])
    t["pairs"]["asserted_share_of_negatives"] = share(t["pairs"]["asserted_by_S1b"], t["pairs"]["negatives"])
    for d in t["predicates"].values():
        d["asserted_share_of_comparable"] = share(d["asserted_by_S1b"], d["comparable"])
    t["objects"]["unmatched_share_joint"] = share(t["objects"]["s1b_unmatched_joint"], t["objects"]["s1b_objects"])
    t["objects"]["unmatched_share_iou"] = share(t["objects"]["s1b_unmatched_iou"], t["objects"]["s1b_objects"])
    return t


def main(a):
    require(sha(Path(pc.__file__)) == PE_COMMON_SHA256, "student_rules_changed")
    require(sha(a.listes) == LISTES_SHA256, "listes_sha")
    rows = [r for r in json.loads(Path(a.listes).read_text())["evaluation"]
            if r["gemini_graph_sha256"] and r.get("s1b_graph_sha256")]
    require(len(rows) == 26, "twenty_six_double_graphs")
    per_image = {}
    for r in rows:
        g, s = Path(a.gemini) / r["name"] / "g.json", Path(a.s1b) / f"{r['name']}.json"
        require(sha(g) == r["gemini_graph_sha256"] and sha(s) == r["s1b_graph_sha256"], f"graph_sha_{r['name']}")
        per_image[r["name"]] = count(load(g), load(s))
    out = {"descriptive_only": True, "no_gate": True, "totals": total(per_image), "per_image": per_image,
           "reading": "a negative S1b asserts is not certainly wrong in Gemini, nor certainly true in S1b",
           "listes_sha256": LISTES_SHA256, "pe_common_sha256": PE_COMMON_SHA256}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print("COMPTAGE_DONE", json.dumps(out["totals"]["pairs"]))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("listes", "gemini", "s1b", "out"):
        p.add_argument(f"--{k}", required=True)
    try:
        main(p.parse_args())
    except RuntimeError as e:
        print(f"COMPTAGE_FAILED {e}", file=sys.stderr)
        sys.exit(1)
