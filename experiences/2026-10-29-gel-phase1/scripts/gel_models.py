"""Frozen phase-1 heads, no optimizer and no training/evaluation loop."""
import importlib.util
import sys

import numpy as np
import torch
from torch import nn

from gel_common import FEATURE_CONFIG, GRID_CONFIG, ancestors, bound, require, sha


def vector_head(classes):
    return nn.Sequential(nn.Linear(4096, 2048), nn.GELU(), nn.Dropout(0.2), nn.Linear(2048, classes))


class SpatialPooling(nn.Module):
    def __init__(self, classes):
        super().__init__()
        self.q = nn.Parameter(torch.empty(1024))
        self.mlp = nn.Sequential(nn.Linear(1024, 2048), nn.GELU(), nn.Dropout(0.2), nn.Linear(2048, classes))

    def forward(self, x):
        w = torch.softmax((x @ self.q) / 32.0, dim=1)
        return self.mlp((w.unsqueeze(-1) * x).sum(1))


def ml_decoder(path, expected_sha, classes, checkpoint):
    """Import unchanged MIT upstream file with exactly E3's compatibility shim."""
    path = bound(path)
    require(sha(path) == expected_sha, "mldec_source_sha")
    spec = importlib.util.spec_from_file_location("gel_pinned_ml_decoder", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # TorchScript's inspect needs the source module.
    spec.loader.exec_module(module)
    original = module.TransformerDecoderLayerOptimal.forward

    def shim(self, tgt, memory, tgt_mask=None, memory_mask=None, tgt_key_padding_mask=None,
             memory_key_padding_mask=None, tgt_is_causal=None, memory_is_causal=None):
        return original(self, tgt, memory, tgt_mask, memory_mask, tgt_key_padding_mask, memory_key_padding_mask)

    module.TransformerDecoderLayerOptimal.forward = shim
    module.TransformerDecoderLayerOptimal.self_attn = property(lambda self: self.multihead_attn)

    class Decoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.dec = module.MLDecoder(num_classes=classes, num_of_groups=100,
                                       decoder_embedding=768, initial_num_features=1024)
            self.register_buffer("slot_of_class", torch.from_numpy(np.random.default_rng(0).permutation(classes)).long())

        def forward(self, x):
            return self.dec(x)[:, self.slot_of_class]

    expected = np.random.default_rng(0).permutation(classes)
    require(np.array_equal(checkpoint["slot_of_class"], expected) and
            np.array_equal(checkpoint["class_of_slot"], np.argsort(expected)), "decoder_class_permutation")
    require(checkpoint["ml_decoder"] == {"commit": "8a9e984f671c9c30c98d2c45dfcaf4383381c254",
            "num_of_groups": 100, "decoder_embedding": 768}, "decoder_configuration")
    return Decoder()


def load_checkpoint(path, expected_sha, vocab, epoch, threshold, spatial):
    path = bound(path)
    require(sha(path) == expected_sha, "head_sha")
    # E3 T-D metadata contains numpy lists; allow pickle only for this SHA-pinned,
    # reviewed historical checkpoint. No unverified file reaches torch.load.
    ck = torch.load(path, map_location="cpu", weights_only=False)
    require(list(ck["vocab"]) == vocab and ck["epoch"] == epoch and ck["threshold"] == threshold,
            "head_vocabulary_epoch_threshold")
    require(ck["grid_config" if spatial else "feature_config"] == (GRID_CONFIG if spatial else FEATURE_CONFIG),
            "head_feature_configuration")
    return ck


def ancestor_pairs(vocab):
    vi = {c: i for i, c in enumerate(vocab)}
    aa, dd = [], []
    for j, code in enumerate(vocab):
        for a in ancestors(code):
            if a in vi:
                aa.append(vi[a])
                dd.append(j)
    return torch.tensor(aa, dtype=torch.long, device="cuda"), torch.tensor(dd, dtype=torch.long, device="cuda")


@torch.no_grad()
def probabilities(model, vectors, grids, batch, constrained=False, pairs=None):
    model.eval()
    out = []
    source = grids if grids is not None else vectors
    for start in range(0, len(source), batch):
        x = torch.from_numpy(np.array(source[start:start + batch], dtype=np.float32, copy=True)).cuda()
        p = torch.sigmoid(model(x))  # all head inference float32, no AMP
        if constrained:
            aa, dd = pairs
            p = torch.full_like(p, -1).scatter_reduce(1, aa.expand(len(p), -1), p[:, dd],
                                                     reduce="amax", include_self=True)
        require(bool(torch.isfinite(p).all()) and bool(((p >= 0) & (p <= 1)).all()), "invalid_head_probability")
        out.append(p.cpu().numpy())
    return np.concatenate(out)
