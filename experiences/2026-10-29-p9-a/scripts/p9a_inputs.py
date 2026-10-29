"""Only the eleven explicit train shards. All expensive verification is remote."""
from collections import Counter
import hashlib
from pathlib import Path
import re

import numpy as np
import torch

from p9a_common import (TRAIN, DATASET, GRID_CONFIG, FEATURE_CONFIG, B_SHA, E3_SHA, RUN_SHA,
                       ancestors, drop86, e3_hash, input_path, object_hash, read_json, require, sha)


def graph(vocab):
    ix = {c: i for i, c in enumerate(vocab)}
    proper = [{ix[a] for a in ancestors(c) - {c} if a in ix} for c in vocab]
    # Exact transitivity/antisymmetry, not just a successful topological sort.
    for c, aset in enumerate(proper):
        require(c not in aset, "reflexive strict relation")
        for a in aset:
            require(c not in proper[a], "antisymmetry fails")
            require(proper[a] <= aset, "historical ancestor relation is not transitive")
    parents = [sorted(aset - set().union(*(proper[a] for a in aset))) if aset else [] for aset in proper]
    # Empty parent list means the artificial root, never the literal code '0'.
    done, levels = set(), []
    while len(done) < len(vocab):
        level = [c for c, p in enumerate(parents) if c not in done and set(p) <= done]
        require(bool(level), "cycle in historical parser relation")
        levels.append(level)
        done.update(level)
    return parents, levels


class TrainData:
    def __init__(self, binding, inventory, budget):
        self.root = input_path(binding["encoder_root"])
        expected = read_json(inventory)
        require(expected["dataset"] == DATASET and expected["version"] == 3, "inventory identity")
        expected_paths = {f"{kind}/{tag}.{ext}" for tag in TRAIN for kind, ext in
                          (("grid", "npy"), ("grid", "json"), ("feats", "npz"), ("feats", "json"))}
        require(set(expected["files"]) == expected_paths, "inventory is not the exact train allowlist")
        self.grids, self.labels, self.md5, self.where, self.provenance = [], [], [], [], []
        for shard, tag in enumerate(TRAIN):
            paths = {}
            for kind, ext in (("grid", "npy"), ("grid", "json"), ("feats", "npz"), ("feats", "json")):
                rel = f"{kind}/{tag}.{ext}"
                p = input_path(self.root / rel)
                require(p.is_relative_to(self.root), "train input symlink escapes bound encoder")
                require(sha(p) == expected["files"][rel], f"SHA mismatch: {rel}")
                paths[kind, ext] = p
            side, manifest = read_json(paths["grid", "json"]), read_json(paths["feats", "json"])
            n = 8000 if shard < 10 else 6216
            require(side["rows"] == n and len(side["labels"]) == n, f"rows: {tag}")
            require(manifest == side["manifest"], "grid/vector manifests disagree")
            require(manifest["dataset"] == DATASET and manifest["shard"] == f"data/{tag}.parquet"
                    and manifest["rows"] == n and manifest["smoke"] == 0, "source dataset identity")
            require(manifest["feature_config"] == FEATURE_CONFIG and side["grid_config"] == GRID_CONFIG,
                    "encoding configuration")
            require(side["grid_sha256"] == expected["files"][f"grid/{tag}.npy"] and
                    side["vec_sha256"] == expected["files"][f"feats/{tag}.npz"], "sidecar tensor SHA")
            require(re.fullmatch(r"[0-9a-f]{64}", side["run_key_sha256"]) is not None, "run key SHA")
            require(e3_hash(side["labels"]) == manifest["labels_sha256"], "labels SHA")
            require(all(isinstance(y, list) and all(isinstance(c, str) and c.strip() for c in y)
                        for y in side["labels"]), "invalid raw labels")
            grid = np.load(paths["grid", "npy"], mmap_mode="r", allow_pickle=False)
            require(grid.shape == (n, 64, 1024) and grid.dtype == np.float16, "grid shape/dtype")
            for start in range(0, n, 256):
                require(np.isfinite(grid[start:start + 256]).all(), "nonfinite grid")
                budget.check(f"verify_grid/{tag}/{start}")
            with np.load(paths["feats", "npz"], allow_pickle=False) as f:
                require(set(f.files) == {"x", "md5"}, "unexpected vector fields")
                x, md5 = f["x"], f["md5"]
                require(x.shape == (n, 4096) and x.dtype == np.float16, "vector shape/dtype")
                for start in range(0, n, 1024):
                    require(np.isfinite(x[start:start + 1024]).all(), "nonfinite vectors")
                require(md5.shape == (n,) and md5.dtype.kind == "U", "md5 shape/dtype")
                md5 = md5.tolist()
                require(all(re.fullmatch(r"[0-9a-f]{32}", m) for m in md5), "invalid image md5")
                require(e3_hash(md5) == side["md5_sha256"], "md5 alignment hash")
                del x
            self.grids.append(grid)
            self.labels.extend(side["labels"])
            self.md5.extend(md5)
            self.where.extend((shard, row) for row in range(n))
            self.provenance.append({"tag": tag, "run_key_sha256": side["run_key_sha256"]})
        require(len(set(p["run_key_sha256"] for p in self.provenance)) == 1, "mixed encoder runs")
        require(len(self.where) == 86216, "total rows")
        groups = sorted(set(self.md5))
        gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
        self.fit = np.array([i for i, m in enumerate(self.md5) if m not in gval], dtype=np.int64)
        self.val = np.array([i for i, m in enumerate(self.md5) if m in gval], dtype=np.int64)
        self.reg = np.array([i for i in self.val if self.is_reg(self.md5[i])], dtype=np.int64)
        self.diag = np.array([i for i in self.val if not self.is_reg(self.md5[i])], dtype=np.int64)
        require((len(self.fit), len(self.val)) == (81951, 4265), "historical split changed")
        require(not ({self.md5[i] for i in self.fit} & {self.md5[i] for i in self.val}), "md5 leak")
        require(sum(bool(drop86(self.labels[i])) for i in self.val) == 4241, "eligible validation count")
        require(all(sum(bool(drop86(self.labels[i])) for i in part) >= 1000 for part in (self.reg, self.diag)),
                "validation halves too small: amendment required")
        self.raw = Counter(c for i in self.fit for c in set(self.labels[i]))
        self.vocab = sorted({a for c, n in self.raw.items() if n >= 5 for a in ancestors(c)})
        require(len(self.vocab) == 7907, "historical vocabulary size")
        self.vi = {c: j for j, c in enumerate(self.vocab)}
        self.closed = Counter(a for i in self.fit for a in set().union(
            *(ancestors(c) for c in self.labels[i])) if a in self.vi)
        self.rare = sorted(c for c, n in self.raw.items() if 5 <= n <= 20 and drop86([c]))
        require(set(self.rare) <= set(self.vocab), "rare codes outside V")
        # Detect whether stripping raw strings would change V or the rare set.
        stripped = Counter(c for i in self.fit for c in {c.strip() for c in self.labels[i]})
        v2 = sorted({a for c, n in stripped.items() if n >= 5 for a in ancestors(c)})
        r2 = sorted(c for c, n in stripped.items() if 5 <= n <= 20 and drop86([c]))
        self.collisions = sorted(c for c in self.raw if c != c.strip())
        require(v2 == self.vocab and r2 == self.rare, "raw/stripped strings change V/R: amend, do not normalize")
        self.parents, self.levels = graph(self.vocab)
        self.universe = sorted(set(drop86(list(set(self.raw) | set(self.vocab) |
                                              {c for i in self.val for c in self.labels[i]}))))
        budget.check("metadata_and_graph")

    @staticmethod
    def is_reg(md5):
        return hashlib.sha256(("p9-a/v1/validation/" + md5).encode()).digest()[0] < 128

    def identities(self, indices):
        return [[TRAIN[self.where[i][0]], self.where[i][1], self.md5[i]] for i in indices]

    def manifest(self):
        identities = {k: self.identities(getattr(self, k)) for k in ("fit", "val", "reg", "diag")}
        return {"dataset": DATASET, "rows": identities,
                "rows_sha256": {k: object_hash(v) for k, v in identities.items()},
                "vocab": self.vocab, "vocab_sha256": object_hash(self.vocab),
                "n_raw": dict(sorted(self.raw.items())), "n_closed": dict(sorted(self.closed.items())),
                "n_raw_sha256": object_hash(dict(self.raw)), "n_closed_sha256": object_hash(dict(self.closed)),
                "rare": self.rare, "rare_sha256": object_hash(self.rare),
                "parents": self.parents, "levels": self.levels, "graph_sha256": object_hash(self.parents),
                "descriptive_universe": self.universe, "universe_sha256": object_hash(self.universe),
                "raw_whitespace_strings": self.collisions, "encoder_runs": self.provenance}

    def batch(self, indices):
        out = np.empty((len(indices), 64, 1024), dtype=np.float32)
        for pos, i in enumerate(indices):
            shard, row = self.where[i]
            out[pos] = self.grids[shard][row]
        return torch.from_numpy(out)

    def targets(self, indices):
        y = np.zeros((len(indices), len(self.vocab)), dtype=np.float32)
        for pos, i in enumerate(indices):
            for c in self.labels[i]:
                for a in ancestors(c):
                    if a in self.vi:
                        y[pos, self.vi[a]] = 1
        return torch.from_numpy(y)


def baseline_checkpoint(binding, data):
    p = input_path(binding["baseline_pt"])
    require(p.name == "t_z.pt" and sha(p) == B_SHA, "baseline checkpoint identity")
    for key, expected in (("e3_json", E3_SHA), ("e3_run_json", RUN_SHA)):
        require(sha(input_path(binding[key])) == expected, f"historical artifact {key}")
    ck = torch.load(p, map_location="cpu", weights_only=True)
    require(ck["vocab"] == data.vocab and ck["epoch"] == 29 and ck["threshold"] == 0.65 and
            ck["grid_config"] == GRID_CONFIG, "baseline checkpoint metadata")
    return ck
