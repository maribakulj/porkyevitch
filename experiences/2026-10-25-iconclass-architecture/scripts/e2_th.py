#!/usr/bin/env python3
"""E2 of the architecture series (PREINSCRIPTION.md): T-H, the C-HMCNN recipe (Giunchiglia and Lukasiewicz, NeurIPS 2020, eq. 4),
written by us from the paper (the authors' code is GPL-3.0, not copied). Head retrained alone; choice on the ICAI validation only;
no test measure (amendment 4).

Usage: e2_th.py OUT ENC TSTAR
ENC: the `full/` folder of kernel caypollard-encode-cradio version 3; TSTAR: the `full/` folder of E0 (porky-e0-run version 2:
t_long.pt, the vocabulary of T0). ENV E2_SMOKE=N trains N epochs and measures the first N x 100 validation images with a non-empty
projected truth (dry run: technical only); E2_SMOKE=0 is the full run.

- Same data, split, vocabulary, targets (closed upward), architecture (4096 -> 2048 -> GELU -> dropout 0.2 -> vocabulary), optimiser
  (AdamW 1e-3, weight decay 1e-4), batch 512 and seeds 0 as T* (E0); horizon of T*: 30 epochs; epoch and threshold chosen on the
  validation measure of the series (chapter 86 removed, empty projected truths left out, extended grid 0.05 to 0.95; ties: the
  earliest epoch, then the smallest threshold).
- Constraint module: D(a) = the descendants of a in the vocabulary, a included (b in D(a) iff a in ancestors(b)); m_a = max over D(a)
  of p_b, p = sigmoid of the head. MCLoss: m+_a = max over D(a) of y_b * p_b; L_a = - y_a log(m+_a) - (1 - y_a) log(1 - m_a); sum over
  codes, mean over images. Maxima computed on the list of (ancestor, descendant) pairs with scatter_reduce amax, never a
  batch x codes x codes tensor. Prediction: m_a >= t, then most_specific, as T.
- Mandatory toy test, before training (stop, exit 3, if it fails): a positive parent whose negative child has the highest score:
  m+ of the parent must not take the child's score; m of the parent must.
- T-H0 check (published, not a brick): on T*'s validation probabilities, the maximum over descendants followed by T*'s threshold and
  most_specific gives T*'s predictions on every validation image.
- Not done here: the descriptive comparison with the official Iconclass tree (separate, no effect on the constraint).
Outputs: e2.json (controls, the T-H0 check, the chosen epoch and threshold, validation score), journal_t_h.jsonl, t_h.pt, run.json,
budget.json.
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
SMOKE = int(os.environ.get("E2_SMOKE", "-1"))
assert SMOKE >= 0, "E2_SMOKE must be set explicitly (0 = full run)"
TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
TSTAR_SHA = "5a1b3041c0d9aab0e3403182b0881272a02f395542fe8414dc54b4fc7fa045ea"
FEATURE_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|square-grey128|448|bicubic|autocast-fp16|"
                  "summary+meanspatial|l2-each-then-l2")
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
            "gpu": torch.cuda.get_device_name() if dev == "cuda" else None, "tstar_sha256": sha(TSTAR / "t_long.pt")}, OUT / "run.json")

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


def pair_index(vocab):
    """(ancestor index, descendant index) for every a in ancestors(b) within the vocabulary, a == b included."""
    vi = {c: i for i, c in enumerate(vocab)}
    anc, desc = [], []
    for j, b in enumerate(vocab):
        for a in ancestors(b):
            if a in vi:
                anc.append(vi[a])
                desc.append(j)
    return torch.tensor(anc, dtype=torch.long), torch.tensor(desc, dtype=torch.long)


def max_desc(v, anc, desc, n):
    """out[:, a] = max over the pairs (a, b) of v[:, b]; every a has its own pair, so the result is defined everywhere."""
    out = torch.full((v.shape[0], n), -1.0, device=v.device, dtype=v.dtype)
    return out.scatter_reduce(1, anc.to(v.device).expand(v.shape[0], -1), v[:, desc.to(v.device)], reduce="amax", include_self=True)


def mcloss(logits, y, anc, desc):
    p = torch.sigmoid(logits)
    n = p.shape[1]
    m = max_desc(p, anc, desc, n)
    m_plus = max_desc(y * p, anc, desc, n)
    loss = -(y * torch.log(m_plus.clamp(min=1e-8)) + (1 - y) * torch.log((1 - m).clamp(min=1e-8)))
    return loss.sum(1).mean()


# ---- Toy test (mandatory) ----
toy_vocab = ["1", "11", "11A"]
ta, td = pair_index(toy_vocab)
p_toy = torch.tensor([[0.30, 0.40, 0.90]])
y_toy = torch.tensor([[1.0, 1.0, 0.0]])  # parent "11" positive, child "11A" negative with the highest score
m_toy = max_desc(p_toy, ta, td, 3)
mp_toy = max_desc(y_toy * p_toy, ta, td, 3)
toy = {"m_parent": float(m_toy[0, 1]), "m_plus_parent": float(mp_toy[0, 1]),
       "passed": abs(float(mp_toy[0, 1]) - 0.40) < 1e-6 and abs(float(m_toy[0, 1]) - 0.90) < 1e-6 and abs(float(m_toy[0, 0]) - 0.90) < 1e-6}
progress(f"toy test: {toy}")
if not toy["passed"]:
    write_json({"toy_test": toy}, OUT / "e2.json")
    sys.exit(3)

# ---- Data (as E0) ----
X, Y, M = [], [], []
for tag in TRAIN:
    s = json.load(open(ENC / "grid" / f"{tag}.json"))
    assert sha(ENC / "feats" / f"{tag}.npz") == s["vec_sha256"], tag
    z = np.load(ENC / "feats" / f"{tag}.npz")
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
counts = {}
for y in Ytr:
    for c in set(y):
        counts[c] = counts.get(c, 0) + 1
vocab = sorted({a for c, n in counts.items() if n >= 5 for a in ancestors(c)})
ck = torch.load(TSTAR / "t_long.pt", map_location="cpu", weights_only=False)
controls = {"toy_test": toy["passed"], "tstar_sha256_ok": sha(TSTAR / "t_long.pt") == TSTAR_SHA, "vocab_equal_tstar": vocab == list(ck["vocab"])}
vi = {c: i for i, c in enumerate(vocab)}
anc, desc = pair_index(vocab)
controls["pairs"] = int(len(anc))
keep = [i for i, y in enumerate(Yva) if drop86(y)]
if SMOKE:
    keep = keep[:SMOKE * 100]
Xk, Yk = Xva[keep], [drop86(Yva[i]) for i in keep]


def make_head():
    return torch.nn.Sequential(torch.nn.Linear(4096, 2048), torch.nn.GELU(), torch.nn.Dropout(0.2),
                               torch.nn.Linear(2048, len(vocab))).to(dev)


@torch.no_grad()
def probs(head, Q, constrained):
    head.eval()
    out = []
    for i in range(0, len(Q), 1024):
        p = torch.sigmoid(head(torch.from_numpy(Q[i:i + 1024]).to(dev)))
        out.append(max_desc(p, anc, desc, len(vocab)) if constrained else p)
    return torch.cat(out).cpu().numpy()


def predict(P, t):
    return [most_specific([vocab[j] for j in np.nonzero(row >= t)[0]]) for row in P]


def score(P, t):
    return float(np.mean([hier_f1(g, drop86(p)) for g, p in zip(Yk, predict(P, t), strict=True)]))


# ---- T-H0 check on T*'s validation probabilities ----
tstar = make_head()
tstar.load_state_dict(ck["state"])
Pt = probs(tstar, Xk, constrained=False)
Pt_h0 = probs(tstar, Xk, constrained=True)
t_star = float(ck["threshold"])
h0_same = predict(Pt, t_star) == predict(Pt_h0, t_star)
controls["t_h0_identical_to_tstar"] = bool(h0_same)
del tstar
controls["passed"] = controls["toy_test"] and controls["tstar_sha256_ok"] and controls["vocab_equal_tstar"] and controls["t_h0_identical_to_tstar"]
progress(f"controls: {controls}")
if not controls["passed"]:
    write_json({"controls": controls}, OUT / "e2.json")
    sys.exit(3)

# ---- T-H training ----
torch.manual_seed(0)
torch.cuda.manual_seed_all(0)


def targets(ys):
    t = np.zeros((len(ys), len(vocab)), dtype=np.float32)
    for r, y in enumerate(ys):
        for c in y:
            for a in ancestors(c):
                if a in vi:
                    t[r, vi[a]] = 1
    return t


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
        loss = mcloss(head(Xtr_t[b].to(dev)), Ttr[b].to(dev), anc, desc)
        opt.zero_grad()
        loss.backward()
        opt.step()
    P = probs(head, Xk, constrained=True)
    scores = {t: score(P, t) for t in GRID}
    t = min(GRID, key=lambda t: (-scores[t], t))
    with open(OUT / "journal_t_h.jsonl", "a") as f:
        f.write(json.dumps({"epoch": epoch, "val": scores[t], "threshold": t, "loss": float(loss)}) + "\n")
    progress(f"T-H epoch {epoch}: val {scores[t]:.4f} at {t}")
    if best is None or scores[t] > best["val"]:
        best = {"epoch": epoch, "threshold": t, "val": scores[t]}
        tmp = OUT / "t_h.tmp.pt"
        torch.save({"state": head.state_dict(), "vocab": vocab, "threshold": t, "epoch": epoch, "feature_config": FEATURE_CONFIG,
                    "constraint": "max over descendants (ancestors() of the notation)"}, tmp)
        os.replace(tmp, OUT / "t_h.pt")
write_json({"technical_only": bool(SMOKE), "controls": controls, "toy_test": toy, "val_images_measured": len(keep),
            "T-H": {**best, "horizon": 30}, "t_h_sha256": sha(OUT / "t_h.pt"), "grid": GRID,
            "note": "validation only; no test measure (amendment 4)"}, OUT / "e2.json")
write_json({"ram_peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
            "vram_peak_allocated_gb": torch.cuda.max_memory_allocated() / 1e9 if dev == "cuda" else None,
            "wall_seconds": time.time() - started}, OUT / "budget.json")
progress(f"done: {best}")
