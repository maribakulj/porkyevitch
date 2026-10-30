"""A3 — exactitude of the L1 lower bound of labelled FGW on the 178 accepted pilot graphs.

Reads only graphes/p*/g.json of the Gemini pilot (never verite.json, images or calls). Pure numpy, CPU,
light. Checks LB(G,G') <= E(T) for every unordered pair and several exactly feasible couplings T, then
describes tightness and simulates filter-and-refine top-10 against the frozen matcher. No verdict on
relevance, no Iconclass code read. See README.md for the rule written before running.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np

ALPHA = 0.5          # weight of the pair term
EPS = 0.05           # entropic step of the frozen matcher
OUTER, INNER = 10, 100
TOL_BOUND, TOL_EXACT = 1e-9, 1e-12
N_GRAPHS, TOP_K = 178, 10
FORBIDDEN = (Path.home() / "porkyevitch", Path.home() / "lermolieff")


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def norm(text):
    # Λ v1, frozen before use: lower case, collapsed spaces; no synonym table; 0/1 name metric.
    return " ".join(str(text).lower().split())


class Graph:
    def __init__(self, gid, data):
        objects = data["objects"]
        require(len(objects) > 0, "empty_graph")
        index = {o["id"]: i for i, o in enumerate(objects)}
        require(len(index) == len(objects), "duplicate_object_id")
        self.gid, self.n = gid, len(objects)
        self.names = [norm(o["name"]) for o in objects]
        rels = collections.defaultdict(set)
        for subject, relation, obj in data["relations"]:
            require(subject in index and obj in index, "relation_to_unknown_object")
            rels[index[subject], index[obj]].add(norm(relation))
        self.types = [[(self.names[u], self.names[v],
                        "self" if u == v else "|".join(sorted(rels[u, v])) or "none")
                       for v in range(self.n)] for u in range(self.n)]
        self.mass = np.full(self.n, 1.0 / self.n)
        self.name_hist = {k: c / self.n for k, c in collections.Counter(self.names).items()}
        self.pair_hist = {k: c / self.n ** 2 for k, c in
                          collections.Counter(t for row in self.types for t in row).items()}

    def phi(self):
        # Sparse L1 embedding: star-tree Wasserstein on names (edge 1/2) and TV on pair types (mu = 1).
        out = {("n",) + (k,): (1 - ALPHA) * 0.5 * v for k, v in self.name_hist.items()}
        out.update({("p",) + k: ALPHA * 0.5 * v for k, v in self.pair_hist.items()})
        return out


def lower_bound(g, h):
    names = set(g.name_hist) | set(h.name_hist)
    pairs = set(g.pair_hist) | set(h.pair_hist)
    node = 0.5 * sum(abs(g.name_hist.get(k, 0) - h.name_hist.get(k, 0)) for k in names)
    pair = 0.5 * sum(abs(g.pair_hist.get(k, 0) - h.pair_hist.get(k, 0)) for k in pairs)
    return (1 - ALPHA) * node + ALPHA * pair


def lower_bound_inverted(phi_g, phi_h):
    # ||φ−φ'||₁ = |φ| + |φ'| − 2 Σ min(φ, φ') over shared coordinates only (inverted-list form).
    shared = sum(min(v, phi_h[k]) for k, v in phi_g.items() if k in phi_h)
    return sum(phi_g.values()) + sum(phi_h.values()) - 2 * shared


class Pair:
    def __init__(self, g, h):
        self.g, self.h = g, h
        self.D = np.array([[float(x != y) for y in h.names] for x in g.names])
        codes = {}
        ga = np.array([[codes.setdefault(t, len(codes)) for t in row] for row in g.types])
        hb = np.array([[codes.get(t, -1) for t in row] for row in h.types])
        self.blocks = [((ga == k).astype(float), (hb == k).astype(float)) for k in np.intersect1d(ga, hb[hb >= 0])]

    def energy(self, T):
        node = float((self.D * T).sum())
        matched = sum(float((P * (T @ Q @ T.T)).sum()) for P, Q in self.blocks)
        return (1 - ALPHA) * node + ALPHA * (1.0 - matched)

    def gradient(self, T):
        grad = (1 - ALPHA) * self.D
        for P, Q in self.blocks:
            grad = grad - ALPHA * (P @ T @ Q.T + P.T @ T @ Q)
        return grad


def energy_dense(g, h, T):
    # Independent 4-index evaluation, for small graphs only.
    D = np.array([[float(x != y) for y in h.names] for x in g.names])
    A, B = g.types, h.types
    C2 = np.array([[[[float(A[u][v] != B[s][t]) for t in range(h.n)] for s in range(h.n)]
                    for v in range(g.n)] for u in range(g.n)])
    return (1 - ALPHA) * float((D * T).sum()) + ALPHA * float(np.einsum("uvst,us,vt->", C2, T, T))


def sinkhorn(K, a, b, iterations):
    u = np.ones_like(a)
    for _ in range(iterations):
        v = b / np.maximum(K.T @ u, 1e-300)
        u = a / np.maximum(K @ v, 1e-300)
    return u[:, None] * K * v[None, :]


def round_feasible(F, a, b):
    # Altschuler, Weed, Rigollet (2017), algorithm 2: an exactly feasible coupling near F.
    F = F * np.minimum(a / np.maximum(F.sum(1), 1e-300), 1.0)[:, None]
    F = F * np.minimum(b / np.maximum(F.sum(0), 1e-300), 1.0)[None, :]
    er, ec = a - F.sum(1), b - F.sum(0)
    total = er.sum()
    return F + np.outer(er, ec) / total if total > 0 else F


def feasibility_error(T, a, b):
    return max(float(np.abs(T.sum(1) - a).max()), float(np.abs(T.sum(0) - b).max()), float(max(0.0, -T.min())))


def frozen_matcher(pair):
    # Deterministic KL-proximal mirror descent from the product coupling, then exact rounding.
    a, b = pair.g.mass, pair.h.mass
    T = np.outer(a, b)
    for _ in range(OUTER):
        G = pair.gradient(T)
        T = sinkhorn(T * np.exp(-(G - G.min()) / EPS), a, b, INNER)
    return round_feasible(T, a, b)


def random_coupling(a, b, seed):
    rng = np.random.default_rng(seed)
    return round_feasible(sinkhorn(rng.random((a.size, b.size)) + 1e-3, a, b, INNER), a, b)


def ranks(x):
    order = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[order] = np.arange(len(x))
    return r


def filter_and_refine(lb_row, s_row, k, tol=TOL_BOUND):
    # Multi-step k-NN: refine candidates by increasing LB until the next LB exceeds the k-th best S.
    # The bound is certified only up to tol (LB <= S + tol), so pruning needs LB > k-th S + tol: where the
    # bound is tight, LB exceeds S by a few ulps and a strict test drops a candidate tied with the k-th S.
    order = sorted(range(len(lb_row)), key=lambda j: (lb_row[j], j))
    best, refined = [], 0
    for j in order:
        if len(best) == k and lb_row[j] > best[-1][0] + tol:
            break
        refined += 1
        best = sorted(best + [(s_row[j], j)])[:k]
    return [j for _, j in best], refined


def load_graphs(root):
    root = Path(root).resolve(strict=True)
    files = sorted(root.glob("graphes/p*/g.json"))
    require(len(files) == N_GRAPHS, "expected_178_accepted_graphs")
    return [Graph(f.parent.name, json.loads(f.read_text())) for f in files], \
        {f.parent.name: sha(f) for f in files}


def run(graphs):
    start = time.monotonic()
    phis = [g.phi() for g in graphs]
    m = len(graphs)
    LB, S = np.zeros((m, m)), np.zeros((m, m))
    stats = collections.Counter()
    violations, worst = [], {"slack": np.inf}
    for i in range(m):
        for j in range(i + 1, m):
            g, h = graphs[i], graphs[j]
            pair = Pair(g, h)
            lb = lower_bound(g, h)
            require(abs(lb - lower_bound_inverted(phis[i], phis[j])) <= TOL_EXACT, "lb_forms_differ")
            matcher = frozen_matcher(pair)
            couplings = {"product": np.outer(g.mass, h.mass), "matcher": matcher,
                         "random0": random_coupling(g.mass, h.mass, 1_000_003 * i + j),
                         "random1": random_coupling(g.mass, h.mass, 2_000_003 * i + j)}
            for name, T in couplings.items():
                require(feasibility_error(T, g.mass, h.mass) <= TOL_EXACT, "coupling_not_feasible")
                e = pair.energy(T)
                require(np.isfinite(e) and np.isfinite(lb), "non_finite")
                if g.n <= 8 and h.n <= 8 and stats["dense_checked"] < 2000:
                    require(abs(e - energy_dense(g, h, T)) <= TOL_EXACT, "energy_forms_differ")
                    stats["dense_checked"] += 1
                stats["checks"] += 1
                slack = e - lb
                if slack < worst["slack"]:
                    worst = {"slack": slack, "pair": [g.gid, h.gid], "coupling": name}
                if lb > e + TOL_BOUND:
                    violations.append({"pair": [g.gid, h.gid], "coupling": name, "lb": lb, "energy": e})
            LB[i, j] = LB[j, i] = lb
            S[i, j] = S[j, i] = pair.energy(matcher)
            stats["pairs"] += 1
    iu = np.triu_indices(m, 1)
    lb_flat, s_flat = LB[iu], S[iu]
    ratio = lb_flat[s_flat > 0] / s_flat[s_flat > 0]
    spearman = float(np.corrcoef(ranks(lb_flat), ranks(s_flat))[0, 1])
    loo, avoided = [], []
    for q in range(m):
        others = [j for j in range(m) if j != q]
        lb_row, s_row = [LB[q, j] for j in others], [S[q, j] for j in others]
        top, refined = filter_and_refine(lb_row, s_row, TOP_K)
        exhaustive = [j for _, j in sorted((s_row[j], j) for j in range(len(others)))[:TOP_K]]
        loo.append(top == exhaustive)
        avoided.append(1 - refined / len(others))
    quantiles = lambda x: {f"q{int(p * 100):02d}": float(np.quantile(x, p)) for p in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1)}
    result = {"stage": "A3_exactitude_178", "alpha": ALPHA, "matcher": {"eps": EPS, "outer": OUTER, "inner": INNER},
              "tolerances": {"bound": TOL_BOUND, "exact": TOL_EXACT}, "graphs": m, "pairs": stats["pairs"],
              "checks": stats["checks"], "dense_checks": stats["dense_checked"], "violations": violations,
              "min_slack": worst, "bound_conforms": not violations,
              "top10_identical_queries": int(sum(loo)), "top10_identical_all": all(loo),
              "descriptive": {"lb_over_matcher": quantiles(ratio), "spearman_lb_matcher": spearman,
                              "refinements_avoided": quantiles(np.array(avoided))},
              "wall_seconds": time.monotonic() - start}
    return result


def main(args):
    out = Path(args.out).resolve()
    require(not any(out == f or f in out.parents for f in FORBIDDEN), "output_in_forbidden_repository")
    require(not out.exists() or not any(out.iterdir()), "output_not_empty")
    graphs, inputs = load_graphs(args.pilot)
    result = run(graphs)
    result.update({"inputs_sha256": inputs, "script_sha256": sha(__file__),
                   "versions": {"python": platform.python_version(), "numpy": np.__version__}})
    out.mkdir(parents=True, exist_ok=True)
    (out / "exactitude.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print("A3_BOUND_CONFORMS" if result["bound_conforms"] else "A3_BOUND_VIOLATED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True, help="~/porkyevitch-donnees/graphes-gemini/pilote")
    parser.add_argument("--out", required=True, help="empty folder, e.g. ~/porkyevitch-donnees/maths/a3-exactitude")
    try:
        main(parser.parse_args())
    except RuntimeError as error:
        print(f"A3_FAILED {error}", file=sys.stderr)
        sys.exit(1)
