"""P9-A scientific series: selection, measures, bootstrap and verdicts. numpy only (no torch, no data access).

Every rule is the preregistration's (sha 25f1040f..., sections 7 to 9); this module only implements them.
"""
import numpy as np

from p9a_common import ancestors, code_f1, drop86, most_specific, require

ALPHAS = (0.25, 0.5, 1.0)
THETAS = tuple(round(0.05 * k, 2) for k in range(1, 20))
EPOCHS = 10
B_THRESHOLD = 0.65
TIE = 1e-12
BOOT_SEED, BOOT_DRAWS = 20261029, 10_000
ARM_ORDER = {0: ("F", "controle_global", "A", "C"), 1: ("controle_global", "A", "C", "F"),
             2: ("A", "C", "F", "controle_global")}
TRANCHES = (("0", 0, 0), ("1-4", 1, 4), ("5-20", 5, 20), ("21-100", 21, 100), (">100", 101, None))
RARE_SUPPORT_MIN = 100


# ---- Section 7: B envelope and mixing in intensity space ----
def envelope(prob, parents, levels):
    """b_c = max over descendants d of c (c included) of p_B,d, clipped to [1e-7, 1-1e-7]; returns L^B = -log1p(-b)."""
    b = np.array(prob, dtype=np.float64, copy=True)
    for level in reversed(levels):
        for c in level:
            for p in parents[c]:
                np.maximum(b[:, p], b[:, c], out=b[:, p])
    b = np.clip(b, 1e-7, 1 - 1e-7)
    return -np.log1p(-b)


def mix(LB, Lh, alpha):
    require(alpha in ALPHAS, "mix is only for alpha > 0; alpha = 0 returns frozen B")
    return -np.expm1(-((1 - alpha) * LB + alpha * np.asarray(Lh, dtype=np.float64)))


def predict(prob, vocab, theta):
    """Threshold p >= theta, then most_specific, then drop86 (E3 order)."""
    return [drop86(most_specific([vocab[j] for j in np.flatnonzero(row >= theta)])) for row in prob]


class Truth:
    """Projected truths and their closures, computed once."""
    def __init__(self, labels):
        self.y = [drop86(y) for y in labels]
        self.eligible = [i for i, y in enumerate(self.y) if y]
        self.closure = [set().union(*map(ancestors, y)) if y else set() for y in self.y]


def fast_h(truth, i, pred):
    g = truth.closure[i]
    if not pred or not g:
        return 0.0
    p = set().union(*map(ancestors, pred))
    k = len(g & p)
    return 0.0 if k == 0 else 2 * k / (len(g) + len(p))


def mean_h(truth, rows, preds):
    """Mean H-F1 over the eligible rows among `rows` (positions in truth); preds aligned with rows."""
    vals = [fast_h(truth, i, p) for i, p in zip(rows, preds, strict=True) if truth.y[i]]
    return float(np.mean(vals))


def epoch_grid(LB_reg, Lh_reg, vocab, truth, reg_rows, epoch):
    """The 57 candidates of one epoch on V-reglage: (alpha, theta) -> H-F1."""
    out = []
    for alpha in ALPHAS:
        p = mix(LB_reg, Lh_reg, alpha)
        for theta in THETAS:
            out.append({"alpha": alpha, "epoch": epoch, "theta": theta,
                        "H_Vreg": mean_h(truth, reg_rows, predict(p, vocab, theta))})
    return out


def select(candidates):
    """Best V-reglage H-F1; ties within 1e-12: lowest alpha, then earliest epoch, then lowest theta.
    candidates must hold exactly the reference (alpha 0, B threshold) and the 570 grid points."""
    ref = [c for c in candidates if c["alpha"] == 0]
    require(len(ref) == 1 and ref[0]["theta"] == B_THRESHOLD and ref[0]["epoch"] is None, "reference candidate")
    grid = [c for c in candidates if c["alpha"] != 0]
    require(len(grid) == EPOCHS * len(ALPHAS) * len(THETAS) == 570, "grid of 570")
    require(len({(c["alpha"], c["epoch"], c["theta"]) for c in grid}) == 570, "duplicate candidates")
    best = max(c["H_Vreg"] for c in candidates)
    tied = [c for c in candidates if c["H_Vreg"] >= best - TIE]
    return min(tied, key=lambda c: (c["alpha"], -1 if c["epoch"] is None else c["epoch"], c["theta"]))


# ---- Section 8: measures ----
def exact_e(gt, pred):
    if not pred or not gt:
        return 0.0
    return 2 * len(set(gt) & set(pred)) / (len(set(gt)) + len(set(pred)))


def measures(truth, preds, rare, universe, n_raw, vocab):
    """H and E on the eligible rows; F_R and tranches on all rows (empty truths as negatives)."""
    el = truth.eligible
    h = [fast_h(truth, i, preds[i]) for i in el]
    e = [exact_e(truth.y[i], preds[i]) for i in el]
    fr = code_f1(truth.y, preds, rare)
    represented = [c for c in rare if any(c in y for y in truth.y)]
    tranches = {}
    for name, lo, hi in TRANCHES:
        codes = [c for c in universe if n_raw.get(c, 0) >= lo and (hi is None or n_raw.get(c, 0) <= hi)]
        tranches[name] = code_f1(truth.y, preds, codes) if codes else "not_applicable"
    v = set(vocab)
    return {"H": float(np.mean(h)), "E": float(np.mean(e)), "eligible": len(el), "F_R": fr["macro_F1"], "rare": fr,
            "F_R_represented_descriptive": code_f1(truth.y, preds, represented)["macro_F1"] if represented else None,
            "tranches": tranches, "codes_predicted_mean": float(np.mean([len(preds[i]) for i in el])),
            "truth_outside_V_share": float(np.mean([c not in v for i in el for c in set(truth.y[i])]))}


# ---- Section 9: verdicts ----
def verdict(m_arm, m_b, alpha):
    dH, dE, dR = m_arm["H"] - m_b["H"], m_arm["E"] - m_b["E"], m_arm["F_R"] - m_b["F_R"]
    g = bool(alpha > 0 and dH >= 0.005 and dE >= -0.01)
    r = bool(not g and alpha > 0 and dR > 0 and dH >= -0.005 and dE >= -0.01)
    label = "G" if g else "R" if r else ("reference_conservee" if alpha == 0 else "non_retenue")
    return {"verdict": label, "delta_H": dH, "delta_E": dE, "delta_F_R": dR, "alpha": alpha}


def mechanism(v_a, vdiag, rare_occ_vdiag):
    """9.3 on V-diagnostic. v_a: A's verdict against B (full validation); vdiag: {arm: measures on V-diagnostic}."""
    a, g = vdiag["A"], vdiag["controle_global"]
    general = bool(v_a["verdict"] == "G" and a["H"] - g["H"] >= 0.003)
    if rare_occ_vdiag < RARE_SUPPORT_MIN:
        rare = "indecidable_support_Vdiag_below_100"
    else:
        rare = bool(v_a["verdict"] in ("G", "R") and a["F_R"] - g["F_R"] > 0 and a["H"] - g["H"] >= -0.005)
    return {"general_local_nesting_supported": general, "rare_local_nesting_supported": rare,
            "A_minus_G_H_Vdiag": a["H"] - g["H"], "A_minus_G_F_R_Vdiag": a["F_R"] - g["F_R"],
            "A_minus_F_H_Vdiag": a["H"] - vdiag["F"]["H"], "A_minus_C_H_Vdiag": a["H"] - vdiag["C"]["H"],
            "rare_positive_occurrences_Vdiag": rare_occ_vdiag,
            "reading": "A beating F but not G is a hierarchical recipe, not local nesting; CSRA better is said"}


# ---- Section 9.4: paired bootstrap by md5 groups ----
def group_draws(n_groups, draws=BOOT_DRAWS, seed=BOOT_SEED, block=500):
    """Yields blocks of counts (block x groups): multiplicity of each group in each draw. Same for all systems."""
    rng = np.random.default_rng(seed)
    done = 0
    while done < draws:
        k = min(block, draws - done)
        idx = rng.integers(0, n_groups, (k, n_groups))
        counts = np.zeros((k, n_groups), dtype=np.int32)
        for d in range(k):
            counts[d] = np.bincount(idx[d], minlength=n_groups)
        yield counts
        done += k


def group_tables(truth, preds, rows, group_of, n_groups, rare):
    """Per group: sums of H and E over eligible rows, eligible count, and TP/FP/FN of every rare code."""
    from scipy.sparse import lil_matrix
    ri = {c: k for k, c in enumerate(rare)}
    sh, se, n = np.zeros(n_groups), np.zeros(n_groups), np.zeros(n_groups)
    tp, fp, fn = (lil_matrix((n_groups, len(rare)), dtype=np.float64) for _ in range(3))
    for i in rows:
        g = group_of[i]
        y, p = set(truth.y[i]), set(preds[i])
        if truth.y[i]:
            sh[g] += fast_h(truth, i, preds[i])
            se[g] += exact_e(truth.y[i], preds[i])
            n[g] += 1
        for c in y & p:
            if c in ri:
                tp[g, ri[c]] += 1
        for c in p - y:
            if c in ri:
                fp[g, ri[c]] += 1
        for c in y - p:
            if c in ri:
                fn[g, ri[c]] += 1
    # Sparse: rare codes are rare. Counts stay exact integers in float64.
    return {"H": sh, "E": se, "n": n, "tp": tp.tocsr(), "fp": fp.tocsr(), "fn": fn.tocsr()}


def draw_stats(t, counts):
    """H, E and F_R (full fixed R, zero convention) for each draw of a block."""
    counts = np.asarray(counts, dtype=np.float64)
    n = counts @ t["n"]
    tp, fp, fn = ((t[k].T @ counts.T).T for k in ("tp", "fp", "fn"))
    den = 2 * tp + fp + fn
    f = np.divide(2 * tp, den, out=np.zeros(den.shape, dtype=float), where=den != 0)
    return {"H": (counts @ t["H"]) / n, "E": (counts @ t["E"]) / n, "F_R": f.mean(1)}


def summarise(values):
    v = np.asarray(values)
    return {"mean": float(v.mean()), "ci95": [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))],
            "quantiles": {q: float(np.quantile(v, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}, "draws": len(v)}


# ---- Section 11.4: plates after the freeze ----
def plate_rows(truth, preds_arm, preds_b, where, n=12):
    """12 eligible validation rows with the largest |H_i(arm) - H_i(B)|; ties: (shard number, row) ascending."""
    diffs = [(abs(fast_h(truth, i, preds_arm[i]) - fast_h(truth, i, preds_b[i])), where[i], i) for i in truth.eligible]
    return [i for _, _, i in sorted(diffs, key=lambda x: (-x[0], x[1]))[:n]]
