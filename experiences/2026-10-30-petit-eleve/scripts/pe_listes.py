"""Petit élève: the frozen lists and the name table (PREINSCRIPTION.md section 1 and 2). Local, light: file bookkeeping only.

Usage: pe_listes.py PILOT HAIKU OUT
  PILOT  ~/porkyevitch-donnees/graphes-gemini/pilote (tirage.json, images/, graphes/pNNN/g.json)
  HAIKU  ~/porkyevitch-donnees/graphes-haiku (systemes/ensembles.json, systemes/evaluation/S1b, test20/selection.json)
  OUT    the experiment folder: listes.json and noms.json (identifiers and sha256 only; no image, no code, no score)
Reads the names of the training graphs only to build the name table. Reads no object, box or relation of the tuning or
evaluation graphs: their files are only hashed.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pe_common as pc  # noqa: E402

TIRAGE_SHA256 = "6f618135db479c6842b36fc6fb7a4b20ee7543e8bcc6b11d77847c3d04836749"
ENSEMBLES_SHA256 = "87fab98819cd53ce96e925ed4a88143c05f2251bae4d7cc4e839fd89e8d56921"
TEST20_SHA256 = "0c0098dc20c14b38842e6b24fefdf15a6fc834df27bbece998c530eb6bdbe0ed"
SEED_PLANCHE, SEED_OVERFIT, SEED_TIMING = 1230, 1231, 1232
N_PLANCHE, N_OVERFIT, N_TIMING = 12, 8, 96


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stem(n):
    return Path(n).stem


def main(pilot, haiku, out):
    pilot, haiku, out = Path(pilot), Path(haiku), Path(out)
    for p, want in ((pilot / "tirage.json", TIRAGE_SHA256), (haiku / "systemes/ensembles.json", ENSEMBLES_SHA256),
                    (haiku / "test20/selection.json", TEST20_SHA256)):
        assert sha(p) == want, f"{p}: not the pinned file"
    tirage = json.loads((pilot / "tirage.json").read_text())
    picks = {stem(p["file"]): p for p in tirage["picks"]}
    ens = json.loads((haiku / "systemes/ensembles.json").read_text())
    test20 = [stem(n) for n in json.loads((haiku / "test20/selection.json").read_text())["images"]]
    sets = {"exemples": [stem(n) for n in ens["exemples"]], "reglage": [stem(n) for n in ens["reglage"]],
            "evaluation": [stem(n) for n in ens["evaluation"]], "test20": test20}
    reserved = set().union(*sets.values())
    assert reserved <= set(picks) and sum(map(len, sets.values())) == len(reserved) == 83, "reserved sets overlap"
    accepted = sorted(p.parent.name for p in (pilot / "graphes").glob("p*/g.json"))
    assert len(accepted) == 178
    train = [p for p in accepted if p not in reserved]

    def item(name, s1b=False):
        img = pilot / "images" / picks[name]["file"]
        g = pilot / "graphes" / name / "g.json"
        row = {"name": name, "md5": picks[name]["md5"], "shard": picks[name]["shard"], "row": picks[name]["row"],
               "image_sha256": sha(img), "gemini_graph_sha256": sha(g) if g.exists() else None}
        assert hashlib.md5(img.read_bytes()).hexdigest() == row["md5"], name
        if s1b:
            f = haiku / "systemes/evaluation/S1b" / f"{name}.json"
            row["s1b_graph_sha256"] = sha(f) if f.exists() else None
            twin = haiku / "systemes/evaluation/images" / picks[name]["file"]
            assert sha(twin) == row["image_sha256"], f"{name}: the S1b image differs from the pilot's"
        return row

    lists = {"entrainement": [item(n) for n in train],
             "reglage": [item(n) for n in sets["reglage"]],
             "evaluation": [item(n, s1b=True) for n in sets["evaluation"]],
             "fermes": {"exemples": sets["exemples"], "test20": sets["test20"]}}
    assert len(lists["entrainement"]) == 106
    with_graph = [r["name"] for r in lists["evaluation"] if r["gemini_graph_sha256"]]
    assert len(with_graph) == 26 and sum(1 for r in lists["reglage"] if r["gemini_graph_sha256"]) == 26
    lists["planche"] = sorted(np.random.default_rng(SEED_PLANCHE).choice(with_graph, N_PLANCHE, replace=False).tolist())
    lists["surapprentissage"] = sorted(np.random.default_rng(SEED_OVERFIT).choice(train, N_OVERFIT, replace=False).tolist())
    lists["chronometrage"] = sorted(np.random.default_rng(SEED_TIMING).choice(train, N_TIMING, replace=False).tolist())
    lists["seeds"] = {"planche": SEED_PLANCHE, "surapprentissage": SEED_OVERFIT, "chronometrage": SEED_TIMING}
    lists["sources_sha256"] = {"tirage.json": TIRAGE_SHA256, "ensembles.json": ENSEMBLES_SHA256,
                               "test20/selection.json": TEST20_SHA256}

    names = Counter()
    for n in train:
        names.update(o["name"].strip().lower() for o in json.loads((pilot / "graphes" / n / "g.json").read_text())["objects"])
    table = pc.name_table(names)
    by_cat = Counter()
    for v in table.values():
        by_cat[v["category"]] += v["count"]
    noms = {"built_on": "names of the 106 training graphs only", "rules_module_sha256": sha(Path(pc.__file__)),
            "objects_by_category": dict(sorted(by_cat.items())), "autre_share": by_cat[pc.AUTRE] / sum(by_cat.values()),
            "table": table}
    for f, obj in (("listes.json", lists), ("noms.json", noms)):
        (out / f).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n")
    print({k: len(v) for k, v in lists.items() if isinstance(v, list)}, dict(by_cat))


if __name__ == "__main__":
    main(*sys.argv[1:4])
