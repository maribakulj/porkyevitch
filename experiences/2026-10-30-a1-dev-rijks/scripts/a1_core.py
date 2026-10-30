"""A1 v2 core: q from neighbours, GFM sort, certificate, exact constrained solver. numpy + scipy (HiGHS) only.

Preregistration v2 sha ed452dc3...; Grok p2 notes 7.3 are written in the code (marked [G7.3]).
"""
import re

import numpy as np

# ---- E3 transcription (e3_spatial.py:103-104 and 108-141): PART, TOKEN, ancestors, most_specific, drop86, hier_f1 [G7.3]
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
    return [c for c in codes if not c.strip().startswith("86")]


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


def non_emissible(code):
    return code.strip().startswith("86")  # same test as drop86 [G7.3]


def closure(codes):
    return frozenset().union(*map(ancestors, codes)) if codes else frozenset()


def project(prob, vocab, threshold):
    """B's projection as the diagnostic cache: threshold cast to the probabilities' dtype, >=, most_specific, drop86."""
    t = np.asarray(threshold, dtype=prob.dtype)
    return [drop86(most_specific([vocab[j] for j in np.flatnonzero(row >= t)])) for row in prob]


# ---- q: atoms and weights (section 4) ----
def logit_clipped(p):
    p = np.clip(np.asarray(p, dtype=np.float64), 1e-6, 1 - 1e-6)
    return np.log(p) - np.log1p(-p)


def lbar_of(footprints, logits_b, vi):
    """Mean over a in T_j ∩ V of B's clipped logit for this image; 0 if T_j ∩ V is empty."""
    out = []
    for t in footprints:
        inside = [vi[a] for a in t if a in vi]
        out.append(float(np.mean(logits_b[inside])) if inside else 0.0)
    return np.array(out)


def atoms_for(t0, footprints):
    """Distinct footprints (T0 included) in a deterministic order, and the atom index of T0 and of each neighbour."""
    atoms = sorted(set(footprints) | {t0}, key=lambda t: (len(t), sorted(t)))
    pos = {t: k for k, t in enumerate(atoms)}
    return atoms, pos[t0], [pos[t] for t in footprints]


def masses(n_atoms, i0, idx, cos, lbar, tau, eta, pi0):
    """q = pi0 delta_T0 + (1 - pi0) sum_j pi_j delta_Tj, pi_j ∝ exp(cos_j/tau + eta lbar_j) (stable softmax);
    identical footprints share one atom, their masses are summed (exact); zero masses are kept."""
    z = np.asarray(cos, dtype=np.float64) / tau + eta * np.asarray(lbar, dtype=np.float64)
    w = np.exp(z - z.max())
    w /= w.sum()
    q = np.zeros(n_atoms)
    q[i0] += pi0
    for k, m in zip(idx, w):
        q[k] += (1 - pi0) * m
    return q


def make_q(t0, footprints, cos, logits_b, vi, tau, eta, pi0):
    atoms, i0, idx = atoms_for(t0, footprints)
    return atoms, masses(len(atoms), i0, idx, cos, lbar_of(footprints, logits_b, vi), tau, eta, pi0)


class Problem:
    """Universe U = (T0 ∪ ⋃T_j) ∩ V, membership matrix, static tie key (depth, code)."""
    def __init__(self, t0, atoms, q, vocab_set):
        nodes = set(t0) | set().union(*atoms) if atoms else set(t0)
        self.nodes = sorted((a for a in nodes if a in vocab_set), key=lambda a: (len(ancestors(a)), a))
        self.index = {a: k for k, a in enumerate(self.nodes)}   # position = static rank (depth, then code)
        self.q = np.asarray(q, dtype=np.float64)
        self.sizes = np.array([len(t) for t in atoms], dtype=np.float64)
        self.member = np.zeros((len(atoms), len(self.nodes)), dtype=bool)
        for j, t in enumerate(atoms):
            for a in t:
                if a in self.index:
                    self.member[j, self.index[a]] = True
        self.n86 = np.array([non_emissible(a) for a in self.nodes], dtype=bool)
        # proper ancestors / descendants within U
        self.anc = [[self.index[b] for b in ancestors(a) if b != a and b in self.index] for a in self.nodes]
        self.desc = [[] for _ in self.nodes]
        for b, al in enumerate(self.anc):
            for a in al:
                self.desc[a].append(b)

    def weights(self, k):
        """w_a(k) = sum_j q_j 2 1[a in T_j] / (k + |T_j|), accumulated sequentially over atoms in a fixed order: an
        ancestor's sum holds a superset of its descendant's nonnegative terms, so w_ancestor >= w_descendant also in
        floating point, and identical memberships give identical weights."""
        w = np.zeros(len(self.nodes))
        for j in range(len(self.q)):
            if self.q[j] > 0:
                w += np.where(self.member[j], 2 * self.q[j] / (k + self.sizes[j]), 0.0)
        return w

    def utility(self, s_idx):
        """Direct GFM utility of a set of node indices: sum_j q_j 2 |S ∩ T_j| / (|S| + |T_j|); U(empty) = 0."""
        s = list(s_idx)
        if not s:
            return 0.0
        inter = self.member[:, s].sum(1)
        return float(np.sum(self.q * 2 * inter / (len(s) + self.sizes)))

    def bound(self, k):
        """Upper bound on U over sets of size k: |S ∩ T_j| <= min(k, |T_j ∩ U|)."""
        inside = self.member.sum(1)
        return float(np.sum(self.q * 2 * np.minimum(k, inside) / (k + self.sizes)))

    def top_k(self, k):
        w = self.weights(k)
        order = np.lexsort((np.arange(len(w)), -w))  # -w first, then static rank (depth, code)
        return order[:k], w

    def maximal(self, s_idx):
        s = set(int(i) for i in s_idx)
        return [i for i in s if not any(d in s for d in self.desc[i])]

    def is_closed(self, s_idx):
        s = set(int(i) for i in s_idx)
        return all(a in s for i in s for a in self.anc[i])


def flat_curve(pb, kmax=None):
    """U(S_k) for k = 1..kmax with S_k the k first of the sort (closed, optimal for closure alone)."""
    n = len(pb.nodes)
    kmax = n if kmax is None else min(n, kmax)
    out = []
    for k in range(1, kmax + 1):
        idx, w = pb.top_k(k)
        out.append((k, float(np.sum(w[idx])), idx))
    return out


def flat_optimum(pb):
    """k* = smallest argmax of U(S_k); the empty set if the best value is <= 0. Stops once k >= max |T_j ∩ U| and
    the bound of every larger k (decreasing there) is below the best."""
    n = len(pb.nodes)
    if n == 0:
        return 0, 0.0, np.array([], dtype=int)
    vmax = int(pb.member.sum(1).max()) if len(pb.q) else 0
    best = (0, 0.0, np.array([], dtype=int))
    for k in range(1, n + 1):
        if k > vmax and pb.bound(k) < best[1] - 1e-12:
            break
        idx, w = pb.top_k(k)
        val = float(np.sum(w[idx]))
        if val > best[1] + 1e-12:
            best = (k, val, idx)
    return best


# ---- exact constrained solver (HiGHS through scipy.optimize.milp) ----
def milp_k(pb, k, emission=True, w=None, tie_value=None, rank=None, exclude=None, rank_cap=None, time_limit=10.0):
    """max w(k).x s.t. sum x = k, closure (x_b <= x_a for every ancestor a of b in U), and if emission:
    x_a <= sum of its proper descendants for every non-emissible a. With tie_value: keep value >= tie_value and
    minimise sum rank(a) x_a (second PLNE, deterministic tie-break); exclude/rank_cap: residual-tie check.
    Returns (status, value, x, certified): certified = proven optimal with |dual bound - objective| <= 1e-9."""
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import csr_matrix
    n = len(pb.nodes)
    w = pb.weights(k) if w is None else w
    # HiGHS stops at an absolute gap of 1e-6, not settable through scipy: scale so that max w = 1e6, which makes
    # that gap (and the feasibility tolerance of the value row) about 1e-12 in original units.
    scale = 1e6 / float(w.max()) if w.size and w.max() > 0 else 1.0
    data, ri, ci, lo, hi = [], [], [], [], []

    def row(entries, low, high):
        r = len(lo)
        for col, val in entries:
            data.append(val), ri.append(r), ci.append(col)
        lo.append(low), hi.append(high)

    row([(i, 1.0) for i in range(n)], k, k)
    for b, al in enumerate(pb.anc):
        for a in al:
            row([(b, 1.0), (a, -1.0)], -np.inf, 0)
    if emission:
        for a in np.flatnonzero(pb.n86):
            row([(int(a), 1.0)] + [(d, -1.0) for d in pb.desc[a]], -np.inf, 0)
    if tie_value is not None:
        row([(i, float(scale * w[i])) for i in range(n) if w[i] != 0], scale * tie_value, np.inf)
        c = np.asarray(rank, dtype=float)
        if exclude is not None:  # another set of the same size: at most k-1 of the found elements
            row([(int(i), 1.0) for i in exclude], -np.inf, k - 1)
            row([(i, float(c[i])) for i in range(n)], -np.inf, rank_cap)
    else:
        c = -scale * w
    matrix = csr_matrix((data, (ri, ci)), shape=(len(lo), n))
    res = milp(c, constraints=LinearConstraint(matrix, lo, hi), integrality=np.ones(n),
               bounds=Bounds(0, 1), options={"time_limit": time_limit, "mip_rel_gap": 0.0, "presolve": False})
    # presolve OFF: with scipy 1.18.1 the HiGHS presolve returned a wrong "optimal" value with a zero gap on a
    # synthetic closure-only problem that E1-(i) caught (tests/test_a1_run.py, regression test)
    if res.x is None:
        return res.status, None, None, res.status == 2  # 2: infeasible (a certified fact)
    x = np.round(res.x).astype(int)
    value = float(w @ x)
    dual = getattr(res, "mip_dual_bound", None)
    certified = res.status == 0 and dual is not None and abs(dual - res.fun) / (scale if tie_value is None else 1) <= 1e-9
    return res.status, value, x, bool(certified)


def decode(pb, constrained=True):
    """Section 4 decoder. Returns dict: emitted codes, S (node indices), value, path, certification, counts."""
    k, val, idx = flat_optimum(pb)
    info = {"k_sort": k, "value_sort": val, "milp_calls": 0, "milp_status": [], "certified": True,
            "residual_tie": False}
    s_sort = sorted(int(i) for i in idx)
    info["sort_unconstrained_emitted"] = sorted(drop86([pb.nodes[i] for i in pb.maximal(s_sort)]))
    if k == 0:
        return {**info, "path": "empty", "S": [], "value": 0.0, "emitted": []}
    if not any(pb.n86[i] for i in pb.maximal(s_sort)) or not constrained:
        return {**info, "path": "sort_certified", "S": s_sort, "value": val,
                "emitted": sorted(drop86([pb.nodes[i] for i in pb.maximal(s_sort)]))}
    # Exact search: k by decreasing sort bound; stop when the next bound is below the best certified value (ties kept).
    curve = sorted(((v, kk) for kk, v, _ in flat_curve(pb)), key=lambda x: (-x[0], x[1]))
    best_val, best = 0.0, []  # the empty set is feasible with utility 0 [G7.3]
    for bound, kk in curve:
        if bound < best_val - 1e-12 or bound <= 0:
            break
        status, value, x, cert = milp_k(pb, kk)
        info["milp_calls"] += 1
        info["milp_status"].append(int(status))
        if value is None:
            if not cert:
                info["certified"] = False
            continue
        info["certified"] &= cert
        if value > best_val + 1e-12:
            best_val, best = value, [(kk, x)]
        elif value >= best_val - 1e-12:
            best.append((kk, x))
    if best_val <= 0 or not best:
        return {**info, "path": "solver_empty", "S": [], "value": 0.0, "emitted": []}
    kk, x = min(best, key=lambda t: t[0])           # smallest k among optimal values
    order, w = pb.top_k(kk)
    rank = np.empty(len(pb.nodes))
    rank[np.lexsort((np.arange(len(w)), -w))] = np.arange(len(w))
    status, value, x2, cert = milp_k(pb, kk, w=w, tie_value=best_val - 1e-12, rank=rank)
    info["milp_calls"] += 1
    if x2 is not None:
        x = x2
        found = np.flatnonzero(x)
        # Residual tie: another optimal set of the same size with a rank sum not larger; HiGHS's choice is kept, counted.
        st3, _, x3, _ = milp_k(pb, kk, w=w, tie_value=best_val - 1e-12, rank=rank, exclude=found,
                               rank_cap=float(rank @ x))
        info["milp_calls"] += 1
        info["residual_tie"] = x3 is not None
    s = sorted(int(i) for i in np.flatnonzero(x))
    require_closed = pb.is_closed(s) and not any(pb.n86[i] for i in pb.maximal(s))
    info["solution_feasible"] = bool(require_closed)
    return {**info, "path": "solver", "S": s, "value": pb.utility(s),
            "emitted": sorted(drop86([pb.nodes[i] for i in pb.maximal(s)]))}


def threshold_control(pb, t):
    """Same q, threshold on marginals m_a = sum_j q_j 1[a in T_j]: drop86(most_specific({a in U minus N, m_a >= t}))."""
    m = pb.member.T.astype(float) @ pb.q
    keep = [pb.nodes[i] for i in range(len(pb.nodes)) if m[i] >= t and not pb.n86[i]]  # N removed first [G7.3]
    return sorted(drop86(most_specific(keep)))
