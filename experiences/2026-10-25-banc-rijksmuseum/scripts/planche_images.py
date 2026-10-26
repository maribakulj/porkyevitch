#!/usr/bin/env python3
"""Rijksmuseum bench, chronology step 4: the images of the audit sheet, assembled remotely (Kaggle), no code, no prediction.

Usage: planche_images.py OUT FILTRES PLANCHE
FILTRES: the output folder of filtres_distances.py (full run: images/<k>.jpg, images.jsonl). PLANCHE: planche.json (or
planche_repli.json) of composantes_reserve.py: reserve pairs (candidate PID, reference index). For each pair, the candidate image (its
kept bytes, sha256 checked against images.jsonl) and the reference image (brillfull, pinned revision, row = global index in the
encoder's shard order, md5 checked against ref_dhash.npz of FILTRES) are put side by side, each fitted into 512 x 512 without
cropping, with a caption line: pair number, support, filters and groups selected, distances. Writes OUT/paires/<n>.jpg (n = order
of planche.json, from 1), OUT/planches/<support>-<m>.jpg (contact sheets of 6 pairs) and OUT/index.json (n, pid, ref, support,
selected, sha256 of the candidate image, md5 of the reference image as in ref_dhash.npz). Nothing else about the objects is shown.
"""

import hashlib
import io
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT, FILTRES, PLANCHE = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
for d in ("paires", "planches"):
    (OUT / d).mkdir(parents=True, exist_ok=True)
CACHE = Path(os.environ.get("PLANCHE_HF_CACHE", "/tmp/planche_hf"))
REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
SHARDS = ["data/test-00000-of-00001.parquet"] + [f"data/train-{i:05d}-of-00011.parquet" for i in range(11)]
SIDE = 512

pl = json.load(open(PLANCHE))
pairs = pl["pairs"]
images = {r["pid"]: r for r in map(json.loads, open(FILTRES / "images.jsonl"))}
ref = np.load(FILTRES / "ref_dhash.npz")
ref_md5 = {int(i): str(m) for i, m in zip(ref["idx"], ref["md5"])}
assert len(ref_md5) == 87004, "the sheet needs the full reference (87,004 rows)"

# Reference rows needed, grouped by shard (global index -> shard and row, from the shard sizes in the encoder's order)
import pyarrow.parquet as pq  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402

os.environ.setdefault("HF_HOME", str(CACHE))
need = sorted({p["ref"] for p in pairs})
ref_bytes, start = {}, 0
for shard in SHARDS:
    path = hf_hub_download(REPO, shard, repo_type="dataset", revision=REV, cache_dir=CACHE / "hub")
    pf = pq.ParquetFile(path)
    n = pf.metadata.num_rows
    rows = [g - start for g in need if start <= g < start + n]
    if rows:
        col = pf.read(columns=["image"]).column("image")
        for r in rows:
            b = col[r].as_py()["bytes"]
            assert hashlib.md5(b).hexdigest() == ref_md5[start + r], f"reference row {start + r}: md5 differs"
            ref_bytes[start + r] = b
        del col
    start += n
    blob = Path(os.path.realpath(path))
    assert CACHE.resolve() in blob.parents, blob
    blob.unlink()
    Path(path).unlink(missing_ok=True)
assert start == 87004 and set(ref_bytes) == set(need)


def fit(im):
    im = im.convert("RGB")
    im.thumbnail((SIDE, SIDE), Image.BICUBIC)
    c = Image.new("RGB", (SIDE, SIDE), (255, 255, 255))
    c.paste(im, ((SIDE - im.width) // 2, (SIDE - im.height) // 2))
    return c


def caption(n, p):
    sel = "; ".join(f"{s['filter']} {s['group']} {s['distance']:.3f}" if s["filter"] == "cos" else f"{s['filter']} {s['group']} {s['distance']}"
                    for s in p["selected"])
    return f"paire {n}  {p['support']}  {sel}  (gauche : Rijksmuseum, droite : référence d'entraînement)"


index, tiles = [], {}
for n, p in enumerate(pairs, 1):
    row = images[p["pid"]]
    cb = (FILTRES / "images" / f"{row['k']}.jpg").read_bytes()
    assert hashlib.sha256(cb).hexdigest() == row["sha256"], p["pid"]
    rb = ref_bytes[p["ref"]]
    canvas = Image.new("RGB", (2 * SIDE + 12, SIDE + 36), (255, 255, 255))
    canvas.paste(fit(Image.open(io.BytesIO(cb))), (0, 36))
    canvas.paste(fit(Image.open(io.BytesIO(rb))), (SIDE + 12, 36))
    ImageDraw.Draw(canvas).text((6, 10), caption(n, p), fill=(0, 0, 0))
    canvas.save(OUT / "paires" / f"{n}.jpg", quality=88)
    tiles.setdefault(p["support"], []).append(canvas)
    index.append({"n": n, "pid": p["pid"], "ref": p["ref"], "support": p["support"], "selected": p["selected"],
                  "candidate_sha256": row["sha256"], "reference_md5": ref_md5[p["ref"]]})
for support, lst in tiles.items():
    for m in range(0, len(lst), 6):
        chunk = lst[m:m + 6]
        w, h = chunk[0].size
        sheet = Image.new("RGB", (w, h * len(chunk)), (255, 255, 255))
        for j, t in enumerate(chunk):
            sheet.paste(t, (0, j * h))
        sheet.save(OUT / "planches" / f"{support}-{m // 6 + 1}.jpg", quality=85)
tmp = OUT / "index.json.tmp"
json.dump({"planche": str(PLANCHE.name), "planche_sha256": hashlib.sha256(PLANCHE.read_bytes()).hexdigest(), "pairs": index},
          open(tmp, "w"), ensure_ascii=False, indent=1)
tmp.replace(OUT / "index.json")
print(len(index), "pairs assembled")
