"""Non-transfer diagnostic, pure part (numpy only): per (image, truth code) pair, is the code reached by the frozen head T*,
by the weighted vote of its 20 training neighbours (TK), by 20 random training images (prevalence control)? Descriptive.

Inputs per bank (built by nt_run.py): projected truths, T* exact sets and probabilities, TK exact sets and mixed scores,
neighbour weights/indices, random indices; training ancestor sets within V; raw per-image training counts n_brut.
Fixed before any computation (PREINSCRIPTION.md): V, n_brut on the 81 951 training rows, historical depth, projection
without 86, K = 20, the main target G = {c in V, n_brut(c) > 100, depth(c) >= 3}, the frequency x depth cells.
"""
from collections import defaultdict
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesure_metrics as mm  # noqa: E402  (pinned copy of the phase-1 measures: ancestors, depth, tranches)

FREQ = ("5-20", "21-100", ">100")
DEPTH = mm.TRANCHES3
MAIN = "G: n_brut > 100 and depth >= 3"


def cell(code, vocab_set, counts):
    """(frequency tranche, depth tranche) of a truth code, or None outside V (no fixed head can emit it)."""
    if code not in vocab_set:
        return None
    return mm.frequency_tranche(counts.get(code, 0)), mm.tranche3(mm.depth(code))


def in_main(c):
    return c is not None and c[0] == ">100" and c[1] in ("3-4", "5+")


def neighbour_available(code_index, neighbour_sets, weights):
    """The code is in the closure (within V) of at least one neighbour of POSITIVE weight."""
    return any(w > 0 and code_index in s for w, s in zip(weights, neighbour_sets))


def pair_records(bank, vocab, counts, ancestor_sets, tk_threshold, star_threshold):
    """One record per (image, distinct projected truth code in V). bank keys: truths, star, star_prob, tk, tk_score,
    nn_weight, nn_index, rand_index, groups, vote. Probabilities, scores and votes are rows over vocab (float32).
    Threshold events use the EFFECTIVE vote of TK (bank["vote"], gel_predictions.votes, float32) against the threshold
    in its dtype (B1, Codex p4: a float64 reconstruction of 10 equal weights out of 20 gives 0.49999999999999994 where
    TK's float32 matrix gives 0.5000000596); the independent reconstruction is kept apart as an oracle."""
    vi = {c: j for j, c in enumerate(vocab)}
    vset = set(vocab)
    star_t = np.float32(star_threshold)
    records = []
    for i, truth in enumerate(bank["truths"]):
        star, tk = set(bank["star"][i]), set(bank["tk"][i])
        star_cl, tk_cl = mm.closure(star), mm.closure(tk)
        w = np.asarray(bank["nn_weight"][i], dtype=np.float64)
        total = max(float(w.clip(min=0).sum()), 1e-9)
        nsets = [ancestor_sets[j] for j in bank["nn_index"][i]]
        rsets = [ancestor_sets[j] for j in bank["rand_index"][i]]
        for c in dict.fromkeys(truth):
            k = cell(c, vset, counts)
            if k is None:
                continue
            j = vi[c]
            reconstructed = sum(max(x, 0.0) / total for x, s in zip(w, nsets) if j in s)
            effective = bank["vote"][i][j]
            records.append({
                "image": i, "group": bank["groups"][i], "code": c, "cell": k, "main": in_main(k),
                "head_closure": c in star_cl, "head_exact": c in star,
                "head_above_threshold": bool(bank["star_prob"][i][j] >= star_t),
                "vote_available": neighbour_available(j, nsets, w), "vote": float(effective),
                "vote_reconstructed": reconstructed, "vote_reconstructed_at_tk_threshold": reconstructed >= tk_threshold,
                "vote_alone_at_tk_threshold": bool(effective >= np.asarray(tk_threshold, dtype=np.asarray(effective).dtype)),
                "tk_closure": c in tk_cl, "tk_exact": c in tk,
                "tk_above_threshold": bool(bank["tk_score"][i][j] >= np.float32(tk_threshold)),
                "random_available": any(j in s for s in rsets),
                "random_vote": sum(j in s for s in rsets) / len(rsets),
            })
    return records


EVENTS = ("head_closure", "head_exact", "head_above_threshold", "vote_available", "vote_alone_at_tk_threshold",
          "tk_closure", "tk_exact", "tk_above_threshold", "random_available")


def summary(records):
    """Pooled recalls over (image, code) pairs: sum of successes / sum of |G_i|; mean vote values; paired table."""
    n = len(records)
    if not n:
        return {"pairs": 0, "images": 0}
    out = {"pairs": n, "images": len({r["image"] for r in records}),
           "recall": {e: sum(r[e] for r in records) / n for e in EVENTS},
           "vote_mean": float(np.mean([r["vote"] for r in records])),
           "random_vote_mean": float(np.mean([r["random_vote"] for r in records])),
           "vote_deciles": [float(x) for x in np.quantile([r["vote"] for r in records], np.linspace(0.1, 0.9, 9))]}
    out["paired_head_closure_x_vote_available"] = {
        "both": sum(r["head_closure"] and r["vote_available"] for r in records),
        "head_only": sum(r["head_closure"] and not r["vote_available"] for r in records),
        "vote_only": sum(not r["head_closure"] and r["vote_available"] for r in records),
        "neither": sum(not r["head_closure"] and not r["vote_available"] for r in records)}
    out["threshold_to_most_specific"] = {
        "above_threshold": sum(r["head_above_threshold"] for r in records),
        "above_threshold_not_emitted_exactly": sum(r["head_above_threshold"] and not r["head_exact"] for r in records),
        "emitted_exactly": sum(r["head_exact"] for r in records),
        "reached_by_closure_only": sum(r["head_closure"] and not r["head_exact"] for r in records),
        "tk_above_threshold": sum(r["tk_above_threshold"] for r in records),
        "tk_above_threshold_not_emitted_exactly": sum(r["tk_above_threshold"] and not r["tk_exact"] for r in records)}
    out["vote_oracle"] = {"max_gap": max(abs(r["vote"] - r["vote_reconstructed"]) for r in records),
                          "threshold_decisions_differing": sum(r["vote_reconstructed_at_tk_threshold"] != r["vote_alone_at_tk_threshold"]
                                                               for r in records),
                          "read_as": "events use TK's effective float32 vote; the float64 reconstruction is an oracle"}
    return out


def cross_table(records):
    """frequency (5-20, 21-100, >100) x depth (1-2, 3-4, 5+), every cell published with its support."""
    by = defaultdict(list)
    for r in records:
        by[r["cell"]].append(r)
    return {f"{f}|{d}": summary(by[(f, d)]) for f in FREQ for d in DEPTH}


def per_code(records):
    by = defaultdict(list)
    for r in records:
        by[r["code"]].append(r)
    return {c: {"pairs": len(v), "head_closure": float(np.mean([r["head_closure"] for r in v])),
                "head_exact": float(np.mean([r["head_exact"] for r in v])),
                "vote_available": float(np.mean([r["vote_available"] for r in v])),
                "vote_mean": float(np.mean([r["vote"] for r in v]))} for c, v in sorted(by.items())}


def common_codes(codes_a, codes_b, event):
    """Macro mean over the codes of G present in BOTH banks, equal weight per code (fixed before computation);
    a code absent from one bank is not evaluable there and is left out, never counted as zero."""
    common = sorted(set(codes_a) & set(codes_b))
    if not common:
        return {"codes": 0}
    return {"codes": len(common), "a": float(np.mean([codes_a[c][event] for c in common])),
            "b": float(np.mean([codes_b[c][event] for c in common]))}


def bootstrap(records, n_images, groups_of_images, draws, seed, events=("head_closure", "head_exact", "vote_available",
              "vote_alone_at_tk_threshold", "random_available")):
    """Ratio estimator (successes / pairs) under resampling of whole groups (Rijksmuseum components, ICAI md5 groups);
    the same draws for every event, so differences between events are paired. Percentile, descriptive."""
    uniq, inverse = np.unique(np.asarray(groups_of_images), return_inverse=True)
    img_group = inverse
    pairs = np.bincount(img_group[[r["image"] for r in records]], minlength=len(uniq)).astype(float) if records else None
    hits = {e: np.bincount(img_group[[r["image"] for r in records]], weights=[float(r[e]) for r in records],
                           minlength=len(uniq)) for e in events} if records else {}
    rng = np.random.default_rng(seed)
    acc = defaultdict(list)
    for _ in range(draws if records else 0):
        w = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        n = float((w * pairs).sum())
        vals = {e: float((w * hits[e]).sum()) / n if n else float("nan") for e in events}
        for e in events:
            acc[e].append(vals[e])
        acc["vote_available-head_closure"].append(vals["vote_available"] - vals["head_closure"])
        acc["vote_available-random_available"].append(vals["vote_available"] - vals["random_available"])
    def ci(v):
        v = np.asarray(v, dtype=float)
        ok = v[np.isfinite(v)]
        interval = ([float(np.quantile(ok, 0.025, method="linear")), float(np.quantile(ok, 0.975, method="linear"))]
                    if len(ok) else None)
        return {"ci95": interval, "defined_draws": int(len(ok)), "undefined_draws": int(len(v) - len(ok))}
    # a draw with no target pair has an undefined ratio: counted and left out, never read as a value
    return {"unit": "group", "groups": int(len(uniq)), "images": int(n_images), "draws": draws, "seed": seed,
            "method": "percentile, numpy quantile method linear, descriptive", "intervals": {k: ci(v) for k, v in acc.items()}}


def bank_report(bank, vocab, counts, ancestor_sets, recipe, draws, seed):
    recs = pair_records(bank, vocab, counts, ancestor_sets, recipe["tk_threshold"], recipe["star_threshold"])
    main = [r for r in recs if r["main"]]
    with_target = {r["image"] for r in main}
    return recs, {
        "images": len(bank["truths"]), "images_without_main_target": len(bank["truths"]) - len(with_target),
        "main": {"definition": MAIN, **summary(main),
                 "bootstrap": bootstrap(main, len(bank["truths"]), bank["groups"], draws, seed)},
        "cross_table": cross_table(recs), "per_code_main": per_code(main),
        "outside_vocabulary_pairs": sum(1 for t in bank["truths"] for c in dict.fromkeys(t) if c not in set(vocab))}
