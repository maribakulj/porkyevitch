#!/usr/bin/env python3
"""Rijksmuseum bench, chronology steps 3-4 (PREINSCRIPTION.md, amendment 1): components, audit reserve, pairs of the audit sheet.

Usage: composantes_reserve.py NOTICES FILTRES OUT [repli]
NOTICES: notices.jsonl of the collection (Mac). FILTRES: the output folder of filtres_distances.py (full run): images.jsonl,
voisins.jsonl, internes.jsonl. With "repli", only the sheet is rebuilt, at the fallback values (dHash < 64, cosine >= 0.92, bands
64-93 bits and 0.82-0.92), on the same reserve; components are never rebuilt.
Nodes: eligible objects whose image was kept. Edges (B1): a shared linking actor (actors[].links true; generic actors were already
left out by the collection), a shared parent (part_of), an internal copy (internes.jsonl: dHash < 64 or cosine >= 0.92). Components
by union-find, canonical order by the smallest member PID (Unicode code points), permutation default_rng(0).permutation(k), audit
reserve = the first ceil(10 % of k) components of the permutation. Cap: per component, default_rng([1, i]).permutation of its members
sorted by PID, i its rank (from 0) in canonical order, first 20 kept (used by the draw, written here once).
Sheet (B2): for each reserve object (every member, uncapped) and each filter, its one nearest reference pair (voisins.jsonl). Support =
first of its types in the order painting, print, drawing. Per support and filter: (a) 6 rejected pairs closest to the threshold, (b) 6
kept pairs closest to the threshold, (c) 4 kept pairs drawn by default_rng(2) Generator.choice without replacement among kept pairs
outside (b) inside the band (dHash 50-79 bits / cosine 0.85-0.95, both ends included on the kept side), supports then filters in
that order, no call when the band holds 4 pairs or fewer (all shown). Order of every selection: distance to the threshold, then
candidate PID. A pair (candidate, reference index) selected by both filters is listed once and counts for both.
Outputs (atomic): groupes.json (components: members, edges with type and key; canonical rank, permutation rank, reserve flag, capped
members), resume.json (counts: nodes, edges by type, components, sizes, singletons, objects with only generic actors, largest
component), planche.json (pairs, no code). numpy 2.5.4 is required. Prints counts only.
"""

import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

assert np.__version__ == "2.5.4", f"numpy {np.__version__}: the preregistered draw needs numpy 2.5.4"
NOTICES, FILTRES, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
REPLI = len(sys.argv) > 4 and sys.argv[4] == "repli"
OUT.mkdir(parents=True, exist_ok=True)
TYPES = ["painting", "print", "drawing"]
CAP = 20
if REPLI:
    T_DHASH, T_COS, BAND_DHASH, BAND_COS = 64, 0.92, (64, 93), (0.82, 0.92)
else:
    T_DHASH, T_COS, BAND_DHASH, BAND_COS = 50, 0.95, (50, 79), (0.85, 0.95)


def write_json(obj, path: Path):
    tmp = path.with_name(path.name + ".tmp")
    json.dump(obj, open(tmp, "w"), ensure_ascii=False, indent=1)
    tmp.replace(path)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


notices = {r["pid"]: r for r in map(json.loads, open(NOTICES))}
images = {r["pid"]: r for r in map(json.loads, open(FILTRES / "images.jsonl"))}
voisins = {r["pid"]: r for r in map(json.loads, open(FILTRES / "voisins.jsonl"))}
nodes = sorted(p for p, r in notices.items() if r.get("eligible") and images.get(p, {}).get("sha256"))
assert set(nodes) == set(voisins), "voisins.jsonl does not cover exactly the kept images"
index = {p: i for i, p in enumerate(nodes)}

# ---- Components (step 3) ----
parent = list(range(len(nodes)))


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[max(ra, rb)] = min(ra, rb)


edges = []
by_key = defaultdict(list)
for p in nodes:
    r = notices[p]
    for a in r.get("actors", []):
        if a["links"]:
            by_key[("actor", a["actor"])].append(p)
    for q in r.get("parents", []):
        by_key[("parent", q)].append(p)
for (kind, key), members in sorted(by_key.items()):
    members = sorted(set(members))
    for m in members[1:]:
        union(index[members[0]], index[m])
    if len(members) > 1:
        edges.append({"type": kind, "key": key, "members": members})
internal = 0
for r in map(json.loads, open(FILTRES / "internes.jsonl")):
    if r["pid_a"] in index and r["pid_b"] in index:
        union(index[r["pid_a"]], index[r["pid_b"]])
        edges.append({"type": "internal_copy", "key": f"dhash={r['dhash_bits']};cos={r['cosine']:.4f}",
                      "members": sorted([r["pid_a"], r["pid_b"]])})
        internal += 1
comp = defaultdict(list)
for p in nodes:
    comp[find(index[p])].append(p)
components = sorted((sorted(m) for m in comp.values()), key=lambda m: m[0])
k = len(components)
perm = np.random.default_rng(0).permutation(k)
n_reserve = math.ceil(0.1 * k)
reserve_ranks = set(int(x) for x in perm[:n_reserve])
perm_rank = {int(c): r for r, c in enumerate(perm)}
comp_of = {}
groups = []
for i, members in enumerate(components):
    capped = [members[j] for j in np.random.default_rng([1, i]).permutation(len(members))[:CAP]]
    for m in members:
        comp_of[m] = i
    groups.append({"canonical_rank": i, "permutation_rank": perm_rank[i], "reserve": i in reserve_ranks, "members": members,
                   "capped": capped})
edges_by_comp = defaultdict(list)
for e in edges:
    edges_by_comp[comp_of[e["members"][0]]].append(e)
for g in groups:
    g["edges"] = edges_by_comp[g["canonical_rank"]]


def support(p):
    return next(t for t in TYPES if t in notices[p]["types"])


sizes = [len(g["members"]) for g in groups]
only_generic = sum(1 for p in nodes if not any(a["links"] for a in notices[p].get("actors", [])) and notices[p].get("generic_actors"))
resume = {"repli": REPLI, "nodes": len(nodes), "edges": {t: sum(1 for e in edges if e["type"] == t) for t in ("actor", "parent", "internal_copy")},
          "components": k, "singletons": sum(s == 1 for s in sizes), "largest_component": max(sizes) if sizes else 0,
          "size_histogram": np.histogram(sizes, bins=[1, 2, 3, 6, 11, 21, 51, 101, 1001, 10 ** 6])[0].tolist(),
          "objects_only_generic_actor": only_generic, "reserve_components": n_reserve,
          "reserve_objects": sum(len(g["members"]) for g in groups if g["reserve"]),
          "nodes_by_support": {t: sum(1 for p in nodes if support(p) == t) for t in TYPES},
          "inputs_sha256": {"notices": sha(NOTICES), **{f: sha(FILTRES / f) for f in ("images.jsonl", "voisins.jsonl", "internes.jsonl")}},
          "script_sha256": sha(Path(__file__)), "numpy": np.__version__}
if not REPLI:
    write_json(groups, OUT / "groupes.json")
else:
    old = json.load(open(OUT / "groupes.json"))
    assert [g["members"] for g in old] == [g["members"] for g in groups] and [g["reserve"] for g in old] == [g["reserve"] for g in groups], \
        "components or reserve differ from the first pass: they are never rebuilt"

# ---- Sheet (step 4) ----
reserve_objs = sorted(p for g in groups if g["reserve"] for p in g["members"])
rng = np.random.default_rng(2)
sheet = {}
choices = []
for t in TYPES:
    objs = [p for p in reserve_objs if support(p) == t]
    for filt in ("dhash", "cos"):
        if filt == "dhash":
            pairs = [(p, voisins[p]["dhash_ref"], voisins[p]["dhash_min_bits"]) for p in objs]
            rejected = sorted([x for x in pairs if x[2] < T_DHASH], key=lambda x: (T_DHASH - x[2], x[0]))
            kept = sorted([x for x in pairs if x[2] >= T_DHASH], key=lambda x: (x[2] - T_DHASH, x[0]))
            band = lambda x: BAND_DHASH[0] <= x[2] <= BAND_DHASH[1]  # noqa: E731
        else:
            pairs = [(p, voisins[p]["cos_ref"], voisins[p]["cos_max"]) for p in objs]
            rejected = sorted([x for x in pairs if x[2] >= T_COS], key=lambda x: (x[2] - T_COS, x[0]))
            kept = sorted([x for x in pairs if x[2] < T_COS], key=lambda x: (T_COS - x[2], x[0]))
            band = lambda x: BAND_COS[0] <= x[2] < BAND_COS[1]  # noqa: E731
        a, b = rejected[:6], kept[:6]
        rest = [x for x in kept[6:] if band(x)]
        if len(rest) > 4:
            c = [rest[j] for j in sorted(rng.choice(len(rest), 4, replace=False))]
            choices.append({"support": t, "filter": filt, "band_size": len(rest)})
        else:
            c = rest
        for tag, lst in (("a_rejected", a), ("b_kept_near", b), ("c_kept_band", c)):
            for p, ref, d in lst:
                e = sheet.setdefault((p, ref), {"pid": p, "ref": ref, "support": t, "selected": []})
                e["selected"].append({"filter": filt, "group": tag, "distance": d})
        resume.setdefault("sheet_counts", {})[f"{t}/{filt}"] = {"a": len(a), "b": len(b), "c": len(c), "band": len(rest),
                                                               "rejected_total": len(rejected), "kept_total": len(kept)}
planche = {"thresholds": {"dhash_lt": T_DHASH, "cos_ge": T_COS, "band_dhash": BAND_DHASH, "band_cos": BAND_COS}, "repli": REPLI,
           "pairs": sorted(sheet.values(), key=lambda e: (TYPES.index(e["support"]), e["pid"], e["ref"])), "rng2_calls": choices}
resume["sheet_pairs"] = len(planche["pairs"])
write_json(planche, OUT / ("planche_repli.json" if REPLI else "planche.json"))
write_json(resume, OUT / ("resume_repli.json" if REPLI else "resume.json"))
print(json.dumps({k: v for k, v in resume.items() if k != "inputs_sha256"}))
