"""A1-dev, pure part (numpy only): per-image H-F1 contrasts of the frozen q-threshold rule against B (T-Z, main) and
T* (frozen reference) on the Rijksmuseum dev, paired bootstrap of whole components, the reading written in advance
(PREINSCRIPTION.md section 3). No choice, no threshold, nothing tuned here."""
from collections import defaultdict

import numpy as np

SEED, DRAWS = 20261034, 10_000


def component_bootstrap(per_image, components, draws=DRAWS, seed=SEED):
    """per_image: {name: array of per-image values (same images)}. Mean over the images of the drawn components (whole
    components with multiplicity), the same draws for every name; percentile 95 %, numpy linear; undefined draws (no
    image) counted and left out."""
    uniq, inverse = np.unique(np.asarray(components), return_inverse=True)
    sizes = np.bincount(inverse, minlength=len(uniq)).astype(float)
    sums = {k: np.bincount(inverse, weights=np.asarray(v, dtype=float), minlength=len(uniq)) for k, v in per_image.items()}
    rng = np.random.default_rng(seed)
    acc = defaultdict(list)
    for _ in range(draws):
        w = np.bincount(rng.integers(0, len(uniq), len(uniq)), minlength=len(uniq))
        n = float((w * sizes).sum())
        for k, s in sums.items():
            acc[k].append(float((w * s).sum()) / n if n else float("nan"))
    out = {}
    for k, v in acc.items():
        v = np.asarray(v)
        ok = v[np.isfinite(v)]
        out[k] = {"mean": float(np.mean(per_image[k])),
                  "ci95": ([float(np.quantile(ok, 0.025, method="linear")), float(np.quantile(ok, 0.975, method="linear"))]
                           if len(ok) else None),
                  "defined_draws": int(len(ok)), "undefined_draws": int(len(v) - len(ok))}
    return {"unit": "component", "components": int(len(uniq)), "images": int(len(components)), "draws": draws,
            "seed": seed, "method": "percentile, numpy quantile linear, paired (same draws for every contrast)",
            "contrasts": out}


def reading(contrast):
    """Section 3: exploratory signal of transfer iff delta > 0 and the lower bound of the 95 % interval > 0, strictly."""
    ci = contrast["ci95"]
    signal = contrast["mean"] > 0 and ci is not None and ci[0] > 0
    return {"signal_exploratoire_de_transfert": bool(signal),
            "read_as": ("signal exploratoire de transfert (exploratoire, ni test ni revendication confirmatoire)" if signal else
                        "transfert non établi : le gain d'A1 reste un gain de validation ICAI ; un intervalle contenant 0 "
                        "ne réfute pas toute amélioration")}


def strata(values, labels):
    """Descriptive means of per-image values by stratum label (support, proximity), no interval."""
    by = defaultdict(list)
    for v, s in zip(values, labels, strict=True):
        by[s].append(v)
    return {str(s): {"images": len(v), "mean": float(np.mean(v))} for s, v in sorted(by.items(), key=lambda x: str(x[0]))}


def gains_losses(rule, ref):
    d = np.asarray(rule, dtype=float) - np.asarray(ref, dtype=float)
    return {"gains": int((d > 0).sum()), "losses": int((d < 0).sum()), "ties": int((d == 0).sum())}
