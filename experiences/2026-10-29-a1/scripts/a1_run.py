"""A1 v2 on Kaggle CPU (one thread). Preregistration v2 sha ed452dc3...; Grok p2 notes 7.3 marked [G7.3].

Usage: a1_run.py --stage blanc|reglage|diagnostic --encoder ENC --inventory INV --diag DIAG --out OUT
                 [--blank BLANC_JSON --blank-sha256 S] [--reglage DIR --receipt RECU]
  ENC   full output of caypollard-encode-cradio v3 (train-* feats npz and grid json only; no grid tensor)
  INV   ENCODAGE_TRAIN_V3.json of P9-A (pinned sha) for the shard hashes
  DIAG  output of the kernel mabaku/porky-diag-run v3 (diagnostic.json, probabilites_validation.npz,
        identites_validation.json, vocabulaire.json)
blanc      : E0, B from the cache, E1-(i) on 8 V-reglage images, E1-(ii) on 64, timings and extrapolation. No score.
reglage    : E0, E1 complete, the 108-configuration grid on V-reglage, sealed reglage.json, then the E2 plate.
diagnostic : only after the plate receipt; one opening of V-diagnostic (E3), bootstrap by md5 groups.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_core as a1  # noqa: E402

TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
PREREG_SHA256 = "ed452dc3218028e33759151cbd0d8dd21038cd105b45492cb77964a673d3f383"
INVENTORY_SHA256 = "ff424e6453192f6465e23e3cdf9acf29aa5827d84565deb329de4c1b891a65d9"
DIAG_SHA256 = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
CACHE_SHA256 = "c7df9d3dd28acea7454cf7609cf083fe961fa5ff5a7ef121a85fc1d7c2eedbe9"
DECISIONS_SHA256 = "ea2502e101ed96a5bf13f00b014e204db9e3bf3d29ca0b32aa34406338d5e910"
B_H = 0.5890847528448202
SALT = "A1-2026-10-29|"
KS, TAUS, ETAS, PI0S = (16, 32, 64), (0.02, 0.05, 0.1), (0, 1, 2), (0, 0.25, 0.5, 0.75)
THRESHOLDS = tuple(round(0.05 * k, 2) for k in range(1, 20))
E1_CONFIG = {"K": 4, "tau": 0.05, "eta": 1, "pi0": 0.25}
BOOT_SEED, BOOT_DRAWS = 20261029, 10_000  # fixed here, percentile method (numpy linear) [G7.3]
TOL = 1e-9


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


def write_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False, default=float) + "\n")
    os.replace(tmp, path)


def versions():
    import scipy
    return {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
            "highs": "bundled with scipy " + scipy.__version__, "omp_threads": os.environ.get("OMP_NUM_THREADS")}


# ---------------------------------------------------------------- data
class Data:
    def __init__(self, enc, inventory, diag):
        enc, diag = Path(enc), Path(diag)
        require(sha(inventory) == INVENTORY_SHA256, "inventory_sha")
        inv = json.loads(Path(inventory).read_text())["files"]
        labels, md5, xs, where = [], [], [], []
        for s, tag in enumerate(TRAIN):
            for rel in (f"feats/{tag}.npz", f"grid/{tag}.json"):
                require(sha(enc / rel) == inv[rel], f"encoder_sha_{rel}")
            side = json.loads((enc / "grid" / f"{tag}.json").read_text())
            with np.load(enc / "feats" / f"{tag}.npz", allow_pickle=False) as z:
                m = [str(v) for v in z["md5"]]
                xs.append(np.asarray(z["x"]))
            require(len(m) == len(side["labels"]) and legacy_sha(m) == side["md5_sha256"], "alignment")
            labels += side["labels"]
            md5 += m
            where += [(tag, r) for r in range(len(m))]
        require(len(md5) == 86216, "rows")
        x = np.concatenate(xs).astype(np.float32)
        del xs
        groups = sorted(set(md5))
        gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
        self.fit = np.array([i for i, m in enumerate(md5) if m not in gval])
        self.val = np.array([i for i, m in enumerate(md5) if m in gval])
        require((len(self.fit), len(self.val)) == (81951, 4265), "split")
        self.raw = {}
        for i in self.fit:
            for c in set(labels[i]):
                self.raw[c] = self.raw.get(c, 0) + 1
        self.vocab = sorted({a for c, n in self.raw.items() if n >= 5 for a in a1.ancestors(c)})
        require(len(self.vocab) == 7907, "vocabulary")
        self.vi = {c: k for k, c in enumerate(self.vocab)}
        # diagnostic cache, read from the mounted porky-diag-run v3 output
        require(sha(diag / "diagnostic.json") == DIAG_SHA256, "diagnostic_sha")
        d = json.loads((diag / "diagnostic.json").read_text())
        for f in ("probabilites_validation.npz", "identites_validation.json", "vocabulaire.json"):
            require(sha(diag / f) == d["files_sha256"][f], f"diag_file_{f}")
        require(d["files_sha256"]["probabilites_validation.npz"] == CACHE_SHA256, "cache_identity")
        cache = d["probability_cache"]
        require(cache["dtype"] == "float32" and cache["systems"]["B_TZ"]["decisions_sha256"] == DECISIONS_SHA256 and
                cache["systems"]["B_TZ"]["threshold"] == 0.65, "cache_manifest")
        require(json.loads((diag / "vocabulaire.json").read_text()) == self.vocab and
                legacy_sha(self.vocab) == cache["vocabulary_sha256"], "cache_vocabulary")
        ids = json.loads((diag / "identites_validation.json").read_text())
        require(ids == [{"shard": where[i][0], "row": where[i][1], "md5": md5[i]} for i in self.val], "cache_rows")
        with np.load(diag / "probabilites_validation.npz", allow_pickle=False) as z:
            self.pb = np.asarray(z["B_TZ"])
        require(self.pb.shape == (4265, 7907) and self.pb.dtype == np.float32, "cache_shape")
        self.b_pred = a1.project(self.pb, self.vocab, 0.65)
        require(legacy_sha([sorted(q) for q in self.b_pred]) == DECISIONS_SHA256, "B_decisions_not_reproduced")
        self.truth = [a1.drop86(labels[i]) for i in self.val]
        self.eligible = [k for k, g in enumerate(self.truth) if g]
        require(len(self.eligible) == 4241, "eligible")
        self.h_b = float(np.mean([a1.hier_f1(self.truth[k], self.b_pred[k]) for k in self.eligible]))
        require(abs(self.h_b - B_H) <= 1e-6, "B_H_not_reproduced")
        self.labels, self.md5, self.where = labels, md5, where
        self.vmd5 = [md5[i] for i in self.val]
        self.reg = [k for k in range(4265) if hashlib.sha256((SALT + self.vmd5[k]).encode()).digest()[0] < 128]
        self.diag = [k for k in range(4265) if k not in set(self.reg)]
        require(not ({self.vmd5[k] for k in self.reg} & {self.vmd5[k] for k in self.diag}), "partition_md5")
        # neighbours: normalised vectors, dot product, ties by canonical fit order [G7.3 order of identities]
        xf, xv = x[self.fit], x[self.val]
        del x
        nf, nv = np.linalg.norm(xf, axis=1), np.linalg.norm(xv, axis=1)
        xf /= nf[:, None]
        xv /= nv[:, None]
        self.raw_tk_overlap = self.neighbours(xf, xv, nf, nv)
        del xf, xv
        self._fp = {}

    def neighbours(self, xf, xv, nf, nv, kmax=64):
        """Top-64 by cosine of normalised vectors, ties by fit order. Also: overlap of the top-20 with the raw dot
        product of the saved vectors (TK's recipe), published, not assumed."""
        self.nn = np.zeros((len(xv), kmax), dtype=np.int64)
        self.cos = np.zeros((len(xv), kmax))
        same20 = []
        for s in range(0, len(xv), 256):
            sim = xv[s:s + 256] @ xf.T
            raw = sim * nv[s:s + 256, None] * nf[None, :]  # dot product of the saved vectors (TK)
            for r in range(sim.shape[0]):
                row = sim[r]
                cut = np.partition(row, -kmax)[-kmax]
                cand = np.flatnonzero(row >= cut)
                order = cand[np.lexsort((cand, -row[cand]))][:kmax]
                self.nn[s + r], self.cos[s + r] = order, row[order]
                rr = raw[r]
                cut2 = np.partition(rr, -20)[-20]
                c2 = np.flatnonzero(rr >= cut2)
                same20.append(set(c2[np.lexsort((c2, -rr[c2]))][:20]) == set(order[:20]))
        return float(np.mean(same20))

    def footprint(self, j):
        if j not in self._fp:
            self._fp[j] = a1.closure(a1.drop86(self.labels[self.fit[j]]))
        return self._fp[j]


# ---------------------------------------------------------------- E0
def structure(data):
    vset = set(data.vocab)
    require(all(a1.ancestors(c) <= vset for c in data.vocab), "E0_c_V_not_closed")
    codes = set(data.vocab) | {a for j in range(len(data.fit)) for a in data.footprint(j)}
    for b in codes:
        ab = a1.ancestors(b)
        for a in ab:
            if a != b:
                aa = a1.ancestors(a)
                require(aa <= ab and len(aa) < len(ab), "E0_t_not_transitive_or_ordered")
    simple = [c for c in codes if ":" not in c]
    chain = sum(all(x <= y or y <= x for x in (a1.ancestors(a) for a in a1.ancestors(c))
                    for y in (a1.ancestors(a) for a in a1.ancestors(c))) for c in simple)
    n86 = {a for c in codes if ":" in c for a in a1.ancestors(c) if a1.non_emissible(a) and a != c}
    return {"codes_checked": len(codes), "simple_codes_chain_share": chain / len(simple),
            "nodes_86_as_composite_ancestors": len(n86), "c_closed": True, "t_transitive_ordered": True}


# ---------------------------------------------------------------- problems and decoding
class Image:
    """Everything of one validation image that does not depend on tau, eta, pi0."""
    def __init__(self, data, k, K):
        self.k = k
        self.t0 = a1.closure(data.b_pred[k])
        self.logits = a1.logit_clipped(data.pb[k])
        self.fps = [data.footprint(int(j)) for j in data.nn[k, :K]]
        self.cos = data.cos[k, :K]
        self.lbar = a1.lbar_of(self.fps, self.logits, data.vi)
        atoms, self.i0, self.idx = a1.atoms_for(self.t0, self.fps)
        self.pb = a1.Problem(self.t0, atoms, np.zeros(len(atoms)), set(data.vocab))
        self.n_distinct = len(atoms)

    def set_q(self, tau, eta, pi0):
        self.pb.q = a1.masses(len(self.pb.q), self.i0, self.idx, self.cos, self.lbar, tau, eta, pi0)
        return self.pb


def decode_checked(pb):
    out = a1.decode(pb)
    emitted_closure = a1.closure(out["emitted"])
    direct = pb.utility([pb.index[a] for a in emitted_closure if a in pb.index])
    require(abs(direct - out["value"]) <= TOL, "E1_iii_utility_of_emitted_closure")  # E1-(iii)
    return out


def e1_identity(data, rows, K, cfg):
    """E1-(i): for each k, sort = PLNE closure only; decoder = PLNE constrained for every k without pruning."""
    report = []
    for k in rows:
        img = Image(data, k, K)
        pb = img.set_q(cfg["tau"], cfg["eta"], cfg["pi0"])
        out = decode_checked(pb)
        best = 0.0
        for kk, val, _ in a1.flat_curve(pb):
            st, v, _, cert = a1.milp_k(pb, kk, emission=False)
            require(cert and abs(v - val) <= TOL, "E1_i_sort_vs_closure_plne")
            st2, v2, _, cert2 = a1.milp_k(pb, kk, emission=True)
            require(cert2, "E1_iv_plne_not_certified")
            if v2 is not None:
                best = max(best, v2)
        require(abs(best - out["value"]) <= TOL, "E1_i_decoder_vs_constrained_plne")
        report.append({"position": k, "U": len(pb.nodes), "value": out["value"], "path": out["path"]})
    return report


def e1_pi0_one(data, rows):
    """E1-(ii): pi0 = 1 gives exactly B's projected sets."""
    for k in rows:
        img = Image(data, k, 16)
        out = decode_checked(img.set_q(0.05, 1, 1.0))
        require(out["emitted"] == sorted(data.b_pred[k]), "E1_ii_pi0_one_not_B")
    return len(rows)


def grid_scores(data, rows, timer=None):
    """The 108 configurations on `rows`: mean H-F1 of the decoder over eligible rows; certification counts."""
    scores = {}
    for K in KS:
        images = [Image(data, k, K) for k in rows]
        for tau in TAUS:
            for eta in ETAS:
                for pi0 in PI0S:
                    hs, uncertified, solver = [], 0, 0
                    for img in images:
                        out = decode_checked(img.set_q(tau, eta, pi0))
                        uncertified += not out["certified"]
                        solver += out["path"] == "solver"
                        if data.truth[img.k]:
                            hs.append(a1.hier_f1(data.truth[img.k], out["emitted"]))
                    scores[(K, tau, eta, pi0)] = {"H": float(np.mean(hs)), "uncertified": uncertified, "solver": solver}
    return scores


def choose(scores):
    """Best mean H on V-reglage; ties: smaller K, then larger tau, then smaller eta, then larger pi0."""
    best = max(v["H"] for v in scores.values())
    tied = [c for c, v in scores.items() if v["H"] >= best - 1e-12]
    return min(tied, key=lambda c: (c[0], -c[1], c[2], -c[3]))


def threshold_all(data, rows, configs=None):
    """Threshold control 'same q' for every configuration and every t, on eligible `rows`: {cfg: {t: H}}."""
    out = {}
    for K in KS:
        images = [Image(data, k, K) for k in rows if data.truth[k]]
        for tau in TAUS:
            for eta in ETAS:
                for pi0 in PI0S:
                    cfg = (K, tau, eta, pi0)
                    if configs is not None and cfg not in configs:
                        continue
                    hs = {t: [] for t in THRESHOLDS}
                    for img in images:
                        pb = img.set_q(tau, eta, pi0)
                        for t in THRESHOLDS:
                            hs[t].append(a1.hier_f1(data.truth[img.k], a1.threshold_control(pb, t)))
                    out[cfg] = {t: float(np.mean(v)) for t, v in hs.items()}
    return out


def best_t(ts):
    best = max(ts.values())
    return min(t for t, v in ts.items() if v >= best - 1e-12)  # ties: smallest t (fixed here) [G7.3]


# ---------------------------------------------------------------- stages
def common(a):
    t0 = time.monotonic()
    data = Data(a.encoder, a.inventory, a.diag)
    out = Path(a.out)
    require(not out.exists() or not any(out.iterdir()), "output_not_empty")
    out.mkdir(parents=True, exist_ok=True)
    reg_rows = [k for k in data.reg]  # V-reglage in the order of identites_validation.json [G7.3]
    info = {"prereg_sha256": PREREG_SHA256, "versions": versions(), "counts": {
        "validation": 4265, "eligible": 4241, "Vreg": len(data.reg), "Vdiag": len(data.diag),
        "Vreg_eligible": sum(1 for k in data.reg if data.truth[k]), "Vdiag_eligible": sum(1 for k in data.diag if data.truth[k]),
        "md5_shared_between_halves": 0}, "B": {"H": data.h_b, "decisions_sha256": DECISIONS_SHA256},
        "recipe_vs_TK_top20_identical_share": data.raw_tk_overlap, "setup_s": time.monotonic() - t0}
    return data, out, reg_rows, info


def stage_blanc(a):
    data, out, reg, info = common(a)
    t0 = time.monotonic()
    info["E0"] = structure(data)
    info["E0_s"] = time.monotonic() - t0
    t0 = time.monotonic()
    info["E1_i_8"] = e1_identity(data, reg[:8], E1_CONFIG["K"], E1_CONFIG)
    info["E1_i_8_s"] = time.monotonic() - t0
    t0 = time.monotonic()
    info["E1_ii_64"] = e1_pi0_one(data, reg[:64])
    info["E1_ii_64_s"] = time.monotonic() - t0
    # timings for the extrapolation only: 16 V-reglage images, every K, two configurations each; values discarded
    sample = reg[:16]
    t0 = time.monotonic()
    decodes = 0
    u_sizes = {}
    for K in KS:
        images = [Image(data, k, K) for k in sample]
        u_sizes[K] = [len(img.pb.nodes) for img in images]
        for cfg in ((0.05, 1, 0.25), (0.02, 2, 0)):
            for img in images:
                decode_checked(img.set_q(*cfg))
                decodes += 1
    per_decode = (time.monotonic() - t0) / decodes
    t0 = time.monotonic()
    threshold_all(data, sample, configs={(16, 0.05, 1, 0.25), (64, 0.02, 2, 0)})
    per_threshold_cfg_image = (time.monotonic() - t0) / (2 * len(sample))
    t1 = time.monotonic()
    e1_identity(data, reg[8:9], 64, E1_CONFIG)
    e1_k64_one = time.monotonic() - t1
    n_reg = len(reg)
    est = {"per_decode_s": per_decode, "grid_108_Vreg_s": per_decode * 108 * n_reg,
           "E1_full_s": info["E1_i_8_s"] / 8 * 64 + e1_k64_one * 16 + info["E1_ii_64_s"] / 64 * 4241,
           "threshold_controls_s": per_threshold_cfg_image * 108 * n_reg,
           "diagnostic_s": per_decode * 3 * len(data.diag) + 600}
    est["total_hours"] = (info["setup_s"] + info["E0_s"] + sum(v for k, v in est.items() if k.endswith("_s") and
                          k != "per_decode_s")) / 3600
    info.update({"U_sizes_sample": u_sizes, "estimate": est, "technical_only": True, "scores": None,
                 "status": "WITHIN_2H" if est["total_hours"] <= 2 else "AMENDMENT_REQUIRED"})
    write_json(out / "blanc.json", info)
    print("A1_BLANC_DONE_NO_SCORE")


def stage_reglage(a):
    data, out, reg, info = common(a)
    blank = json.loads(Path(a.blank).read_text())
    require(sha(a.blank) == a.blank_sha256 and blank["status"] == "WITHIN_2H" and
            blank["versions"] == info["versions"], "reviewed blank missing or other environment")
    info["E0"] = structure(data)
    info["E1_i_64"] = e1_identity(data, reg[:64], E1_CONFIG["K"], E1_CONFIG)
    info["E1_i_16_K64"] = e1_identity(data, reg[:16], 64, E1_CONFIG)
    info["E1_ii"] = e1_pi0_one(data, data.eligible)
    write_json(out / "structure.json", info["E0"])
    write_json(out / "identite.json", {k: info[k] for k in ("E1_i_64", "E1_i_16_K64", "E1_ii")})
    scores = grid_scores(data, reg)
    chosen = choose(scores)
    all_t = threshold_all(data, reg)
    ts = all_t[chosen]
    t_star = best_t(ts)
    # secondary analysis: the threshold control with its own best configuration q (same tie order, then smallest t)
    top = max(v for tc in all_t.values() for v in tc.values())
    tied = [(cfg, t) for cfg, tc in all_t.items() for t, v in tc.items() if v >= top - 1e-12]
    cfg2, t2 = min(tied, key=lambda x: (x[0][0], -x[0][1], x[0][2], -x[0][3], x[1]))
    secondary = (all_t[cfg2][t2], cfg2, t2)
    cfg_dict = lambda c: {"K": c[0], "tau": c[1], "eta": c[2], "pi0": c[3]}
    sealed = {"prereg_sha256": PREREG_SHA256, "scores_Vreg": [{**cfg_dict(c), **v} for c, v in scores.items()],
              "chosen": cfg_dict(chosen), "threshold_control": {"same_q": cfg_dict(chosen), "t": t_star, "scores": ts},
              "secondary_threshold_control": {**cfg_dict(secondary[1]), "t": secondary[2], "H_Vreg": secondary[0]},
              "B_H_Vreg": float(np.mean([a1.hier_f1(data.truth[k], data.b_pred[k]) for k in reg if data.truth[k]])),
              "versions": info["versions"], "V_diagnostic_opened": False}
    write_json(out / "reglage.json", sealed)
    # E2 plate: 12 V-reglage images drawn among groups by default_rng(1029); first row of each group, codes only
    groups = sorted({data.vmd5[k] for k in reg})
    picked = sorted(np.random.default_rng(1029).choice(len(groups), 12, replace=False).tolist())
    first = {}
    for k in reg:
        first.setdefault(data.vmd5[k], k)
    rows = []
    K, tau, eta, pi0 = chosen
    for g in picked:
        k = first[groups[g]]
        img = Image(data, k, K)
        pb = img.set_q(tau, eta, pi0)
        o = decode_checked(pb)
        u_b = pb.utility([pb.index[x] for x in a1.closure(data.b_pred[k]) if x in pb.index])
        rows.append({"position": k, "shard": data.where[data.val[k]][0], "row": data.where[data.val[k]][1],
                     "md5": data.vmd5[k], "B": sorted(data.b_pred[k]), "A1": o["emitted"],
                     "U_q_A1": o["value"], "U_q_B": u_b, "path": o["path"]})
    write_json(out / "planche.json", {"rule": "default_rng(1029) among V-reglage md5 groups, first row of the group",
                                      "rows": rows})
    body = "".join(f"<section><h3>{r['shard']} · ligne {r['row']} · {r['path']}</h3><p><b>B</b> (U sous q = "
                   f"{r['U_q_B']:.4f}) : {html.escape(', '.join(r['B']) or '(vide)')}</p><p><b>A1</b> (U sous q = "
                   f"{r['U_q_A1']:.4f}) : {html.escape(', '.join(r['A1']) or '(vide)')}</p></section>" for r in rows)
    (out / "planche.html").write_text("<!doctype html><meta charset='utf-8'><title>A1 planche E2</title><h1>A1, "
                                      "planche E2 (12 images de V-réglage, codes et utilités sous q ; aucune vérité, "
                                      "aucun score)</h1>" + body)
    files = sorted(p for p in out.rglob("*") if p.is_file())
    write_json(out / "MANIFEST_REGLAGE.json", {"files": {str(p.relative_to(out)): sha(p) for p in files},
                                               "script_sha256": {n: sha(Path(__file__).parent / n)
                                                                 for n in ("a1_run.py", "a1_core.py")}})
    print("A1_REGLAGE_SEALED_VDIAG_CLOSED")


def code_f1(truth, pred, codes):
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
    return {"codes": len(ix), "macro_F1": float(f.mean()) if len(ix) else None}


def stage_diagnostic(a):
    data, out, reg, info = common(a)
    rdir = Path(a.reglage)
    man = json.loads((rdir / "MANIFEST_REGLAGE.json").read_text())
    for rel, digest in man["files"].items():
        require(sha(rdir / rel) == digest, "reglage_output_changed")
    receipt = json.loads(Path(a.receipt).read_text())
    viewers = [x.get("viewer", "") for x in receipt.get("regards", []) if x.get("viewed_at")]
    require(receipt.get("stage") == "planche_a1_regardee" and
            receipt.get("reglage_manifest_sha256") == sha(rdir / "MANIFEST_REGLAGE.json") and
            any(v == "wA:p1" for v in viewers) and any(v.startswith("Grok") for v in viewers), "plate_not_viewed")
    sealed = json.loads((rdir / "reglage.json").read_text())
    require(sealed["prereg_sha256"] == PREREG_SHA256 and sealed["versions"] == info["versions"], "sealed_identity")
    c = sealed["chosen"]
    t_ctrl, sec = sealed["threshold_control"]["t"], sealed["secondary_threshold_control"]
    rows = data.diag
    a1_pred, ctrl, ctrl2, sort_w, paths, sizes, lat, first_cos = {}, {}, {}, {}, [], [], [], {}
    for k in rows:
        img = Image(data, k, c["K"])
        pb = img.set_q(c["tau"], c["eta"], c["pi0"])
        t0 = time.perf_counter()
        o = decode_checked(pb)
        lat.append(time.perf_counter() - t0)
        a1_pred[k], sort_w[k] = o["emitted"], o["sort_unconstrained_emitted"]
        paths.append((o["path"], o["certified"], o.get("residual_tie", False)))
        sizes.append(len(o["S"]))
        ctrl[k] = a1.threshold_control(pb, t_ctrl)
        img2 = Image(data, k, sec["K"])
        ctrl2[k] = a1.threshold_control(img2.set_q(sec["tau"], sec["eta"], sec["pi0"]), sec["t"])
        first_cos[k] = float(data.cos[k, 0])
    el = [k for k in rows if data.truth[k]]
    systems = {"A1": a1_pred, "threshold_same_q": ctrl, "threshold_own_q": ctrl2, "sort_unconstrained": sort_w,
               "B": {k: data.b_pred[k] for k in rows}}
    H = {s: np.array([a1.hier_f1(data.truth[k], p[k]) for k in el]) for s, p in systems.items()}
    E = {s: np.array([a1.exact_e(data.truth[k], p[k]) for k in el]) for s, p in systems.items()}
    # paired bootstrap by md5 groups (V-diagnostic), same draws for every system
    gl = sorted({data.vmd5[k] for k in el})
    gi = {g: n for n, g in enumerate(gl)}
    unit = np.array([gi[data.vmd5[k]] for k in el])
    rng = np.random.default_rng(BOOT_SEED)
    nn = np.bincount(unit, minlength=len(gl)).astype(float)
    sums = {s: {m: np.bincount(unit, weights=v[s], minlength=len(gl)) for m, v in (("H", H), ("E", E))} for s in H}
    draws = {key: [] for key in ("mech", "gH", "gE")}
    for start in range(0, BOOT_DRAWS, 500):
        n = min(500, BOOT_DRAWS - start)
        counts = np.stack([np.bincount(rng.integers(0, len(gl), len(gl)), minlength=len(gl)) for _ in range(n)])
        denom = counts @ nn
        mean = lambda s, m: (counts @ sums[s][m]) / denom
        draws["mech"].append(mean("A1", "H") - mean("threshold_same_q", "H"))
        draws["gH"].append(mean("A1", "H") - mean("B", "H"))
        draws["gE"].append(mean("A1", "E") - mean("B", "E"))
    draws = {k: np.concatenate(v) for k, v in draws.items()}
    ci = lambda d: [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]
    d_mech = float(H["A1"].mean() - H["threshold_same_q"].mean())
    lo, hi = ci(draws["mech"])
    mechanism = "refute_dans_ce_regime" if hi < 0.003 else "mecanisme_utile" if d_mech >= 0.003 else "indecidable"
    dH, dE = float(H["A1"].mean() - H["B"].mean()), float(E["A1"].mean() - E["B"].mean())
    candidate = dH >= 0.005 and dE >= -0.01
    near = np.array([first_cos[k] >= 0.95 for k in el])
    gain = H["A1"] - H["B"]
    share_near = float(gain[near].sum() / gain.sum()) if gain.sum() > 0 else None
    concentrated = bool(candidate and share_near is not None and share_near > 0.5 and near.mean() < 0.2)
    path_counts = {p: sum(1 for x in paths if x[0] == p) for p in ("empty", "sort_certified", "solver", "solver_empty")}
    tranches = {}
    universe = sorted(set(a1.drop86(list(set(data.raw) | set(data.vocab) | {c for k in rows for c in data.truth[k]}))))
    for name, lo_n, hi_n in (("0", 0, 0), ("1-4", 1, 4), ("5-20", 5, 20), ("21-100", 21, 100), (">100", 101, None)):
        codes = [x for x in universe if data.raw.get(x, 0) >= lo_n and (hi_n is None or data.raw.get(x, 0) <= hi_n)]
        tranches[name] = {s: code_f1([data.truth[k] for k in rows], [p[k] for k in rows], codes) for s, p in systems.items()}
    write_json(out / "diagnostic.json", {
        "V_diagnostic_images": len(rows), "eligible": len(el), "groups": len(gl),
        "H": {s: float(v.mean()) for s, v in H.items()}, "E": {s: float(v.mean()) for s, v in E.items()},
        "mechanism": {"delta": d_mech, "ci95": [lo, hi], "case": mechanism, "order": "H<0.003, then delta>=0.003"},
        "product_rule_G": {"delta_H": dH, "delta_E": dE, "ci95_H": ci(draws["gH"]), "ci95_E": ci(draws["gE"]),
                           "candidate": candidate},
        "proximity_stratum_cos_ge_0_95": {"images": int(near.sum()), "share_images": float(near.mean()),
                                          "weighted_contribution_near": float(gain[near].sum() / len(el)),
                                          "weighted_contribution_far": float(gain[~near].sum() / len(el)),
                                          "gains_far": int((gain[~near] > 0).sum()),
                                          "losses_far": int((gain[~near] < 0).sum()),
                                          "gain_share": share_near, "gains": int((gain[near] > 0).sum()),
                                          "losses": int((gain[near] < 0).sum()),
                                          "not_recommended_if_candidate": concentrated,
                                          "reading": "strong proximity, not proof of copying"},
        "recommended": bool(candidate and not concentrated),
        "certification": {"paths": path_counts, "uncertified": sum(1 for x in paths if not x[1]),
                          "residual_ties": sum(1 for x in paths if x[2]),
                          "reading": "on uncertified images the result is the executed decoder, not a certified optimum"},
        "sort_witness": {"images_changed_by_emission_constraints": sum(1 for k in rows if a1_pred[k] != sort_w[k]),
                         "H_sort_unconstrained": float(H["sort_unconstrained"].mean())},
        "always": {"S_size_distribution": np.bincount(sizes).tolist(),
                   "codes_emitted_mean": float(np.mean([len(a1_pred[k]) for k in rows])),
                   "share_modified_vs_B": float(np.mean([a1_pred[k] != sorted(data.b_pred[k]) for k in rows])),
                   "latency_s": {"P50": float(np.quantile(lat, 0.5)), "P95": float(np.quantile(lat, 0.95)),
                                 "P99": float(np.quantile(lat, 0.99)), "threads": os.environ.get("OMP_NUM_THREADS")},
                   "tranches_F1": tranches},
        "bootstrap": {"seed": BOOT_SEED, "draws": BOOT_DRAWS, "unit": "md5 group", "method": "percentile, numpy linear"},
        "exploratory": True, "versions": info["versions"]})
    print("A1_DIAGNOSTIC_DONE")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("blanc", "reglage", "diagnostic"), required=True)
    for k in ("encoder", "inventory", "diag", "out"):
        p.add_argument(f"--{k}", required=True)
    for k in ("blank", "blank-sha256", "reglage", "receipt"):
        p.add_argument(f"--{k}")
    a = p.parse_args()
    try:
        {"blanc": stage_blanc, "reglage": stage_reglage, "diagnostic": stage_diagnostic}[a.stage](a)
    except RuntimeError as e:
        print(f"A1_FAILED {e}", file=sys.stderr)
        sys.exit(1)
