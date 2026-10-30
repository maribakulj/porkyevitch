"""Phase 1 measures and verdicts, pure functions (numpy only). Every rule is the architecture preregistration's
(~/porkyevitch/experiences/2026-10-25-iconclass-architecture/PREINSCRIPTION.md, sha 5115c3a5...); nothing is chosen here.
"""
import re

import numpy as np

# ---- T's functions, unchanged (E3 transcription; exact = remote_iconclass_head.py) ----
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


def drop86(codes):
    return [c for c in codes if not c.strip().startswith("86")]


def exact(gts, preds):
    tp = sum(len(set(g) & set(p)) for g, p in zip(gts, preds, strict=True))
    npred, ngt = sum(len(set(p)) for p in preds), sum(len(set(g)) for g in gts)
    pr, rc = tp / max(npred, 1), tp / max(ngt, 1)
    return {"precision": pr, "recall": rc, "f1": 0 if pr + rc == 0 else 2 * pr * rc / (pr + rc)}


# ---- Family, level, verdict ----
FAMILY = [("T_star", "T0"), ("TK", "T_star"), ("T-niv", "T_star"), ("TK-niv", "T_star"),
          ("T-H", "T_star"), ("T-Z", "T_star"), ("T-D", "T_star")]
CONDITIONAL = "TK-niv"  # executed only if TK and T-niv are both retained
LEVEL = 1 - 0.05 / 7    # one-sided Bonferroni bound, ~99.29 %
DRAWS = 10_000


def comparison_name(brick, ref):
    return f"{brick}-{ref}"


def retained(low_rijks, low_icai):
    """Retained iff one-sided lower bound of Delta_Rijks > 0 AND of Delta_ICAI > -0.01 (both required)."""
    return bool(low_rijks > 0 and low_icai > -0.01)


def tk_niv_active(verdicts):
    return bool(verdicts["TK"]["retained"] and verdicts["T-niv"]["retained"])


# ---- Paired bootstrap ----
def unit_draws(n_units, draws=DRAWS, seed=0):
    """Counts matrix (draws x units): how many times each unit is drawn, units drawn with replacement."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_units, (draws, n_units))
    counts = np.zeros((draws, n_units), dtype=np.int32)
    for d in range(draws):
        counts[d] = np.bincount(idx[d], minlength=n_units)
    return counts


def unit_sums(values, unit_of, n_units):
    """Sum of per-image values and number of images per unit (component, or image itself)."""
    s = np.zeros(n_units)
    n = np.zeros(n_units)
    np.add.at(s, unit_of, values)
    np.add.at(n, unit_of, 1)
    return s, n


def bootstrap_delta(f_brick, f_ref, unit_of, counts):
    """Per draw: mean per image over the images of the drawn units (with multiplicity), brick minus ref.
    The same counts are used for every system of a bank (paired)."""
    n_units = counts.shape[1]
    sb, n = unit_sums(np.asarray(f_brick, float), unit_of, n_units)
    sr, _ = unit_sums(np.asarray(f_ref, float), unit_of, n_units)
    denom = counts @ n
    return (counts @ sb - counts @ sr) / denom


def summarise(delta_point, draws):
    return {"delta": float(delta_point),
            "lower_one_sided_99_29": float(np.quantile(draws, 1 - LEVEL)),
            "ci95_two_sided": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
            "draws": int(len(draws)), "quantile_method": "numpy linear"}


# ---- Planche (dev): 12 images with the largest |hF1 brick - hF1 ref|, ties by identifier ----
def planche(ids, f_brick, f_ref, n=12):
    order = sorted(range(len(ids)), key=lambda i: (-abs(f_brick[i] - f_ref[i]), ids[i]))
    return [ids[i] for i in order[:n]]


# ---- Secondary measures and diagnostic D ----
def depth(code):
    return len(ancestors(code))


def tranche3(d):
    return "1-2" if d <= 2 else "3-4" if d <= 4 else "5+"


TRANCHES3 = ("1-2", "3-4", "5+")


def closure(codes):
    return set().union(*map(ancestors, codes)) if codes else set()


def depth_f1(gts, preds):
    """Per tranche: F1 between truth and prediction ancestors restricted to the tranche, on images whose truth has an
    ancestor in the tranche; an image without prediction in the tranche counts 0. Mean over those images."""
    out = {}
    for t in TRANCHES3:
        vals = []
        for g, p in zip(gts, preds, strict=True):
            G = {a for a in closure(g) if tranche3(depth(a)) == t}
            if not G:
                continue
            P = {a for a in closure(p) if tranche3(depth(a)) == t}
            vals.append(0.0 if not P else 2 * len(G & P) / (len(G) + len(P)))
        out[t] = {"f1": float(np.mean(vals)) if vals else None, "images": len(vals)}
    return out


def ancestor_recall_by_tranche(gts, preds):
    """D(1): pooled recall of the truth's ancestors, per tranche of depth."""
    out = {}
    for t in TRANCHES3:
        hit = tot = 0
        for g, p in zip(gts, preds, strict=True):
            G = {a for a in closure(g) if tranche3(depth(a)) == t}
            hit += len(G & closure(p))
            tot += len(G)
        out[t] = {"recall": hit / tot if tot else None, "truth_ancestors": tot}
    return out


def rare_recall(gts, preds, rare):
    """Share of (image, rare truth code) pairs whose code is among the prediction's ancestors."""
    pairs = hits = 0
    for g, p in zip(gts, preds, strict=True):
        cp = closure(p)
        for c in set(g):
            if c in rare:
                pairs += 1
                hits += c in cp
    return {"recall": hits / pairs if pairs else None, "pairs": pairs}


def frequency_tranche(n):
    return "5-20" if 5 <= n <= 20 else "21-100" if 21 <= n <= 100 else ">100" if n > 100 else "<5"


def f1_by_frequency(gts, preds, counts):
    """D(2): pooled exact-code F1 per tranche of training images (5-20, 21-100, >100); truth codes outside V and
    codes seen fewer than 5 times form '<5'."""
    acc = {t: [0, 0, 0] for t in ("5-20", "21-100", ">100", "<5")}
    for g, p in zip(gts, preds, strict=True):
        g, p = set(g), set(p)
        for c in g | p:
            t = frequency_tranche(counts.get(c, 0))
            acc[t][0] += c in g and c in p
            acc[t][1] += c in p and c not in g
            acc[t][2] += c in g and c not in p
    return {t: {"tp": tp, "fp": fp, "fn": fn, "f1": 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None}
            for t, (tp, fp, fn) in acc.items()}


def coverage(gts, vocab):
    """D(3): share of truth codes outside the vocabulary, per image (mean) and per (image, code) pair, and distinct."""
    v = set(vocab)
    per_image = [sum(c not in v for c in set(g)) / len(set(g)) for g in gts if g]
    pairs = [(c not in v) for g in gts for c in set(g)]
    distinct = {c for g in gts for c in g}
    return {"per_image_mean": float(np.mean(per_image)) if per_image else None,
            "per_pair": float(np.mean(pairs)) if pairs else None,
            "distinct_codes": len(distinct), "distinct_outside": sum(c not in v for c in distinct)}


def codes_per_tranche(gts, preds):
    """D(4): mean number of emitted codes per image by depth tranche of the code itself, prediction against truth."""
    out = {}
    for t in TRANCHES3:
        out[t] = {"predicted": float(np.mean([sum(tranche3(depth(c)) == t for c in set(p)) for p in preds])),
                  "truth": float(np.mean([sum(tranche3(depth(c)) == t for c in set(g)) for g in gts]))}
    return out


def by_support(f, supports):
    out = {}
    for s in sorted(set(supports)):
        vals = [x for x, t in zip(f, supports, strict=True) if t == s]
        out[s] = {"hier_f1": float(np.mean(vals)), "images": len(vals)}
    return out
