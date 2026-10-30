"""Synthetic tests of the A3 bound, energy, couplings and filter-and-refine. No pilot data.

Run: python3 -I tests/test_a3.py
"""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location("a3", Path(__file__).resolve().parents[1] / "scripts/a3_exactitude.py")
a3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a3)

NAMES = ["man", "woman", "child", "horse", "book"]
RELS = ["holds", "left of", "looks at"]


def graph(gid, names, relations=()):
    objects = [{"id": f"o{i}", "name": n, "box": [0, 0, 1, 1], "attributes": []} for i, n in enumerate(names)]
    return a3.Graph(gid, {"objects": objects, "relations": [[f"o{u}", r, f"o{v}"] for u, r, v in relations]})


def random_graph(rng, gid):
    n = int(rng.integers(1, 7))
    names = [NAMES[i] for i in rng.integers(0, len(NAMES), n)]
    relations = [(int(rng.integers(n)), RELS[int(rng.integers(len(RELS)))], int(rng.integers(n)))
                 for _ in range(int(rng.integers(0, 2 * n)))]
    return graph(gid, names, relations)


class BoundTest(unittest.TestCase):
    def test_identical_graphs_bound_zero_and_identity_coupling_zero(self):
        g = graph("a", ["man", "child"], [(0, "holds", 1)])
        h = graph("b", ["man", "child"], [(0, "holds", 1)])
        self.assertEqual(a3.lower_bound(g, h), 0.0)
        self.assertAlmostEqual(a3.Pair(g, h).energy(np.diag(g.mass)), 0.0, places=15)

    def test_single_nodes_different_names_bound_is_tight(self):
        g, h = graph("a", ["man"]), graph("b", ["woman"])
        T = np.ones((1, 1))
        self.assertAlmostEqual(a3.lower_bound(g, h), 1.0)
        self.assertAlmostEqual(a3.Pair(g, h).energy(T), 1.0)

    def test_name_normalisation_is_case_and_space_only(self):
        g, h = graph("a", ["Standing  Man"]), graph("b", ["standing man"])
        self.assertEqual(a3.lower_bound(g, h), 0.0)
        self.assertGreater(a3.lower_bound(g, graph("c", ["man"])), 0.0)

    def test_relation_direction_matters(self):
        g = graph("a", ["man", "child"], [(0, "holds", 1)])
        h = graph("b", ["man", "child"], [(1, "holds", 0)])
        self.assertGreater(a3.lower_bound(g, h), 0.0)

    def test_random_graphs_bound_below_every_feasible_coupling(self):
        rng = np.random.default_rng(0)
        for trial in range(300):
            g, h = random_graph(rng, "g"), random_graph(rng, "h")
            pair, lb = a3.Pair(g, h), a3.lower_bound(g, h)
            self.assertAlmostEqual(lb, a3.lower_bound_inverted(g.phi(), h.phi()), places=12)
            couplings = [np.outer(g.mass, h.mass), a3.frozen_matcher(pair), a3.random_coupling(g.mass, h.mass, trial)]
            for T in couplings:
                self.assertLessEqual(a3.feasibility_error(T, g.mass, h.mass), a3.TOL_EXACT)
                e = pair.energy(T)
                self.assertAlmostEqual(e, a3.energy_dense(g, h, T), places=12)
                self.assertLessEqual(lb, e + a3.TOL_BOUND)

    def test_gradient_matches_finite_differences(self):
        rng = np.random.default_rng(1)
        g, h = random_graph(rng, "g"), random_graph(rng, "h")
        pair = a3.Pair(g, h)
        T = a3.random_coupling(g.mass, h.mass, 7)
        G, step = pair.gradient(T), 1e-6
        for u in range(g.n):
            for s in range(h.n):
                E = np.zeros_like(T)
                E[u, s] = step
                fd = (pair.energy(T + E) - pair.energy(T - E)) / (2 * step)
                self.assertAlmostEqual(G[u, s], fd, places=6)

    def test_rounding_gives_exact_marginals(self):
        rng = np.random.default_rng(2)
        a, b = np.full(5, 0.2), np.full(3, 1 / 3)
        T = a3.round_feasible(rng.random((5, 3)), a, b)
        self.assertLessEqual(a3.feasibility_error(T, a, b), 1e-15)

    def test_filter_and_refine_returns_exhaustive_top_k(self):
        rng = np.random.default_rng(3)
        for _ in range(200):
            s = rng.random(40)
            lb = s * rng.random(40)  # any valid lower bound
            top, refined = a3.filter_and_refine(list(lb), list(s), 10)
            self.assertEqual(top, [j for _, j in sorted((s[j], j) for j in range(40))[:10]])
            self.assertLessEqual(refined, 40)

    def test_filter_and_refine_with_ties(self):
        s = [0.5] * 12 + [0.2]
        top, _ = a3.filter_and_refine([0.0] * 13, s, 10)
        self.assertEqual(top, [12] + list(range(9)))

    def test_tight_bound_one_ulp_above_kth_score_not_pruned(self):
        # Case of the first run (12/178 queries): LB = S mathematically, LB − S = 2.2e-16 in floating point,
        # and S equals the 10th best score. The candidate with the smaller index must stay in the top-10.
        kth = 0.99999999999999978
        s = [0.5] * 9 + [kth] * 3
        lb = [0.5] * 9 + [kth + 2.220446049250313e-16, kth, kth]
        top, _ = a3.filter_and_refine(lb, s, 10)
        self.assertEqual(top, list(range(10)))

    def test_filter_exact_when_bound_holds_only_within_tolerance(self):
        rng = np.random.default_rng(4)
        for _ in range(500):
            s = np.round(rng.random(60), 2)  # many exact ties, as in the pilot
            lb = np.minimum(s, s * rng.random(60) + (rng.random(60) < 0.5) * s) + rng.uniform(-1, 1, 60) * a3.TOL_BOUND
            top, _ = a3.filter_and_refine(list(lb), list(s), 10)
            self.assertEqual(top, [j for _, j in sorted((s[j], j) for j in range(60))[:10]])

    def test_output_refused_inside_forbidden_repositories(self):
        with self.assertRaisesRegex(RuntimeError, "output_in_forbidden_repository"):
            a3.main(type("A", (), {"out": str(Path.home() / "porkyevitch/x"), "pilot": "."}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
