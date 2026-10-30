#!/usr/bin/env python3
"""Rijksmuseum bench, chronology steps 4 (rule) to 7: audit rule, removal by the reference filter, feasibility, draw, freeze.

Usage: tirage_gel.py NOTICES FILTRES COMP OUT CACHE
CACHE: the response cache of the collection (raw bytes + sidecars); the sha256 of the raw responses of each frozen object (object,
visual item, digital object, profile la-framed) are read from their sidecars and frozen with it; a missing sidecar stops the script.
COMP: the folder of composantes_reserve.py (groupes.json, planche.json, and planche_repli.json if the fallback sheet was made) and the
audit decisions: audit.json (first sheet) and, if the fallback was triggered, audit_repli.json. An audit file maps the pair number of
the sheet (index.json of planche_images.py, from 1) to {"orchestrateur": d, "verificateur": d}, d in copie / non-copie / incertain; a
disagreement counts as incertain (PREINSCRIPTION.md).
Rule, fixed before the sheet: for a filter and a support, at least 2 kept pairs (groups b or c) judged copie, or 1 copie and 2
incertain, trigger the fallback (dHash < 64, cosine >= 0.92, all supports) and the fallback sheet; if the fallback sheet triggers again,
stop (exit 2, new preregistration). False rejections never loosen a threshold.
Then: components of the population outside the reserve with a member under the final thresholds (dhash_min_bits < T or cos_max >= Tc)
are removed whole; components keep their capped members (groupes.json); in permutation order, each remaining component is added
whole to the test while the test has fewer than 1 200 images, then to the dev while it has fewer than 300. Feasibility: test >= 1 200
images and >= 150 components, dev >= 300 images and >= 40 components, otherwise stop (exit 2). Writes frozen.json (test and dev:
PID, types, component, IIIF URL, image sha256 and size, raw truth with URIs, projected truth without chapter 86; component edges and
reasons; thresholds, audit summary, sha256 of every input and script; counts by support), then vu.json (sha256 of frozen.json and
of the audit files). Prints counts only.
"""

import hashlib
import json
import sys
from pathlib import Path

NOTICES, FILTRES, COMP, OUT, CACHE = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
PROFILE, ACCEPT = "la-framed", "application/ld+json"
OUT.mkdir(parents=True, exist_ok=True)
TYPES = ["painting", "print", "drawing"]
TEST_N, DEV_N, TEST_C, DEV_C = 1200, 300, 150, 40


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(obj, path: Path):
    tmp = path.with_name(path.name + ".tmp")
    json.dump(obj, open(tmp, "w"), ensure_ascii=False, indent=1)
    tmp.replace(path)


def verdict(d: dict) -> str:
    a, b = d["orchestrateur"], d["verificateur"]
    assert a in ("copie", "non-copie", "incertain") and b in ("copie", "non-copie", "incertain"), d
    return a if a == b else "incertain"


def triggered(planche: Path, audit: Path) -> tuple[bool, dict]:
    pairs = json.load(open(planche))["pairs"]
    dec = json.load(open(audit))
    assert set(dec) == {str(n) for n in range(1, len(pairs) + 1)}, f"{audit.name}: every pair of the sheet needs a decision"
    counts = {}
    for n, p in enumerate(pairs, 1):
        v = verdict(dec[str(n)])
        for s in p["selected"]:
            if s["group"] in ("b_kept_near", "c_kept_band"):
                c = counts.setdefault(f"{p['support']}/{s['filter']}", {"copie": 0, "incertain": 0, "non-copie": 0})
                c[v] += 1
    hit = {k: c for k, c in counts.items() if c["copie"] >= 2 or (c["copie"] >= 1 and c["incertain"] >= 2)}
    return bool(hit), {"counts": counts, "triggered_by": sorted(hit)}


first, summary1 = triggered(COMP / "planche.json", COMP / "audit.json")
audit_files = [COMP / "audit.json"]
sheet_files = [COMP / "planche.json"]
summary = {"first_sheet": summary1}
if first:
    second, summary2 = triggered(COMP / "planche_repli.json", COMP / "audit_repli.json")
    audit_files.append(COMP / "audit_repli.json")
    sheet_files.append(COMP / "planche_repli.json")
    summary["fallback_sheet"] = summary2
    if second:
        write_json({"stop": "fallback sheet contradicts the thresholds again", **summary,
                    "inputs_sha256": {f.name: sha(f) for f in sheet_files + audit_files}}, OUT / "arret.json")
        print("STOP: fallback sheet triggered again; new preregistration")
        sys.exit(2)
    T, TC = 64, 0.92
else:
    T, TC = 50, 0.95

notices = {r["pid"]: r for r in map(json.loads, open(NOTICES))}
images = {r["pid"]: r for r in map(json.loads, open(FILTRES / "images.jsonl"))}
voisins = {r["pid"]: r for r in map(json.loads, open(FILTRES / "voisins.jsonl"))}
groups = json.load(open(COMP / "groupes.json"))
order = sorted((g for g in groups if not g["reserve"]), key=lambda g: g["permutation_rank"])
touched = [g for g in order if any(voisins[p]["dhash_min_bits"] < T or voisins[p]["cos_max"] >= TC for p in g["members"])]
touched_ranks = {g["canonical_rank"] for g in touched}
test, dev = [], []
for g in order:
    if g["canonical_rank"] in touched_ranks:
        continue
    if sum(len(x["capped"]) for x in test) < TEST_N:
        test.append(g)
    elif sum(len(x["capped"]) for x in dev) < DEV_N:
        dev.append(g)
    else:
        break
n_test, n_dev = sum(len(g["capped"]) for g in test), sum(len(g["capped"]) for g in dev)
feas = {"test_images": n_test, "test_components": len(test), "dev_images": n_dev, "dev_components": len(dev),
        "removed_components": len(touched), "removed_objects": sum(len(g["members"]) for g in touched),
        "thresholds": {"dhash_lt": T, "cos_ge": TC}}
if n_test < TEST_N or len(test) < TEST_C or n_dev < DEV_N or len(dev) < DEV_C:
    write_json({"stop": "feasibility not reached", **feas, **summary}, OUT / "arret.json")
    print("STOP: feasibility not reached;", json.dumps(feas))
    sys.exit(2)


def raw_sha(url):
    """sha256 of the raw response cached for url (as collecte_notices.get keys it), checked against its bytes."""
    full = url + ("&" if "?" in url else "?") + f"_profile={PROFILE}"
    key = hashlib.sha256(f"{full}\n{ACCEPT}".encode()).hexdigest()
    side = json.load(open(CACHE / f"{key}.json"))
    assert side["url"] == full and hashlib.sha256((CACHE / f"{key}.raw").read_bytes()).hexdigest() == side["sha256"], url
    return {"url": full, "sha256": side["sha256"], "date_utc": side["date_utc"]}


def item(p, g):
    r, im = notices[p], images[p]
    return {"pid": p, "types": r["types"], "support": next(t for t in TYPES if t in r["types"]), "component": g["canonical_rank"],
            "iiif": r["image"]["iiif"], "visual": r["image"]["visual"], "digital": r["image"]["digital"],
            "image_sha256": im["sha256"], "width": im["width"], "height": im["height"],
            "responses": {"object": raw_sha(p), "visual": raw_sha(r["image"]["visual"]), "digital": raw_sha(r["image"]["digital"])},
            "truth_raw": r["codes_all"], "truth": [c["code"] for c in r["codes"]], "truth_projected": r["projected"]}


def split(gs):
    return {"items": [item(p, g) for g in gs for p in g["capped"]],
            "components": [{"canonical_rank": g["canonical_rank"], "members_capped": g["capped"], "size": len(g["members"]),
                            "edges": g["edges"]} for g in gs]}


here = Path(__file__).parent
frozen = {"date_utc": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
          "test": split(test), "dev": split(dev), "feasibility": feas, "audit": summary,
          "by_support": {name: {t: sum(1 for g in gs for p in g["capped"] if next(u for u in TYPES if u in notices[p]["types"]) == t)
                                for t in TYPES} for name, gs in (("test", test), ("dev", dev))},
          "inputs_sha256": {"notices": sha(NOTICES), "groupes": sha(COMP / "groupes.json"),
                            **{f.name: sha(f) for f in sheet_files + audit_files},
                            **{f: sha(FILTRES / f) for f in ("images.jsonl", "voisins.jsonl", "internes.jsonl", "run.json", "rijks.json")}},
          "scripts_sha256": {s: sha(here / s) for s in ("collecte_notices.py", "liste_eligibles.py", "filtres_distances.py",
                                                        "composantes_reserve.py", "planche_images.py", "tirage_gel.py")},
          "reference": {"dataset": "davanstrien/iconclass-vlm-brillfull@8045366ff092a06e8e1c4e47f1eb43cb2a54d732", "rows": 87004,
                        "encoder_output": "kernel mabaku/caypollard-encode-cradio v3 (encode_cradio.py c3f12bb7…)"},
          "rights": "metadata CC0 (record subject_of); reproductions PDM (digital object or visual item) under the Rijksmuseum "
                    "information and data policy, §1.1 and §3.7"}
write_json(frozen, OUT / "frozen.json")
write_json({"frozen_sha256": sha(OUT / "frozen.json"), **{f.name: sha(f) for f in sheet_files + audit_files}}, OUT / "vu.json")
print(json.dumps({**feas, "by_support": frozen["by_support"]}))
