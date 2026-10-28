#!/usr/bin/env python3
"""E1 of the architecture series (PREINSCRIPTION.md): TK, T-niv and TK-niv, chosen on the ICAI validation only, no retraining.
No test measure (amendment 4). The chosen parameters are written for the common prediction step, run once the bench is frozen.

Usage: e1_decision.py OUT ENC TSTAR
ENC: the `full/` folder of kernel caypollard-encode-cradio version 3 (the vectors; the tensors were checked by E0).
TSTAR: the `full/` folder of E0 (kernel porky-e0-run version 2): t_long.pt and e0.json. ENV E1_SMOKE=N keeps the first N x 100
validation images with a non-empty projected truth (dry run: technical only); E1_SMOKE=0 is the full run.

Data and validation measure: those of E0 (split by md5 groups, default_rng(0) < 0.05; chapter 86 removed from truth and predictions,
empty projected truths left out; extended grid 0.05 to 0.95 by 0.05). T* = T-long of reference.json (sha256 5a1b3041..., epoch 27,
threshold 0.60), checked against e0.json.
- TK: s_c = a * p_c + (1 - a) * v_c on T*'s vocabulary. v_c: the 20 nearest non-validation training images by cosine (vectors are
  L2-normalised: dot product), weights clipped at 0 and divided by their sum (historical K); v_c = sum of the weights of the neighbours
  having a code with c among its ancestors (c included); codes outside the vocabulary ignored. Prediction: s_c >= t, then
  most_specific. a in {0, 0.25, 0.5, 0.75, 1} and t on the grid chosen together; ties: the largest a, then the smallest t. Control:
  a = 1 at T*'s threshold reproduces T*'s predictions exactly on every validation image (otherwise stop, exit 3).
- T-niv: one threshold per depth slice of the predicted code: depth = len(ancestors(c)), the code and its ancestors read from the
  notation (a top-level code has depth 1); slices 1-2, 3-4, 5 and more. Start: the three thresholds at T*'s threshold; coordinate
  search on the grid, slices in the order 1-2, 3-4, 5+, three passes; at each step the value that maximises the validation score;
  ties: the current value is kept, otherwise the smallest.
- TK-niv: TK with its chosen a, then the T-niv search on s_c, same procedure. Its parameters are computed here; whether it counts in
  the family follows the preregistered condition (TK and T-niv both retained), decided only when the verdicts are opened.
Outputs: e1.json (chosen parameters, validation scores, the full TK grid, the T-niv search path, controls), run.json, budget.json.
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

OUT, ENC, TSTAR = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
SMOKE = int(os.environ.get("E1_SMOKE", "-1"))
assert SMOKE >= 0, "E1_SMOKE must be set explicitly (0 = full run)"
TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
TSTAR_SHA = "5a1b3041c0d9aab0e3403182b0881272a02f395542fe8414dc54b4fc7fa045ea"
GRID = [round(0.05 * k, 2) for k in range(1, 20)]
ALPHAS = [0.0, 0.25, 0.5, 0.75, 1.0]
SLICES = [(1, 2), (3, 4), (5, 10 ** 6)]
dev = "cuda" if torch.cuda.is_available() else "cpu"
started = time.time()


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def write_json(obj, path):
    tmp = path.with_name(path.name + ".tmp")
    json.dump(obj, open(tmp, "w"), indent=1)
    os.replace(tmp, path)


def progress(msg):
    line = f"{time.time() - started:7.0f} s  {msg}"
    print(line, flush=True)
    with open(OUT / "progress.log", "a") as f:
        f.write(line + "\n")


write_json({"script_sha256": sha(__file__), "smoke": SMOKE, "torch": torch.__version__, "numpy": np.__version__,
            "gpu": torch.cuda.get_device_name() if dev == "cuda" else None, "tstar_sha256": sha(TSTAR / "t_long.pt"),
            "e0_json_sha256": sha(TSTAR / "e0.json")}, OUT / "run.json")

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


def drop86(codes):
    return [c for c in codes if not c.strip().startswith("86")]


# ---- Data and T* (as E0) ----
X, Y, M = [], [], []
for tag in TRAIN:
    s = json.load(open(ENC / "grid" / f"{tag}.json"))
    z = np.load(ENC / "feats" / f"{tag}.npz")
    assert sha(ENC / "feats" / f"{tag}.npz") == s["vec_sha256"], tag
    X.append(z["x"])
    Y += s["labels"]
    M += list(z["md5"])
X = np.concatenate(X).astype(np.float32)
assert len(X) == 86216
groups = sorted(set(M))
gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
val = np.array([m in gval for m in M])
Xtr, Ytr = X[~val], [y for y, v in zip(Y, val) if not v]
Xva, Yva = X[val], [y for y, v in zip(Y, val) if v]
e0 = json.load(open(TSTAR / "e0.json"))
ck = torch.load(TSTAR / "t_long.pt", map_location="cpu", weights_only=False)
vocab, t_star = list(ck["vocab"]), float(ck["threshold"])
controls = {"tstar_sha256_ok": sha(TSTAR / "t_long.pt") == TSTAR_SHA, "e0_tstar": e0["T_star"] == "T-long",
            "epoch_threshold_ok": ck["epoch"] == 27 and t_star == 0.6 == e0["validation"]["T-long"]["threshold"]}
vi = {c: i for i, c in enumerate(vocab)}
head = torch.nn.Sequential(torch.nn.Linear(4096, 2048), torch.nn.GELU(), torch.nn.Dropout(0.2),
                           torch.nn.Linear(2048, len(vocab))).to(dev)
head.load_state_dict(ck["state"])
head.eval()
keep = [i for i, y in enumerate(Yva) if drop86(y)]
if SMOKE:
    keep = keep[:SMOKE * 100]
Xk = Xva[keep]
Yk = [drop86(Yva[i]) for i in keep]
with torch.no_grad():
    P = torch.cat([torch.sigmoid(head(torch.from_numpy(Xk[i:i + 4096]).to(dev))) for i in range(0, len(Xk), 4096)]).cpu().numpy()

# ---- Neighbour votes, extended to ancestors, on T*'s vocabulary ----
anc_idx = []
for y in Ytr:
    s = set()
    for c in y:
        s |= {vi[a] for a in ancestors(c) if a in vi}
    anc_idx.append(np.array(sorted(s), dtype=np.int64))
Xtr_dev = torch.from_numpy(Xtr).to(dev)
V = np.zeros_like(P)
for i in range(0, len(Xk), 1024):
    w, j = (torch.from_numpy(Xk[i:i + 1024]).to(dev) @ Xtr_dev.T).topk(20, dim=1)
    w = w.clamp(min=0).cpu().numpy()
    j = j.cpu().numpy()
    for r in range(len(w)):
        tot = max(float(w[r].sum()), 1e-9)
        for wt, jj in zip(w[r], j[r], strict=True):
            V[i + r, anc_idx[jj]] += wt / tot
del Xtr_dev
progress(f"votes ready on {len(Xk)} validation images")


def predict(S, thresholds):
    """thresholds: one value, or one value per code of the vocabulary (T-niv)."""
    return [most_specific([vocab[j] for j in np.nonzero(row >= thresholds)[0]]) for row in S]


def score(preds):
    return float(np.mean([hier_f1(g, drop86(p)) for g, p in zip(Yk, preds, strict=True)]))


# Control: a = 1 at T*'s threshold reproduces T*.
same = predict(1.0 * P + 0.0 * V, t_star) == predict(P, t_star)
controls["tk_alpha1_reproduces_tstar"] = bool(same)
controls["passed"] = all(controls.values())
progress(f"controls: {controls}")
if not controls["passed"]:
    write_json({"controls": controls}, OUT / "e1.json")
    sys.exit(3)
tstar_val = score(predict(P, t_star))

# ---- TK ----
tk_grid = {}
for a in ALPHAS:
    S = a * P + (1 - a) * V
    for t in GRID:
        tk_grid[f"{a}|{t}"] = score(predict(S, t))
best_a, best_t = min(((a, t) for a in ALPHAS for t in GRID), key=lambda x: (-tk_grid[f"{x[0]}|{x[1]}"], -x[0], x[1]))
tk = {"alpha": best_a, "threshold": best_t, "val": tk_grid[f"{best_a}|{best_t}"]}
progress(f"TK: {tk}")

# ---- T-niv and TK-niv: coordinate search on per-slice thresholds ----
depth = np.array([len(ancestors(c)) for c in vocab])
slice_of = np.array([next(k for k, (lo, hi) in enumerate(SLICES) if lo <= d <= hi) for d in depth])


def niv_search(S, start):
    th = [start] * 3
    path = []
    for p in range(3):
        for k in range(3):
            def val_with(v):
                trial = list(th)
                trial[k] = v
                return score(predict(S, np.array(trial)[slice_of]))
            scores = {v: val_with(v) for v in GRID}
            top = max(scores.values())
            if scores.get(th[k], -1) == top:
                new = th[k]
            else:
                new = min(v for v in GRID if scores[v] == top)
            th[k] = new
            path.append({"pass": p, "slice": SLICES[k][0], "value": new, "val": scores[new]})
    return th, score(predict(S, np.array(th)[slice_of])), path


niv_th, niv_val, niv_path = niv_search(P, t_star)
progress(f"T-niv: {niv_th} {niv_val:.4f}")
S_tk = best_a * P + (1 - best_a) * V
tkniv_th, tkniv_val, tkniv_path = niv_search(S_tk, best_t)
progress(f"TK-niv: alpha {best_a}, {tkniv_th} {tkniv_val:.4f}")

out = {"technical_only": bool(SMOKE), "controls": controls, "val_images_measured": len(keep), "tstar": {"threshold": t_star, "val": tstar_val},
       "TK": tk, "TK_grid": tk_grid, "T-niv": {"thresholds": dict(zip(("1-2", "3-4", "5+"), niv_th)), "val": niv_val, "path": niv_path},
       "TK-niv": {"alpha": best_a, "thresholds": dict(zip(("1-2", "3-4", "5+"), tkniv_th)), "val": tkniv_val, "path": tkniv_path},
       "slice_sizes_in_vocab": {f"{lo}-{hi if hi < 10 ** 6 else '+'}": int((slice_of == k).sum()) for k, (lo, hi) in enumerate(SLICES)},
       "note": "validation only; no test measure (amendment 4)"}
write_json(out, OUT / "e1.json")
write_json({"ram_peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
            "vram_peak_allocated_gb": torch.cuda.max_memory_allocated() / 1e9 if dev == "cuda" else None,
            "wall_seconds": time.time() - started}, OUT / "budget.json")
progress("done")
