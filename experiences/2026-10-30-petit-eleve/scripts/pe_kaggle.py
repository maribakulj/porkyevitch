"""Petit élève (jalon 5) on Kaggle T4: re-encoding, identity and overfit controls, heads, witnesses, throughput, D2 reading.

Usage: pe_kaggle.py --stage smoke|full|mesures --inputs IN --encoder ENC --out OUT [--predictions P --receipt R]
  IN   dataset holding listes.json, noms.json, images/pNNN.jpg, graphes/pNNN.json (Gemini) and s1b/pNNN.json (evaluation only);
       it must hold no image or graph of the closed sets (exemples, test20): the script refuses them.
  ENC  full output of caypollard-encode-cradio v3 (grid/<shard>.npy), used only for the 8x8 identity control.
  OUT  /kaggle/working/... (empty).
smoke (blank): hashes and opens the training files only; encodes the 8 overfit images, identity control, overfit control,
  OWLv2 and Florence-2 on 2 of them (revisions recorded), a one-repetition timing on them. No tuning or evaluation file is opened.
full: heads, witnesses (OWLv2, Florence-2, YOLOE-v8-S), throughput and the plate; predictions are written and sealed
  (MANIFEST_PREDICTIONS.json) but NO measure is computed, so the plate is looked at before any number (Codex p4, 30/10).
mesures (CPU): only with the plate receipt of wA:p1 and a Grok bound to that manifest; measures and the D2 reading from the
  sealed predictions, nothing re-inferred. Rules are in pe_common.py, fixed in advance.
Amendment 30/10 (before the full run): revisions pinned from the reviewed smoke; Florence-2 loaded through the native
transformers class from the official converted checkpoint (the remote code of microsoft/Florence-2-base fails under
transformers 5.16: forced_bos_token_id); every timed system under no_grad + fp16 autocast; box offsets equal to the
integer padding of the square; a failed overfit control fails the smoke; YOLOE-v8-S text mode added (D8), frozen below.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pe_common as pc  # noqa: E402

ENC_REPO, ENC_REV = "nvidia/C-RADIOv3-L", "9d0413465e8a91e67bbf2c1ad342815478d1b906"
OWL_REPO = "google/owlv2-base-patch16-ensemble"
OWL_REV = "cfd3195ba4ea9592eec887ded089f4c08eff231d"  # resolved by the reviewed smoke (Grok p3, 30/10)
FLO_SOURCE = ("microsoft/Florence-2-base", "5ca5edf5bd017b9919c05d08aebef5e4c7ac3bac")  # resolved by the smoke; its remote
# code cannot load under transformers 5.16, so the weights are taken from the official transformers conversion of it:
FLO_NATIVE_REPO, FLO_REV = "florence-community/Florence-2-base", "00921df66db728a9ceb750f5eca43e5c203a2051"  # MIT
YOLOE_PACKAGE = "ultralytics==8.4.177"  # installed by the pilot (wheel sha256 de8fd2fc...), AGPL-3.0, recorded
YOLOE_WEIGHTS = ("https://github.com/ultralytics/assets/releases/download/v8.3.0/yoloe-v8s-seg.pt",
                 "ac2b90ed23011495a3e86d89caeb3432a15129cac8d849ba121293c8fc1e0536")  # 31 135 890 bytes, text/visual mode
YOLOE_TEXT_MODEL = "mobileclip:blt"     # text encoder the checkpoint asks for (checked at load)
YOLOE_TEXT_SHA256 = None                # sha of mobileclip_blt.ts, recorded by the smoke, pinned by a reviewed commit
YOLOE_CONF, YOLOE_IOU, YOLOE_MAX_DET, YOLOE_IMGSZ = 0.1, 0.5, 300, 640  # same score threshold and NMS as OWLv2
LISTES_SHA256 = "87e45b418ace7a4f1a15857456d3d40d107ee3a9c286962e9c19723ecfb065af"  # listes.json as committed
NOMS_SHA256 = "dfa0e011f7f1df458d5396602b5f33ede99ac2a9f34b7465940241afec648ed2"  # noms.json as committed
OWL_THRESHOLD, NMS_IOU = 0.1, 0.5
NQ, D_MODEL, LAYERS, EPOCHS, BATCH, LR = 30, 256, 3, 300, 8, 1e-4
EVAL_EVERY, OVERFIT_STEPS = 5, 1000
SEEDS = (0, 1, 2)
NCLS = len(pc.CATEGORIES) + 1  # 8 categories + autre; index NCLS is "no object"
NREL = len(pc.RELATIONS) + 1  # 13 predicates + autre_relation
BUDGET_SECONDS = 4 * 3600
START = time.monotonic()


def require(ok, code):
    if not ok:
        raise RuntimeError(code)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def clean(obj):
    """NaN and infinities become null; numpy scalars become Python numbers."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, (np.integer, np.bool_)):
        return obj.item()
    return obj


def write_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    os.replace(tmp, path)


def budget(step):
    require(time.monotonic() - START <= BUDGET_SECONDS, f"budget_exceeded_at_{step}")


def finite(x):
    return x if isinstance(x, (int, float)) and np.isfinite(x) else None


# ---------------------------------------------------------------- inputs
def load_graph(path):
    """Teacher objects (cleaned boxes, category index) and relations between kept objects."""
    g = json.loads(Path(path).read_text())
    objs, dropped, index = [], 0, {}
    for o in g["objects"]:
        b = pc.clean_box(o["box"])
        if b is None:
            dropped += 1
            continue
        cat, _ = pc.categorie(o["name"])
        index[o["id"]] = len(objs)
        objs.append({"box": b, "cat": pc.CATEGORIES.index(cat) if cat in pc.CATEGORIES else len(pc.CATEGORIES)})
    rels = []
    for r in g["relations"]:
        s, p, o = r if isinstance(r, list) else (r["subject"], r["predicate"], r["object"])
        if s in index and o in index and s != o:
            c = pc.relation_class(p)
            rels.append((index[s], (pc.RELATIONS + [pc.AUTRE_RELATION]).index(c), index[o]))
    return {"objects": objs, "relations": rels, "dropped_boxes": dropped}


def preflight(inp, listes, stage):
    closed = set(listes["fermes"]["exemples"]) | set(listes["fermes"]["test20"])
    present = {Path(p).stem for d in ("images", "graphes", "s1b") for p in (inp / d).glob("*")}
    require(not (present & closed), "closed_set_present_in_inputs")
    roles = {"entrainement": listes["entrainement"]}
    if stage == "full":
        roles |= {"reglage": [r for r in listes["reglage"] if r["gemini_graph_sha256"]], "evaluation": listes["evaluation"]}
    for role, rows in roles.items():
        for r in rows:
            require(sha(inp / "images" / f"{r['name']}.jpg") == r["image_sha256"], f"image_sha_{r['name']}")
            if r["gemini_graph_sha256"]:
                require(sha(inp / "graphes" / f"{r['name']}.json") == r["gemini_graph_sha256"], f"graph_sha_{r['name']}")
            if r.get("s1b_graph_sha256"):
                require(sha(inp / "s1b" / f"{r['name']}.json") == r["s1b_graph_sha256"], f"s1b_sha_{r['name']}")
    return roles


# ---------------------------------------------------------------- encoder (the v3 recipe, unchanged)
class Encoder:
    def __init__(self, dev):
        from transformers import AutoModel, CLIPImageProcessor
        import torch
        self.torch, self.dev = torch, dev
        self.model = AutoModel.from_pretrained(ENC_REPO, revision=ENC_REV, trust_remote_code=True).to(dev).eval()
        self.processor = CLIPImageProcessor.from_pretrained(ENC_REPO, revision=ENC_REV)

    @staticmethod
    def square(im):
        from PIL import Image
        im = im.convert("RGB")
        s = max(im.size)
        c = Image.new("RGB", (s, s), (128, 128, 128))
        c.paste(im, pad_offsets(im.width, im.height))
        return c.resize((448, 448), Image.BICUBIC)

    def pixels(self, images):
        return self.processor(images=[self.square(i) for i in images], return_tensors="pt", do_resize=False).pixel_values

    def tokens(self, px):
        """(b, 784, 1024) float16 spatial tokens and their 8x8 adaptive average (the stored grid recipe)."""
        torch = self.torch
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16, enabled=self.dev == "cuda"):
            _, spatial = self.model(px.to(self.dev))
        b = px.shape[0]
        require(tuple(spatial.shape) == (b, 784, 1024), "spatial_shape")
        g = spatial.float().reshape(b, 28, 28, 1024).permute(0, 3, 1, 2)
        g8 = torch.nn.functional.adaptive_avg_pool2d(g, 8).permute(0, 2, 3, 1).reshape(b, 64, 1024)
        return spatial.half(), g8.half()


def pad_offsets(w, h):
    """Integer offsets of the image in its grey square, the same for the pixels (Encoder.square) and the boxes."""
    s = max(w, h)
    return (s - w) // 2, (s - h) // 2


def square_box(box, w, h):
    """Box in thousandths of the image -> thousandths of the grey square the encoder sees (centred padding)."""
    s = max(w, h)
    ox, oy = pad_offsets(w, h)
    x0, y0, x1, y1 = box
    return [(x0 * w / 1000 + ox) / s * 1000, (y0 * h / 1000 + oy) / s * 1000,
            (x1 * w / 1000 + ox) / s * 1000, (y1 * h / 1000 + oy) / s * 1000]


def unsquare_box(box, w, h):
    s = max(w, h)
    ox, oy = pad_offsets(w, h)
    x0, y0, x1, y1 = box
    return [((x0 * s / 1000) - ox) / w * 1000, ((y0 * s / 1000) - oy) / h * 1000,
            ((x1 * s / 1000) - ox) / w * 1000, ((y1 * s / 1000) - oy) / h * 1000]


# ---------------------------------------------------------------- student
def build_student(side, seed):
    import torch
    from torch import nn
    torch.manual_seed(seed)

    def sine(side, d):
        y, x = np.meshgrid(np.arange(side), np.arange(side), indexing="ij")
        dim = d // 4
        freq = 1.0 / (10000 ** (np.arange(dim) / dim))
        parts = [f(c.reshape(-1, 1) / side * 2 * np.pi * 10 * freq) for c in (x, y) for f in (np.sin, np.cos)]
        return torch.tensor(np.concatenate(parts, 1), dtype=torch.float32)

    def mlp(i, h, o, n):
        dims = [i] + [h] * (n - 1) + [o]
        layers = []
        for a, b in zip(dims[:-1], dims[1:]):
            layers += [nn.Linear(a, b), nn.ReLU()]
        return nn.Sequential(*layers[:-1])

    class Student(nn.Module):
        def __init__(self):
            super().__init__()
            self.proj = nn.Linear(1024, D_MODEL)
            self.register_buffer("pos", sine(side, D_MODEL))
            self.query = nn.Embedding(NQ, D_MODEL)
            layer = nn.TransformerDecoderLayer(D_MODEL, 8, 1024, dropout=0.1, batch_first=True)
            self.layers = nn.ModuleList([copy.deepcopy(layer) for _ in range(LAYERS)])
            self.norm = nn.LayerNorm(D_MODEL)
            self.cls = nn.Linear(D_MODEL, NCLS + 1)
            self.box = mlp(D_MODEL, D_MODEL, 4, 3)
            self.rel = mlp(2 * D_MODEL + 6, D_MODEL, NREL, 2)

        def forward(self, tokens):
            mem = self.proj(tokens.float()) + self.pos
            h = self.query.weight.unsqueeze(0).expand(tokens.shape[0], -1, -1)
            outs = []
            for layer in self.layers:
                h = layer(h, mem)
                z = self.norm(h)
                outs.append((self.cls(z), self.box(z).sigmoid(), z))
            return outs

    return Student()


def cxcywh_to_xyxy(b):
    import torch
    cx, cy, w, h = b.unbind(-1)
    return torch.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], -1)


def xyxy_to_cxcywh(b):
    import torch
    x0, y0, x1, y1 = b.unbind(-1)
    return torch.stack([(x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0], -1)


def giou(a, b):
    """Pairwise generalized IoU of xyxy boxes, (n, m)."""
    import torch
    area = lambda x: (x[:, 2] - x[:, 0]).clamp(min=0) * (x[:, 3] - x[:, 1]).clamp(min=0)
    lt, rb = torch.max(a[:, None, :2], b[None, :, :2]), torch.min(a[:, None, 2:], b[None, :, 2:])
    inter = (rb - lt).clamp(min=0).prod(2)
    union = area(a)[:, None] + area(b)[None] - inter
    iou = inter / union.clamp(min=1e-9)
    lt2, rb2 = torch.min(a[:, None, :2], b[None, :, :2]), torch.max(a[:, None, 2:], b[None, :, 2:])
    hull = (rb2 - lt2).clamp(min=0).prod(2)
    return iou - (hull - union) / hull.clamp(min=1e-9)


def hungarian(logits, boxes, target):
    """DETR costs 1 x class, 5 x L1, 2 x GIoU. Returns (query indices, target indices)."""
    import torch
    from scipy.optimize import linear_sum_assignment
    if not len(target["cat"]):
        return torch.zeros(0, dtype=torch.long), torch.zeros(0, dtype=torch.long)
    prob = logits.softmax(-1)
    cost = (-prob[:, target["cat"]] + 5 * torch.cdist(boxes, target["box"], p=1)
            - 2 * giou(cxcywh_to_xyxy(boxes), cxcywh_to_xyxy(target["box"])))
    q, t = linear_sum_assignment(cost.detach().cpu().numpy())
    require(len(set(q)) == len(q) and len(set(t)) == len(t), "hungarian_not_injective")
    return torch.as_tensor(q, dtype=torch.long), torch.as_tensor(t, dtype=torch.long)


def pair_features(z, boxes, qi, qj):
    import torch
    bi, bj = boxes[qi].detach(), boxes[qj].detach()
    gi = giou(cxcywh_to_xyxy(bi), cxcywh_to_xyxy(bj)).diagonal()
    geom = torch.stack([bi[:, 0] - bj[:, 0], bi[:, 1] - bj[:, 1], torch.log(bi[:, 2].clamp(min=1e-4) / bj[:, 2].clamp(min=1e-4)),
                        torch.log(bi[:, 3].clamp(min=1e-4) / bj[:, 3].clamp(min=1e-4)), gi, (bi[:, :2] - bj[:, :2]).norm(dim=1)], 1)
    return torch.cat([z[qi], z[qj], geom], 1)


def losses(model, outs, targets, gen=None, negatives=3):
    """Detection loss on every layer (auxiliary), relation loss on the last. gen=None: all negative pairs (deterministic)."""
    import torch
    import torch.nn.functional as F
    dev = outs[0][0].device
    weight = torch.ones(NCLS + 1, device=dev)
    weight[NCLS] = 0.1
    det, n_box, matches = 0.0, max(1, sum(len(t["cat"]) for t in targets)), None
    for li, (logits, boxes, _) in enumerate(outs):
        layer_matches = []
        for b, t in enumerate(targets):
            q, k = hungarian(logits[b], boxes[b], t)
            layer_matches.append((q, k))
            cls_t = torch.full((NQ,), NCLS, dtype=torch.long, device=dev)
            q, k = q.to(dev), k.to(dev)
            cls_t[q] = t["cat"][k]
            det = det + F.cross_entropy(logits[b], cls_t, weight) / len(targets)
            if len(q):
                pb, tb = boxes[b][q], t["box"][k]
                det = det + (5 * F.l1_loss(pb, tb, reduction="sum")
                             + 2 * (1 - giou(cxcywh_to_xyxy(pb), cxcywh_to_xyxy(tb)).diagonal()).sum()) / n_box
        matches = layer_matches
    logits, boxes, z = outs[-1]
    feats, labels = [], []
    for b, t in enumerate(targets):
        q, k = matches[b]
        to_q = {int(kk): int(qq) for qq, kk in zip(q.tolist(), k.tolist())}
        pos = {}
        for s, r, o in t["rels"]:
            if s in to_q and o in to_q:
                pos.setdefault((to_q[s], to_q[o]), set()).add(r)
        qs = sorted(to_q.values())
        neg = [(i, j) for i in qs for j in qs if i != j and (i, j) not in pos]
        if gen is not None and neg:
            keep = torch.randperm(len(neg), generator=gen)[:negatives * max(1, len(pos))].tolist()
            neg = [neg[i] for i in keep]
        pairs = list(pos) + neg
        if not pairs:
            continue
        qi = torch.tensor([p[0] for p in pairs], device=dev)
        qj = torch.tensor([p[1] for p in pairs], device=dev)
        feats.append(pair_features(z[b], boxes[b], qi, qj))
        y = torch.zeros(len(pairs), NREL, device=dev)
        for n, p in enumerate(pairs):
            for r in pos.get(p, ()):
                y[n, r] = 1
        labels.append(y)
    rel = F.binary_cross_entropy_with_logits(model.rel(torch.cat(feats)), torch.cat(labels)) if feats else 0.0 * det
    return det, rel


def make_target(graph, w, h, dev):
    import torch
    boxes = [square_box(o["box"], w, h) for o in graph["objects"]]
    xyxy = torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4) / 1000
    return {"cat": torch.tensor([o["cat"] for o in graph["objects"]], dtype=torch.long, device=dev),
            "box": xyxy_to_cxcywh(xyxy).to(dev), "rels": graph["relations"]}


def train(side, seed, data, tune, dev, epochs=EPOCHS, steps=None):
    """data/tune: lists of (tokens tensor on dev, target). steps: fixed number of full-batch steps (overfit control)."""
    import torch
    model = build_student(side, seed).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    gen = torch.Generator().manual_seed(seed)
    best, best_state, history, checks = None, None, [], {"grads_finite": True, "zero_grad_params_at_step1": None}
    step = 0
    n_epochs = epochs if steps is None else steps
    for epoch in range(n_epochs):
        model.train()
        order = torch.randperm(len(data), generator=gen).tolist() if steps is None else list(range(len(data)))
        batch_size = BATCH if steps is None else len(data)
        for i in range(0, len(order), batch_size):
            idx = order[i:i + batch_size]
            outs = model(torch.stack([data[j][0] for j in idx]))
            det, rel = losses(model, outs, [data[j][1] for j in idx], gen)
            loss = det + rel
            opt.zero_grad()
            loss.backward()
            if step == 0:
                checks["zero_grad_params_at_step1"] = [n for n, p in model.named_parameters()
                                                       if p.grad is None or not p.grad.abs().sum() > 0]
            checks["grads_finite"] &= all(torch.isfinite(p.grad).all().item() for p in model.parameters() if p.grad is not None)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 0.1)
            opt.step()
            if step == 0:
                checks["first_loss"] = loss.item()
            step += 1
        checks["last_loss"] = loss.item()
        if steps is None and ((epoch + 1) % EVAL_EVERY == 0 or epoch + 1 == epochs):
            tl = tune_loss(model, tune)
            history.append({"epoch": epoch + 1, "train_loss": float(loss), "tune_loss": tl})
            if best is None or tl < best:
                best, best_state = tl, {k: v.detach().clone() for k, v in model.state_dict().items()}
                history[-1]["best"] = True
            budget(f"train_{side}_{seed}_{epoch}")
    if best_state is not None:
        model.load_state_dict(best_state)
    return model.eval(), history, checks


def tune_loss(model, tune):
    import torch
    model.eval()
    total = 0.0
    with torch.no_grad():
        for i in range(0, len(tune), BATCH):
            chunk = tune[i:i + BATCH]
            det, rel = losses(model, model(torch.stack([c[0] for c in chunk])), [c[1] for c in chunk], None)
            total += float(det + rel) * len(chunk)
    model.train()
    return total / len(tune)


def predict(model, tokens, sizes):
    """Per image: boxes (thousandths of the image), agnostic scores, category, per-category score, relation logits."""
    import torch
    with torch.no_grad():
        logits, boxes, z = model(tokens)[-1]
        prob = logits.softmax(-1)
        out = []
        for b, (w, h) in enumerate(sizes):
            xyxy = (cxcywh_to_xyxy(boxes[b]) * 1000).cpu().numpy().tolist()
            qi, qj = torch.meshgrid(torch.arange(NQ, device=tokens.device), torch.arange(NQ, device=tokens.device),
                                    indexing="ij")
            mask = qi != qj
            rel = model.rel(pair_features(z[b], boxes[b], qi[mask], qj[mask])).sigmoid().cpu().numpy()
            cat = prob[b, :, :NCLS].argmax(-1).cpu().numpy()
            out.append({"boxes": [unsquare_box(x, w, h) for x in xyxy],
                        "score": (1 - prob[b, :, NCLS]).cpu().numpy().tolist(),
                        "cat": cat.tolist(), "cat_score": prob[b, :, :NCLS].max(-1).values.cpu().numpy().tolist(),
                        "pairs": list(zip(qi[mask].tolist(), qj[mask].tolist())), "rel": rel})
    return out


# ---------------------------------------------------------------- witnesses
def owl_detect(images, dev, revision):
    """Per image: (boxes thousandths, scores, query index). Queries, threshold and NMS fixed in pe_common / constants."""
    import torch
    from torchvision.ops import nms
    from transformers import Owlv2ForObjectDetection, Owlv2Processor
    proc = Owlv2Processor.from_pretrained(OWL_REPO, revision=revision)
    model = Owlv2ForObjectDetection.from_pretrained(OWL_REPO, revision=revision).to(dev).eval()
    texts = [pc.OWL_QUERIES[c] for c in pc.CATEGORIES]
    out = []
    for im in images:
        im = im.convert("RGB")
        inputs = proc(text=[texts], images=im, return_tensors="pt").to(dev)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16, enabled=dev == "cuda"):
            res = model(**inputs)
        s = max(im.size)  # OWLv2 pads bottom/right to a square: post-process on the padded side, then divide by w, h
        post = getattr(proc, "post_process_object_detection", None) or proc.post_process_grounded_object_detection
        r = post(res, threshold=OWL_THRESHOLD, target_sizes=torch.tensor([[s, s]]))[0]
        boxes, scores, labels = r["boxes"].float().cpu(), r["scores"].float().cpu(), r["labels"].cpu()
        w, h = im.size
        norm = (boxes / torch.tensor([w, h, w, h]) * 1000).tolist()
        out.append({"boxes": [pc.clean_box(b) or [0, 0, 0, 0] for b in norm], "score": scores.tolist(),
                    "cat": labels.tolist(), "agnostic": nms(boxes, scores, NMS_IOU).tolist()})
    return out, (proc, model)


def florence_detect(images, dev, revision):
    """Native transformers Florence-2 (no remote code), fp16, task <OD>, greedy beams as in the model card."""
    import torch
    from transformers import AutoProcessor, Florence2ForConditionalGeneration
    proc = AutoProcessor.from_pretrained(FLO_NATIVE_REPO, revision=revision)
    dtype = torch.float16 if dev == "cuda" else torch.float32
    model = Florence2ForConditionalGeneration.from_pretrained(FLO_NATIVE_REPO, revision=revision, dtype=dtype).to(dev).eval()
    out = []
    for im in images:
        im = im.convert("RGB")
        inputs = proc(text="<OD>", images=im, return_tensors="pt").to(dev, dtype)
        with torch.no_grad():
            ids = model.generate(**inputs, max_new_tokens=1024, num_beams=3, do_sample=False)
        text = proc.batch_decode(ids, skip_special_tokens=False)[0]
        r = proc.post_process_generation(text, task="<OD>", image_size=im.size)["<OD>"]
        w, h = im.size
        boxes = [pc.clean_box([b[0] / w * 1000, b[1] / h * 1000, b[2] / w * 1000, b[3] / h * 1000]) for b in r["bboxes"]]
        out.append({"boxes": [b or [0, 0, 0, 0] for b in boxes]})
    return out, (proc, model)


def yoloe_load(dev, work):
    """YOLOE-v8-S in text mode with the eight OWLv2 queries; weights downloaded and sha-checked here, text encoder sha
    recorded (pinned for the full run). Returns (model, record)."""
    import urllib.request
    from ultralytics import YOLOE
    import ultralytics
    work.mkdir(parents=True, exist_ok=True)
    weights = work / "yoloe-v8s-seg.pt"
    urllib.request.urlretrieve(YOLOE_WEIGHTS[0], weights)
    require(sha(weights) == YOLOE_WEIGHTS[1], "yoloe_weights_sha")
    model = YOLOE(str(weights))
    text_model = getattr(model.model, "text_model", "mobileclip:blt")
    require(text_model == YOLOE_TEXT_MODEL, "yoloe_text_model")
    texts = [pc.OWL_QUERIES[c] for c in pc.CATEGORIES]
    cwd = os.getcwd()
    os.chdir(work)  # the text encoder is downloaded into the current folder by ultralytics
    try:
        t0 = time.perf_counter()
        model.set_classes(texts, model.get_text_pe(texts))
        prep = time.perf_counter() - t0
    finally:
        os.chdir(cwd)
    ts = sorted(work.rglob("mobileclip_blt.ts"))
    require(len(ts) == 1, "yoloe_text_encoder_file")
    record = {"package": ultralytics.__version__, "weights_url": YOLOE_WEIGHTS[0], "weights_sha256": YOLOE_WEIGHTS[1],
              "text_model": text_model, "text_encoder_sha256": sha(ts[0]), "queries": texts,
              "text_preparation_seconds": prep, "conf": YOLOE_CONF, "nms_iou_per_class": YOLOE_IOU,
              "agnostic_nms_iou": NMS_IOU, "max_det": YOLOE_MAX_DET, "imgsz": YOLOE_IMGSZ, "fp16": dev == "cuda",
              "executed": "detection and segmentation heads (masks computed by the -seg checkpoint, not used)"}
    return model, record


def yoloe_detect(model, images, dev):
    """Per image: boxes (thousandths), scores, query index, and the class-free list after NMS at NMS_IOU, as for OWLv2."""
    import torch
    from torchvision.ops import nms
    out = []
    for im in images:
        r = model.predict(im.convert("RGB"), conf=YOLOE_CONF, iou=YOLOE_IOU, max_det=YOLOE_MAX_DET, imgsz=YOLOE_IMGSZ,
                          quantize=16 if dev == "cuda" else None, device=0 if dev == "cuda" else "cpu",
                          verbose=False)[0]
        boxes = r.boxes.xyxy.float().cpu()
        scores, labels = r.boxes.conf.float().cpu(), r.boxes.cls.long().cpu()
        w, h = im.size
        norm = (boxes / torch.tensor([w, h, w, h]) * 1000).tolist()
        out.append({"boxes": [pc.clean_box(b) or [0, 0, 0, 0] for b in norm], "score": scores.tolist(),
                    "cat": labels.tolist(), "agnostic": nms(boxes, scores, NMS_IOU).tolist()})
    return out


def student_forward(model, enc, px=None, tokens=None):
    """The student as timed: no_grad and fp16 autocast around the encoder AND the head, as OWLv2 and YOLOE."""
    import torch
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        return model(enc.tokens(px)[0] if tokens is None else tokens)


def resolved_revision(repo):
    from huggingface_hub import HfApi
    return HfApi().model_info(repo).sha


# ---------------------------------------------------------------- measures
def gt_boxes(graph, cat=None):
    return [o["box"] for o in graph["objects"] if cat is None or o["cat"] == cat]


def student_images(preds, graphs, cat=None):
    if cat is None:
        return [(p["boxes"], p["score"], gt_boxes(g)) for p, g in zip(preds, graphs)]
    return [([b for b, c in zip(p["boxes"], p["cat"]) if c == cat], [s for s, c in zip(p["cat_score"], p["cat"]) if c == cat],
             gt_boxes(g, cat)) for p, g in zip(preds, graphs)]


def owl_images(preds, graphs, cat=None):
    if cat is None:
        return [([p["boxes"][i] for i in p["agnostic"]], [p["score"][i] for i in p["agnostic"]], gt_boxes(g))
                for p, g in zip(preds, graphs)]
    return [([b for b, c in zip(p["boxes"], p["cat"]) if c == cat], [s for s, c in zip(p["score"], p["cat"]) if c == cat],
             gt_boxes(g, cat)) for p, g in zip(preds, graphs)]


def relation_measures(preds, graphs, prior=None):
    """(a) predicate on matched pairs (recall@1 by predicate); (b) triplet recall@20 with IoU >= 0.5 on both boxes."""
    hit, tot, trip_hit, trip_tot = {}, {}, 0, 0
    for p, g in zip(preds, graphs):
        _, to_q = pc.greedy_assign(p["boxes"], p["score"], gt_boxes(g))
        pair_index = {pq: n for n, pq in enumerate(p.get("pairs", []))}
        for s, r, o in g["relations"]:
            name = (pc.RELATIONS + [pc.AUTRE_RELATION])[r]
            tot[name] = tot.get(name, 0) + 1
            if s in to_q and o in to_q:
                if prior is not None:
                    guess = prior.get((g["objects"][s]["cat"], g["objects"][o]["cat"]), prior["global"])
                else:
                    guess = int(np.argmax(p["rel"][pair_index[(to_q[s], to_q[o])]]))
                hit[name] = hit.get(name, 0) + int(guess == r)
        if prior is not None:
            continue
        cand = []
        for n, (i, j) in enumerate(p["pairs"]):
            for r in range(len(pc.RELATIONS)):
                cand.append((p["score"][i] * p["score"][j] * float(p["rel"][n, r]), i, j, r))
        top = sorted(cand, key=lambda x: (-x[0], x[1], x[2], x[3]))[:20]
        gtb = gt_boxes(g)
        for s, r, o in g["relations"]:
            if r == len(pc.RELATIONS):
                continue
            trip_tot += 1
            trip_hit += int(any(rr == r and pc.iou_matrix([p["boxes"][i]], [gtb[s]])[0, 0] >= 0.5
                                and pc.iou_matrix([p["boxes"][j]], [gtb[o]])[0, 0] >= 0.5 for _, i, j, rr in top))
    out = {"predicate_recall_at_1": {k: {"hits": hit.get(k, 0), "total": v, "judged": v >= 10} for k, v in sorted(tot.items())}}
    if prior is None:
        out["triplet_recall_at_20"] = trip_hit / trip_tot if trip_tot else None
    return out


def timing(fn, batches, reps=5, warm=1, counts=None):
    """counts: images per batch (default len(batch))."""
    counts = counts or [len(b) for b in batches]
    import torch
    for _ in range(warm):
        for b in batches:
            fn(b)
    runs = []
    for _ in range(reps):
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        t = time.perf_counter()
        for b in batches:
            fn(b)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        runs.append(sum(counts) / (time.perf_counter() - t))
    return {"images_per_second_median": float(np.median(runs)), "min": float(min(runs)), "max": float(max(runs)),
            "repetitions": reps}


# ---------------------------------------------------------------- sealed predictions (full) and their reading (mesures)
PRED_DIR = "predictions"


def query_pairs():
    """Ordered pairs (i, j), i != j, of the NQ queries in the order predict() emits them."""
    return [(i, j) for i in range(NQ) for j in range(NQ) if i != j]


def save_student(out, key, preds):
    """Boxes and scores as JSON, relation scores as one float32 array; the pairs are query_pairs()."""
    require(all(p["pairs"] == query_pairs() for p in preds), "pairs_order")
    write_json(out / PRED_DIR / f"{key}.json", [{k: p[k] for k in ("boxes", "score", "cat", "cat_score")} for p in preds])
    with open(out / PRED_DIR / f"{key}_rel.npy", "wb") as f:
        np.save(f, np.stack([np.asarray(p["rel"], dtype=np.float32) for p in preds]) if preds else np.zeros((0,)))


def load_student(root, key):
    preds = json.loads((root / PRED_DIR / f"{key}.json").read_text())
    rel = np.load(root / PRED_DIR / f"{key}_rel.npy", allow_pickle=False)
    pairs = query_pairs()
    for p, r in zip(preds, rel, strict=True):
        p["pairs"], p["rel"] = pairs, r
    return preds


def seal(out, record):
    """MANIFEST_PREDICTIONS.json: sha of every file written by the full stage, the plate included; written last."""
    files = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write_json(out / "MANIFEST_PREDICTIONS.json", {**record, "files": files})
    return sha(out / "MANIFEST_PREDICTIONS.json")


def check_receipt(root, receipt_path):
    """Before any number: every sealed file present and unchanged, and a receipt of both looks (wA:p1 and a Grok, each
    with viewed_at) on exactly this manifest, as phase 1 and P9-A."""
    manifest_path = root / "MANIFEST_PREDICTIONS.json"
    manifest = json.loads(manifest_path.read_text())
    for rel, digest in manifest["files"].items():
        require((root / rel).is_file() and sha(root / rel) == digest, f"sealed_file_missing_or_changed_{rel}")
    require(all(f"planche/{n}.jpg" in manifest["files"] for n in manifest["planche"]), "plate_not_sealed")
    receipt = json.loads(Path(receipt_path).read_text())
    looks = [x for x in receipt.get("regards") or [] if x.get("viewer") and x.get("viewed_at")]
    require(receipt.get("stage") == "planche_petit_eleve_regardee" and receipt.get("manifest_sha256") == sha(manifest_path),
            "plate_not_viewed")
    require(any(x["viewer"] == "wA:p1" for x in looks) and any(x["viewer"].startswith("Grok") for x in looks),
            "both_looks_required")
    return manifest, receipt


# ---------------------------------------------------------------- main
def main(a):
    if a.stage == "mesures":
        return mesures(a)
    import torch
    from PIL import Image
    torch.backends.cudnn.benchmark = False
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    require(dev == "cuda", "gpu_required")
    inp, out = Path(a.inputs).resolve(), Path(a.out).resolve()
    require(not out.exists() or not any(out.iterdir()), "output_not_empty")
    out.mkdir(parents=True, exist_ok=True)
    listes = json.loads((inp / "listes.json").read_text())
    if a.stage == "full":
        require(YOLOE_TEXT_SHA256 is not None, "yoloe_text_encoder_not_pinned_after_smoke")
    require(sha(inp / "listes.json") == LISTES_SHA256 and sha(inp / "noms.json") == NOMS_SHA256, "lists_sha")
    roles = preflight(inp, listes, a.stage)
    results = {"stage": a.stage, "versions": versions(), "gpu": torch.cuda.get_device_name()}
    by_name = {r["name"]: r for role in roles.values() for r in role}
    names = (listes["surapprentissage"] if a.stage == "smoke" else
             [r["name"] for r in roles["entrainement"] + roles["reglage"] + roles["evaluation"]])
    images = {n: Image.open(inp / "images" / f"{n}.jpg").convert("RGB") for n in names}
    sizes = {n: images[n].size for n in names}

    # (1) re-encoding, then identity with the stored 8x8 grid
    enc = Encoder(dev)
    tok28, tok8, ident = {}, {}, []
    grids = {}
    for i in range(0, len(names), 32):
        chunk = names[i:i + 32]
        t28, t8 = enc.tokens(enc.pixels([images[n] for n in chunk]))
        for k, n in enumerate(chunk):
            tok28[n], tok8[n] = t28[k], t8[k]
            r = by_name[n]
            if r["shard"] not in grids:
                grids[r["shard"]] = np.load(Path(a.encoder) / "grid" / f"{r['shard']}.npy", mmap_mode="r")
            stored = torch.from_numpy(np.asarray(grids[r["shard"]][r["row"]], dtype=np.float32))
            new = t8[k].float().cpu()
            cos = torch.nn.functional.cosine_similarity(stored, new, dim=1)
            ident.append({"name": n, "min_cell_cosine": float(cos.min()), "max_abs_diff": float((stored - new).abs().max())})
    results["identity_8x8"] = {"images": len(ident), "min_cell_cosine": min(x["min_cell_cosine"] for x in ident),
                               "max_abs_diff": max(x["max_abs_diff"] for x in ident), "rule": "min cell cosine >= 0.999"}
    require(results["identity_8x8"]["min_cell_cosine"] >= 0.999, "encoder_recipe_not_reproduced")
    budget("encode")
    graphs = {n: load_graph(inp / "graphes" / f"{n}.json") for n in names if by_name[n]["gemini_graph_sha256"]}

    def dataset(ns, side):
        tok = tok28 if side == 28 else tok8
        return [(tok[n].to(dev), make_target(graphs[n], *sizes[n], dev)) for n in ns]

    # (2) overfit control on 8 fixed training images: a failure is a technical failure, never "pas de signal"
    ov = listes["surapprentissage"]
    model, _, checks = train(28, 0, dataset(ov, 28), None, dev, steps=OVERFIT_STEPS)
    pred = predict(model, torch.stack([tok28[n].to(dev) for n in ov]), [sizes[n] for n in ov])
    rec = pc.pooled_recall(pc.recall_counts(student_images(pred, [graphs[n] for n in ov]), 30))
    xy = torch.rand(64, 4, generator=torch.Generator().manual_seed(7))
    xy = torch.stack([xy[:, [0, 2]].min(1).values, xy[:, [1, 3]].min(1).values,
                      xy[:, [0, 2]].max(1).values, xy[:, [1, 3]].max(1).values], 1)
    roundtrip = float((cxcywh_to_xyxy(xyxy_to_cxcywh(xy)) - xy).abs().max())
    probe = ([0, 0, 1000, 1000], [100, 200, 300, 900])
    for w, h in ((640, 480), (641, 480), (480, 641)):  # odd differences included (half-pixel case of Codex p4)
        roundtrip = max(roundtrip, max(abs(u - v) for b in probe for u, v in zip(unsquare_box(square_box(b, w, h), w, h), b))
                        / 1000)
    overfit = {"images": ov, "steps": OVERFIT_STEPS, "recall_at_30": rec, "first_loss": checks["first_loss"],
               "last_loss": checks["last_loss"], "grads_finite": checks["grads_finite"],
               "parameters_without_gradient_at_step1": checks["zero_grad_params_at_step1"],
               "box_roundtrip_max_error": roundtrip}
    overfit["passed"] = bool(rec >= 0.8 and checks["last_loss"] <= 0.5 * checks["first_loss"] and checks["grads_finite"]
                             and not checks["zero_grad_params_at_step1"] and roundtrip < 1e-5)
    results["overfit_control"] = overfit
    budget("overfit")
    model.eval()

    if a.stage == "smoke":
        two = [images[n] for n in ov[:2]]
        results["revisions"] = {OWL_REPO: OWL_REV, "florence_native": [FLO_NATIVE_REPO, FLO_REV],
                                "florence_source": list(FLO_SOURCE),
                                "resolved_now": {OWL_REPO: resolved_revision(OWL_REPO),
                                                 FLO_NATIVE_REPO: resolved_revision(FLO_NATIVE_REPO)}}
        o, _ = owl_detect(two, dev, OWL_REV)
        results["owlv2_smoke"] = [{"detections": len(x["score"]), "agnostic": len(x["agnostic"])} for x in o]
        try:
            f, _ = florence_detect(two, dev, FLO_REV)
            results["florence2_smoke"] = [{"boxes": len(x["boxes"])} for x in f]
        except Exception as e:  # recorded: Florence-2 is a descriptive witness
            results["florence2_smoke"] = f"unavailable: {type(e).__name__}: {e}"[:500]
        ymodel, results["yoloe"] = yoloe_load(dev, out / "yoloe-cache")
        results["yoloe_smoke"] = [{"detections": len(x["score"]), "agnostic": len(x["agnostic"])}
                                  for x in yoloe_detect(ymodel, two, dev)]
        shutil.rmtree(out / "yoloe-cache")
        px = enc.pixels([images[n] for n in ov]).to(dev)
        results["timing_smoke_student_full_b8"] = timing(lambda b: student_forward(model, enc, px=b), [px], reps=1)
        results["listes_sha256"], results["noms_sha256"] = sha(inp / "listes.json"), sha(inp / "noms.json")
        results["script_sha256"] = {f: sha(Path(__file__).parent / f) for f in ("pe_kaggle.py", "pe_common.py")}
        results["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        results["vram_peak_gib"] = torch.cuda.max_memory_allocated() / 2 ** 30
        results["wall_seconds"] = time.monotonic() - START
        write_json(out / "blanc.json", results)
        require(overfit["passed"], "overfit_control_failed_technical_failure")  # never a successful blank (Codex p4)
        print("PETIT_ELEVE_SMOKE_DONE_NO_TUNING_NO_EVALUATION")
        return
    if not overfit["passed"]:
        results["issue"] = pc.issue(None, None, None, technical_failure=True)
        write_json(out / "resultats.json", results)
        print("PETIT_ELEVE_TECHNICAL_FAILURE")
        return

    # (3) heads: 2 grids x 3 seeds, epoch chosen on the tuning loss; predictions written, not measured
    (out / PRED_DIR).mkdir()
    tr = [r["name"] for r in roles["entrainement"]]
    tu = [r["name"] for r in roles["reglage"]]
    ev = [r["name"] for r in roles["evaluation"] if r["gemini_graph_sha256"]]
    arms, models = {}, {}
    for side in (28, 8):
        data, tune = dataset(tr, side), dataset(tu, side)
        tok = tok28 if side == 28 else tok8
        for seed in SEEDS:
            model, history, _ = train(side, seed, data, tune, dev)
            model.eval()
            save_student(out, f"student_{side}x{side}_seed{seed}",
                         predict(model, torch.stack([tok[n].to(dev) for n in ev]), [sizes[n] for n in ev]))
            arms[f"{side}x{side}_seed{seed}"] = {"history": history}
            if (side, seed) == (28, 0):
                models["m0"] = model
    budget("heads")

    # (4) witnesses on the same evaluation images, outputs only
    train_boxes = [o["box"] for n in tr for o in graphs[n]["objects"]]
    protos, share = pc.kmeans_prototypes(train_boxes)
    pair_counts = {}
    for n in tr:
        g = graphs[n]
        for s, r, o in g["relations"]:
            key = (g["objects"][s]["cat"], g["objects"][o]["cat"])
            pair_counts.setdefault(key, np.zeros(NREL))[r] += 1
    glob = np.sum(list(pair_counts.values()), 0)
    write_json(out / PRED_DIR / "a_priori.json", {"protos": [list(map(float, b)) for b in protos],
                                                  "share": [float(x) for x in share],
                                                  "rel_prior": [[list(k), int(np.argmax(v))] for k, v in pair_counts.items()],
                                                  "rel_prior_global": int(np.argmax(glob))})
    owl, owl_models = owl_detect([images[n] for n in ev], dev, OWL_REV)
    write_json(out / PRED_DIR / "owlv2.json", owl)
    witnesses = {"florence2": None}
    try:
        flo, flo_models = florence_detect([images[n] for n in ev], dev, FLO_REV)
        write_json(out / PRED_DIR / "florence2.json", flo)
    except Exception as e:
        flo, flo_models = None, None
        witnesses["florence2"] = f"unavailable: {type(e).__name__}: {e}"[:500]
    ymodel, witnesses["yoloe"] = yoloe_load(dev, out.parent / "yoloe-cache")  # cache kept outside the sealed folder
    require(witnesses["yoloe"]["text_encoder_sha256"] == YOLOE_TEXT_SHA256, "yoloe_text_encoder_sha")
    write_json(out / PRED_DIR / "yoloe.json", yoloe_detect(ymodel, [images[n] for n in ev], dev))
    budget("witnesses")

    # (6) the seed-0 28x28 student on the 30 evaluation images with an S1b graph: agreement measured later, plate now
    allv = [r["name"] for r in roles["evaluation"] if r.get("s1b_graph_sha256")]
    m0 = models["m0"]
    pa = predict(m0, torch.stack([tok28[n].to(dev) for n in allv]), [sizes[n] for n in allv])
    save_student(out, "student_28x28_seed0_s1b30", pa)

    # (7) throughput on the fixed training timing corpus (no evaluation image); decoding excluded for every system;
    # every system timed under no_grad + fp16 autocast (Codex p4); the student's measured predictions stay float32
    tim = [images[n] for n in listes["chronometrage"]]
    t0 = time.perf_counter()
    px = [enc.pixels(tim[i:i + 32]) for i in range(0, len(tim), 32)]
    px = [x.to(dev) for x in px]
    timing_ = {"student_preprocess_cpu_images_per_second": len(tim) / (time.perf_counter() - t0)}
    tok_batches = [enc.tokens(b)[0] for b in px]
    timing_["student_full_b32"] = timing(lambda b: student_forward(m0, enc, px=b), px)
    timing_["student_heads_only_b32"] = timing(lambda t: student_forward(m0, enc, tokens=t), tok_batches)
    timing_["student_full_b1"] = timing(lambda b: student_forward(m0, enc, px=b), list(px[0][:32].split(1)))
    proc, owl_model = owl_models
    texts = [[pc.OWL_QUERIES[c] for c in pc.CATEGORIES]]
    owl_batch = None
    for bs in (32, 16, 8):
        try:
            t0 = time.perf_counter()
            owl_px = [proc(text=texts * len(tim[i:i + bs]), images=tim[i:i + bs], return_tensors="pt") for i in range(0, len(tim), bs)]
            prep = len(tim) / (time.perf_counter() - t0)
            owl_counts = [len(tim[i:i + bs]) for i in range(0, len(tim), bs)]
            owl_px = [x.to(dev) for x in owl_px]

            def owl_fwd(x):
                with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
                    return owl_model(**x)

            timing_["owlv2_full"] = timing(owl_fwd, owl_px, counts=owl_counts) | {"batch": bs, "preprocess_cpu_images_per_second": prep}
            owl_batch = bs
            break
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
    require(owl_batch is not None, "owlv2_timing_failed")
    timing_["yoloe_v8s_text_b32_with_preprocess"] = timing(
        lambda ims: ymodel.predict(ims, conf=YOLOE_CONF, iou=YOLOE_IOU, max_det=YOLOE_MAX_DET, imgsz=YOLOE_IMGSZ,
                                   quantize=16, device=0, verbose=False), [tim[i:i + 32] for i in range(0, len(tim), 32)])
    if flo_models is not None:
        fproc, fmodel = flo_models

        def flo_fwd(ims):
            x = fproc(text=["<OD>"] * len(ims), images=ims, return_tensors="pt").to(dev, torch.float16)
            with torch.no_grad():
                fmodel.generate(**x, max_new_tokens=1024, num_beams=3, do_sample=False)

        timing_["florence2_full_b8_with_preprocess"] = timing(flo_fwd, [tim[i:i + 8] for i in range(0, 32, 8)], reps=2)
    timing_["D"] = timing_["student_full_b32"]["images_per_second_median"] / timing_["owlv2_full"]["images_per_second_median"]
    timing_["note"] = ("student batch 32, OWLv2 at the largest batch <= 32 that fits, YOLOE batch 32 through its own "
                       "predictor (preprocessing, NMS and mask branch included); no_grad + fp16 for every system; images "
                       "decoded beforehand; student and OWLv2 preprocessing timed apart on CPU")
    write_json(out / "timing.json", timing_)
    budget("timing")

    # (9) plate BEFORE any number: 12 evaluation images, student (seed 0, 28x28) / Gemini / S1b drawn side by side
    from PIL import ImageDraw
    (out / "planche").mkdir()
    s1b = {n: load_graph(inp / "s1b" / f"{n}.json") for n in allv}
    for n in listes["planche"]:
        p = pa[allv.index(n)]
        panels = []
        for boxes in ([b for b, s in zip(p["boxes"], p["score"]) if s >= 0.5], gt_boxes(graphs[n]), gt_boxes(s1b[n])):
            im = images[n].copy()
            dr = ImageDraw.Draw(im)
            w, h = im.size
            for b in boxes:
                dr.rectangle([b[0] * w / 1000, b[1] * h / 1000, b[2] * w / 1000, b[3] * h / 1000], outline=(255, 0, 0), width=3)
            panels.append(im)
        w, h = panels[0].size
        sheet = Image.new("RGB", (3 * w, h), (255, 255, 255))
        for k, im in enumerate(panels):
            sheet.paste(im, (k * w, 0))
        sheet.save(out / "planche" / f"{n}.jpg", quality=90)
    results.update({"arms": arms, "witnesses": witnesses, "evaluation_images": ev, "s1b_images": allv,
                    "script_sha256": {f: sha(Path(__file__).parent / f) for f in ("pe_kaggle.py", "pe_common.py")},
                    "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                    "vram_peak_gib": torch.cuda.max_memory_allocated() / 2 ** 30, "wall_seconds": time.monotonic() - START,
                    "measures": None})
    write_json(out / "run.json", results)
    digest = seal(out, {"stage": "predictions_sealed", "planche": listes["planche"],
                        "panels": ["élève 28x28 graine 0, score >= 0.5", "Gemini", "S1b"],
                        "script_sha256": results["script_sha256"], "listes_sha256": LISTES_SHA256})
    print("PETIT_ELEVE_PREDICTIONS_SEALED_NO_MEASURE", digest)


def versions():
    import torch
    v = {"python": sys.version.split()[0], "torch": torch.__version__, "numpy": np.__version__}
    for name in ("transformers", "ultralytics", "open_clip_torch", "torchvision"):
        try:
            v[name] = __import__("importlib.metadata").metadata.version(name)
        except Exception:
            v[name] = None
    return v


def mesures(a):
    """CPU: the measures of PREINSCRIPTION.md and the D2 reading, from the sealed predictions, after the plate receipt."""
    inp, root, out = Path(a.inputs).resolve(), Path(a.predictions).resolve(), Path(a.out).resolve()
    require(not out.exists() or not any(out.iterdir()), "output_not_empty")
    manifest, receipt = check_receipt(root, a.receipt)
    require(manifest["script_sha256"] == {f: sha(Path(__file__).parent / f) for f in ("pe_kaggle.py", "pe_common.py")},
            "measures_with_other_scripts_than_the_sealed_run")
    out.mkdir(parents=True, exist_ok=True)
    listes = json.loads((inp / "listes.json").read_text())
    require(sha(inp / "listes.json") == LISTES_SHA256 and sha(inp / "noms.json") == NOMS_SHA256, "lists_sha")
    roles = preflight(inp, listes, "full")
    by_name = {r["name"]: r for role in roles.values() for r in role}
    run = json.loads((root / "run.json").read_text())
    ev, allv = run["evaluation_images"], run["s1b_images"]
    require(ev == [r["name"] for r in roles["evaluation"] if r["gemini_graph_sha256"]], "evaluation_list")
    ev_graphs = [load_graph(inp / "graphes" / f"{n}.json") for n in ev]
    results = {k: run[k] for k in ("stage", "versions", "gpu", "identity_8x8", "overfit_control", "arms", "witnesses")}
    results.update({"stage": "mesures", "predictions_manifest_sha256": receipt["manifest_sha256"], "receipt": receipt})
    prior = json.loads((root / PRED_DIR / "a_priori.json").read_text())
    protos, share = prior["protos"], prior["share"]
    rel_prior = {tuple(k): v for k, v in prior["rel_prior"]} | {"global": prior["rel_prior_global"]}
    owl = json.loads((root / PRED_DIR / "owlv2.json").read_text())
    flo_path = root / PRED_DIR / "florence2.json"
    flo = json.loads(flo_path.read_text()) if flo_path.is_file() else None
    yol = json.loads((root / PRED_DIR / "yoloe.json").read_text())
    timing_ = json.loads((root / "timing.json").read_text())

    # (5) measures on the 26 evaluation graphs (Gemini = reference of fidelity, not a human truth)
    prior_images = [(protos, share, gt_boxes(g)) for g in ev_graphs]
    counts_prior = pc.recall_counts(prior_images, 30)
    judged = [c for c in range(len(pc.CATEGORIES)) if sum(1 for g in ev_graphs for o in g["objects"] if o["cat"] == c) >= 10]
    owl_cat = {c: owl_images(owl, ev_graphs, c) for c in judged}
    owl_agn = owl_images(owl, ev_graphs)
    yol_agn = owl_images(yol, ev_graphs)
    results["witnesses_measures"] = {
        "a_priori": {"recall_at_30": pc.pooled_recall(counts_prior),
                     "relations": relation_measures([{"boxes": protos, "score": share}] * len(ev_graphs), ev_graphs,
                                                    prior=rel_prior)},
        "owlv2_base": {"recall_at_30": pc.pooled_recall(pc.recall_counts(owl_agn, 30)),
                       "ap50_agnostic": pc.average_precision(owl_agn),
                       "ap50_by_category": {pc.CATEGORIES[c]: pc.average_precision(owl_cat[c]) for c in judged},
                       "autre_objects_not_queried": sum(1 for g in ev_graphs for o in g["objects"]
                                                        if o["cat"] == len(pc.CATEGORIES))},
        "yoloe_v8s_text": {"recall_at_10": pc.pooled_recall(pc.recall_counts(yol_agn, 10)),
                           "recall_at_20": pc.pooled_recall(pc.recall_counts(yol_agn, 20)),
                           "recall_at_30": pc.pooled_recall(pc.recall_counts(yol_agn, 30)),
                           "ap50_agnostic": pc.average_precision(yol_agn),
                           "read_as": "descriptive column (D8): no veto on D2, OWLv2 stays the reference of the gate"}}
    if flo is not None:
        flo_imgs = [(f["boxes"], [1.0 - k / max(1, len(f["boxes"])) for k in range(len(f["boxes"]))], gt_boxes(g))
                    for f, g in zip(flo, ev_graphs)]
        results["witnesses_measures"]["florence2_base_od"] = {
            "recall_all_boxes": pc.pooled_recall(pc.recall_counts(flo_imgs, 10 ** 6)),
            "boxes_per_image": float(np.mean([len(f["boxes"]) for f in flo])), "scores": "none: output order only"}
    results["judged_categories"] = [pc.CATEGORIES[c] for c in judged]
    reading = {"delta": [], "low": [], "high": [], "g": [], "g_interval": []}
    for side in (28, 8):
        for seed in SEEDS:
            p = load_student(root, f"student_{side}x{side}_seed{seed}")
            imgs = student_images(p, ev_graphs)
            counts = pc.recall_counts(imgs, 30)
            cats = {c: student_images(p, ev_graphs, c) for c in judged}
            arm = results["arms"][f"{side}x{side}_seed{seed}"]
            arm.update({"recall_at_10": pc.pooled_recall(pc.recall_counts(imgs, 10)),
                        "recall_at_20": pc.pooled_recall(pc.recall_counts(imgs, 20)), "recall_at_30": pc.pooled_recall(counts),
                        "ap50_agnostic": pc.average_precision(imgs),
                        "ap50_by_category": {pc.CATEGORIES[c]: pc.average_precision(cats[c]) for c in judged},
                        "objects_per_image_score_ge_0.5": float(np.mean([sum(s >= 0.5 for s in x["score"]) for x in p])),
                        "relations": relation_measures(p, ev_graphs)})
            if side != 28:
                continue
            delta = pc.pooled_recall(counts) - pc.pooled_recall(counts_prior)
            ci = pc.bootstrap(lambda idx: pc.pooled_recall(counts, idx) - pc.pooled_recall(counts_prior, idx), len(ev),
                              seed=2030 + seed)
            g = pc.per_category(cats, judged) - pc.per_category(owl_cat, judged)
            gi = pc.bootstrap(lambda idx: pc.per_category(cats, judged, idx=idx) - pc.per_category(owl_cat, judged, idx=idx),
                              len(ev), seed=2040 + seed)
            arm["d2"] = {"delta": delta, "low": ci["low"], "high": ci["high"], "g": finite(g), "g_interval_descriptive": gi}
            for k, v in (("delta", delta), ("low", ci["low"]), ("high", ci["high"]), ("g", g), ("g_interval", gi)):
                reading[k].append(v)

    # (6) agreement with S1b on the 30 evaluation images (26 with a Gemini graph, 4 without), descriptive
    s1b = {n: load_graph(inp / "s1b" / f"{n}.json") for n in allv}
    pa = load_student(root, "student_28x28_seed0_s1b30")
    agree = {"with_gemini_graph": [], "without_gemini_graph": []}
    for n, p in zip(allv, pa, strict=True):
        key = "with_gemini_graph" if by_name[n]["gemini_graph_sha256"] else "without_gemini_graph"
        agree[key].append(pc.recall_counts([(p["boxes"], p["score"], gt_boxes(s1b[n]))], 30)[0])
    results["agreement_with_s1b_seed0_recall_at_30"] = {k: {"recall": pc.pooled_recall(v), "images": len(v)}
                                                         for k, v in agree.items()}
    results["timing"] = timing_

    # (8) D2 reading, rules fixed in pe_common
    loc, ap, dd = pc.states(reading["delta"], reading["low"], reading["high"],
                            [x if np.isfinite(x) else float("nan") for x in reading["g"]], timing_["D"])
    results["d2_reading"] = {"states": [loc, ap, dd], "issue": pc.issue(loc, ap, dd),
                             "per_seed": {k: [finite(x) if not isinstance(x, dict) else x for x in v]
                                          for k, v in reading.items()},
                             "read_as": "pas de signal = no justification of this campaign by this prototype; it refutes "
                                        "neither Haiku nor distillation, and adopts nothing automatically"}
    results["script_sha256"] = manifest["script_sha256"]
    write_json(out / "resultats.json", results)
    print("PETIT_ELEVE_DONE", results["d2_reading"]["issue"])


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser(description=__doc__)
    ap_.add_argument("--stage", choices=("smoke", "full", "mesures"), required=True)
    ap_.add_argument("--inputs", required=True)
    ap_.add_argument("--encoder", required=True)
    ap_.add_argument("--out", required=True)
    ap_.add_argument("--predictions")
    ap_.add_argument("--receipt")
    try:
        main(ap_.parse_args())
    except RuntimeError as error:
        print(f"PETIT_ELEVE_FAILED {error}", file=sys.stderr)
        sys.exit(1)
