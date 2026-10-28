#!/usr/bin/env python3
"""E0 of the architecture series (PREINSCRIPTION.md): remote check of the encoder tensors, then T-seuil and T-long, chosen on the
ICAI validation only. No test measure is computed here (amendment 4: test aggregates stay closed until the seven arms are frozen).

Usage: e0_reference.py OUT ENC T0
ENC: the `full/` folder of kernel caypollard-encode-cradio version 3 (feats/<shard>.npz + .json, grid/<shard>.npy + .json).
T0: the folder holding head.pt of the published C-RADIO head (sha256 2b403a91...). ENV E0_SMOKE=N keeps N training epochs for T-long
and N rows of validation for the grid search (dry run: technical only); E0_SMOKE=0 is the full run.

(1) Tensors: for each of the 12 shards (test, then train 0-10), the vector npz and the grid npy against their sidecar: sha256 of both
    files, manifest equal to its sidecar copy, labels and md5 hashes, shapes (n, 4096) and (n, 64, 1024), float16, finite (grids read
    memory-mapped by chunks). 87,004 rows in total, 788 in test. Any failure stops the run (exit 3) before any training.
(2) The data of the head script (remote_iconclass_head.py of the published head, unchanged): train = the 11 train shards in order;
    validation = 5 % of the groups of byte-identical images (md5), default_rng(0).random(len(groups)) < 0.05 on the sorted md5;
    vocabulary = codes seen on >= 5 non-validation images, with their ancestors. Controls: the vocabulary equals T0's (7,907 codes, same
    order) and T0's weights at its threshold 0.60 give its published validation score 0.5517433451139009 under the historical measure
    (no projection), within 0.001 (the reproduction tolerance of the encoding control); otherwise stop (exit 3).
(3) Validation measure of the series: chapter 86 removed from truth and predictions (codes whose notation starts with "86"), an
    image whose projected truth is empty is left out, mean hierarchical F1 over the rest. Extended grid: 0.05 to 0.95 by 0.05.
    T0 = T0's weights at 0.60. T-seuil = T0's weights, threshold chosen on the grid (ties: the smallest). T-long = the same head
    retrained (same architecture, loss, optimiser, batch 512, seeds 0, as the head script) for 30 epochs; after each epoch the
    threshold is chosen on the grid; epoch and threshold kept for the best validation score (ties: the earliest epoch, then the
    smallest threshold). T* = the best of T0, T-seuil, T-long on validation (ties: the simplest, in that order).
Outputs: tenseurs.json (every check), e0.json (validation scores, chosen thresholds and epochs, T*, controls, versions),
journal_t_long.jsonl, t_long.pt (weights, vocabulary, threshold, epoch, feature configuration), run.json, budget.json.
"""

import hashlib
import json
import os
import re
import resource
import sys
import time
from pathlib import Path

import numpy as np
import torch

OUT, ENC, T0 = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
SMOKE = int(os.environ.get("E0_SMOKE", "-1"))
assert SMOKE >= 0, "E0_SMOKE must be set explicitly (0 = full run)"
SHARDS = ["test-00000-of-00001"] + [f"train-{i:05d}-of-00011" for i in range(11)]
FEATURE_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|square-grey128|448|bicubic|autocast-fp16|"
                  "summary+meanspatial|l2-each-then-l2")
GRID_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|square-grey128|448|bicubic|autocast-fp16|"
               "spatial28x28|adaptive-avg-8x8|fp16")
T0_SHA = "2b403a912383853d52ed771ef5843a42a80160e39b180ccf98e8bf3b1fc98242"
T0_VAL = 0.5517433451139009  # published validation score of T0, epoch 14, threshold 0.6 (journal.jsonl of the head run)
GRID = [round(0.05 * k, 2) for k in range(1, 20)]
EPOCHS = 30 if not SMOKE else SMOKE
dev = "cuda" if torch.cuda.is_available() else "cpu"
started = time.time()


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def jsha(x):
    return hashlib.sha256(json.dumps(x).encode()).hexdigest()


def write_json(obj, path):
    tmp = path.with_name(path.name + ".tmp")
    json.dump(obj, open(tmp, "w"), indent=1)
    os.replace(tmp, path)


def progress(msg):
    line = f"{time.time() - started:7.0f} s  {msg}"
    print(line, flush=True)
    with open(OUT / "progress.log", "a") as f:
        f.write(line + "\n")


def finite_by_chunks(a, step=2048):
    return all(np.isfinite(a[i:i + step]).all() for i in range(0, len(a), step))


write_json({"script_sha256": sha(__file__), "smoke": SMOKE, "torch": torch.__version__, "numpy": np.__version__,
            "gpu": torch.cuda.get_device_name() if dev == "cuda" else None, "feature_config": FEATURE_CONFIG,
            "t0_sha256": sha(T0 / "head.pt")}, OUT / "run.json")

# ---- (1) Tensors ----
checks, X, Y, M = [], {}, {}, {}
for tag in SHARDS:
    npz, man, grid, side = ENC / "feats" / f"{tag}.npz", ENC / "feats" / f"{tag}.json", ENC / "grid" / f"{tag}.npy", ENC / "grid" / f"{tag}.json"
    s = json.load(open(side))
    n = s["rows"]
    z = np.load(npz)
    g = np.load(grid, mmap_mode="r")
    c = {"shard": tag, "rows": n,
         "vec_sha256_ok": sha(npz) == s["vec_sha256"], "grid_sha256_ok": sha(grid) == s["grid_sha256"],
         "manifest_ok": json.load(open(man)) == s["manifest"], "feature_config_ok": s["manifest"]["feature_config"] == FEATURE_CONFIG,
         "grid_config_ok": s["grid_config"] == GRID_CONFIG, "labels_ok": jsha(s["labels"]) == s["manifest"]["labels_sha256"],
         "md5_ok": jsha(list(z["md5"])) == s["md5_sha256"] and len(z["md5"]) == n,
         "vec_shape_dtype_ok": z["x"].shape == (n, 4096) and z["x"].dtype == np.float16,
         "grid_shape_dtype_ok": g.shape == (n, 64, 1024) and g.dtype == np.float16,
         "vec_finite": bool(finite_by_chunks(z["x"])), "grid_finite": bool(finite_by_chunks(g))}
    c["ok"] = all(v for k, v in c.items() if k.endswith(("_ok", "_finite")))
    checks.append(c)
    X[tag], Y[tag], M[tag] = z["x"], s["labels"], list(z["md5"])
    del g
    progress(f"{tag}: {'ok' if c['ok'] else 'FAILED'}")
total = sum(c["rows"] for c in checks)
tensors = {"shards": checks, "rows": total, "test_rows": checks[0]["rows"],
           "passed": all(c["ok"] for c in checks) and total == 87004 and checks[0]["rows"] == 788}
write_json(tensors, OUT / "tenseurs.json")
if not tensors["passed"]:
    progress("tensor check failed")
    sys.exit(3)

# ---- (2) Data, split and vocabulary of the head script ----
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
TOKEN = re.compile(r"\([^)]*\)|[A-Z]{1,2}|\d")
_anc = {}


def ancestors(code):
    code = code.strip()
    if code in _anc:
        return _anc[code]
    parts = code.split(":")
    out = {code}
    if all(PART.fullmatch(p) for p in parts):
        for p in parts:
            cur = ""
            for t in TOKEN.findall(p):
                cur += t
                out.add(cur)
    _anc[code] = frozenset(out)
    return _anc[code]


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


train = SHARDS[1:]
Xall = np.concatenate([X[t] for t in train]).astype(np.float32)
Yall = [y for t in train for y in Y[t]]
Mall = [m for t in train for m in M[t]]
assert len(Xall) == 86216
groups = sorted(set(Mall))
gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
val = np.array([m in gval for m in Mall])
Xtr, Ytr = Xall[~val], [y for y, v in zip(Yall, val) if not v]
Xva, Yva = Xall[val], [y for y, v in zip(Yall, val) if v]
counts = {}
for y in Ytr:
    for c in set(y):
        counts[c] = counts.get(c, 0) + 1
vocab = sorted({a for c, n in counts.items() if n >= 5 for a in ancestors(c)})
ck = torch.load(T0 / "head.pt", map_location="cpu", weights_only=False)
controls = {"t0_sha256_ok": sha(T0 / "head.pt") == T0_SHA, "vocab_equal_t0": vocab == list(ck["vocab"]), "vocab_size": len(vocab),
            "val_images": int(val.sum()), "train_images": int((~val).sum())}
vi = {c: i for i, c in enumerate(vocab)}


def make_head():
    return torch.nn.Sequential(torch.nn.Linear(4096, 2048), torch.nn.GELU(), torch.nn.Dropout(0.2),
                               torch.nn.Linear(2048, len(vocab))).to(dev)


@torch.no_grad()
def probs(head, Q):
    head.eval()
    return torch.cat([torch.sigmoid(head(torch.from_numpy(Q[i:i + 4096]).to(dev))) for i in range(0, len(Q), 4096)]).cpu().numpy()


def head_pred(P, t):
    return [most_specific([vocab[j] for j in np.nonzero(row >= t)[0]]) for row in P]


def drop86(codes):
    return [c for c in codes if not c.strip().startswith("86")]


keep = [i for i, y in enumerate(Yva) if drop86(y)]
if SMOKE:
    keep = keep[:SMOKE * 100]
Yva_p = [drop86(Yva[i]) for i in keep]


def val_score(P, t):
    """Validation measure of the series: chapter 86 removed from truth and predictions, empty projected truths left out."""
    preds = head_pred(P[keep], t)
    return float(np.mean([hier_f1(g, drop86(p)) for g, p in zip(Yva_p, preds, strict=True)]))


def best_threshold(P):
    scores = {t: val_score(P, t) for t in GRID}
    t = min(GRID, key=lambda t: (-scores[t], t))
    return t, scores[t], scores


t0_head = make_head()
t0_head.load_state_dict(ck["state"])
P0 = probs(t0_head, Xva)
historical = float(np.mean([hier_f1(g, p) for g, p in zip(Yva, head_pred(P0, 0.6), strict=True)]))
controls["t0_val_historical"] = historical
controls["t0_val_historical_ok"] = abs(historical - T0_VAL) <= 0.001
controls["passed"] = controls["t0_sha256_ok"] and controls["vocab_equal_t0"] and controls["t0_val_historical_ok"]
progress(f"controls: {controls}")
if not controls["passed"] and not SMOKE:
    write_json({"controls": controls, "tensors_passed": True}, OUT / "e0.json")
    sys.exit(3)

# ---- (3) T0, T-seuil, T-long on the validation measure of the series ----
res = {"T0": {"threshold": 0.6, "epoch": 14, "horizon": 15, "val": val_score(P0, 0.6)}}
t, s, grid_scores = best_threshold(P0)
res["T-seuil"] = {"threshold": t, "epoch": 14, "horizon": 15, "val": s, "grid": grid_scores}
del t0_head
progress(f"T0 {res['T0']['val']:.4f}, T-seuil {s:.4f} at {t}")

torch.manual_seed(0)
torch.cuda.manual_seed_all(0)


def targets(ys):
    out = np.zeros((len(ys), len(vocab)), dtype=np.float32)
    for r, y in enumerate(ys):
        for c in y:
            for a in ancestors(c):
                if a in vi:
                    out[r, vi[a]] = 1
    return out


def asym_loss(logits, y, gn=4.0, gp=0.0, clip=0.05):
    p = torch.sigmoid(logits)
    pn = (p - clip).clamp(min=0)
    lp = y * (1 - p) ** gp * torch.log(p.clamp(min=1e-8))
    ln = (1 - y) * pn ** gn * torch.log((1 - pn).clamp(min=1e-8))
    return -(lp + ln).sum(1).mean()


Ttr = torch.from_numpy(targets(Ytr))
head = make_head()
opt = torch.optim.AdamW(head.parameters(), lr=1e-3, weight_decay=1e-4)
Xtr_t = torch.from_numpy(Xtr)
gen = torch.Generator().manual_seed(0)
best = None
for epoch in range(EPOCHS):
    head.train()
    perm = torch.randperm(len(Xtr_t), generator=gen)
    for i in range(0, len(perm), 512):
        b = perm[i:i + 512]
        loss = asym_loss(head(Xtr_t[b].to(dev)), Ttr[b].to(dev))
        opt.zero_grad()
        loss.backward()
        opt.step()
    P = probs(head, Xva)
    t, s, _ = best_threshold(P)
    hist = float(np.mean([hier_f1(g, p) for g, p in zip(Yva, head_pred(P, 0.6), strict=True)]))
    with open(OUT / "journal_t_long.jsonl", "a") as f:
        f.write(json.dumps({"epoch": epoch, "val": s, "threshold": t, "val_historical_at_0.6": hist, "loss": float(loss)}) + "\n")
    progress(f"T-long epoch {epoch}: val {s:.4f} at {t} (historical at 0.6: {hist:.4f})")
    if best is None or s > best["val"]:
        best = {"threshold": t, "epoch": epoch, "horizon": 30, "val": s}
        tmp = OUT / "t_long.tmp.pt"
        torch.save({"state": head.state_dict(), "vocab": vocab, "threshold": t, "epoch": epoch, "feature_config": FEATURE_CONFIG}, tmp)
        os.replace(tmp, OUT / "t_long.pt")
res["T-long"] = best
order = ["T0", "T-seuil", "T-long"]
t_star = min(order, key=lambda k: (-res[k]["val"], order.index(k)))
out = {"technical_only": bool(SMOKE), "controls": controls, "tensors_passed": True, "validation": res, "T_star": t_star,
       "val_images_measured": len(keep), "grid": GRID, "t_long_sha256": sha(OUT / "t_long.pt"),
       "note": "validation only; no test measure (amendment 4)"}
write_json(out, OUT / "e0.json")
write_json({"ram_peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
            "vram_peak_allocated_gb": torch.cuda.max_memory_allocated() / 1e9 if dev == "cuda" else None,
            "wall_seconds": time.time() - started}, OUT / "budget.json")
progress(f"done: T* = {t_star}")
