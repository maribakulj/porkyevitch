"""Four paired heads; all hierarchical arithmetic and losses are float32."""
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from p9a_common import ARMS, require


class Baseline(nn.Module):
    def __init__(self, classes):
        super().__init__()
        self.q = nn.Parameter(torch.empty(1024))
        self.mlp = nn.Sequential(nn.Linear(1024, 2048), nn.GELU(), nn.Dropout(0.2), nn.Linear(2048, classes))

    def forward(self, x):
        w = torch.softmax((x @ self.q) / 32.0, dim=1)
        return torch.sigmoid(self.mlp((w.unsqueeze(-1) * x).sum(1)))


class Hierarchy(nn.Module):
    """Vectorized by topological level, never a code x code field.

    Artificial root is slot 0; real code indices are independent of that slot.
    amin distributes a tied gradient equally over actual minimizing parents.
    Padded parents are +inf, not duplicate roots.
    """
    def __init__(self, parents, levels):
        super().__init__()
        completed = {-1: 0}
        ordering = []
        self.depths = len(levels)
        for depth, nodes in enumerate(levels):
            nparents = max(len(parents[c]) or 1 for c in nodes)
            gather = np.zeros((len(nodes), nparents), dtype=np.int64)
            mask = np.zeros_like(gather, dtype=bool)
            for row, c in enumerate(nodes):
                ps = parents[c] or [-1]
                gather[row, :len(ps)] = [completed[p] for p in ps]
                mask[row, :len(ps)] = True
            self.register_buffer(f"nodes_{depth}", torch.tensor(nodes, dtype=torch.long))
            self.register_buffer(f"gather_{depth}", torch.from_numpy(gather))
            self.register_buffer(f"mask_{depth}", torch.from_numpy(mask))
            for c in nodes:
                completed[c] = len(completed)
            ordering.extend(nodes)
        self.register_buffer("inverse", torch.tensor(np.argsort(ordering), dtype=torch.long))
        self.register_buffer("edge_children", torch.tensor([c for c, ps in enumerate(parents) for _ in ps], dtype=torch.long))
        self.register_buffer("edge_parents", torch.tensor([p for ps in parents for p in ps], dtype=torch.long))

    def forward(self, gates, root):
        pieces = [root.unsqueeze(-1)]
        for depth in range(self.depths):
            nodes = getattr(self, f"nodes_{depth}")
            gather, mask = getattr(self, f"gather_{depth}"), getattr(self, f"mask_{depth}")
            values = torch.cat(pieces, dim=-1)
            pv = values.index_select(-1, gather.flatten()).reshape(*values.shape[:-1], *gather.shape)
            minimum = pv.masked_fill(~mask, float("inf")).amin(-1)
            pieces.append(minimum * gates.index_select(-1, nodes))
        return torch.cat(pieces[1:], dim=-1).index_select(-1, self.inverse)

    def violation(self, value):
        if not self.edge_parents.numel():
            return 0.0
        return float((value.index_select(-1, self.edge_children) - value.index_select(-1, self.edge_parents)).max())


class Head(nn.Module):
    def __init__(self, arm, data, prototypes, initial_W):
        super().__init__()
        require(arm in ARMS, "unknown arm")
        self.arm = arm
        classes = len(data.vocab)
        self.W = nn.Parameter(initial_W.clone())
        self.U = nn.Parameter(torch.zeros(128, 384))
        self.delta = nn.Parameter(torch.zeros(classes, 128))
        self.b = nn.Parameter(torch.zeros(classes))
        self.register_buffer("prototypes", torch.from_numpy(prototypes.copy()).float())
        n = np.array([data.closed[c] for c in data.vocab], dtype=np.float64)
        self.register_buffer("shrinkage", torch.tensor(55 / (n + 5), dtype=torch.float32))
        pi = (n + 0.5) / (len(data.fit) + 1)
        L0 = -np.log1p(-pi)
        root = max(1.0, L0.max()) / 0.99
        self.register_buffer("prior", torch.tensor(pi, dtype=torch.float32))
        self.hierarchy = Hierarchy(data.parents, data.levels)
        if arm == "C":
            biases = np.log(pi / (1 - pi)) / 1.1
        else:
            self.w0 = nn.Parameter(torch.zeros(1024))
            # Stable inverse softplus; eps included in the forward root.
            root_pre = root - 1e-8
            self.b0 = nn.Parameter(torch.tensor(root_pre + np.log(-np.expm1(-root_pre)), dtype=torch.float32))
            denom = np.array([min(L0[p] for p in ps) if ps else root for ps in data.parents])
            ratio = L0 / (root if arm == "F" else denom)
            ratio = np.clip(ratio, 1e-6, 1 - 1e-6)
            biases = np.log(ratio / (1 - ratio))
        with torch.no_grad():
            self.b.copy_(torch.tensor(biases, dtype=torch.float32))
        want = 1200227 if arm == "C" else 1201252
        require(sum(p.numel() for p in self.parameters()) == want, "active parameter count")

    def linear_scores(self, x, fp16=True):
        # No AMP context around normalization, roots, gates, reductions or exp/log.
        # fp16=True is the training/inference path (unchanged, float32 elsewhere). fp16=False keeps the
        # parameters' own dtype everywhere: used only by the invariant checks on a float64 copy.
        dtype = torch.float32 if fp16 else self.W.dtype
        z = F.layer_norm(x.to(dtype), (1024,), eps=1e-5)
        # fp16 is allowed only for these three linear products, then cast to fp32.
        with torch.autocast("cuda", dtype=torch.float16, enabled=fp16):
            v = F.linear(z, self.W)
            code = F.linear(self.prototypes, self.U) + self.delta
            dot = v @ code.T
        scores = dot.to(dtype) / math.sqrt(128) + self.b
        return z, scores

    def forward(self, x, weights=None, return_fields=False, fp16=True):
        z, scores = self.linear_scores(x, fp16)
        if weights is None:
            weights = torch.full((x.shape[1],), 1 / x.shape[1], device=x.device, dtype=torch.float32)
        require(weights.dtype == torch.float32 and weights.shape == (x.shape[1],), "cell weights")
        require(bool((weights >= 0).all()) and abs(float(weights.sum()) - 1) <= 1e-6, "cell mass")
        omega = weights.view(1, -1, 1)
        if self.arm == "C":
            attention = torch.softmax(scores, dim=1)
            logits = scores.mean(1) + 0.1 * (attention * scores).sum(1)
            probability = torch.sigmoid(logits)
            intensity = -torch.log1p(-probability.clamp(1e-7, 1 - 1e-7))
            fields = scores
        else:
            root = F.softplus(F.linear(z, self.w0.unsqueeze(0), self.b0.view(1)).squeeze(-1)) + 1e-8
            mu = (weights * root).sum(1)
            gates = torch.sigmoid(scores)
            if self.arm == "F":
                fields = root.unsqueeze(-1) * gates
                intensity = (omega * fields).sum(1)
            elif self.arm == "controle_global":
                g = (omega * root.unsqueeze(-1) * gates).sum(1) / mu.unsqueeze(-1)
                intensity = self.hierarchy(g, mu)
                fields = None  # G has no local hierarchical evidence field.
            else:
                fields = self.hierarchy(gates, root)
                intensity = (omega * fields).sum(1)
            probability = -torch.expm1(-intensity)
        if return_fields:
            return probability, intensity, fields
        return probability

    def regularization(self):
        return 1e-4 * (self.shrinkage * self.delta.square().sum(1)).sum()


def asymmetric_loss(p, target):
    p = p.float()
    pn = (p - 0.05).clamp_min(0)
    return -(target * torch.log(p.clamp_min(1e-8)) +
             (1 - target) * pn.pow(4) * torch.log((1 - pn).clamp_min(1e-8))).sum(1).mean()


def optimizer(model):
    decay = [p for name, p in model.named_parameters() if name in {"W", "U", "w0"}]
    zero = [p for name, p in model.named_parameters() if name not in {"W", "U", "w0"}]
    return torch.optim.AdamW([{"params": decay, "weight_decay": 1e-4},
                              {"params": zero, "weight_decay": 0.0}],
                             lr=1e-3, betas=(0.9, 0.999), eps=1e-8, foreach=False, fused=False)
