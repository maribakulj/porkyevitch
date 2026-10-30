"""Draw of the 300-image S1b slice, stratified by Iconclass chapter (porkyevitch-maths, experiences/2026-10-30-tirage-300,
PREINSCRIPTION.md). Kaggle CPU. Derived from the reviewed tirage_pilote.py (graphes-gemini, sha 42e6efc4...).

Usage: tirage_300.py --stage plan|full ENC PILOT OUT
  ENC    the full output of kernel caypollard-encode-cradio v3 (feats/<shard>.npz with md5, grid/<shard>.json with labels)
  PILOT  tirage.json of the Gemini pilot (its 200 md5 are excluded; pinned sha below)
  OUT    output directory. plan: tirage.json and run.json only, no image read. full: the same tirage.json, plus
         images/tNNN.<ext> (original bytes) and verite.json (codes, never shown to the annotator), kept apart.
Steps, all fixed before any image is sent:
  (1) the eleven ICAI train shards only; validation = the series' groups, default_rng(0).random(len(groups)) < 0.05 on the
      sorted md5 of the 86,216 train rows; then groups that are exact copies of a test image (md5 field of the test shard
      only) and the 200 groups of the pilot are removed. One image per group: its first row in shard order.
  (2) chapter of a code = its first character, a digit 0-9, on the train labels with 86 removed (drop86, as the series).
      Chapter of an image = the chapter holding most of its distinct codes; ties: the chapter present in fewer population
      groups, then the smaller digit. Groups without any chapter are left out and counted.
  (3) allocation of N = 300: each chapter gets min(10, N_h); the rest is shared in proportion to N_h by largest remainder
      (ties: smaller digit), never above N_h. Inclusion probability n_h / N_h published per chapter.
  (4) in chapter h: default_rng([31, h]).choice(sorted groups of h, n_h, replace=False).
  (5) internal validation of 60, frozen before any annotation (Codex p4, D2): v_h = 60 n_h / 300 by largest remainder (ties:
      smaller digit); in chapter h the first v_h of default_rng([32, h]).permutation(n_h) over the drawn order.
  (6) file names t000-t299 in the order of default_rng(33).permutation(300) over the (chapter, draw) order, so that a name
      tells nothing of the chapter or of the role.
  (7) full only: each image read from the dataset at the pinned revision, md5 checked, bytes written unchanged.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np

REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
PILOT_SHA256 = "6f618135db479c6842b36fc6fb7a4b20ee7543e8bcc6b11d77847c3d04836749"
N, MINIMUM, N_VAL = 300, 10, 60
SEED_DRAW, SEED_VAL, SEED_NAMES = 31, 32, 33
CHAPTERS = [str(d) for d in range(10)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def drop86(codes):
    return [c for c in codes if not c.strip().startswith("86")]


def chapter_counts(labels):
    counts = {}
    for c in {c.strip() for c in drop86(labels)}:
        head = c[:1]
        if head in CHAPTERS:
            counts[head] = counts.get(head, 0) + 1
    return counts


def image_chapters(group_labels):
    """group_labels: {md5: labels}. Returns ({md5: chapter}, [md5 without chapter], {chapter: groups present})."""
    counts = {m: chapter_counts(y) for m, y in group_labels.items()}
    present = {h: sum(1 for c in counts.values() if h in c) for h in CHAPTERS}
    chapter, none = {}, []
    for m in sorted(counts):
        c = counts[m]
        if not c:
            none.append(m)
            continue
        chapter[m] = min(c, key=lambda h: (-c[h], present[h], h))
    return chapter, none, present


def largest_remainder(total, weights, caps):
    """Integers summing to min(total, sum(caps)), proportional to weights, each <= cap; ties: smaller key."""
    alloc = {h: 0 for h in weights}
    left = min(total, sum(caps.values()))
    while left > 0:
        open_ = [h for h in weights if alloc[h] < caps[h] and weights[h] > 0]
        wsum = sum(weights[h] for h in open_)
        quota = {h: left * weights[h] / wsum for h in open_}
        base = {h: min(int(quota[h]), caps[h] - alloc[h]) for h in open_}
        for h in open_:
            alloc[h] += base[h]
        left -= sum(base.values())
        for h in sorted((h for h in open_ if alloc[h] < caps[h]), key=lambda h: (-(quota[h] - int(quota[h])), h)):
            if left == 0:
                break
            alloc[h] += 1
            left -= 1
    return alloc


def allocate(sizes, n=N, minimum=MINIMUM):
    """sizes: {chapter: N_h}. min(minimum, N_h) each, rest proportional to N_h, never above N_h."""
    base = {h: min(minimum, s) for h, s in sizes.items()}
    rest = largest_remainder(n - sum(base.values()), sizes, {h: sizes[h] - base[h] for h in sizes})
    return {h: base[h] + rest[h] for h in sizes}


def plan(rows, test_md5, pilot_md5):
    """rows: [(shard, row, md5, labels)] in shard order. Returns the draw description (no image read)."""
    groups = sorted({r[2] for r in rows})
    gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
    assert not (pilot_md5 & (gval | test_md5)), "pilot overlaps validation or test copies"
    first = {}
    for r in rows:
        first.setdefault(r[2], r)
    population = [g for g in groups if g not in gval and g not in test_md5 and g not in pilot_md5]
    chapter, none, present = image_chapters({g: first[g][3] for g in population})
    sizes = {h: sum(1 for g in chapter.values() if g == h) for h in CHAPTERS}
    alloc = allocate(sizes)
    vals = largest_remainder(N_VAL, alloc, alloc)
    drawn = []  # (chapter, md5, role)
    for h in CHAPTERS:
        if not alloc[h]:
            continue
        pool = sorted(g for g, c in chapter.items() if c == h)
        picked = list(np.random.default_rng([SEED_DRAW, int(h)]).choice(pool, alloc[h], replace=False))
        val_idx = set(np.random.default_rng([SEED_VAL, int(h)]).permutation(alloc[h])[:vals[h]].tolist())
        drawn += [(h, str(m), "validation_interne" if k in val_idx else "apprentissage") for k, m in enumerate(picked)]
    order = np.random.default_rng(SEED_NAMES).permutation(len(drawn))
    picks = []
    for name_index, k in enumerate(order):
        h, m, role = drawn[k]
        shard, row, _, _ = first[m]
        picks.append({"name": f"t{name_index:03d}", "md5": m, "shard": shard, "row": int(row), "chapter": h, "role": role})
    assert len({p["md5"] for p in picks}) == len(picks) == N
    assert not ({p["md5"] for p in picks} & (gval | test_md5 | pilot_md5))
    return {"dataset": [REPO, REV], "train_rows": len(rows), "train_groups": len(groups), "validation_groups": len(gval),
            "test_copy_groups_excluded": len((set(groups) - gval) & test_md5),
            "pilot_groups_excluded": len(pilot_md5), "population_groups": len(population),
            "groups_without_chapter": len(none),
            "chapters": {h: {"population": sizes[h], "groups_with_a_code_of_this_chapter": present[h], "drawn": alloc[h],
                             "inclusion_probability": alloc[h] / sizes[h] if sizes[h] else None,
                             "validation_interne": vals[h]} for h in CHAPTERS},
            "rule": {"n": N, "minimum": MINIMUM, "n_validation": N_VAL,
                     "seeds": {"draw": SEED_DRAW, "validation": SEED_VAL, "names": SEED_NAMES}},
            "picks": picks}


def read_rows(enc):
    rows = []
    for tag in TRAIN:
        with np.load(enc / "feats" / f"{tag}.npz", allow_pickle=False) as z:
            md5 = [str(m) for m in z["md5"]]
        labels = json.load(open(enc / "grid" / f"{tag}.json"))["labels"]
        assert len(md5) == len(labels)
        rows += [(tag, i, m, y) for i, (m, y) in enumerate(zip(md5, labels))]
    assert len(rows) == 86216
    with np.load(enc / "feats" / "test-00000-of-00001.npz", allow_pickle=False) as z:
        test_md5 = {str(m) for m in z["md5"]}  # md5 field only: no image, no label, no score
    return rows, test_md5


def fetch(picks, out):
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    from PIL import Image
    files, need = {}, {}
    for p in picks:
        need.setdefault(p["shard"], []).append(p)
    for tag, items in need.items():
        path = hf_hub_download(REPO, f"data/{tag}.parquet", repo_type="dataset", revision=REV, cache_dir="/tmp/tirage_hf")
        col = pq.read_table(path, columns=["image"]).column("image")
        for p in items:
            b = col[p["row"]].as_py()["bytes"]
            assert hashlib.md5(b).hexdigest() == p["md5"], (tag, p["row"])
            ext = {"JPEG": "jpg", "PNG": "png"}.get(Image.open(io.BytesIO(b)).format, "img")
            files[p["name"]] = f"{p['name']}.{ext}"
            (out / "images" / files[p["name"]]).write_bytes(b)
        del col
    return files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("plan", "full"), required=True)
    ap.add_argument("enc", type=Path)
    ap.add_argument("pilot", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args(argv)
    assert sha(a.pilot) == PILOT_SHA256, "pilot tirage.json is not the pinned one"
    pilot_md5 = {p["md5"] for p in json.load(open(a.pilot))["picks"]}
    assert len(pilot_md5) == 200
    rows, test_md5 = read_rows(a.enc)
    result = plan(rows, test_md5, pilot_md5)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.stage == "full":
        (a.out / "images").mkdir(exist_ok=True)
        labels = {(r[0], r[1]): r[3] for r in rows}
        files = fetch(result["picks"], a.out)
        for p in result["picks"]:
            p["file"] = files[p["name"]]
        write_json({p["file"]: {"md5": p["md5"], "labels": labels[(p["shard"], p["row"])]} for p in result["picks"]},
                   a.out / "verite.json")
    write_json(result, a.out / "tirage.json")
    write_json({"stage": a.stage, "script_sha256": sha(__file__), "pilot_sha256": PILOT_SHA256, "numpy": np.__version__,
                "python": sys.version.split()[0]}, a.out / "run.json")
    print("done", a.stage, {h: c["drawn"] for h, c in result["chapters"].items()})


if __name__ == "__main__":
    main()
