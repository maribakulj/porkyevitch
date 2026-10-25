#!/usr/bin/env python3
"""One C-RADIOv3-L pass over ICAI and the Emblematica candidates: the head's vector and an 8 x 8 grid of spatial tokens (PREINSCRIPTION.md).

Usage: encode_cradio.py OUT EXT T0
EXT holds candidates.jsonl, near256.json, images/ and gel2/ (test.json, predictions.json, candidats_feats.npz) of the external bench;
T0 holds head.pt, predictions.json and resultats.json of the published C-RADIO head (T0). ENC_SMOKE=N keeps N rows per shard and N
Emblematica rows (dry run: technical only, the T0 control is skipped); ENC_SMOKE=0 is the full run.

Order: (1) preflight on every input, before any download or model (expected sha256 below, counts, image fingerprints);
(2) ICAI shards, test then train, in the head script's order and batches of 32; (3) the 7,320 Emblematica candidates, in the external
script's order and batches; (4) the preregistered T0 control (full run only), which exits non-zero when it fails.
Outputs, each set published atomically (temporary files, then its manifest written last):
  feats/<shard>.npz + .json   vector (summary + mean spatial, the head's exact recipe) and manifest, format of remote_iconclass_head.py
  grid/<shard>.npy + .json    float16 (rows, 64, 1024): spatial tokens 28 x 28 -> adaptive average pooling 8 x 8; sidecar with labels,
                              md5 hash, sha256 of grid and vector, configs, run key
  emb_vec.npz, emb_grid.npy, emb.json   the same for Emblematica (emb.json last)
  run.json (first run kept; a resumed run must have the same key), runs.jsonl (one line per run), budget.json, controle.json,
  t0_new_predictions.json, progress.log
Resumption reuses a set only if its manifest, sha256, shapes, dtypes and finiteness all check out, without downloading its images.
"""

import hashlib
import importlib.metadata as md
import io
import json
import os
import re
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

OUT, EXT, T0 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
for d in ("feats", "grid"):
    (OUT / d).mkdir(parents=True, exist_ok=True)
SMOKE = int(os.environ.get("ENC_SMOKE", "-1"))
assert SMOKE >= 0, "ENC_SMOKE must be set explicitly (0 = full run)"
CACHE = Path(os.environ.get("ENC_HF_CACHE", "/tmp/enc_hf"))  # owned by this run only; parquet blobs are deleted from here
REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
SHARDS = ["data/test-00000-of-00001.parquet"] + [f"data/train-{i:05d}-of-00011.parquet" for i in range(11)]
ENC_REPO, ENC_REV = "nvidia/C-RADIOv3-L", "9d0413465e8a91e67bbf2c1ad342815478d1b906"
FEATURE_CONFIG = f"{ENC_REPO}@{ENC_REV}|square-grey128|448|bicubic|autocast-fp16|summary+meanspatial|l2-each-then-l2"
GRID_CONFIG = f"{ENC_REPO}@{ENC_REV}|square-grey128|448|bicubic|autocast-fp16|spatial28x28|adaptive-avg-8x8|fp16"
# Inputs, from caypollard c0bfe6c (T0) and the frozen gel2 (frozen.json lists the last three of EXT).
EXPECTED = {
    T0 / "head.pt": "2b403a912383853d52ed771ef5843a42a80160e39b180ccf98e8bf3b1fc98242",
    T0 / "predictions.json": "84283a881ed15747bd8a023130f638d0c65d0a0535adb239d65e4c818c145fd7",
    T0 / "resultats.json": "d207d0c4ade1d1ba3171cbd0ffe06433637823021ad248b273656159ce63fa33",
    EXT / "gel2" / "candidats_feats.npz": "347babaa95f7ca11615bda760affa26d024c1e2871bb6beea2d411db5b639a9a",
    EXT / "gel2" / "predictions.json": "543a556f7a0dc78446ea27399dc9ceb06c64814df40ef083c59641dff6bb5e85",
    EXT / "gel2" / "test.json": "44cc03f936a58a82ee4ac9f420a56098a89bc5bea831c16372bc0c2b74d01acb",
    EXT / "candidates.jsonl": "bfe9e9703d8ce308fa255f80ef1297a15984d0de5d1df05fd1a64b8409ac3e3a",
    EXT / "near256.json": "a23736e08ab18291e115b8dd303b12264ed686ecc14563dabd71a6a57ea5a5ef",
}
dev = "cuda" if torch.cuda.is_available() else "cpu"
started = time.time()
encode_seconds, encoded_images = 0.0, 0


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


def version(pkg):
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return None


def publish(tmp: Path, final: Path):
    os.replace(tmp, final)


# ---- (1) Preflight, before any download or model ----
for p, want in EXPECTED.items():
    assert p.exists(), f"missing input {p}"
    assert sha(p) == want, f"{p}: sha256 differs from the expected input"
ck = torch.load(T0 / "head.pt", map_location="cpu", weights_only=False)
assert ck["feature_config"] == FEATURE_CONFIG and ck["state"]["0.weight"].shape == (2048, 4096), "T0 head"
assert len(ck["vocab"]) == 7907 and float(ck["threshold"]) == 0.6 and ck["epoch"] == 14, "T0 head"
t0_res = json.load(open(T0 / "resultats.json"))
assert t0_res["head"] == {"vocab": 7907, "best_epoch": 14, "threshold": 0.6} and t0_res["chosen_on_validation"] == "T"
t0_icai = json.load(open(T0 / "predictions.json"))["T_head"]
assert len(t0_icai) == 788
near = json.load(open(EXT / "near256.json"))
bad_books = {b for _, d, _, b in near if 0 <= d < 50}
rows = [json.loads(line) for line in open(EXT / "candidates.jsonl")]
rows = [r for r in rows if r["book_id"] is not None and r["book_id"] not in bad_books]
names = [r["filename"] for r in rows]
assert len(rows) == 7320 and len(set(names)) == 7320, len(rows)
ref = np.load(EXT / "gel2" / "candidats_feats.npz")
assert list(ref["files"]) == names and str(ref["config"]) == FEATURE_CONFIG and ref["x"].shape == (7320, 4096)
img_sha = [sha(EXT / "images" / n) for n in names]
assert list(ref["img_sha"]) == img_sha, "Emblematica images differ from those encoded for gel2"
test = json.load(open(EXT / "gel2" / "test.json"))
gel_pred = json.load(open(EXT / "gel2" / "predictions.json"))["T_head_test"]
assert len(test) == len(gel_pred) == 800 and len({t["filename"] for t in test}) == 800 and {t["filename"] for t in test} <= set(names)
if SMOKE:
    rows, names, img_sha = rows[:SMOKE], names[:SMOKE], img_sha[:SMOKE]

key = {"script_sha256": sha(__file__), "inputs": {f"{p.parent.name}/{p.name}": w for p, w in EXPECTED.items()},
       "dataset": [REPO, REV], "feature_config": FEATURE_CONFIG, "grid_config": GRID_CONFIG, "smoke": SMOKE,
       "versions": {p: version(p) for p in ("torch", "torchvision", "transformers", "timm", "open-clip-torch", "einops", "numpy",
                                             "pillow", "pyarrow", "huggingface-hub")},
       "gpu": torch.cuda.get_device_name() if dev == "cuda" else None}
if (OUT / "run.json").exists():
    assert json.load(open(OUT / "run.json")) == key, "resumed run differs from the first one (run.json): start in a new folder"
else:
    json.dump(key, open(OUT / "run.json", "w"), indent=1)
with open(OUT / "runs.jsonl", "a") as f:
    f.write(json.dumps({"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "pid": os.getpid()}) + "\n")
disk_before = {str(p): shutil.disk_usage(p).free for p in (OUT, Path("/tmp"))}
progress("preflight ok")

# ---- Encoder: the head's recipe, unchanged (remote_iconclass_head.py), plus the grid from the same forward pass ----
os.environ.setdefault("HF_HOME", str(CACHE))
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
    global encode_seconds, encoded_images
    t = time.time()
    px = processor(images=[square(i) for i in images], return_tensors="pt", do_resize=False).pixel_values.to(dev)
    with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):  # RADIO normalises its input itself
        summary, spatial = model(px)
    b = len(images)
    assert spatial.shape == (b, 784, 1024), spatial.shape  # patch tokens only (RADIO strips its prefix tokens itself)
    v = torch.cat([torch.nn.functional.normalize(summary.float(), dim=-1),
                   torch.nn.functional.normalize(spatial.float().mean(1), dim=-1)], 1)
    vec = torch.nn.functional.normalize(v, dim=-1).cpu().numpy().astype(np.float16)
    assert vec.shape == (b, 4096)
    g = spatial.float().reshape(b, 28, 28, 1024).permute(0, 3, 1, 2)
    g = torch.nn.functional.adaptive_avg_pool2d(g, 8).permute(0, 2, 3, 1).reshape(b, 64, 1024)
    if dev == "cuda":
        torch.cuda.synchronize()
    encode_seconds += time.time() - t
    encoded_images += b
    return vec, g.cpu().numpy().astype(np.float16)


def finite_by_chunks(a, step=2048):
    return all(np.isfinite(a[i:i + step]).all() for i in range(0, len(a), step))


def grid_ok(path, n):
    """The .npy header and contents: (n, 64, 1024) float16, finite; read memory-mapped."""
    a = np.load(path, mmap_mode="r")
    return a.shape == (n, 64, 1024) and a.dtype == np.float16 and finite_by_chunks(a)


# ---- (2) ICAI shards ----
def labels_hash(labels):
    return hashlib.sha256(json.dumps(labels).encode()).hexdigest()


ICAI = {}
for shard in SHARDS:
    tag = Path(shard).stem
    npz, man, grid, side = (OUT / "feats" / f"{tag}.npz", OUT / "feats" / f"{tag}.json", OUT / "grid" / f"{tag}.npy",
                            OUT / "grid" / f"{tag}.json")
    if side.exists() and npz.exists() and man.exists() and grid.exists():
        s = json.load(open(side))
        z = np.load(npz)
        n = s["rows"]
        if (s["run_key_sha256"] == hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
                and s["grid_config"] == GRID_CONFIG and s["grid_sha256"] == sha(grid) and s["vec_sha256"] == sha(npz)
                and json.load(open(man)) == s["manifest"] and z["x"].shape == (n, 4096) and z["x"].dtype == np.float16
                and len(z["md5"]) == n and s["md5_sha256"] == labels_hash(list(z["md5"]))
                and labels_hash(s["labels"]) == s["manifest"]["labels_sha256"] and finite_by_chunks(z["x"]) and grid_ok(grid, n)):
            ICAI[tag] = (z["x"], s["labels"])
            progress(f"{tag}: reused, checked")
            continue
        raise SystemExit(f"{tag}: existing outputs fail their checks; start in a new folder")
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(REPO, shard, repo_type="dataset", revision=REV, cache_dir=CACHE / "hub")
    table = pq.read_table(path)
    n = table.num_rows if not SMOKE else min(SMOKE, table.num_rows)
    labels = table.column("label").to_pylist()[:n]
    manifest = {"dataset": [REPO, REV], "shard": shard, "rows": n, "smoke": SMOKE, "feature_config": FEATURE_CONFIG,
                "labels_sha256": labels_hash(labels)}
    imgs = table.column("image").to_pylist()[:n]
    del table
    xs, gs, md5 = [], [], []
    for i in range(0, n, 32):
        chunk = imgs[i:i + 32]
        md5 += [hashlib.md5(x["bytes"]).hexdigest() for x in chunk]
        v, g = encode([Image.open(io.BytesIO(x["bytes"])) for x in chunk])
        xs.append(v)
        gs.append(g)
    del imgs
    x, gr = np.concatenate(xs), np.concatenate(gs)
    del xs, gs
    assert x.shape == (n, 4096) and gr.shape == (n, 64, 1024) and np.isfinite(x).all() and finite_by_chunks(gr)
    np.save(OUT / "grid" / f"{tag}.tmp.npy", gr)
    np.savez(OUT / "feats" / f"{tag}.tmp.npz", x=x, md5=np.array(md5))
    json.dump(manifest, open(OUT / "feats" / f"{tag}.tmp.json", "w"))
    publish(OUT / "grid" / f"{tag}.tmp.npy", grid)
    publish(OUT / "feats" / f"{tag}.tmp.npz", npz)
    publish(OUT / "feats" / f"{tag}.tmp.json", man)
    json.dump({"rows": n, "manifest": manifest, "labels": labels, "md5_sha256": labels_hash(md5), "grid_config": GRID_CONFIG,
               "grid_sha256": sha(grid), "vec_sha256": sha(npz),
               "run_key_sha256": hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()},
              open(OUT / "grid" / f"{tag}.tmp.json", "w"))
    publish(OUT / "grid" / f"{tag}.tmp.json", side)  # written last: the set is complete
    blob = Path(os.path.realpath(path))
    assert CACHE.resolve() in blob.parents, blob  # never delete outside this run's own cache
    blob.unlink()
    Path(path).unlink(missing_ok=True)
    ICAI[tag] = (x, labels)
    del gr
    progress(f"{tag}: {n} rows")

# ---- (3) Emblematica candidates after filter 1 ----
emb_side = OUT / "emb.json"
run_key_sha = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
if emb_side.exists():
    s = json.load(open(emb_side))
    z = np.load(OUT / "emb_vec.npz")
    ok = (s["run_key_sha256"] == run_key_sha and s["vec_sha256"] == sha(OUT / "emb_vec.npz")
          and s["grid_sha256"] == sha(OUT / "emb_grid.npy") and list(z["files"]) == names and list(z["img_sha"]) == img_sha
          and z["x"].shape == (len(names), 4096) and finite_by_chunks(z["x"]) and grid_ok(OUT / "emb_grid.npy", len(names)))
    if not ok:
        raise SystemExit("Emblematica outputs fail their checks; start in a new folder")
    EX = z["x"]
    progress("emblematica: reused, checked")
else:
    xs, gs = [], []
    for i in range(0, len(rows), 32):
        v, g = encode([Image.open(EXT / "images" / n) for n in names[i:i + 32]])
        xs.append(v)
        gs.append(g)
    EX, EG = np.concatenate(xs), np.concatenate(gs)
    assert EX.shape == (len(names), 4096) and EG.shape == (len(names), 64, 1024) and np.isfinite(EX).all() and finite_by_chunks(EG)
    np.savez(OUT / "emb_vec.tmp.npz", x=EX, files=np.array(names), img_sha=np.array(img_sha), config=np.array(FEATURE_CONFIG))
    np.save(OUT / "emb_grid.tmp.npy", EG)
    publish(OUT / "emb_vec.tmp.npz", OUT / "emb_vec.npz")
    publish(OUT / "emb_grid.tmp.npy", OUT / "emb_grid.npy")
    json.dump({"rows": len(names), "grid_config": GRID_CONFIG, "vec_sha256": sha(OUT / "emb_vec.npz"),
               "grid_sha256": sha(OUT / "emb_grid.npy"), "run_key_sha256": run_key_sha}, open(OUT / "emb.tmp.json", "w"))
    publish(OUT / "emb.tmp.json", emb_side)
    del EG
    progress(f"emblematica: {len(names)} rows")
del model
budget = {"ram_peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,  # Linux: kilobytes
          "vram_peak_allocated_gb": torch.cuda.max_memory_allocated() / 1e9 if dev == "cuda" else None,
          "vram_peak_reserved_gb": torch.cuda.max_memory_reserved() / 1e9 if dev == "cuda" else None,
          "disk_free_before_gb": {k: v / 1e9 for k, v in disk_before.items()},
          "disk_free_after_gb": {str(p): shutil.disk_usage(p).free / 1e9 for p in (OUT, Path("/tmp"))},
          "outputs_gb": sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e9,
          "images_encoded_this_run": encoded_images, "encode_seconds": encode_seconds,
          "images_per_second": encoded_images / encode_seconds if encode_seconds else None,
          "wall_seconds": time.time() - started}
json.dump(budget, open(OUT / "budget.json", "w"), indent=1)
torch.cuda.empty_cache()

# ---- (4) Preregistered control: T0 reproduced from the new vectors (full run only) ----
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


vocab, t0 = ck["vocab"], float(ck["threshold"])
head = torch.nn.Sequential(torch.nn.Linear(4096, 2048), torch.nn.GELU(), torch.nn.Dropout(0.2),
                           torch.nn.Linear(2048, len(vocab))).to(dev).eval()
head.load_state_dict(ck["state"])


@torch.no_grad()
def predict(X):
    P = torch.cat([torch.sigmoid(head(torch.from_numpy(np.asarray(X[i:i + 4096], dtype=np.float32)).to(dev)))
                   for i in range(0, len(X), 4096)]).cpu().numpy()
    return [most_specific([vocab[j] for j in np.nonzero(row >= t0)[0]]) for row in P]


control = {"technical_only": bool(SMOKE)}
if not SMOKE:
    xt, yt = ICAI["test-00000-of-00001"]
    assert len(yt) == 788
    new = predict(xt)
    f_new = float(np.mean([hier_f1(g, p) for g, p in zip(yt, new, strict=True)]))
    f_old = float(np.mean([hier_f1(g, p) for g, p in zip(yt, t0_icai, strict=True)]))
    same_icai = int(sum(sorted(a) == sorted(b) for a, b in zip(new, t0_icai, strict=True)))
    idx = {n: i for i, n in enumerate(names)}
    new_e = predict(EX[[idx[t["filename"]] for t in test]])
    same_emb = int(sum(sorted(a) == sorted(b) for a, b in zip(new_e, gel_pred, strict=True)))
    a, b = ref["x"].astype(np.float32), np.asarray(EX, dtype=np.float32)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    b /= np.linalg.norm(b, axis=1, keepdims=True)
    control.update({
        "icai788_historical_measure": {"hier_f1_new": f_new, "hier_f1_published": f_old, "identical_predictions": same_icai,
                                       "images": 788},
        "emblematica_test": {"identical_predictions": same_emb, "images": 800},
        "diagnostic_emblematica_vectors": {"max_abs_diff": float(np.abs(ref["x"].astype(np.float32) - np.asarray(EX, np.float32)).max()),
                                           "min_cosine_fp32": float((a * b).sum(1).min())},
    })
    json.dump({"icai788": new, "emblematica_test": dict(zip([t["filename"] for t in test], new_e))},
              open(OUT / "t0_new_predictions.json", "w"))
    # Rule fixed before the run (reproduction tolerance, not identity): T0's hierarchical F1 on ICAI 788 (historical measure) moves
    # by at most 0.001, and at least 98 % of its predictions are identical on both benches (>= 773/788 and >= 784/800).
    control["passed"] = bool(abs(f_new - f_old) <= 0.001 and same_icai >= 0.98 * 788 and same_emb >= 0.98 * 800)
json.dump(control, open(OUT / "controle.json", "w"), indent=1)
progress(f"done, control {control.get('passed')}")
if not SMOKE and not control["passed"]:
    sys.exit(3)
