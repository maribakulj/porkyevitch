#!/usr/bin/env python3
"""E3 of the architecture series (PREINSCRIPTION.md): T-D (ML-Decoder over the 8 x 8 spatial tokens) and T-Z (learned pooling of the
same tokens, then T's MLP), trained on the ICAI train, chosen on the ICAI validation only; no test measure (amendment 4).

Usage: e3_spatial.py OUT ENC TSTAR MLDEC
ENC: the `full/` folder of kernel caypollard-encode-cradio version 3 (grid/<shard>.npy: float16 (n, 64, 1024), C-RADIO patch tokens
only, 28 x 28 -> adaptive average 8 x 8; feats/ for the md5 of the split). TSTAR: the `full/` folder of E0 (t_long.pt: vocabulary).
MLDEC: ml_decoder.py of Alibaba-MIIL/ML_Decoder at commit 8a9e984f671c9c30c98d2c45dfcaf4383381c254 (MIT licence, (c) Alibaba-MIIL;
sha256 below), used unchanged; one compatibility shim for recent torch: nn.TransformerDecoder passes tgt_is_causal / memory_is_causal
to its layers (dropped, the 2022 layer does not accept them) and reads layers[0].self_attn (exposed as the layer's multihead_attn).
ENV E3_SMOKE=N trains N epochs per arm on the first N x 2048 training rows and measures the first N x 100 validation images with a
non-empty projected truth (dry run: technical only); E3_SMOKE=0 is the full run.

Common to both arms (as T*): split by md5 groups (default_rng(0) < 0.05), vocabulary of T* (checked), targets closed upward,
asymmetric loss of T (gn 4, gp 0, clip 0.05, sum over codes, mean over images), AdamW lr 1e-3 weight decay 1e-4, batch 512, seed 0
before each arm, horizon of T*: 30 epochs; after each epoch the threshold is chosen on the extended grid with the validation measure
of the series (chapter 86 removed, empty projected truths left out); epoch and threshold kept for the best score (ties: the earliest
epoch, then the smallest threshold). Prediction: p_c >= t, then most_specific. Grids read memory-mapped, converted to float32 batch by
batch; never the whole grid on the GPU.
- T-D: MLDecoder(num_classes=len(vocab), num_of_groups=100, decoder_embedding=768, initial_num_features=1024): one layer, FFN 2048,
  dropout 0.1, frozen queries (the official reference settings). Classes spread over the groups at random: slot_of_class =
  default_rng(0).permutation(len(vocab)); the logit of class c is output slot_of_class[c]; the permutation and its inverse are saved.
- T-Z: one learned query q (1024); weights softmax_z(q . x_z / sqrt(1024)) over the 64 zones; pooled vector sum_z w_z x_z (1024);
  then T's MLP shape (1024 -> 2048 -> GELU -> dropout 0.2 -> vocabulary). The 1/sqrt(1024) scale is the usual dot-product attention
  scale (not fixed by the preregistration; written here before any run).
Outputs: e3.json (controls, chosen epoch/threshold/score per arm, parameter counts), journal_t_d.jsonl, journal_t_z.jsonl, t_d.pt,
t_z.pt (weights, vocabulary, threshold, epoch, configuration, class permutation for T-D), run.json, budget.json.
"""

import hashlib
import importlib.util
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

OUT, ENC, TSTAR, MLDEC = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
SMOKE = int(os.environ.get("E3_SMOKE", "-1"))
assert SMOKE >= 0, "E3_SMOKE must be set explicitly (0 = full run)"
TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
TSTAR_SHA = "5a1b3041c0d9aab0e3403182b0881272a02f395542fe8414dc54b4fc7fa045ea"
MLDEC_SHA = "59fbf54f027c1ef07e4943d1cb7d9ba6d11a5710018ab05fb7b34270cf1f83f7"
MLDEC_COMMIT = "8a9e984f671c9c30c98d2c45dfcaf4383381c254"
GRID_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|square-grey128|448|bicubic|autocast-fp16|"
               "spatial28x28|adaptive-avg-8x8|fp16")
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
            "gpu": torch.cuda.get_device_name() if dev == "cuda" else None, "tstar_sha256": sha(TSTAR / "t_long.pt"),
            "ml_decoder": {"commit": MLDEC_COMMIT, "sha256": sha(MLDEC)}}, OUT / "run.json")

# ---- ML-Decoder, official file, unchanged, plus the keyword shim ----
spec = importlib.util.spec_from_file_location("ml_decoder", MLDEC)
mld = importlib.util.module_from_spec(spec)
sys.modules["ml_decoder"] = mld  # TorchScript compiles GroupFC from its source: inspect needs the module registered
spec.loader.exec_module(mld)
_orig_forward = mld.TransformerDecoderLayerOptimal.forward


def _forward(self, tgt, memory, tgt_mask=None, memory_mask=None, tgt_key_padding_mask=None, memory_key_padding_mask=None,
             tgt_is_causal=None, memory_is_causal=None):
    return _orig_forward(self, tgt, memory, tgt_mask, memory_mask, tgt_key_padding_mask, memory_key_padding_mask)


mld.TransformerDecoderLayerOptimal.forward = _forward
# torch >= 2.1: nn.TransformerDecoder reads layers[0].self_attn.batch_first before calling the layer; the 2022 layer names its
# attention multihead_attn. Expose it under that name too (batch_first False, as the official (length, batch, dim) tensors).
mld.TransformerDecoderLayerOptimal.self_attn = property(lambda self: self.multihead_attn)

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


# ---- Data: grids memory-mapped, split and vocabulary as T* ----
grids, Y, M, where = [], [], [], []
for s_i, tag in enumerate(TRAIN):
    side = json.load(open(ENC / "grid" / f"{tag}.json"))
    assert side["grid_config"] == GRID_CONFIG, tag
    g = np.load(ENC / "grid" / f"{tag}.npy", mmap_mode="r")
    z = np.load(ENC / "feats" / f"{tag}.npz")
    assert g.shape == (side["rows"], 64, 1024) and g.dtype == np.float16 and len(z["md5"]) == side["rows"], tag
    grids.append(g)
    Y += side["labels"]
    M += list(z["md5"])
    where += [(s_i, r) for r in range(side["rows"])]
assert len(where) == 86216
groups = sorted(set(M))
gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
val = np.array([m in gval for m in M])
tr_idx = np.nonzero(~val)[0]
va_idx = np.nonzero(val)[0]
Ytr = [Y[i] for i in tr_idx]
counts = {}
for y in Ytr:
    for c in set(y):
        counts[c] = counts.get(c, 0) + 1
vocab = sorted({a for c, n in counts.items() if n >= 5 for a in ancestors(c)})
ck = torch.load(TSTAR / "t_long.pt", map_location="cpu", weights_only=False)
controls = {"tstar_sha256_ok": sha(TSTAR / "t_long.pt") == TSTAR_SHA, "vocab_equal_tstar": vocab == list(ck["vocab"]),
            "ml_decoder_sha256_ok": sha(MLDEC) == MLDEC_SHA}
controls["passed"] = all(controls.values())
progress(f"controls: {controls}")
if not controls["passed"]:
    write_json({"controls": controls}, OUT / "e3.json")
    sys.exit(3)
vi = {c: i for i, c in enumerate(vocab)}
V = len(vocab)
keep = [int(i) for i in va_idx if drop86(Y[i])]
if SMOKE:
    tr_idx = tr_idx[:SMOKE * 2048]
    keep = keep[:SMOKE * 100]
Yk = [drop86(Y[i]) for i in keep]


def batch_grid(idx):
    """float32 (b, 64, 1024) for global indices idx, read shard by shard from the memory maps."""
    out = np.empty((len(idx), 64, 1024), dtype=np.float32)
    order = np.argsort(idx)
    for pos in order:
        s_i, r = where[idx[pos]]
        out[pos] = grids[s_i][r]
    return torch.from_numpy(out)


def targets(ix):
    t = np.zeros((len(ix), V), dtype=np.float32)
    for r, i in enumerate(ix):
        for c in Y[i]:
            for a in ancestors(c):
                if a in vi:
                    t[r, vi[a]] = 1
    return torch.from_numpy(t)


def asym_loss(logits, y, gn=4.0, gp=0.0, clip=0.05):
    p = torch.sigmoid(logits)
    pn = (p - clip).clamp(min=0)
    lp = y * (1 - p) ** gp * torch.log(p.clamp(min=1e-8))
    ln = (1 - y) * pn ** gn * torch.log((1 - pn).clamp(min=1e-8))
    return -(lp + ln).sum(1).mean()


class TD(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.dec = mld.MLDecoder(num_classes=V, num_of_groups=100, decoder_embedding=768, initial_num_features=1024)
        self.register_buffer("slot_of_class", torch.from_numpy(np.random.default_rng(0).permutation(V)).long())

    def forward(self, x):
        return self.dec(x)[:, self.slot_of_class]


class TZ(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.q = torch.nn.Parameter(torch.randn(1024) / 32.0)
        self.mlp = torch.nn.Sequential(torch.nn.Linear(1024, 2048), torch.nn.GELU(), torch.nn.Dropout(0.2), torch.nn.Linear(2048, V))

    def forward(self, x):
        w = torch.softmax((x @ self.q) / 32.0, dim=1)  # sqrt(1024) = 32
        return self.mlp((w.unsqueeze(-1) * x).sum(1))


@torch.no_grad()
def val_probs(model):
    model.eval()
    out = []
    for i in range(0, len(keep), 256):
        out.append(torch.sigmoid(model(batch_grid(keep[i:i + 256]).to(dev))).cpu().numpy())
    return np.concatenate(out)


def score(P, t):
    preds = [most_specific([vocab[j] for j in np.nonzero(row >= t)[0]]) for row in P]
    return float(np.mean([hier_f1(g, drop86(p)) for g, p in zip(Yk, preds, strict=True)]))


def nbytes(tensors):
    return int(sum(t.numel() * t.element_size() for t in tensors))


def sync():
    if dev == "cuda":
        torch.cuda.synchronize()


def alloc():
    sync()
    return torch.cuda.memory_allocated() if dev == "cuda" else None


disk_before = {str(q): shutil.disk_usage(q).free for q in (OUT, Path("/tmp"))}
results, budgets = {}, {}
for arm, make, tag in (("T-D", TD, "t_d"), ("T-Z", TZ, "t_z")):
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    if dev == "cuda":
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    arm_started = time.time()
    model = make().to(dev)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-3, weight_decay=1e-4)
    gen = torch.Generator().manual_seed(0)
    # Budget (preregistration, E3 "Budget mesuré à l'essai à blanc"): measured on the first training batch of the arm, inside the normal
    # loop (no extra forward, so no extra random draw: the training trajectory is the same with or without these measures).
    # Units: bytes (CUDA allocator, torch.cuda.memory_allocated, at the instants named); peaks are not added to persistent sizes.
    attn_out = []
    hooks = []
    if arm == "T-D":
        hooks.append(model.dec.decoder.layers[0].multihead_attn.register_forward_hook(
            lambda m, i, o: attn_out.append(nbytes([t for t in (o if isinstance(o, tuple) else (o,)) if torch.is_tensor(t)]))))
    budget = {"weights_bytes": {"trainable": nbytes([q for q in model.parameters() if q.requires_grad]),
                                "frozen": nbytes([q for q in model.parameters() if not q.requires_grad]),
                                "buffers": nbytes(list(model.buffers()))},
              "method": "first training batch of the arm, inside the loop: allocated before forward (A0), after forward (A1: "
                        "activations and attention kept for backward), after backward (A2: + gradients, - freed activations), after "
                        "the first AdamW step (A3: + optimiser states); peak = torch.cuda.max_memory_allocated over that batch after a "
                        "reset; attention = bytes of the outputs of the decoder's multihead attention returned to the caller (forward "
                        "hook; T-D only); its internal buffers kept for backward are inside A1 - A0 and are not separable from the other "
                        "activations by this method"}
    epoch_times = []
    best = None
    for epoch in range(EPOCHS):
        model.train()
        perm = tr_idx[torch.randperm(len(tr_idx), generator=gen).numpy()]
        sync()
        t_ep = time.time()
        for i in range(0, len(perm), 512):
            b = perm[i:i + 512]
            first = epoch == 0 and i == 0
            xb, yb = batch_grid(b).to(dev), targets(b).to(dev)
            if first:
                if dev == "cuda":
                    torch.cuda.reset_peak_memory_stats()
                a0 = alloc()
            loss = asym_loss(model(xb), yb)
            if first:
                a1 = alloc()
            opt.zero_grad()
            loss.backward()
            if first:
                a2 = alloc()
                grads = nbytes([q.grad for q in model.parameters() if q.grad is not None])
            opt.step()
            if first:
                a3 = alloc()
                states = nbytes([v for st in opt.state.values() for v in st.values() if torch.is_tensor(v)])
                budget["first_batch"] = {"batch": len(b), "A0_before_forward": a0, "A1_after_forward": a1, "A2_after_backward": a2,
                                         "A3_after_step": a3, "activations_kept_A1_minus_A0": None if a0 is None else a1 - a0,
                                         "gradients_bytes": grads, "adamw_states_bytes": states,
                                         "attention_outputs_bytes": attn_out[0] if attn_out else None,
                                         "peak_over_batch": torch.cuda.max_memory_allocated() if dev == "cuda" else None}
                for h in hooks:
                    h.remove()
        sync()
        epoch_times.append({"epoch": epoch, "seconds": time.time() - t_ep, "images": int(len(perm)),
                            "images_per_second": len(perm) / max(time.time() - t_ep, 1e-9)})
        P = val_probs(model)
        scores = {t: score(P, t) for t in GRID}
        t = min(GRID, key=lambda t: (-scores[t], t))
        with open(OUT / f"journal_{tag}.jsonl", "a") as f:
            f.write(json.dumps({"epoch": epoch, "val": scores[t], "threshold": t, "loss": float(loss),
                                "train_seconds": epoch_times[-1]["seconds"]}) + "\n")
        progress(f"{arm} epoch {epoch}: val {scores[t]:.4f} at {t}")
        if best is None or scores[t] > best["val"]:
            best = {"epoch": epoch, "threshold": t, "val": scores[t]}
            extra = {"slot_of_class": model.slot_of_class.cpu().numpy().tolist(),
                     "class_of_slot": np.argsort(model.slot_of_class.cpu().numpy()).tolist(),
                     "ml_decoder": {"commit": MLDEC_COMMIT, "num_of_groups": 100, "decoder_embedding": 768}} if arm == "T-D" else {
                "pooling": "softmax(q . x / sqrt(1024)) over 64 zones"}
            tmp = OUT / f"{tag}.tmp.pt"
            torch.save({"state": model.state_dict(), "vocab": vocab, "threshold": t, "epoch": epoch, "grid_config": GRID_CONFIG,
                        **extra}, tmp)
            os.replace(tmp, OUT / f"{tag}.pt")
    sync()
    budget.update({"epochs": epoch_times, "arm_wall_seconds": time.time() - arm_started,
                   "vram_peak_allocated_arm_bytes": torch.cuda.max_memory_allocated() if dev == "cuda" else None,
                   "vram_peak_reserved_arm_bytes": torch.cuda.max_memory_reserved() if dev == "cuda" else None,
                   "ram_peak_process_so_far_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
                   "checkpoint_bytes": (OUT / f"{tag}.pt").stat().st_size})
    budgets[arm] = budget
    results[arm] = {**best, "horizon": 30, "sha256": sha(OUT / f"{tag}.pt"),
                    "trainable_parameters": int(sum(p.numel() for p in model.parameters() if p.requires_grad))}
    del loss, xb, yb, model, opt  # the last batch's graph would otherwise keep the arm's parameters alive into the next arm
    torch.cuda.empty_cache()
write_json({"technical_only": bool(SMOKE), "controls": controls, "val_images_measured": len(keep), "train_images": int(len(tr_idx)),
            **results, "grid": GRID, "note": "validation only; no test measure (amendment 4)"}, OUT / "e3.json")
write_json({"arms": budgets, "ram_peak_gb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
            "ram_note": "ru_maxrss of the process (Linux: KiB), divided by 1e6: GB to 2.4 %",
            "disk_free_before_gb": {k: v / 1e9 for k, v in disk_before.items()},
            "disk_free_after_gb": {str(q): shutil.disk_usage(q).free / 1e9 for q in (OUT, Path("/tmp"))},
            "outputs_bytes": int(sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())),
            "resumption": "none inside a run: checkpoints are written atomically at each best epoch; a lost session is rerun from zero "
                          "in a new output folder (the optimiser state is not saved, so a resumed run would not be the same run)",
            "wall_seconds": time.time() - started}, OUT / "budget.json")
progress(f"done: {results}")
