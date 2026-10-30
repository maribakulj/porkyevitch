"""Petit élève (jalon 5): shared rules, numpy only. Name table, boxes, metrics, paired bootstrap, D2 reading.

Everything here is fixed before training (PREINSCRIPTION.md). The name rules were written by hand from the names of the 106
training graphs only; they apply unchanged to any other name (tuning, evaluation, S1b): unknown names fall into "autre".
"""
import re

import numpy as np

CATEGORIES = ["personne", "surnaturel", "animal", "vetement_parure", "objet", "construction", "paysage", "texte_image"]
AUTRE = "autre"
# OWLv2 text queries, one per category, frozen (no prompt search on tuning or evaluation).
OWL_QUERIES = {"personne": "a person", "surnaturel": "an angel or a winged figure", "animal": "an animal",
               "vetement_parure": "a piece of clothing or jewellery", "objet": "a small object",
               "construction": "a building, furniture, a statue or a vehicle",
               "paysage": "a tree, a plant, a rock, water or the sky",
               "texte_image": "text, an inscription, a coat of arms or a framed picture"}

# Rules in priority order: the first rule whose phrase occurs as whole words in the name wins.
# A keyword also matches its plural in -s or -es. Body parts go to "autre" on purpose (not objects of the scene).
RULES = [
    ("texte_image", ["coat of arms"]),
    ("vetement_parure", ["hair ornament"]),
    ("objet", ["clock face", "clock hands", "birdcage", "lid"]),
    ("construction", ["barrel vault", "glass panel"]),
    (AUTRE, ["hand", "head", "beard", "face", "hair", "arm", "leg", "foot", "shoulder"]),
    ("objet", ["hobby horse", "animal skin", "dried fish", "beehive", "shell", "doll"]),
    ("surnaturel", ["winged", "angel", "putto", "putti", "cherub", "dragon", "devil", "demon"]),
    ("texte_image", ["coat of arms", "inscription", "text", "letter", "page", "handwriting", "newspaper", "stamp", "logo",
                     "cartouche", "plaque", "initial", "number", "card", "paper", "print", "illustration", "painting",
                     "picture", "frame", "medallion", "ornament", "border", "garland", "banner", "flag", "tablet",
                     "scroll", "lines", "heart", "circle"]),
    ("vetement_parure", ["bow tie", "top hat", "hat", "dress", "coat", "mitre", "cravat", "jacket", "necklace", "collar",
                         "garment", "cloak", "waistcoat", "shirt", "shoe", "breeches", "robe", "veil", "cap", "wig",
                         "ribbon", "kimono", "hairpin", "hair ornament", "headdress", "handkerchief", "doublet", "boot",
                         "pouch", "helmet", "sandal", "sweater", "shorts", "button", "tassel", "bandolier", "ring",
                         "wreath", "halo", "crown", "armour", "armor"]),
    ("construction", ["statue", "bust", "architectural model", "equestrian statue"]),
    ("personne", ["man", "men", "woman", "women", "child", "children", "people", "person", "girl", "boy", "soldier",
                  "crowd", "horseman", "rider", "figure", "stonemason", "saint", "king", "queen", "monk", "nun",
                  "procession", "baby", "infant"]),
    ("animal", ["animal", "horse", "dog", "cow", "ox", "bird", "sheep", "goat", "duck", "pig", "donkey", "calf", "hare",
                "eagle", "cattle", "seahorse", "fish", "eel", "bear", "rooster", "peacock", "swan", "lion", "cat",
                "deer", "snake", "serpent", "lamb", "bull", "camel", "monkey"]),
    ("objet", ["staff", "book", "sword", "cross", "key", "shield", "spear", "bow", "club", "scourge", "torch", "rod",
               "quill", "pipe", "stick", "ruler", "pole", "crosier", "halberd", "musket", "matchcord", "scabbard",
               "knife", "hammer", "palette", "umbrella", "horn", "quiver", "anchor", "net", "basket", "lantern", "cup",
               "dish", "bowl", "plate", "pot", "jug", "urn", "bread", "fruit", "cherries", "bouquet", "palm branch",
               "candle", "gridiron", "bone", "balloon", "string", "drum", "barrel", "box", "chest", "inkwell",
               "inkstand", "spectacles", "clock", "sphere", "globe", "lamp", "cord", "clip", "bubble", "bedding",
               "cushion", "carpet", "skull", "vase", "bottle", "glass", "musical instrument", "lute", "trumpet"]),
    ("construction", ["building", "window", "table", "wall", "tower", "curtain", "drapery", "column", "pedestal",
                      "bridge", "roof", "balustrade", "door", "doorway", "floor", "church", "throne", "chair",
                      "armchair", "altar", "bed", "cradle", "fireplace", "cupboard", "desk", "counter", "canopy",
                      "baldachin", "dome", "staircase", "portal", "plaza", "arcade", "vault", "ceiling", "ruins",
                      "house", "cottage", "town", "city", "tent", "fountain", "trough", "fence", "post", "beam",
                      "timbers", "platform", "balcony", "terrace", "base", "carriage", "cart", "chariot", "wheel", "boat",
                      "sailboat", "ship", "steamship", "breakwater", "opening", "panel", "basin", "stone block", "ribs",
                      "book stand", "water wheel", "pile of wood", "arch"]),
    ("paysage", ["tree", "cloud", "sky", "ground", "water", "hill", "hillside", "mountain", "rock", "rocky outcrop",
                 "cliff", "plant", "foliage", "sea", "river", "riverbed", "cave", "bush", "bushes", "shore", "grass",
                 "moon", "star", "path", "sand dunes", "branch", "field", "waterfall", "reeds", "stream", "landscape",
                 "bank", "smoke", "fire", "flames", "garden", "flower", "sun"]),
]


def _words(text):
    return re.findall(r"[a-z]+", text.lower())


def _phrase_in(phrase, words):
    p = _words(phrase)
    for i in range(len(words) - len(p) + 1):
        if all(w in (k, k + "s", k + "es") for w, k in zip(words[i:i + len(p)], p)):
            return True
    return False


def categorie(name):
    """(category, rule index) for a free name; (AUTRE, None) when no rule fires."""
    words = _words(name)
    for k, (cat, phrases) in enumerate(RULES):
        if any(_phrase_in(p, words) for p in phrases):
            return cat, k
    return AUTRE, None


def name_table(names):
    """{name: {"category", "rule", "count"}} for a Counter-like mapping of names."""
    out = {}
    for n in sorted(names):
        c, k = categorie(n)
        out[n] = {"category": c, "rule": k, "count": int(names[n])}
    return out


# Relations v0: the 13 teacher predicates with >= 20 training occurrences. All others are kept as one "autre_relation"
# output, never turned into "no relation". Names are the teacher's, unchanged.
RELATIONS = ["left of", "above", "inside", "behind", "right of", "on", "stands on", "wears", "holds", "below",
             "in front of", "looks at", "sits on"]
AUTRE_RELATION = "autre_relation"


def relation_class(pred):
    p = " ".join(_words(pred))
    return p if p in RELATIONS else AUTRE_RELATION


# ---- Boxes: [x0, y0, x1, y1] in thousandths of width and height ----
def clean_box(box):
    """Ordered and clipped to [0, 1000]; None when degenerate (zero width or height)."""
    x0, y0, x1, y1 = (min(max(float(v), 0.0), 1000.0) for v in box)
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    return None if x1 - x0 <= 0 or y1 - y0 <= 0 else [x0, y0, x1, y1]


def iou_matrix(a, b):
    a, b = np.asarray(a, float).reshape(-1, 4), np.asarray(b, float).reshape(-1, 4)
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    lt = np.maximum(a[:, None, :2], b[None, :, :2])
    rb = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.prod(np.clip(rb - lt, 0, None), axis=2)
    area = lambda x: (x[:, 2] - x[:, 0]) * (x[:, 3] - x[:, 1])
    return inter / (area(a)[:, None] + area(b)[None, :] - inter)


def greedy_assign(pred_boxes, scores, gt_boxes, thr=0.5):
    """COCO-style: predictions by decreasing score (ties: index), each takes the free reference box of highest IoU >= thr
    (ties: lower index). Returns (order, {reference index: prediction index})."""
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    iou = iou_matrix([pred_boxes[i] for i in order], gt_boxes)
    free = np.ones(len(gt_boxes), bool)
    assign = {}
    for r in range(len(order)):
        if not free.any() or not iou.shape[1]:
            break
        cand = np.where(free, np.nan_to_num(iou[r], nan=-1.0), -1.0)
        j = int(np.argmax(cand))
        if cand[j] >= thr:
            assign[j], free[j] = order[r], False
    return order, assign


def greedy_match(pred_boxes, scores, gt_boxes, thr=0.5):
    """Returns (tp flags in score order, scores in that order)."""
    order, assign = greedy_assign(pred_boxes, scores, gt_boxes, thr)
    matched = set(assign.values())
    return np.array([i in matched for i in order], bool), [scores[i] for i in order]


def recall_counts(images, k, thr=0.5):
    """images: [(pred_boxes, scores, gt_boxes)]. Per image (matched among its top-k, number of reference boxes)."""
    out = []
    for boxes, scores, gts in images:
        top = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]
        tp, _ = greedy_match([boxes[i] for i in top], [scores[i] for i in top], gts, thr)
        out.append((int(tp.sum()), len(gts)))
    return out


def pooled_recall(counts, idx=None):
    idx = range(len(counts)) if idx is None else idx
    m, n = sum(counts[i][0] for i in idx), sum(counts[i][1] for i in idx)
    return m / n if n else float("nan")


def average_precision(images, thr=0.5, idx=None):
    """AP at IoU thr pooled over images (101-point interpolation, COCO). images: [(pred_boxes, scores, gt_boxes)]."""
    idx = range(len(images)) if idx is None else idx
    flags, scores, n_gt = [], [], 0
    for i in idx:
        boxes, s, gts = images[i]
        tp, ordered = greedy_match(boxes, s, gts, thr)
        flags += list(tp)
        scores += ordered
        n_gt += len(gts)
    if n_gt == 0:
        return float("nan")
    order = np.argsort(-np.asarray(scores, float), kind="stable")
    tp = np.asarray(flags, bool)[order]
    ctp, cfp = np.cumsum(tp), np.cumsum(~tp)
    recall = ctp / n_gt
    precision = ctp / np.maximum(ctp + cfp, 1)
    precision = np.maximum.accumulate(precision[::-1])[::-1] if len(precision) else precision
    ap = 0.0
    for r in np.linspace(0, 1, 101):
        hit = np.nonzero(recall >= r)[0]
        ap += float(precision[hit[0]]) if len(hit) else 0.0
    return ap / 101


def per_category(images_by_cat, judged, thr=0.5, idx=None):
    """Mean AP over the judged categories. images_by_cat: {cat: [(pred_boxes, scores, gt_boxes)] per image}."""
    if not judged:
        return float("nan")
    return float(np.mean([float(average_precision(images_by_cat[c], thr, idx)) for c in judged]))


def bootstrap(stat, n_images, draws=2000, seed=0):
    """Paired bootstrap over images: the same resampled images for every term of stat(idx). Quantiles 2.5 / 97.5 %."""
    rng = np.random.default_rng(seed)
    vals = np.array([stat(rng.integers(0, n_images, n_images)) for _ in range(draws)], float)
    vals = vals[np.isfinite(vals)]
    if not len(vals):
        return {"low": None, "high": None, "draws": 0}
    return {"low": float(np.quantile(vals, 0.025)), "high": float(np.quantile(vals, 0.975)), "draws": int(len(vals))}


# ---- A priori witness: 30 box prototypes learnt on the training boxes ----
def kmeans_prototypes(boxes, k=30, iters=50, seed=2031):
    """Deterministic k-means on (cx, cy, w, h); score of a prototype = share of training boxes in its cluster."""
    b = np.asarray(boxes, float)
    x = np.stack([(b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2, b[:, 2] - b[:, 0], b[:, 3] - b[:, 1]], 1)
    centres = x[np.random.default_rng(seed).choice(len(x), k, replace=False)]
    for _ in range(iters):
        lab = np.argmin(((x[:, None] - centres[None]) ** 2).sum(2), 1)
        centres = np.stack([x[lab == j].mean(0) if (lab == j).any() else centres[j] for j in range(k)])
    lab = np.argmin(((x[:, None] - centres[None]) ** 2).sum(2), 1)
    share = np.bincount(lab, minlength=k) / len(x)
    protos = [[c[0] - c[2] / 2, c[1] - c[3] / 2, c[0] + c[2] / 2, c[1] + c[3] / 2] for c in centres]
    return protos, share.tolist()


# ---- D2 reading, fixed in advance (PREINSCRIPTION.md section 5) ----
GAIN, AP_MARGIN = 0.15, -0.05


def states(delta, low, high, g, d):
    """delta, low, high, g: one value per seed (g may hold nan when no category is judged); d: throughput ratio."""
    if all(x >= GAIN and lo > 0 for x, lo in zip(delta, low)):
        loc = "Loc+"
    elif all(hi < GAIN for hi in high):
        loc = "Loc-"
    else:
        loc = "Loc?"
    finite = [x for x in g if np.isfinite(x)]
    if len(finite) == len(g) and all(x >= AP_MARGIN for x in g):
        ap = "AP+"
    elif len(finite) == len(g) and all(x < AP_MARGIN for x in g):
        ap = "AP-"
    else:
        ap = "AP?"
    return loc, ap, "D+" if d >= 1 else "D-"


def issue(loc, ap, d, technical_failure=False):
    if technical_failure:
        return "panne technique"
    if loc == "Loc-":
        return "pas de signal"
    if loc == "Loc?":
        return "indécidable"
    return {("AP+", "D+"): "signal", ("AP+", "D-"): "pas de signal", ("AP-", "D-"): "pas de signal",
            ("AP-", "D+"): "indécidable"}.get((ap, d), "indécidable")
