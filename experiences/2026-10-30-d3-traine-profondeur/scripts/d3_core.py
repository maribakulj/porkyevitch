"""D3, pure functions (numpy). Preregistration sha 4a4c0c63...; Grok p2 notes (section 6) marked [G6]."""
import re

import numpy as np

# ---- E3 transcription with PART and TOKEN [G6]
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
TOKEN = re.compile(r"\([^)]*\)|[A-Z]{1,2}|\d")
_anc = {}


def ancestors(code):
    code = code.strip()
    if code not in _anc:
        parts, out = code.split(":"), {code}
        if all(PART.fullmatch(p) for p in parts):
            for p in parts:
                cur = ""
                for t in TOKEN.findall(p):
                    cur += t
                    out.add(cur)
        _anc[code] = frozenset(out)
    return _anc[code]


def most_specific(codes):
    codes = list(dict.fromkeys(codes))
    implied = set()
    for c in codes:
        implied |= ancestors(c) - {c}
    return [c for c in codes if c not in implied]


def drop86(codes):
    return [c for c in codes if not c.strip().startswith("86")]  # strip() then prefix 86 [G6]


def is86(code):
    return code.strip().startswith("86")


def hier_f1(gt, pred):
    if not pred or not gt:
        return 0.0
    g, p = set().union(*map(ancestors, gt)), set().union(*map(ancestors, pred))
    i = len(g & p)
    return 0.0 if i == 0 else 2 * i / (len(g) + len(p))


def exact_e(gt, pred):
    if not pred or not gt:
        return 0.0
    return 2 * len(set(gt) & set(pred)) / (len(set(gt)) + len(set(pred)))


def closure(codes):
    return frozenset().union(*map(ancestors, codes)) if codes else frozenset()


def project(prob, vocab, threshold):
    """Threshold cast to the probabilities' dtype (as the diagnostic cache), >=, most_specific, drop86."""
    t = np.asarray(threshold, dtype=prob.dtype)
    return [drop86(most_specific([vocab[j] for j in np.flatnonzero(row >= t)])) for row in prob]


def code_f1(truth, pred, codes):
    """P9-A 8.2 convention: fixed code list, F_c = 0 when 2TP+FP+FN = 0."""
    ix = {c: i for i, c in enumerate(codes)}
    tp, fp, fn = (np.zeros(len(ix)) for _ in range(3))
    for g, p in zip(truth, pred, strict=True):
        g, p = set(g), set(p)
        for coll, arr in ((g & p, tp), (p - g, fp), (g - p, fn)):
            for c in coll:
                if c in ix:
                    arr[ix[c]] += 1
    den = 2 * tp + fp + fn
    f = np.divide(2 * tp, den, out=np.zeros(len(ix)), where=den != 0)
    return {"codes": len(ix), "supported": int(((tp + fn) > 0).sum()), "positive": int((tp + fn).sum()),
            "TP": int(tp.sum()), "FP": int(fp.sum()), "FN": int(fn.sum()),
            "macro_F1": float(f.mean()) if len(ix) else None,
            "micro_F1": float(2 * tp.sum() / den.sum()) if den.sum() else None}


# ---- S0: supports and emissibility ----
TRANCHES = (("0", 0, 0), ("1-4", 1, 4), ("5-20", 5, 20), ("21-100", 21, 100), ("101-1000", 101, 1000),
            (">1000", 1001, None))


def tranche(n):
    for name, lo, hi in TRANCHES:
        if n >= lo and (hi is None or n <= hi):
            return name


def depth_case(code):
    """Simple code: number of its prefix nodes (1..6, '7+'); composites form their own case [G6]."""
    if ":" in code:
        return "compose"
    d = len(ancestors(code))
    return str(d) if d <= 6 else "7+"


def s0_table(universe, vocab, n_raw, n_closed, val_truths):
    vset = set(vocab)
    sup_raw, sup_closed = {}, {}
    for y in val_truths:
        for c in set(y):
            sup_raw[c] = sup_raw.get(c, 0) + 1
        for c in closure(y):
            sup_closed[c] = sup_closed.get(c, 0) + 1
    cells = {}
    for c in universe:
        key = f"{tranche(n_raw.get(c, 0))}|{depth_case(c)}"
        cell = cells.setdefault(key, {"in_V": 0, "outside_V": 0, "n_raw": [], "n_closed": [], "val_raw": 0,
                                      "val_closed": 0})
        cell["in_V" if c in vset else "outside_V"] += 1
        cell["n_raw"].append(n_raw.get(c, 0))
        cell["n_closed"].append(n_closed.get(c, 0))
        cell["val_raw"] += sup_raw.get(c, 0)
        cell["val_closed"] += sup_closed.get(c, 0)
    for cell in cells.values():
        cell["n_raw_median"] = float(np.median(cell.pop("n_raw")))
        cell["n_closed_median"] = float(np.median(cell.pop("n_closed")))
    return cells


def rare_target(vocab, n_raw):
    return sorted(c for c in vocab if not is86(c) and 5 <= n_raw.get(c, 0) <= 20)


# ---- Arm 1: vote of the neighbours on R ----
def tk_weights(cos):
    w = np.clip(np.asarray(cos, dtype=np.float64), 0, None)
    s = w.sum()
    return w / s if s > 0 else w  # a zero sum gives a zero vote


def votes(nn_rows, cos, closures_of, rare_ix):
    """v_c = sum of the weights of the neighbours whose closed raw label contains c, for c in R only."""
    v = np.zeros(len(rare_ix))
    w = tk_weights(cos)
    for j, wj in zip(nn_rows, w):
        if wj == 0:
            continue
        for c in closures_of(int(j)):
            k = rare_ix.get(c)
            if k is not None:
                v[k] += wj
    return v


def mix_rare(p_row, v, rare_cols, weight):
    """s = (1 - weight) p_B + weight v on R, p_B elsewhere; weight 0 returns p_B unchanged (same dtype)."""
    s = np.array(p_row, copy=True)
    if weight:
        s[rare_cols] = ((1 - weight) * p_row[rare_cols].astype(np.float64) + weight * v).astype(s.dtype)
    return s


# ---- Arm 2: families, gate, routed decision ----
def direct_parent(code):
    """Simple code: proper ancestor with the most ancestors (prefixes form a chain); None for roots/composites."""
    if ":" in code:
        return None
    proper = [a for a in ancestors(code) if a != code]
    return max(proper, key=lambda a: len(ancestors(a))) if proper else None


def families(vocab, n_closed, parent_min=100, child_min=5):
    """{parent: [children]} by training supports only: n_closed(parent) >= 100 and >= 2 simple children in V,
    outside 86, with n_closed >= 5. Composites are excluded and stay with B."""
    kids = {}
    for c in vocab:
        if ":" in c or is86(c) or n_closed.get(c, 0) < child_min:
            continue
        p = direct_parent(c)
        if p is not None and p in set(vocab) and n_closed.get(p, 0) >= parent_min:
            kids.setdefault(p, []).append(c)
    return {p: sorted(cs) for p, cs in sorted(kids.items()) if len(cs) >= 2}


def routed_set(b_raw_codes, b_closure, scores, children, parent_of, t):
    """B's thresholded codes with every family child removed, plus the children whose parent is in the closure of
    B's projected set and whose head score is >= t; then most_specific and drop86."""
    child_set = set(children)
    keep = [c for c in b_raw_codes if c not in child_set]
    add = [c for k, c in enumerate(children) if parent_of[c] in b_closure and scores[k] >= t]
    return drop86(most_specific(keep + add))


def child_counts(truths, outputs, children, gates_open):
    """Exact-code counts on the family children, after most_specific and drop86, on every image of the lot [G6].
    gates_open[i]: set of children whose parent is in the closure of B's projected set for image i."""
    cs = set(children)
    n_true = n_gate = hit = fp = n_out = 0
    for y, o, g in zip(truths, outputs, gates_open, strict=True):
        ty, to = set(y) & cs, set(o) & cs
        n_true += len(ty)
        n_gate += len(ty & g)
        hit += len(ty & to)
        fp += len(to - ty)
        n_out += len(to)
    cov = n_gate / n_true if n_true else None
    cond = hit / n_gate if n_gate else None
    total = hit / n_true if n_true else None
    prec = hit / n_out if n_out else None
    f1 = 2 * hit / (n_true + n_out) if (n_true + n_out) else None
    return {"true_children": n_true, "gate_coverage": cov, "excluded_by_gate": n_true - n_gate,
            "conditional_recall": cond, "total_recall": total, "precision": prec, "F1": f1, "false_positives": fp,
            "emitted": n_out, "hits": hit}


def choose_t(curves, b_precision, grid):
    """Largest total recall among t with precision >= B's; ties: larger t; none: 0.95, flagged."""
    ok = [t for t in grid if curves[t]["precision"] is not None and curves[t]["precision"] >= b_precision]
    if not ok:
        return 0.95, True
    best = max(curves[t]["total_recall"] for t in ok)
    return max(t for t in ok if curves[t]["total_recall"] >= best - 1e-12), False


# ---- judges ----
def rule_g(h, h_b, e, e_b):
    return bool(h - h_b >= 0.005 and e - e_b >= -0.01)


def route_r(f_r, f_r_b, h, h_b, e, e_b, positives):
    if positives < 100:
        return "indecidable_moins_de_100_occurrences"
    return bool(f_r - f_r_b > 0 and h - h_b >= -0.005 and e - e_b >= -0.01)


def bootstrap_groups(values_by_system, groups, draws=10_000, seed=20261030):
    """Paired percentile bootstrap by md5 groups, same draws for every system (descriptive)."""
    uniq, inv = np.unique(np.asarray(groups), return_inverse=True)
    n = np.bincount(inv).astype(float)
    sums = {k: np.bincount(inv, weights=np.asarray(v, float)) for k, v in values_by_system.items()}
    rng = np.random.default_rng(seed)
    out = {k: [] for k in values_by_system}
    for start in range(0, draws, 500):
        m = min(500, draws - start)
        counts = np.stack([np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq)) for _ in range(m)])
        d = counts @ n
        for k in values_by_system:
            out[k].append((counts @ sums[k]) / d)
    return {k: np.concatenate(v) for k, v in out.items()}
