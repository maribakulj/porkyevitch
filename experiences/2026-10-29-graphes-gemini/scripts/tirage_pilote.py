"""Draw of the Gemini scene-graph pilot (porkyevitch, experiences/2026-10-29-graphes-gemini, PREINSCRIPTION.md). Kaggle CPU.

Usage: tirage_pilote.py ENC OUT
  ENC  the full output of kernel caypollard-encode-cradio v3 (feats/<shard>.npz with md5, grid/<shard>.json with labels)
  OUT  output directory: images/pNNN.<ext> (original bytes), verite.json (codes, never shown to Gemini), tirage.json (md5,
       shard, row, planche), run.json
Steps, all fixed before any image is sent:
  (1) the eleven ICAI train shards only (never test-00000-of-00001); validation = the series' groups:
      default_rng(0).random(len(groups)) < 0.05 on the sorted md5 of the 86,216 train rows (as e0_reference.py);
  (1b) groups whose md5 is also an image of the test shard (exact copies) are removed after the validation draw (md5 field only);
  (2) 200 groups drawn among the remaining groups by default_rng(29).choice(sorted groups, 200, replace=False);
      one image per group: its first row in shard order;
  (3) each image read from the dataset at the pinned revision, md5 checked against the encoder's, bytes written unchanged;
  (4) planche: 12 of the 200 by default_rng(30).choice(200, 12, replace=False), sorted.
"""
import hashlib, io, json, sys
from pathlib import Path

import numpy as np

REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
N, N_PLANCHE = 200, 12


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def write_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


enc, out = Path(sys.argv[1]), Path(sys.argv[2])
(out / "images").mkdir(parents=True, exist_ok=True)

# (1) md5 and labels of the train rows, validation groups as in the series
rows = []  # (shard, row, md5, labels)
for tag in TRAIN:
    md5 = list(np.load(enc / "feats" / f"{tag}.npz")["md5"])
    labels = json.load(open(enc / "grid" / f"{tag}.json"))["labels"]
    assert len(md5) == len(labels)
    rows += [(tag, i, m, y) for i, (m, y) in enumerate(zip(md5, labels))]
assert len(rows) == 86216
groups = sorted({r[2] for r in rows})
gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
# exact copies of test images that also sit in train are excluded AFTER the validation draw (which stays the series' own);
# only the md5 field of the test shard is read: no image, no label, no score
test_md5 = set(np.load(enc / "feats" / "test-00000-of-00001.npz")["md5"])
train_groups = [g for g in groups if g not in gval and g not in test_md5]

# (2) draw
chosen = list(np.random.default_rng(29).choice(train_groups, N, replace=False))
first = {}
for r in rows:
    if r[2] in chosen and r[2] not in first:
        first[r[2]] = r
picks = [first[m] for m in chosen]
assert not ({p[2] for p in picks} & (gval | test_md5)) and len({p[2] for p in picks}) == N

# (3) images from the dataset at the pinned revision
import pyarrow.parquet as pq  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402
from PIL import Image  # noqa: E402

need = {}
for k, (tag, i, m, y) in enumerate(picks):
    need.setdefault(tag, []).append((k, i, m))
files = {}
for tag, items in need.items():
    path = hf_hub_download(REPO, f"data/{tag}.parquet", repo_type="dataset", revision=REV, cache_dir="/tmp/tirage_hf")
    col = pq.read_table(path, columns=["image"]).column("image")
    for k, i, m in items:
        b = col[i].as_py()["bytes"]
        assert hashlib.md5(b).hexdigest() == m, (tag, i)
        ext = {"JPEG": "jpg", "PNG": "png"}.get(Image.open(io.BytesIO(b)).format, "img")
        name = f"p{k:03d}.{ext}"
        (out / "images" / name).write_bytes(b)
        files[k] = name
    del col

# (4) planche
planche = sorted(int(k) for k in np.random.default_rng(30).choice(N, N_PLANCHE, replace=False))

write_json({files[k]: {"md5": m, "labels": y} for k, (tag, i, m, y) in enumerate(picks)}, out / "verite.json")
write_json({"dataset": [REPO, REV], "train_rows": len(rows), "train_groups": len(train_groups), "validation_groups": len(gval),
            "test_copy_groups_excluded": len((set(groups) - gval) & test_md5), "disjoint_from_validation_and_test": True,
            "picks": [{"file": files[k], "md5": m, "shard": tag, "row": i} for k, (tag, i, m, y) in enumerate(picks)],
            "planche": [files[k] for k in planche]}, out / "tirage.json")
write_json({"script_sha256": sha(__file__), "numpy": np.__version__}, out / "run.json")
print("done", len(files), "images; planche", [files[k] for k in planche])
