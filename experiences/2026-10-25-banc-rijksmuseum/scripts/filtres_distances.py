#!/usr/bin/env python3
"""Rijksmuseum bench, chronology step 2 (PREINSCRIPTION.md, amendment 1): images, fingerprints, distances. Remote only (Kaggle GPU).

Usage: filtres_distances.py OUT FEATS ELIG
FEATS: the `full/` folder of kernel caypollard-encode-cradio version 3 (feats/<shard>.npz + .json, grid/<shard>.json sidecars):
the C-RADIO vectors of the 87,004 brillfull images. ELIG: eligibles.jsonl (liste_eligibles.py; no codes).
ENV RIJKS_SMOKE=N keeps the first N eligible objects and the first N rows of each reference shard for the dHash (dry run: technical
only, distances not usable); RIJKS_SMOKE=0 is the full run. Nothing here looks at a code, a prediction or an image: counts only.

Order:
(1) preflight before any download: script inputs, every reference vector shard checked against its sidecar (sha256 of the npz,
    shape (n, 4096), float16, finite, md5 count), 87,004 rows in total (full run);
(2) reference dHash: each brillfull parquet shard of the pinned revision, in the encoder's shard order; the md5 of each image must
    equal the md5 stored with its vector (same identity, same order); 256-bit difference hash, the function of
    build_external_iconclass_bench.py (grey, 17 x 16 bilinear, horizontal gradients, packbits);
(3) images of the eligible objects: IIIF `full/!800,800/0/default.jpg`, one request per second at most (monotonic clock), User-Agent
    "caypollard/0.1 (research prototype)", 5 attempts with Retry-After on 429/5xx; the body must decode as an image. Failure after
    the attempts, undecodable body, or bytes whose sha256 differs on resumption: object excluded, counted, never replaced
    (PREINSCRIPTION.md). Kept: bytes, sha256, width, height;
(4) encoder control: the first 64 rows of the reference test shard re-encoded with the head's recipe; minimum cosine with the stored
    vectors >= 0.999, otherwise stop (environment drift);
(5) C-RADIO vector (head recipe) and 8 x 8 grid (amendment 2 recipe) of each kept image, batches of 32;
(6) distances, on GPU: for each candidate its nearest reference image by dHash (minimum bits; ties: smallest reference index in the
    encoder's shard order) and by cosine (maximum; same tie rule); internal pairs between candidates (i < j) with dHash < 64 bits or
    cosine >= 0.92 (the wide fallback values that define internal copies once for all).
Outputs, each set written atomically (temporary file, then replace): ref_dhash.npz (bits, decodable flag, md5, global reference index of each row), images/<k>.jpg +
images.jsonl (pid, k, sha256, width, height, or the failure), rijks_vec.npz (x float16, pid, img_sha), rijks_grid.npy (float16, n x 64 x
1024) + rijks.json, voisins.jsonl (pid, dhash_min_bits, dhash_ref, cos_max, cos_ref), internes.jsonl (pid_a, pid_b, dhash_bits,
cosine), resume.json (counts and histograms only), run.json, budget.json, progress.log.
"""

import hashlib
import importlib.metadata as md
import io
import json
import os
import resource
import shutil
import sys
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path

import numpy as np
import torch
from PIL import Image

OUT, FEATS, ELIG = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
(OUT / "images").mkdir(parents=True, exist_ok=True)
SMOKE = int(os.environ.get("RIJKS_SMOKE", "-1"))
assert SMOKE >= 0, "RIJKS_SMOKE must be set explicitly (0 = full run)"
CACHE = Path(os.environ.get("RIJKS_HF_CACHE", "/tmp/rijks_hf"))  # owned by this run only; parquet blobs are deleted from here
REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
SHARDS = ["data/test-00000-of-00001.parquet"] + [f"data/train-{i:05d}-of-00011.parquet" for i in range(11)]
ENC_REPO, ENC_REV = "nvidia/C-RADIOv3-L", "9d0413465e8a91e67bbf2c1ad342815478d1b906"
FEATURE_CONFIG = f"{ENC_REPO}@{ENC_REV}|square-grey128|448|bicubic|autocast-fp16|summary+meanspatial|l2-each-then-l2"
GRID_CONFIG = f"{ENC_REPO}@{ENC_REV}|square-grey128|448|bicubic|autocast-fp16|spatial28x28|adaptive-avg-8x8|fp16"
N_REF = 87004
UA = "caypollard/0.1 (research prototype)"
SIZE = "!800,800"
INTERNAL_DHASH, INTERNAL_COS = 64, 0.92  # internal copies: dHash < 64 bits or cosine >= 0.92
dev = "cuda" if torch.cuda.is_available() else "cpu"
started = time.time()
_last = [0.0]


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


def write_json(obj, path: Path, **kw):
    tmp = path.with_name(path.name + ".tmp")
    json.dump(obj, open(tmp, "w"), **kw)
    os.replace(tmp, path)


def write_jsonl(rows, path: Path):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def dhash_bytes(b: bytes):
    """build_external_iconclass_bench.dhash on in-memory bytes; None if the image does not decode."""
    try:
        g = np.asarray(Image.open(io.BytesIO(b)).convert("L").resize((17, 16), Image.BILINEAR), dtype=np.int16)
    except Exception:
        return None
    return np.packbits((g[:, 1:] > g[:, :-1]).flatten())


def finite_by_chunks(a, step=2048):
    return all(np.isfinite(a[i:i + step]).all() for i in range(0, len(a), step))


# ---- (1) Preflight ----
elig = [json.loads(line) for line in open(ELIG)]
assert elig and len({r["pid"] for r in elig}) == len(elig), "eligible list: empty or duplicated PIDs"
assert [r["pid"] for r in elig] == sorted(r["pid"] for r in elig), "eligible list not in PID order"
assert all(r["iiif"].startswith("https://iiif.micr.io/") and r["iiif"].endswith(f"/full/{SIZE}/0/default.jpg") for r in elig)
ref_x, ref_md5, ref_shard = [], [], []
for shard in SHARDS:
    tag = Path(shard).stem
    npz, man, side = FEATS / "feats" / f"{tag}.npz", FEATS / "feats" / f"{tag}.json", FEATS / "grid" / f"{tag}.json"
    s = json.load(open(side))
    z = np.load(npz)
    n = s["rows"]
    assert s["vec_sha256"] == sha(npz) and json.load(open(man)) == s["manifest"], f"{tag}: vector shard differs from its sidecar"
    assert s["manifest"]["feature_config"] == FEATURE_CONFIG and s["manifest"]["dataset"] == [REPO, REV], tag
    assert z["x"].shape == (n, 4096) and z["x"].dtype == np.float16 and finite_by_chunks(z["x"]) and len(z["md5"]) == n, tag
    ref_x.append(z["x"])
    ref_md5 += list(z["md5"])
    ref_shard += [tag] * n
REF_X = np.concatenate(ref_x)
del ref_x
assert len(REF_X) == N_REF == len(ref_md5), f"{len(REF_X)} reference rows, expected {N_REF}"
if SMOKE:
    elig = elig[:SMOKE]
key = {"script_sha256": sha(__file__), "elig_sha256": sha(ELIG), "smoke": SMOKE, "dataset": [REPO, REV],
       "feature_config": FEATURE_CONFIG, "grid_config": GRID_CONFIG, "size": SIZE,
       "internal": {"dhash_lt": INTERNAL_DHASH, "cos_ge": INTERNAL_COS},
       "feats_sidecars_sha256": {Path(sh).stem: sha(FEATS / "grid" / f"{Path(sh).stem}.json") for sh in SHARDS},
       "versions": {p: version(p) for p in ("torch", "torchvision", "transformers", "timm", "open-clip-torch", "einops", "numpy",
                                             "pillow", "pyarrow", "huggingface-hub")},
       "gpu": torch.cuda.get_device_name() if dev == "cuda" else None}
if (OUT / "run.json").exists():
    assert json.load(open(OUT / "run.json")) == key, "resumed run differs from the first one (run.json): start in a new folder"
else:
    write_json(key, OUT / "run.json", indent=1)
disk_before = {str(p): shutil.disk_usage(p).free for p in (OUT, Path("/tmp"))}
progress(f"preflight ok: {len(elig)} eligible objects, {N_REF} reference vectors")

# ---- (2) Reference dHash, identity checked against the stored md5 ----
ref_path = OUT / "ref_dhash.npz"
if ref_path.exists():
    z = np.load(ref_path)
    assert list(z["md5"]) == [ref_md5[i] for i in z["idx"]] and z["bits"].shape[1] == 32, "ref_dhash.npz differs"
    REF_BITS, REF_OK, REF_IDX = z["bits"], z["ok"], z["idx"]
    progress("reference dHash: reused, checked")
else:
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    os.environ.setdefault("HF_HOME", str(CACHE))
    bits, ok, md5s, idx, pos = [], [], [], [], 0
    for shard in SHARDS:
        tag = Path(shard).stem
        path = hf_hub_download(REPO, shard, repo_type="dataset", revision=REV, cache_dir=CACHE / "hub")
        imgs = pq.read_table(path, columns=["image"]).column("image").to_pylist()
        n_shard = ref_shard.count(tag)
        assert len(imgs) == n_shard, f"{tag}: {len(imgs)} images against {n_shard} vectors"
        for k, x in enumerate(imgs[:SMOKE] if SMOKE else imgs):
            m = hashlib.md5(x["bytes"]).hexdigest()
            assert m == ref_md5[pos + k], f"{tag} row {k}: image md5 differs from the vector's md5"
            h = dhash_bytes(x["bytes"])
            ok.append(h is not None)
            bits.append(h if h is not None else np.zeros(32, np.uint8))
            md5s.append(m)
            idx.append(pos + k)
        pos += n_shard
        del imgs
        blob = Path(os.path.realpath(path))
        assert CACHE.resolve() in blob.parents, blob  # never delete outside this run's own cache
        blob.unlink()
        Path(path).unlink(missing_ok=True)
        progress(f"reference dHash {tag}: done")
    REF_BITS, REF_OK, REF_IDX = np.stack(bits), np.array(ok), np.array(idx)
    tmp = OUT / "ref_dhash.tmp.npz"
    np.savez(tmp, bits=REF_BITS, ok=REF_OK, md5=np.array(md5s), idx=REF_IDX)
    os.replace(tmp, ref_path)
    progress(f"reference dHash: {len(md5s)} rows, {int((~REF_OK).sum())} undecodable")
if not SMOKE:
    assert len(REF_BITS) == N_REF and (REF_IDX == np.arange(N_REF)).all()


# ---- (3) Images of the eligible objects ----
def retry_after(e):
    v = e.headers.get("Retry-After") if e.headers else None
    if not v:
        return 0.0
    try:
        return float(v)
    except ValueError:
        try:
            return max(0.0, parsedate_to_datetime(v).timestamp() - time.time())
        except (TypeError, ValueError):
            return 0.0


def fetch(url):
    last = "no attempt"
    for attempt in range(5):
        wait = 1.0 - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read(), None
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(max(retry_after(e), 10 * (attempt + 1)))
                continue
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = type(e).__name__
            time.sleep(10 * (attempt + 1))
    return None, last


done = {}
if (OUT / "images.jsonl").exists():
    for line in open(OUT / "images.jsonl"):
        r = json.loads(line)
        done[r["pid"]] = r
log_rows = []
for k, r in enumerate(elig):
    path = OUT / "images" / f"{k}.jpg"
    prev = done.get(r["pid"])
    if prev and prev.get("sha256") and path.exists():
        if sha(path) != prev["sha256"]:
            row = {"pid": r["pid"], "k": k, "failure": "sha256 differs on resumption"}
            path.unlink()
        else:
            row = prev
    elif prev and prev.get("failure"):
        row = prev  # a failure is final: never retried into the bench, never replaced
    else:
        body, err = fetch(r["iiif"])
        if body is None:
            row = {"pid": r["pid"], "k": k, "failure": err}
        else:
            try:
                im = Image.open(io.BytesIO(body))
                im.load()
                w, h = im.size
            except Exception as e:
                row = {"pid": r["pid"], "k": k, "failure": f"undecodable: {type(e).__name__}"}
            else:
                tmp = path.with_name(path.name + ".tmp")
                tmp.write_bytes(body)
                os.replace(tmp, path)
                row = {"pid": r["pid"], "k": k, "sha256": hashlib.sha256(body).hexdigest(), "width": w, "height": h,
                       "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    log_rows.append(row)
    if (k + 1) % 200 == 0:
        write_jsonl(log_rows + [done[p["pid"]] for p in elig[k + 1:] if p["pid"] in done], OUT / "images.jsonl")
        progress(f"images {k + 1}/{len(elig)}")
write_jsonl(log_rows, OUT / "images.jsonl")
kept = [row for row in log_rows if row.get("sha256")]
progress(f"images: {len(kept)} kept, {len(log_rows) - len(kept)} excluded")

# ---- Encoder: the head's recipe, unchanged (encode_cradio.py) ----
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
    px = processor(images=[square(i) for i in images], return_tensors="pt", do_resize=False).pixel_values.to(dev)
    with torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
        summary, spatial = model(px)
    b = len(images)
    assert spatial.shape == (b, 784, 1024), spatial.shape
    v = torch.cat([torch.nn.functional.normalize(summary.float(), dim=-1),
                   torch.nn.functional.normalize(spatial.float().mean(1), dim=-1)], 1)
    vec = torch.nn.functional.normalize(v, dim=-1).cpu().numpy().astype(np.float16)
    g = spatial.float().reshape(b, 28, 28, 1024).permute(0, 3, 1, 2)
    g = torch.nn.functional.adaptive_avg_pool2d(g, 8).permute(0, 2, 3, 1).reshape(b, 64, 1024)
    return vec, g.cpu().numpy().astype(np.float16)


# ---- (4) Encoder control on the first 64 reference test images ----
import pyarrow.parquet as pq  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402

path = hf_hub_download(REPO, SHARDS[0], repo_type="dataset", revision=REV, cache_dir=CACHE / "hub")
ctrl_imgs = pq.read_table(path, columns=["image"]).column("image").to_pylist()[:64]
assert [hashlib.md5(x["bytes"]).hexdigest() for x in ctrl_imgs] == ref_md5[:64]
v_new = np.concatenate([encode([Image.open(io.BytesIO(x["bytes"])) for x in ctrl_imgs[i:i + 32]])[0] for i in (0, 32)])
a, b = v_new.astype(np.float32), REF_X[:64].astype(np.float32)
cos = (a * b).sum(1) / np.linalg.norm(a, axis=1) / np.linalg.norm(b, axis=1)
control = {"rows": 64, "min_cosine": float(cos.min()), "max_abs_diff": float(np.abs(a - b).max()), "passed": bool(cos.min() >= 0.999)}
del ctrl_imgs
blob = Path(os.path.realpath(path))
assert CACHE.resolve() in blob.parents, blob
blob.unlink()
Path(path).unlink(missing_ok=True)
write_json(control, OUT / "controle_encodeur.json", indent=1)
progress(f"encoder control: {control}")
if not control["passed"]:
    sys.exit(3)

# ---- (5) Vectors and grids of the kept images ----
rj = OUT / "rijks.json"
if rj.exists():
    s = json.load(open(rj))
    z = np.load(OUT / "rijks_vec.npz")
    assert (s["vec_sha256"] == sha(OUT / "rijks_vec.npz") and s["grid_sha256"] == sha(OUT / "rijks_grid.npy")
            and list(z["pid"]) == [r["pid"] for r in kept] and list(z["img_sha"]) == [r["sha256"] for r in kept]), "rijks set"
    X = z["x"]
    progress("rijks vectors: reused, checked")
else:
    xs, gs = [], []
    for i in range(0, len(kept), 32):
        v, g = encode([Image.open(OUT / "images" / f"{r['k']}.jpg") for r in kept[i:i + 32]])
        xs.append(v)
        gs.append(g)
    X, G = np.concatenate(xs), np.concatenate(gs)
    assert X.shape == (len(kept), 4096) and G.shape == (len(kept), 64, 1024) and np.isfinite(X).all() and finite_by_chunks(G)
    np.savez(OUT / "rijks_vec.tmp.npz", x=X, pid=np.array([r["pid"] for r in kept]), img_sha=np.array([r["sha256"] for r in kept]),
             config=np.array(FEATURE_CONFIG))
    np.save(OUT / "rijks_grid.tmp.npy", G)
    os.replace(OUT / "rijks_vec.tmp.npz", OUT / "rijks_vec.npz")
    os.replace(OUT / "rijks_grid.tmp.npy", OUT / "rijks_grid.npy")
    write_json({"rows": len(kept), "feature_config": FEATURE_CONFIG, "grid_config": GRID_CONFIG,
                "vec_sha256": sha(OUT / "rijks_vec.npz"), "grid_sha256": sha(OUT / "rijks_grid.npy")}, rj)
    del G
    progress(f"rijks vectors: {len(kept)} rows")
del model
torch.cuda.empty_cache()

# ---- (6) Distances on GPU ----
cand_bits = []
for r in kept:
    h = dhash_bytes((OUT / "images" / f"{r['k']}.jpg").read_bytes())
    assert h is not None, r["pid"]  # decoded at download
    cand_bits.append(h)
CB = torch.from_numpy(np.unpackbits(np.stack(cand_bits), axis=1).astype(np.float16)).to(dev)  # (n, 256)
RB = torch.from_numpy(np.unpackbits(REF_BITS, axis=1).astype(np.float16)).to(dev)  # (N, 256)
ref_valid = torch.from_numpy(REF_OK).to(dev)
CX = torch.from_numpy(np.asarray(X, np.float32)).to(dev)
CX = CX / CX.norm(dim=1, keepdim=True)
RX = torch.from_numpy(np.asarray(REF_X[REF_IDX], np.float32)).to(dev)  # same rows as the reference dHash (all of them in full)
RX = RX / RX.norm(dim=1, keepdim=True)


def hamming(a, b):
    """Bits differing between rows of a (m, 256) and b (n, 256), exact in float32 (integers <= 256)."""
    a, b = a.float(), b.float()
    return a.sum(1, keepdim=True) + b.sum(1)[None, :] - 2 * a @ b.T


rows = []
for i in range(0, len(kept), 256):
    d = hamming(CB[i:i + 256], RB)
    d[:, ~ref_valid] = 1e9  # an undecodable reference image is never a neighbour
    dmin, darg = d.min(1)  # first index on ties (documented by torch for min/max along a dim)
    c = CX[i:i + 256] @ RX.T
    cmax, carg = c.max(1)
    for j in range(len(dmin)):
        rows.append({"pid": kept[i + j]["pid"], "dhash_min_bits": int(dmin[j]), "dhash_ref": int(REF_IDX[int(darg[j])]),
                     "cos_max": float(cmax[j]), "cos_ref": int(REF_IDX[int(carg[j])])})
write_jsonl(rows, OUT / "voisins.jsonl")
pairs = []
for i in range(0, len(kept), 256):
    d = hamming(CB[i:i + 256], CB)
    c = CX[i:i + 256] @ CX.T
    hit = (d < INTERNAL_DHASH) | (c >= INTERNAL_COS)
    for a_, b_ in torch.nonzero(hit).tolist():
        if i + a_ < b_:
            pairs.append({"pid_a": kept[i + a_]["pid"], "pid_b": kept[b_]["pid"], "dhash_bits": int(d[a_, b_]),
                          "cosine": float(c[a_, b_])})
write_jsonl(pairs, OUT / "internes.jsonl")
dm = np.array([r["dhash_min_bits"] for r in rows])
cm = np.array([r["cos_max"] for r in rows])
resume = {"eligible": len(elig), "images_kept": len(kept), "images_excluded": len(log_rows) - len(kept),
          "reference_rows": int(len(REF_BITS)), "reference_undecodable": int((~REF_OK).sum()),
          "below_50_bits": int((dm < 50).sum()), "below_64_bits": int((dm < 64).sum()),
          "cos_ge_095": int((cm >= 0.95).sum()), "cos_ge_092": int((cm >= 0.92).sum()), "internal_pairs": len(pairs),
          "dhash_histogram": np.histogram(dm, bins=[0, 20, 40, 50, 64, 80, 100, 257])[0].tolist(),
          "cos_histogram": np.histogram(cm, bins=[-1, 0.5, 0.7, 0.85, 0.92, 0.95, 1.01])[0].tolist(), "smoke": SMOKE}
write_json(resume, OUT / "resume.json", indent=1)
budget = {"ram_peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
          "vram_peak_allocated_gb": torch.cuda.max_memory_allocated() / 1e9 if dev == "cuda" else None,
          "disk_free_before_gb": {k: v / 1e9 for k, v in disk_before.items()},
          "disk_free_after_gb": {str(p): shutil.disk_usage(p).free / 1e9 for p in (OUT, Path("/tmp"))},
          "outputs_gb": sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e9, "wall_seconds": time.time() - started}
write_json(budget, OUT / "budget.json", indent=1)
progress(f"done: {resume}")
