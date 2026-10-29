"""S5b: majority vote over three independent S2b runs (PREINSCRIPTION.md, systems bench).

Usage: vote.py RUN1 RUN2 RUN3 OUT
Objects of the three runs are matched greedily (same normalised name, box IoU >= 0.5, at most one object per run in a cluster);
a cluster seen in at least 2 runs is kept, with the mean box and the attributes seen at least twice. Relations are mapped to
clusters after predicate normalisation (passive forms turned active, e.g. "o2 worn by o1" -> "o1 wears o2") and kept when the
same (subject cluster, predicate, object cluster) appears in at least 2 runs. Deterministic; no image is read.
"""
import json, sys
from collections import Counter
from pathlib import Path

IOU_MIN = float(__import__("os").environ.get("VOTE_IOU", "0.5"))
PASSIVE = {"worn by": "wears", "held by": "holds", "carried by": "carries", "ridden by": "rides", "pulled by": "pulls",
           "part of": "is part of", "on": "stands on"}


def norm_name(n):
    n = n.lower().strip()
    return n[:-1] if n.endswith("s") and not n.endswith("ss") else n


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def relation(r):
    s, p, o = r
    p = p.lower().strip()
    if p in ("worn by", "held by", "carried by", "ridden by", "pulled by"):
        return o, PASSIVE[p], s
    return s, PASSIVE.get(p, p), o


runs = [Path(a) for a in sys.argv[1:4]]
out = Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
for f in sorted(runs[0].glob("p*.json")):
    graphs = [json.loads((r / f.name).read_text()) for r in runs]
    clusters = []  # list of {run: object}
    for k, g in enumerate(graphs):
        for o in g["objects"]:
            best, score = None, IOU_MIN
            for c in clusters:
                if k in c:
                    continue
                ref = next(iter(c.values()))
                if norm_name(ref["name"]) == norm_name(o["name"]):
                    s = iou(ref["box"], o["box"])
                    if s >= score:
                        best, score = c, s
            if best is None:
                clusters.append({k: o})
            else:
                best[k] = o
    kept = [c for c in clusters if len(c) >= 2]
    ids, objects = {}, []
    for i, c in enumerate(kept, 1):
        oid = f"o{i}"
        for k, o in c.items():
            ids[(k, o["id"])] = oid
        boxes = [o["box"] for o in c.values()]
        attrs = Counter(a for o in c.values() for a in set(o.get("attributes", [])))
        objects.append({"id": oid, "name": next(iter(c.values()))["name"],
                        "box": [round(sum(b[j] for b in boxes) / len(boxes)) for j in range(4)],
                        "attributes": [a for a, n in attrs.items() if n >= 2], "votes": len(c)})
    rel = Counter()
    for k, g in enumerate(graphs):
        seen = set()
        for r in g["relations"]:
            s, p, o = relation(r)
            if (k, s) in ids and (k, o) in ids:
                seen.add((ids[(k, s)], p, ids[(k, o)]))
        rel.update(seen)
    relations = [list(t) for t, n in rel.items() if n >= 2]
    (out / f.name).write_text(json.dumps({"objects": objects, "relations": relations}, ensure_ascii=False, indent=1))
print("ok")
