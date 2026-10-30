"""D3 on Kaggle T4: S0, arm 1 (rare neighbour vote) and arm 2 (children head routed by the parent).
Preregistration sha 4a4c0c63...; Grok p2 notes (section 6) marked [G6].

Usage: d3_run.py --stage blanc|complet --encoder ENC --inventory INV --diag DIAG --out OUT [--blank B --blank-sha256 S]
  ENC   caypollard-encode-cradio v3 full output: feats/train-*.npz (vectors (n, 4096) float16) and grid/train-*.json
        (labels); grid tensors are not an input of these two arms [G6]
  INV   ENCODAGE_TRAIN_V3.json of P9-A (pinned sha); DIAG  output of mabaku/porky-diag-run v3 (B cache)
blanc  : inputs, B, S0 complete, weight-0 identity on 4265 rows, neighbours of 64 rows and one epoch: timings only.
complet: S0, arm 1 and its permuted-memory witness, arm 2 with seeds 0, 1, 2, judges, tables.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d3_core as d3  # noqa: E402

TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
PREREG_SHA256 = "4a4c0c630ee58be873ddc6377fdca9d3241dab1afe256b1f71b154e86f1f783b"
INVENTORY_SHA256 = "ff424e6453192f6465e23e3cdf9acf29aa5827d84565deb329de4c1b891a65d9"
DIAG_SHA256 = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
CACHE_SHA256 = "c7df9d3dd28acea7454cf7609cf083fe961fa5ff5a7ef121a85fc1d7c2eedbe9"
DECISIONS_SHA256 = "ea2502e101ed96a5bf13f00b014e204db9e3bf3d29ca0b32aa34406338d5e910"
B_H = 0.5890847528448202
SALT = "D3-2026-10-30|"
K, VOTE_WEIGHT, PERM_SEED = 20, 0.25, 3030
EPOCHS, BATCH, LR, WD, SEEDS = 20, 1024, 1e-3, 1e-4, (0, 1, 2)
THRESHOLDS = tuple(round(0.05 * k, 2) for k in range(1, 20))
BOOT_SEED = 20261030  # fixed here, percentile method, descriptive [G6]
CPU_TEST_FLAG = "D3_CPU_FOR_LOCAL_TESTS"  # local tests only; the Kaggle pilot removes it from the child's environment
NEIGHBOURS_DEVICE = ("numpy float32 on CPU, blocks of 256 validation rows; declared derogation from preregistration "
                     "section 5, which announced the GPU (Codex p4, 30/10); a GPU version would be new bytes to review")
COUNTING = ("exact raw codes after most_specific and drop86, every image of the lot, one t for all families; not concept "
            "recognition through the closure: truth 11H and output 11H1 count zero exact success for 11H, although H-F1 "
            "credits the concept. A descent result is therefore not a general causal proof about deep information in the "
            "features; H-F1 stays the judge of the pipeline")
CONDITIONAL_READING = "conditional_recall None = not applicable (gate closed for every true child); never a support"


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def legacy_sha(obj):
    return hashlib.sha256(json.dumps(obj).encode()).hexdigest()


def clean(obj):
    """NaN (an empty mean) becomes null; numpy scalars become Python numbers; dict keys become strings."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, (np.integer, np.bool_)):
        return obj.item()
    return obj


def write_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    os.replace(tmp, path)


class Data:
    def __init__(self, enc, inventory, diag):
        enc, diag = Path(enc), Path(diag)
        require(sha(inventory) == INVENTORY_SHA256, "inventory_sha")
        inv = json.loads(Path(inventory).read_text())["files"]
        labels, md5, xs, where = [], [], [], []
        for tag in TRAIN:
            for rel in (f"feats/{tag}.npz", f"grid/{tag}.json"):
                require(sha(enc / rel) == inv[rel], f"encoder_sha_{rel}")
            side = json.loads((enc / "grid" / f"{tag}.json").read_text())
            require(side["manifest"]["feature_config"].endswith("summary+meanspatial|l2-each-then-l2"), "vector_recipe")
            with np.load(enc / "feats" / f"{tag}.npz", allow_pickle=False) as z:
                m = [str(v) for v in z["md5"]]
                x = np.asarray(z["x"])
                require(x.shape == (len(m), 4096) and x.dtype == np.float16, "vector_shape")
                xs.append(x)
            require(legacy_sha(m) == side["md5_sha256"], "alignment")
            labels += side["labels"]
            md5 += m
            where += [(tag, r) for r in range(len(m))]
        x = np.concatenate(xs).astype(np.float32)
        del xs
        groups = sorted(set(md5))
        gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
        self.fit = np.array([i for i, m in enumerate(md5) if m not in gval])
        self.val = np.array([i for i, m in enumerate(md5) if m in gval])
        require((len(self.fit), len(self.val)) == (81951, 4265), "split")
        require(not ({md5[i] for i in self.fit} & {md5[i] for i in self.val}), "md5_shared")
        self.n_raw, self.n_closed = {}, {}
        for i in self.fit:
            for c in set(labels[i]):
                self.n_raw[c] = self.n_raw.get(c, 0) + 1
            for c in d3.closure(labels[i]):
                self.n_closed[c] = self.n_closed.get(c, 0) + 1
        self.vocab = sorted({a for c, n in self.n_raw.items() if n >= 5 for a in d3.ancestors(c)})
        require(len(self.vocab) == 7907, "vocabulary")
        require(sha(diag / "diagnostic.json") == DIAG_SHA256, "diagnostic_sha")
        d = json.loads((diag / "diagnostic.json").read_text())
        for f in ("probabilites_validation.npz", "identites_validation.json", "vocabulaire.json"):
            require(sha(diag / f) == d["files_sha256"][f], f"diag_file_{f}")
        cache = d["probability_cache"]
        require(d["files_sha256"]["probabilites_validation.npz"] == CACHE_SHA256 and
                cache["systems"]["B_TZ"]["decisions_sha256"] == DECISIONS_SHA256, "cache_manifest")
        require(json.loads((diag / "vocabulaire.json").read_text()) == self.vocab and
                legacy_sha(self.vocab) == cache["vocabulary_sha256"], "cache_vocabulary")
        ids = json.loads((diag / "identites_validation.json").read_text())
        require(ids == [{"shard": where[i][0], "row": where[i][1], "md5": md5[i]} for i in self.val], "cache_rows")
        with np.load(diag / "probabilites_validation.npz", allow_pickle=False) as z:
            self.pb = np.asarray(z["B_TZ"])
        require(self.pb.shape == (4265, 7907) and self.pb.dtype == np.float32, "cache_shape")
        self.b_pred = d3.project(self.pb, self.vocab, 0.65)
        require(legacy_sha([sorted(q) for q in self.b_pred]) == DECISIONS_SHA256, "B_decisions_not_reproduced")
        self.truth = [d3.drop86(labels[i]) for i in self.val]
        self.eligible = [k for k, g in enumerate(self.truth) if g]
        require(len(self.eligible) == 4241, "eligible")
        self.h_b = float(np.mean([d3.hier_f1(self.truth[k], self.b_pred[k]) for k in self.eligible]))
        require(abs(self.h_b - B_H) <= 1e-6, "B_H_not_reproduced")
        self.labels, self.md5, self.where = labels, md5, where
        self.vmd5 = [md5[i] for i in self.val]
        self.reg = [k for k in range(4265) if hashlib.sha256((SALT + self.vmd5[k]).encode()).digest()[0] < 128]
        rs = set(self.reg)
        self.lec = [k for k in range(4265) if k not in rs]
        self.universe = sorted(set(d3.drop86(list(set(self.n_raw) | set(self.vocab) |
                                                  {c for y in self.truth for c in y}))))
        self.xf, self.xv = x[self.fit], x[self.val]
        del x
        self.xf /= np.linalg.norm(self.xf, axis=1, keepdims=True)
        self.xv /= np.linalg.norm(self.xv, axis=1, keepdims=True)
        self._cl = {}

    def closure_fit(self, j):
        if j not in self._cl:
            self._cl[j] = d3.closure(self.labels[self.fit[j]])
        return self._cl[j]

    def neighbours(self, rows):
        nn, cos = np.zeros((len(rows), K), dtype=np.int64), np.zeros((len(rows), K))
        for s in range(0, len(rows), 256):
            sim = self.xv[rows[s:s + 256]] @ self.xf.T
            for r in range(sim.shape[0]):
                row = sim[r]
                cut = np.partition(row, -K)[-K]
                cand = np.flatnonzero(row >= cut)
                order = cand[np.lexsort((cand, -row[cand]))][:K]  # ties: canonical training order
                nn[s + r], cos[s + r] = order, row[order]
        return nn, cos


def s0(data):
    bad = [c for c, n in data.n_raw.items() if n >= 5 and c not in set(data.vocab)]
    require(not bad, "S0_code_with_n_raw_ge_5_outside_V")
    return {"table": d3.s0_table(data.universe, data.vocab, data.n_raw, data.n_closed, data.truth),
            "universe": len(data.universe), "no_code_outside_V_is_emissible": True}


# ---------------------------------------------------------------- arm 1
def arm1(data, nn, cos, rows, weight, permuted=False):
    rare = d3.rare_target(data.vocab, data.n_raw)
    rare_ix = {c: k for k, c in enumerate(rare)}
    vi = {c: j for j, c in enumerate(data.vocab)}
    cols = np.array([vi[c] for c in rare], dtype=int)
    sigma = np.random.default_rng(PERM_SEED).permutation(len(data.fit)) if permuted else None
    closures_of = (lambda j: data.closure_fit(int(sigma[j]))) if permuted else data.closure_fit
    preds = []
    for r, k in enumerate(rows):
        v = d3.votes(nn[r], cos[r], closures_of, rare_ix) if weight else np.zeros(len(rare))
        s = d3.mix_rare(data.pb[k], v, cols, weight)
        preds.append(d3.project(s[None, :], data.vocab, 0.65)[0])
    return preds, rare


def group_rare_tables(truth, preds, groups, rare):
    from scipy.sparse import lil_matrix
    uniq = sorted(set(groups))
    gi = {g: n for n, g in enumerate(uniq)}
    ri = {c: k for k, c in enumerate(rare)}
    tp, fp, fn = (lil_matrix((len(uniq), len(rare))) for _ in range(3))
    for y, p, g in zip(truth, preds, groups, strict=True):
        y, p, gg = set(y), set(p), gi[g]
        for coll, m in ((y & p, tp), (p - y, fp), (y - p, fn)):
            for c in coll:
                if c in ri:
                    m[gg, ri[c]] += 1
    return uniq, tp.tocsr(), fp.tocsr(), fn.tocsr()


def boot_fr(truth, preds_by, groups, rare, draws=10_000, seed=BOOT_SEED):
    """F_R per draw, TP/FP/FN recomputed with group multiplicities; same draws for every system."""
    tabs = {k: group_rare_tables(truth, p, groups, rare) for k, p in preds_by.items()}
    n_groups = len(next(iter(tabs.values()))[0])
    rng = np.random.default_rng(seed)
    out = {k: [] for k in preds_by}
    for start in range(0, draws, 500):
        m = min(500, draws - start)
        counts = np.stack([np.bincount(rng.integers(0, n_groups, n_groups), minlength=n_groups)
                           for _ in range(m)]).astype(float)
        for k, (_, tp, fp, fn) in tabs.items():
            t, f, n = (tp.T @ counts.T).T, (fp.T @ counts.T).T, (fn.T @ counts.T).T
            den = 2 * t + f + n
            out[k].append(np.divide(2 * t, den, out=np.zeros(den.shape), where=den != 0).mean(1))
    return {k: np.concatenate(v) for k, v in out.items()}


def measures(data, rows, preds, rare):
    el = [r for r, k in enumerate(rows) if data.truth[k]]
    truth = [data.truth[k] for k in rows]
    h = [d3.hier_f1(truth[r], preds[r]) for r in el]
    e = [d3.exact_e(truth[r], preds[r]) for r in el]
    tr = {}
    for name, lo, hi in d3.TRANCHES:
        codes = [c for c in data.universe if data.n_raw.get(c, 0) >= lo and (hi is None or data.n_raw.get(c, 0) <= hi)]
        tr[name] = d3.code_f1(truth, preds, codes) if codes else "not_applicable"
    fr = d3.code_f1(truth, preds, rare)
    represented = [c for c in rare if any(c in y for y in truth)]
    return {"H": float(np.mean(h)), "E": float(np.mean(e)), "eligible": len(el), "rows": len(rows), "F_R": fr["macro_F1"],
            "rare": fr, "F_R_represented_descriptive": d3.code_f1(truth, preds, represented)["macro_F1"],
            "tranches": tr, "h_per_image": h, "e_per_image": e}


# ---------------------------------------------------------------- arm 2
def device():
    """One T4, never a silent CPU fallback; CPU only under the explicit local-test flag."""
    import torch
    if os.environ.get(CPU_TEST_FLAG) == "1":
        return "cpu"
    require(torch.cuda.is_available() and "T4" in torch.cuda.get_device_name(0), "one_T4_required_no_cpu_fallback")
    return "cuda"


def environment():
    import scipy
    import torch
    dev = device()
    return {"device": dev, "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
            "local_cpu_test": dev == "cpu", "python": sys.version.split()[0], "numpy": np.__version__,
            "scipy": scipy.__version__, "torch": torch.__version__, "cuda": torch.version.cuda,
            "neighbours": NEIGHBOURS_DEVICE}


def check_identity(c, name):
    """total = coverage x conditional where the conditional is defined; with the gate closed for every true child,
    coverage and hits must be 0 and the conditional is published as not applicable."""
    if not c["true_children"]:
        return
    if c["conditional_recall"] is None:
        require(c["gate_coverage"] == 0 and c["hits"] == 0 and c["total_recall"] == 0, f"identity_closed_gate_{name}")
    else:
        require(abs(c["total_recall"] - c["gate_coverage"] * c["conditional_recall"]) <= 1e-12,
                f"identity_total_equals_coverage_times_conditional_{name}")


def arm2_structures(data):
    fam = d3.families(data.vocab, data.n_closed)
    children = [c for p in fam for c in fam[p]]
    require(len(children) > 0, "no_family_meets_the_training_supports: amend, do not relax")
    parent_of = {c: p for p, cs in fam.items() for c in cs}
    col = {c: k for k, c in enumerate(children)}
    parents = sorted(fam)
    pcols = {p: [col[c] for c in fam[p]] for p in parents}

    def masks(label_rows):
        mask = np.zeros((len(label_rows), len(children)), dtype=bool)
        y = np.zeros_like(mask)
        for r, lab in enumerate(label_rows):
            cl = d3.closure(lab)
            for p in parents:
                if p in cl:
                    mask[r, pcols[p]] = True
            for c in cl:
                k = col.get(c)
                if k is not None:
                    y[r, k] = True
        return mask, y
    return fam, children, parent_of, masks


def train_head(xf, mask, y, seed, epochs=EPOCHS, x_reg=None, mask_reg=None, y_reg=None):
    import torch
    dev = device()
    torch.manual_seed(seed)
    layer = torch.nn.Linear(xf.shape[1], mask.shape[1]).to(dev)
    opt = torch.optim.AdamW(layer.parameters(), lr=LR, weight_decay=WD)
    rows = np.flatnonzero(mask.any(1))  # lots drawn among rows with at least one active child [G6]
    require(len(rows) > 0, "no_training_row_with_an_active_child")
    gen = torch.Generator().manual_seed(seed)
    X = torch.from_numpy(xf)
    history = []
    for epoch in range(epochs):
        order = rows[torch.randperm(len(rows), generator=gen).numpy()]
        total = count = 0.0
        for s in range(0, len(order), BATCH):
            b = order[s:s + BATCH]
            xb = X[b].to(dev)
            mb, yb = torch.from_numpy(mask[b]).to(dev), torch.from_numpy(y[b]).float().to(dev)
            logits = layer(xb)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits[mb], yb[mb])  # mean of active couples [G6]
            opt.zero_grad()
            loss.backward()
            opt.step()
            require(bool(torch.isfinite(loss)), "nonfinite_loss")
            total += float(loss) * int(mb.sum())
            count += int(mb.sum())
        rec = {"epoch": epoch + 1, "train_loss": total / count}
        if x_reg is not None:
            with torch.no_grad():
                lr_ = layer(torch.from_numpy(x_reg).to(dev))
                m = torch.from_numpy(mask_reg).to(dev)
                rec["Vreg_masked_loss"] = float(torch.nn.functional.binary_cross_entropy_with_logits(
                    lr_[m], torch.from_numpy(y_reg).float().to(dev)[m]))
        history.append(rec)
    with torch.no_grad():
        return layer, history


def scores(layer, xv):
    import torch
    with torch.no_grad():
        return torch.sigmoid(layer(torch.from_numpy(xv).to(device()))).cpu().numpy()


def arm2_outputs(data, rows, sc, children, parent_of, t):
    t32 = np.float32(0.65)
    out, gates = [], []
    for r, k in enumerate(rows):
        braw = [data.vocab[j] for j in np.flatnonzero(data.pb[k] >= t32)]
        bcl = d3.closure(data.b_pred[k])
        out.append(d3.routed_set(braw, bcl, sc[r], children, parent_of, t))
        gates.append({c for c in children if parent_of[c] in bcl})
    return out, gates


def gates_for(data, rows, children, parent_of):
    """Children whose parent is in the closure of B's projected set, per image: the same gate for B and the head."""
    return [{c for c in children if parent_of[c] in d3.closure(data.b_pred[k])} for k in rows]


def freq_depth(data, rows, outputs, gates, children):
    table = {}
    cs = set(children)
    for k, o, g in zip(rows, outputs, gates, strict=True):
        for c in set(data.truth[k]) & cs:
            key = f"{d3.tranche(data.n_raw.get(c, 0))}|{d3.depth_case(c)}"
            cell = table.setdefault(key, {"true": 0, "gate": 0, "hit": 0})
            cell["true"] += 1
            cell["gate"] += c in g
            cell["hit"] += c in o
    return table


# ---------------------------------------------------------------- stages
def stage_blanc(a):
    t0 = time.monotonic()
    data = Data(a.encoder, a.inventory, a.diag)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    info = {"prereg_sha256": PREREG_SHA256, "setup_s": time.monotonic() - t0,
            "counts": {"Vreg": len(data.reg), "Vlec": len(data.lec), "eligible": len(data.eligible)}}
    t0 = time.monotonic()
    info["S0"] = s0(data)
    info["S0_s"] = time.monotonic() - t0
    rows = list(range(len(data.val)))
    preds0, rare = arm1(data, None, None, rows, 0.0)
    require(legacy_sha([sorted(q) for q in preds0]) == DECISIONS_SHA256, "weight_zero_identity")
    info["weight_zero_identity_rows"] = len(rows)
    info["R_codes"] = len(rare)
    t0 = time.monotonic()
    data.neighbours(rows[:64])
    info["neighbours_64_s"] = time.monotonic() - t0
    fam, children, parent_of, masks = arm2_structures(data)
    mask, y = masks([data.labels[i] for i in data.fit])
    info["families"] = {"families": len(fam), "children": len(children)}
    t0 = time.monotonic()
    train_head(data.xf, mask, y, 0, epochs=1)
    info["one_epoch_s"] = time.monotonic() - t0
    est = (info["setup_s"] + info["S0_s"] + info["neighbours_64_s"] / 64 * 4265 * 2 +
           info["one_epoch_s"] * EPOCHS * len(SEEDS) + 600)
    info.update({"estimate_hours": est / 3600, "status": "WITHIN_2H" if est <= 2 * 3600 else "AMENDMENT_REQUIRED",
                 "technical_only": True, "scores": None, "environment": environment()})
    write_json(out / "blanc.json", info)
    print("D3_BLANC_DONE_NO_SCORE")


def stage_complet(a):
    blank = json.loads(Path(a.blank).read_text())
    require(sha(a.blank) == a.blank_sha256 and blank["status"] == "WITHIN_2H", "reviewed blank missing")
    env = environment()
    tested = {k: blank["environment"][k] for k in ("device", "gpu", "torch", "cuda", "numpy", "scipy", "python")}
    require(tested == {k: env[k] for k in tested}, "complet_environment_differs_from_the_reviewed_blank")
    data = Data(a.encoder, a.inventory, a.diag)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "s0.json", s0(data))
    rows = list(range(len(data.val)))
    nn, cos = data.neighbours(rows)
    dup = int(sum(len({data.md5[data.fit[j]] for j in r}) < K for r in nn))
    b_m = measures(data, rows, data.b_pred, d3.rare_target(data.vocab, data.n_raw))
    arm, rare = arm1(data, nn, cos, rows, VOTE_WEIGHT)
    perm, _ = arm1(data, nn, cos, rows, VOTE_WEIGHT, permuted=True)
    m1, mp = measures(data, rows, arm, rare), measures(data, rows, perm, rare)
    positives = sum(1 for y in data.truth for c in set(y) if c in set(rare))  # (image, code) couples [G6]
    g = d3.rule_g(m1["H"], b_m["H"], m1["E"], b_m["E"])
    if g:
        r = None
    elif not rare:
        r = "indisponible_R_vide"  # P9-A 8.2: an empty R makes the rare route unavailable, no new definition
    else:
        r = d3.route_r(m1["F_R"], b_m["F_R"], m1["H"], b_m["H"], m1["E"], b_m["E"], positives)
    el = [k for k in rows if data.truth[k]]
    groups_el = [data.vmd5[k] for k in el]
    bh = d3.bootstrap_groups({"arm": m1["h_per_image"], "perm": mp["h_per_image"], "B": b_m["h_per_image"]}, groups_el)
    be = d3.bootstrap_groups({"arm": m1["e_per_image"], "B": b_m["e_per_image"]}, groups_el)
    bf = boot_fr([data.truth[k] for k in rows], {"arm": arm, "B": data.b_pred}, [data.vmd5[k] for k in rows], rare) \
        if rare else None
    ci = lambda v: [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))]
    near = np.array([cos[k, 0] >= 0.95 for k in el])
    gain = np.array(m1["h_per_image"]) - np.array(b_m["h_per_image"])
    lec = data.lec
    strip = lambda m: {k: v for k, v in m.items() if k not in ("h_per_image", "e_per_image")}
    write_json(out / "bras1.json", {
        "B": strip(b_m), "arm": strip(m1), "permuted_memory_witness": strip(mp),
        "witness_reading": "same visual weights, labels moved: its expectation is a prior on R; not a second judge",
        "verdict": {"G": g, "R": r, "rare_positive_couples": positives},
        "bootstrap": {"seed": BOOT_SEED, "draws": 10_000, "unit": "md5 group", "method": "percentile",
                      "H_arm_minus_B": ci(bh["arm"] - bh["B"]), "H_perm_minus_B": ci(bh["perm"] - bh["B"]),
                      "E_arm_minus_B": ci(be["arm"] - be["B"]), "F_R_arm_minus_B": ci(bf["arm"] - bf["B"]) if bf else None},
        "V_lecture": {"arm": strip(measures(data, lec, [arm[k] for k in lec], rare)),
                      "B": strip(measures(data, lec, [data.b_pred[k] for k in lec], rare))},
        "proximity_cos_ge_0_95": {"images": int(near.sum()), "share": float(near.mean()),
                                  "gain_contribution_near": float(gain[near].sum() / len(el)),
                                  "gain_contribution_far": float(gain[~near].sum() / len(el)),
                                  "reading": "strong proximity, not proof of copying"},
        "neighbour_lists_with_repeated_md5": dup})
    # arm 2
    fam, children, parent_of, masks = arm2_structures(data)
    mask, y = masks([data.labels[i] for i in data.fit])
    reg, lec = data.reg, data.lec
    mreg, yreg = masks([data.labels[data.val[k]] for k in reg])
    b_reg = d3.child_counts([data.truth[k] for k in reg], [data.b_pred[k] for k in reg], children,
                            gates_for(data, reg, children, parent_of))
    b_lec_gates = gates_for(data, lec, children, parent_of)
    b_lec = d3.child_counts([data.truth[k] for k in lec], [data.b_pred[k] for k in lec], children, b_lec_gates)
    b_lec_h = measures(data, lec, [data.b_pred[k] for k in lec], rare)
    check_identity(b_reg, "B_Vreg")
    check_identity(b_lec, "B_Vlec")
    seeds = {}
    for seed in SEEDS:
        layer, hist = train_head(data.xf, mask, y, seed, x_reg=data.xv[reg], mask_reg=mreg, y_reg=yreg)
        sc_reg, sc_lec = scores(layer, data.xv[reg]), scores(layer, data.xv[lec])
        curves = {}
        for t in THRESHOLDS:
            o, gts = arm2_outputs(data, reg, sc_reg, children, parent_of, t)
            curves[t] = d3.child_counts([data.truth[k] for k in reg], o, children, gts)
            check_identity(curves[t], f"seed{seed}_t{t}")
        t_star, flagged = d3.choose_t(curves, b_reg["precision"], THRESHOLDS)
        o_lec, g_lec = arm2_outputs(data, lec, sc_lec, children, parent_of, t_star)
        c_lec = d3.child_counts([data.truth[k] for k in lec], o_lec, children, g_lec)
        check_identity(c_lec, f"seed{seed}_Vlec")
        m_lec = measures(data, lec, o_lec, rare)
        seeds[seed] = {"history": hist, "t": t_star, "t_flagged_no_precision": flagged,
                       "t_flag_reason": None if not flagged else ("B_emits_no_child_precision_undefined"
                                                                  if b_reg["precision"] is None else
                                                                  "no_t_reaches_B_precision"),
                       "Vreg_curves": {str(t): v for t, v in curves.items()}, "Vlec_children": c_lec,
                       "Vlec_pipeline": strip(m_lec), "freq_depth": freq_depth(data, lec, o_lec, g_lec, children),
                       "G": d3.rule_g(m_lec["H"], b_lec_h["H"], m_lec["E"], b_lec_h["E"])}
    # an undefined conditional or precision (None) never establishes an improved descent
    descent = all(None not in (s["Vlec_children"]["conditional_recall"], b_lec["conditional_recall"],
                               s["Vlec_children"]["precision"], b_lec["precision"]) and
                  s["Vlec_children"]["conditional_recall"] - b_lec["conditional_recall"] >= 0.02 and
                  s["Vlec_children"]["precision"] >= b_lec["precision"] - 0.01 for s in seeds.values())
    write_json(out / "bras2.json", {
        "families": len(fam), "children": len(children), "B_Vlec_children": b_lec, "B_Vreg_children": b_reg,
        "B_Vlec_pipeline": strip(b_lec_h), "B_freq_depth": freq_depth(data, lec, [data.b_pred[k] for k in lec],
                                                                       b_lec_gates, children),
        "seeds": seeds, "descent_improved_descriptive": descent,
        "G_retained_all_three_seeds": all(s["G"] for s in seeds.values()),
        "counting": COUNTING, "conditional_reading": CONDITIONAL_READING, "environment": env})
    print("D3_COMPLET_DONE")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("blanc", "complet"), required=True)
    for k in ("encoder", "inventory", "diag", "out"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--blank")
    p.add_argument("--blank-sha256")
    args = p.parse_args()
    try:
        {"blanc": stage_blanc, "complet": stage_complet}[args.stage](args)
    except RuntimeError as e:
        print(f"D3_FAILED {e}", file=sys.stderr)
        sys.exit(1)
