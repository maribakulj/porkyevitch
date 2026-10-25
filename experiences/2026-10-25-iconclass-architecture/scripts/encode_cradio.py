#!/usr/bin/env python3
"""One C-RADIOv3-L pass over ICAI and the Emblematica candidates: the head's vector and an 8 x 8 grid of spatial tokens (PREINSCRIPTION.md).

Usage: encode_cradio.py OUT EXT T0
EXT holds candidates.jsonl, near256.json, images/ and gel2/ (test.json, predictions.json, candidats_feats.npz) of the external bench;
T0 holds head.pt, predictions.json and resultats.json of the published C-RADIO head (T0).
ENC_SMOKE=N keeps N rows per shard and N Emblematica rows (dry run, controls skipped, results technical only).

Writes, per ICAI shard: OUT/feats/<shard>.npz + .json (vector and manifest, the format of remote_iconclass_head.py) and
OUT/grid/<shard>.npy (float16, rows x 64 x 1024); for Emblematica: OUT/emb_vec.npz (x, files, img_sha, config) and OUT/emb_grid.npy;
OUT/controle.json (T0 reproduced from the new vectors); OUT/run.json; OUT/progress.log.
Vector = the head's exact recipe (summary token and mean of spatial tokens, each L2-normalised, concatenated, L2-normalised).
Grid = the spatial tokens (28 x 28 at 448 px), adaptive average pooling to 8 x 8, not normalised.
"""

import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

OUT, EXT, T0 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
for d in ("feats", "grid"):
    (OUT / d).mkdir(parents=True, exist_ok=True)
SMOKE = int(os.environ.get("ENC_SMOKE", "0"))
REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
SHARDS = ["data/test-00000-of-00001.parquet"] + [f"data/train-{i:05d}-of-00011.parquet" for i in range(11)]
ENC_REPO, ENC_REV = "nvidia/C-RADIOv3-L", "9d0413465e8a91e67bbf2c1ad342815478d1b906"
FEATURE_CONFIG = f"{ENC_REPO}@{ENC_REV}|square-grey128|448|bicubic|autocast-fp16|summary+meanspatial|l2-each-then-l2"
GRID_CONFIG = f"{ENC_REPO}@{ENC_REV}|square-grey128|448|bicubic|autocast-fp16|spatial28x28|adaptive-avg-8x8|fp16"
dev = "cuda" if torch.cuda.is_available() else "cpu"
started = time.time()


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def progress(msg):
    line = f"{time.time() - started:7.0f} s  {msg}"
    print(line, flush=True)
    with open(OUT / "progress.log", "a") as f:
        f.write(line + "\n")


import transformers  # noqa: E402

json.dump({"smoke": SMOKE, "device": dev, "gpu": torch.cuda.get_device_name() if dev == "cuda" else None,
           "torch": torch.__version__, "transformers": transformers.__version__, "dataset": [REPO, REV],
           "feature_config": FEATURE_CONFIG, "grid_config": GRID_CONFIG, "script_sha256": sha(__file__)},
          open(OUT / "run.json", "w"), indent=1)

# ---- Encoder: the head's recipe, unchanged (remote_iconclass_head.py), plus the grid from the same forward pass ----
from transformers import AutoModel, CLIPImageProcessor  # noqa: E402

model = AutoModel.from_pretrained(ENC_REPO, revision=ENC_REV, trust_remote_code=True).to(dev).eval()
processor = CLIPImageProcessor.from_pretrained(ENC_REPO, revision=ENC_REV)


def square(im):
    im = im.convert("RGB")
    s = max(im.size)
    c = Image.new("RGB", (s, s), (128, 128, 128))
    c.paste(im, ((s - im.width) // 2, (s - im.height) // 2))
    return c.resize((448, 448), Image.BICUBIC)


@torch.no_grad()
def encode(images):
    px = processor(images=[square(i) for i in images], return_tensors="pt", do_resize=False).pixel_values.to(dev)
    with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):  # RADIO normalises its input itself
        summary, spatial = model(px)
    v = torch.cat([torch.nn.functional.normalize(summary.float(), dim=-1),
                   torch.nn.functional.normalize(spatial.float().mean(1), dim=-1)], 1)
    vec = torch.nn.functional.normalize(v, dim=-1).cpu().numpy().astype(np.float16)
    b, n, d = spatial.shape
    assert n == 28 * 28, spatial.shape  # patch tokens only, 448 / 16 = 28 per side
    g = spatial.float().reshape(b, 28, 28, d).permute(0, 3, 1, 2)
    g = torch.nn.functional.adaptive_avg_pool2d(g, 8).permute(0, 2, 3, 1).reshape(b, 64, d)
    return vec, g.cpu().numpy().astype(np.float16)


# ---- ICAI shards, in the order and batches of the head script ----
def read_shard(shard):
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(REPO, shard, repo_type="dataset", revision=REV)
    return path, pq.read_table(path)


ICAI = {}
for shard in SHARDS:
    tag = Path(shard).stem
    npz, man, grid = OUT / "feats" / f"{tag}.npz", OUT / "feats" / f"{tag}.json", OUT / "grid" / f"{tag}.npy"
    path, table = read_shard(shard)
    n = table.num_rows if not SMOKE else min(SMOKE, table.num_rows)
    labels = table.column("label").to_pylist()[:n]
    manifest = {"dataset": [REPO, REV], "shard": shard, "rows": n, "smoke": SMOKE, "feature_config": FEATURE_CONFIG,
                "labels_sha256": hashlib.sha256(json.dumps(labels).encode()).hexdigest()}
    gman = OUT / "grid" / f"{tag}.json"
    if npz.exists() and man.exists() and grid.exists() and gman.exists() and json.load(open(man)) == manifest:
        ICAI[tag] = (np.load(npz)["x"], labels)
        progress(f"{tag}: reused")
        continue
    imgs = table.column("image").to_pylist()[:n]
    xs, gs, md5 = [], [], []
    for i in range(0, n, 32):
        chunk = imgs[i:i + 32]
        md5 += [hashlib.md5(x["bytes"]).hexdigest() for x in chunk]
        v, g = encode([Image.open(io.BytesIO(x["bytes"])) for x in chunk])
        xs.append(v)
        gs.append(g)
    x, gr = np.concatenate(xs), np.concatenate(gs)
    assert x.shape[0] == gr.shape[0] == n and np.isfinite(x).all() and np.isfinite(gr).all()
    np.save(OUT / "grid" / f"{tag}.tmp.npy", gr)
    os.replace(OUT / "grid" / f"{tag}.tmp.npy", grid)
    np.savez(OUT / "feats" / f"{tag}.tmp.npz", x=x, md5=np.array(md5))
    os.replace(OUT / "feats" / f"{tag}.tmp.npz", npz)
    json.dump({**manifest, "grid_config": GRID_CONFIG, "grid_sha256": sha(grid), "md5_sha256":
               hashlib.sha256(json.dumps(md5).encode()).hexdigest()}, open(OUT / "grid" / f"{tag}.tmp.json", "w"))
    os.replace(OUT / "grid" / f"{tag}.tmp.json", gman)
    json.dump(manifest, open(OUT / "feats" / f"{tag}.tmp.json", "w"))
    os.replace(OUT / "feats" / f"{tag}.tmp.json", man)
    os.remove(os.path.realpath(path))  # keep only the features: the cached blob, not just its link
    ICAI[tag] = (x, labels)
    progress(f"{tag}: {n} rows")

# ---- Emblematica candidates after filter 1, in the order and batches of remote_external_iconclass.py ----
near = json.load(open(EXT / "near256.json"))
bad_books = {b for _, d, _, b in near if 0 <= d < 50}
rows = [json.loads(line) for line in open(EXT / "candidates.jsonl")]
rows = [r for r in rows if r["book_id"] is not None and r["book_id"] not in bad_books]
if SMOKE:
    rows = rows[:SMOKE]
else:
    assert len(rows) == 7320, len(rows)
img_sha = [sha(EXT / "images" / r["filename"]) for r in rows]
xs, gs = [], []
for i in range(0, len(rows), 32):
    v, g = encode([Image.open(EXT / "images" / r["filename"]) for r in rows[i:i + 32]])
    xs.append(v)
    gs.append(g)
EX, EG = np.concatenate(xs), np.concatenate(gs)
np.savez(OUT / "emb_vec.npz", x=EX, files=np.array([r["filename"] for r in rows]), img_sha=np.array(img_sha),
         config=np.array(FEATURE_CONFIG))
np.save(OUT / "emb_grid.npy", EG)
progress(f"emblematica: {len(rows)} rows")
del model
torch.cuda.empty_cache()

# ---- Controls (preregistered): T0 reproduced from the new vectors ----
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
TOKEN = re.compile(r"\([^)]*\)|[A-Z]{1,2}|\d")


def ancestors(code):
    code = code.strip()
    parts = code.split(":")
    out = {code}
    if all(PART.fullmatch(p) for p in parts):
        for p in parts:
            cur = ""
            for t in TOKEN.findall(p):
                cur += t
                out.add(cur)
    return out


def hier_f1(gt, pred):
    if not pred or not gt:
        return 0.0
    G, P = set().union(*map(ancestors, gt)), set().union(*map(ancestors, pred))
    i = len(G & P)
    return 0.0 if i == 0 else 2 * i / (len(G) + len(P))


def most_specific(codes):
    codes = list(dict.fromkeys(codes))
    implied = set()
    for c in codes:
        implied |= ancestors(c) - {c}
    return [c for c in codes if c not in implied]


ck = torch.load(T0 / "head.pt", map_location=dev, weights_only=False)
assert ck["feature_config"] == FEATURE_CONFIG
vocab, t0 = ck["vocab"], float(ck["threshold"])
head = torch.nn.Sequential(torch.nn.Linear(4096, 2048), torch.nn.GELU(), torch.nn.Dropout(0.2),
                           torch.nn.Linear(2048, len(vocab))).to(dev).eval()
head.load_state_dict(ck["state"])


@torch.no_grad()
def predict(X):
    P = torch.cat([torch.sigmoid(head(torch.from_numpy(X[i:i + 4096].astype(np.float32)).to(dev)))
                   for i in range(0, len(X), 4096)]).cpu().numpy()
    return [most_specific([vocab[j] for j in np.nonzero(row >= t0)[0]]) for row in P]


control = {"technical_only": bool(SMOKE)}
if not SMOKE:
    xt, yt = ICAI["test-00000-of-00001"]
    new, old = predict(xt), json.load(open(T0 / "predictions.json"))["T_head"]
    f_new, f_old = np.mean([hier_f1(g, p) for g, p in zip(yt, new)]), np.mean([hier_f1(g, p) for g, p in zip(yt, old)])
    control["icai788"] = {"hier_f1_new": f_new, "hier_f1_published": f_old,
                          "identical_predictions": int(sum(sorted(a) == sorted(b) for a, b in zip(new, old))), "images": len(yt)}
    ref = np.load(EXT / "gel2" / "candidats_feats.npz")
    assert list(ref["files"]) == [r["filename"] for r in rows]
    d = np.abs(ref["x"].astype(np.float32) - EX.astype(np.float32))
    cos = (ref["x"].astype(np.float32) * EX.astype(np.float32)).sum(1)
    control["emblematica_vectors"] = {"max_abs_diff": float(d.max()), "min_cosine": float(cos.min())}
    test = json.load(open(EXT / "gel2" / "test.json"))
    idx = {r["filename"]: i for i, r in enumerate(rows)}
    new_e = predict(EX[[idx[t["filename"]] for t in test]])
    old_e = json.load(open(EXT / "gel2" / "predictions.json"))["T_head_test"]
    control["emblematica_test"] = {"identical_predictions": int(sum(sorted(a) == sorted(b) for a, b in zip(new_e, old_e))),
                                   "images": len(test)}
    # Rule fixed before the run: the new vectors stand in for the lost ones only if T0's hierarchical F1 on ICAI moves by at
    # most 0.001 and at least 98 % of its predictions are identical on both benches; otherwise stop and report.
    ok = (abs(f_new - f_old) <= 0.001 and control["icai788"]["identical_predictions"] >= 0.98 * len(yt)
          and control["emblematica_test"]["identical_predictions"] >= 0.98 * len(test))
    control["passed"] = bool(ok)
json.dump(control, open(OUT / "controle.json", "w"), indent=1)
progress(f"done, control {control.get('passed')}")
