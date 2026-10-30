"""Descriptive measures of where a frozen Iconclass head loses points. Pure Python/numpy, no torch.

Parser, most_specific, drop86 and hier_f1 are exact transcriptions of E3 (e3_spatial.py:108-141).
Conventions of tranches and per-code F1 follow the P9-A preregistration, section 8.
"""
from collections import Counter, defaultdict
import re

import numpy as np

PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
TOKEN = re.compile(r"\([^)]*\)|[A-Z]{1,2}|\d")
TRANCHES = ("0", "1-4", "5-20", "21-100", "101-1000", ">1000")
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


def exact_f1(gt, pred):
    # P9-A 8.1: raw projected codes, no closure; empty prediction gives 0.
    if not pred or not gt:
        return 0.0
    return 2 * len(set(gt) & set(pred)) / (len(set(gt)) + len(set(pred)))


def most_specific(codes):
    codes = list(dict.fromkeys(codes))
    implied = set()
    for c in codes:
        implied |= ancestors(c) - {c}
    return [c for c in codes if c not in implied]


def drop86(codes):
    return [c for c in codes if not c.strip().startswith("86")]


def closure(codes):
    return set().union(*map(ancestors, codes)) if codes else set()


def project(prob, vocab, thresholds):
    # Historical order: threshold (>=), most_specific, then drop86. thresholds: scalar or per-code vector.
    thresholds = np.broadcast_to(np.asarray(thresholds, dtype=prob.dtype), (prob.shape[1],))
    return [drop86(most_specific([vocab[j] for j in np.flatnonzero(row >= thresholds)])) for row in prob]


def tranche(n):
    if n == 0:
        return "0"
    if n <= 4:
        return "1-4"
    if n <= 20:
        return "5-20"
    if n <= 100:
        return "21-100"
    if n <= 1000:
        return "101-1000"
    return ">1000"


def depth(code):
    # Number of prefix nodes of a simple notation; composite notations (A:B) form their own bucket.
    return "composite" if ":" in code else len(ancestors(code))


def per_code_counts(gts, preds):
    tp, fp, fn = Counter(), Counter(), Counter()
    for g, p in zip(gts, preds, strict=True):
        g, p = set(g), set(p)
        for c in g & p:
            tp[c] += 1
        for c in p - g:
            fp[c] += 1
        for c in g - p:
            fn[c] += 1
    return tp, fp, fn


def f1(tp, fp, fn):
    return 0.0 if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn)


def tranche_table(gts, preds, n_brut, universe):
    """Per tranche of training raw frequency: codes, represented codes, positives, TP/FP/FN, macro and micro F1.

    universe is fixed before scores (training raw codes, V and validation truths, without 86). A code absent
    from the validation truth stays in the macro denominator (F_c = 0 when 2TP+FP+FN = 0).
    """
    tp, fp, fn = per_code_counts(gts, preds)
    rows = {}
    for t in TRANCHES:
        codes = sorted(c for c in universe if tranche(n_brut.get(c, 0)) == t)
        if not codes:
            rows[t] = "not_applicable"
            continue
        T, F, N = (sum(x[c] for c in codes) for x in (tp, fp, fn))
        rows[t] = {"codes": len(codes), "represented": sum(1 for c in codes if tp[c] + fn[c] > 0),
                   "positives": sum(tp[c] + fn[c] for c in codes), "tp": T, "fp": F, "fn": N,
                   "macro_f1": float(np.mean([f1(tp[c], fp[c], fn[c]) for c in codes])), "micro_f1": f1(T, F, N),
                   "macro_f1_represented": float(np.mean([f1(tp[c], fp[c], fn[c]) for c in codes if tp[c] + fn[c] > 0]))
                   if any(tp[c] + fn[c] > 0 for c in codes) else "not_applicable"}
    stray = sum(x[c] for x in (tp, fp, fn) for c in x if c not in universe)
    rows["outside_universe_counts"] = stray  # must be 0: every predicted or true code is in the universe
    return rows


def node_depth_table(gts, preds):
    # Hierarchical view: every node of the closures, grouped by its own depth.
    tp, fp, fn = Counter(), Counter(), Counter()
    for g, p in zip(gts, preds, strict=True):
        G, P = closure(g), closure(p)
        for a in G & P:
            tp[depth(a)] += 1
        for a in P - G:
            fp[depth(a)] += 1
        for a in G - P:
            fn[depth(a)] += 1
    keys = sorted(set(tp) | set(fp) | set(fn), key=lambda d: (isinstance(d, str), d))
    return {str(d): {"tp": tp[d], "fp": fp[d], "fn": fn[d],
                     "precision": tp[d] / (tp[d] + fp[d]) if tp[d] + fp[d] else "not_applicable",
                     "recall": tp[d] / (tp[d] + fn[d]) if tp[d] + fn[d] else "not_applicable",
                     "f1": f1(tp[d], fp[d], fn[d])} for d in keys}


def stop_depths(gts, preds):
    """For each true raw code not predicted exactly: its depth and the depth of its deepest simple ancestor
    present in the prediction closure (0 if none). Returns counts of (true depth, stop depth)."""
    table = Counter()
    for g, p in zip(gts, preds, strict=True):
        P, exact = closure(p), set(p)
        for y in set(g) - exact:
            reached = [len(ancestors(a)) for a in ancestors(y) & P if ":" not in a]
            table[(str(depth(y)), max(reached) if reached else 0)] += 1
    return [{"true_depth": d, "stop_depth": s, "count": n} for (d, s), n in sorted(table.items())]


def confident_absent(prob, vocab, gts, identities, threshold=0.9, size=100, per_image=2, seed=1030):
    """Sample of (image, code) with p >= threshold, code most specific among those >= threshold, outside 86,
    and absent from the truth closure. Identifiers, code and probability only; no truth is returned."""
    index = {c: j for j, c in enumerate(vocab)}
    candidates = []
    for i, (row, g) in enumerate(zip(prob, gts, strict=True)):
        G = closure(g)
        for c in drop86(most_specific([vocab[j] for j in np.flatnonzero(row >= threshold)])):
            if c not in G:
                candidates.append((i, c, float(row[index[c]])))
    order = np.random.default_rng(seed).permutation(len(candidates))
    taken, per = [], Counter()
    for k in order:
        i, c, p = candidates[k]
        if per[i] < per_image:
            per[i] += 1
            taken.append({**identities[i], "code": c, "p": p})
        if len(taken) == size:
            break
    return {"candidates": len(candidates), "images_with_candidates": len({i for i, _, _ in candidates}),
            "sample": taken}


def mean_hier(gts, preds):
    return float(np.mean([hier_f1(g, p) for g, p in zip(gts, preds, strict=True)]))


def tranche_threshold_coordinate_ascent(prob, vocab, code_tranche, gts, start, grid, passes=2):
    """Score adjusted on the measured validation by coordinate ascent: one threshold per frequency tranche
    (fixed tranche order, fixed grid, ties keep the current value). At least the starting score, but NOT an
    upper bound: neither of the best point of the same grid nor of any future gain. Optimistic for
    generalisation, since it is tuned on the set it scores. Never a production threshold."""
    tranche_of = np.array([TRANCHES.index(code_tranche[c]) for c in vocab])
    current = {t: start for t in TRANCHES}
    best = mean_hier(gts, project(prob, vocab, start))
    trace = [{"step": "start", "thresholds": dict(current), "hf1": best}]
    for sweep in range(passes):
        for t in TRANCHES:
            if not (tranche_of == TRANCHES.index(t)).any():
                continue
            for value in grid:
                trial = dict(current, **{t: value})
                vector = np.array([trial[TRANCHES[k]] for k in tranche_of], dtype=prob.dtype)
                score = mean_hier(gts, project(prob, vocab, vector))
                if score > best:
                    best, current = score, trial
            trace.append({"step": f"pass{sweep}:{t}", "thresholds": dict(current), "hf1": best})
    return {"hf1_adjusted_coordinate_ascent": best, "thresholds": current, "trace": trace}


def group_bootstrap(values_by_system, groups, draws=1000, seed=0):
    """Paired bootstrap over md5 groups of per-image values. Descriptive 95 % intervals."""
    uniq, inverse = np.unique(np.asarray(groups), return_inverse=True)
    rng = np.random.default_rng(seed)
    sums = {k: np.bincount(inverse, weights=np.asarray(v, dtype=float), minlength=len(uniq))
            for k, v in values_by_system.items()}
    sizes = np.bincount(inverse, minlength=len(uniq))
    out = defaultdict(list)
    for _ in range(draws):
        w = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        n = float((w * sizes).sum())
        for k, s in sums.items():
            out[k].append(float((w * s).sum()) / n)
    return {k: {"mean": float(np.mean(values_by_system[k])),
                "ci95": [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))]} for k, v in out.items()}


def error_overlap(gts, preds_a, preds_b, h_a, h_b):
    """Correlation of errors between two systems on the same images (here T* and T-Z, both C-RADIO)."""
    fn_a, fn_b, fp_a, fp_b = set(), set(), set(), set()
    for i, (g, a, b) in enumerate(zip(gts, preds_a, preds_b, strict=True)):
        g = set(g)
        fn_a |= {(i, c) for c in g - set(a)}
        fn_b |= {(i, c) for c in g - set(b)}
        fp_a |= {(i, c) for c in set(a) - g}
        fp_b |= {(i, c) for c in set(b) - g}
    jac = lambda x, y: len(x & y) / len(x | y) if x | y else "not_applicable"
    h_a, h_b = np.asarray(h_a), np.asarray(h_b)
    defined = h_a.std() > 0 and h_b.std() > 0
    return {"pearson_per_image_hf1": float(np.corrcoef(h_a, h_b)[0, 1]) if defined else "not_defined_constant_scores",
            "jaccard_missed_codes": jac(fn_a, fn_b), "jaccard_false_codes": jac(fp_a, fp_b),
            "both_below_0.3": int(((h_a < 0.3) & (h_b < 0.3)).sum()),
            "only_a_below_0.3": int(((h_a < 0.3) & (h_b >= 0.3)).sum()),
            "only_b_below_0.3": int(((h_a >= 0.3) & (h_b < 0.3)).sum())}
