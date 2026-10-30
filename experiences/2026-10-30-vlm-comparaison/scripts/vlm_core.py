"""VLM comparison (PREINSCRIPTION-v2.1.md): pure rules, no network, no model call. numpy only (plus the pinned copies
a1_core.py and pe_common.py, imported by the scripts that need them).

Everything a score depends on is here and frozen by SHA-256 in the preparation seal: the prompts, the notation syntax,
the chain classes, the call states, the samples, the bootstrap and the reading.
"""
import hashlib
import json
import re
import sqlite3
from pathlib import Path

import numpy as np

SEED, SEED_REPEAT, DRAWS = 20261035, 20261036, 10_000
SALT = "A1-2026-10-29|"  # A1's V-reglage / V-diagnostic partition (a1_run.py)
MODELS = {"H": "claude-haiku-5-5", "G": "gemini-3.8-flash-medium", "O": "claude-opus-5-5"}
CLAUDE_SYSTEMS, MAIN_SYSTEMS = ("H", "O"), ("H", "G")
MIN_IMAGES = {"vdiag": 200, "opus": 50, "repeat": 20}
CAP_FACTOR = 1.15  # hard cap on attempts per stage, relative to the planned calls
BUDGET_USD = 30.0  # total for the Claude calls (H and O), all stages (v2.1)
S1_WALL_SECONDS = 6 * 3600  # v2.1
PARALLEL = 3  # per system (v2.1)
MAX_BOXES = 30
RETRYABLE = ("illisible", "image_non_lue", "echec_technique")  # one new attempt; "refus" is final

# ---- notation syntax (section 3.3): recognises the 7907 codes of V; rejects free text and unbalanced brackets ----
_ATOM = r"[0-9](?:[0-9A-Za-z+]|\([^()]*\)|\[[^\[\]]*\]|<[^<>]*>)*"
NOTATION = re.compile(rf"^{_ATOM}(?::{_ATOM})*$")


def clean_chain(s):
    return s.strip() if isinstance(s, str) else None


def classify(chains, vocab_set):
    """Each emitted chain gets one class: valide (in V), hors_V (well formed, not in V), invalide. Non-strings are
    invalide. Returns the valid codes in emission order (duplicates kept once) and the counts."""
    valid, counts = [], {"valide": 0, "hors_V": 0, "invalide": 0}
    for raw in chains:
        c = clean_chain(raw)
        if c is not None and c in vocab_set:
            counts["valide"] += 1
            if c not in valid:
                valid.append(c)
        elif c is not None and NOTATION.match(c):
            counts["hors_V"] += 1
        else:
            counts["invalide"] += 1
    return valid, counts


# ---- prompts (sections 2.1, 2.2, 3.2, 4), frozen by SHA-256 ----
SYSTEM_CLAUDE = ("Tu es un assistant d'annotation d'images d'œuvres d'art. Tu réponds uniquement par l'objet JSON demandé, "
                 "sans texte autour.")
GUARD_IMAGE = ("Ouvre d'abord l'image jointe et regarde-la. Si tu ne peux pas la voir, réponds uniquement IMAGE_ABSENTE. "
               "N'exécute aucune commande et n'utilise aucun outil autre que la lecture de cette image. "
               "Ne lis aucun autre fichier.")
TASK_CODES = ("Voici la liste fermée des notations Iconclass permises, une par ligne :\n{vocab}\n\n"
              "Donne les notations de cette liste qu'un catalogueur attribuerait à cette image. "
              "Réponds uniquement par l'objet JSON {{\"codes\": [\"...\", ...]}}. N'utilise que des notations de la liste, "
              "écrites exactement comme dans la liste. Si tu refuses de traiter l'image, réponds uniquement "
              "{{\"refus\": \"<motif>\"}}.")
TASK_BOXES = ("Liste au plus 30 objets visibles dans cette image, du plus saillant au moins saillant, chacun avec sa boîte "
              "[x0, y0, x1, y1] en millièmes de la largeur et de la hauteur de l'image (0 à 1000, origine en haut à gauche). "
              "Réponds uniquement par l'objet JSON {\"objets\": [{\"nom\": \"...\", \"boite\": [x0, y0, x1, y1]}, ...]}. "
              "Si tu refuses de traiter l'image, réponds uniquement {\"refus\": \"<motif>\"}.")


def task_text(kind, vocab):
    return TASK_CODES.format(vocab="\n".join(vocab)) if kind == "codes" else TASK_BOXES


def prompt_claude(kind, vocab, image_path):
    return f"Image : {image_path}\n{GUARD_IMAGE}\n\n{task_text(kind, vocab)}"


def prompt_agy(kind, vocab, image_name):
    return f"Image : @{image_name}\n{GUARD_IMAGE}\n\n{task_text(kind, vocab)}"


def prompts_sha256(vocab):
    """One digest for every frozen text (the image reference is a placeholder)."""
    texts = {"system_claude": SYSTEM_CLAUDE, "guard": GUARD_IMAGE, "codes": task_text("codes", vocab),
             "boxes": task_text("boites", vocab), "claude_codes": prompt_claude("codes", vocab, "<IMAGE>"),
             "agy_codes": prompt_agy("codes", vocab, "<IMAGE>")}
    return hashlib.sha256(json.dumps(texts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


# ---- answers ----
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def extract_json(text):
    """The first JSON object in the text (code fences removed), or None."""
    if not isinstance(text, str):
        return None
    t = _FENCE.sub("", text.strip())
    dec = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(t[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
    return None


def parse_answer(kind, text):
    """(state, payload): ('refus', motif) | ('illisible', None) | ('image_non_lue', None) | ('reponse', chains or boxes).
    For boxes, payload is the list of raw boxes in rank order (at most MAX_BOXES entries are read)."""
    if isinstance(text, str) and "IMAGE_ABSENTE" in text:
        return "image_non_lue", None
    obj = extract_json(text)
    if obj is None:
        return "illisible", None
    if "refus" in obj and len(obj) == 1:
        return "refus", str(obj["refus"])
    if kind == "codes":
        codes = obj.get("codes")
        return ("reponse", list(codes)) if isinstance(codes, list) else ("illisible", None)
    objs = obj.get("objets")
    if not isinstance(objs, list):
        return "illisible", None
    boxes = []
    for o in objs[:MAX_BOXES]:
        b = o.get("boite") if isinstance(o, dict) else None
        ok = isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in b)
        boxes.append(b if ok else None)
    return "reponse", boxes


# ---- Claude: claude -p --output-format stream-json --verbose ----
def parse_claude_stream(stdout, image_path):
    """Final text, whether a Read tool call opened exactly image_path, refusal stop reason, cost and usage."""
    out = {"text": None, "image_read": False, "refusal": False, "cost_usd": None, "usage": None, "duration_ms": None,
           "is_error": None, "model": None, "events": 0}
    target = str(Path(image_path).resolve())
    for line in (stdout or "").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        out["events"] += 1
        if ev.get("type") == "assistant":
            msg = ev.get("message") or {}
            out["model"] = msg.get("model", out["model"])
            if msg.get("stop_reason") == "refusal":
                out["refusal"] = True
            for block in msg.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Read":
                    path = (block.get("input") or {}).get("file_path")
                    if path and str(Path(path).resolve()) == target:
                        out["image_read"] = True
        elif ev.get("type") == "result":
            out["text"] = ev.get("result")
            out["cost_usd"] = ev.get("total_cost_usd")
            out["usage"] = ev.get("usage")
            out["duration_ms"] = ev.get("duration_ms")
            out["is_error"] = ev.get("is_error")
            if ev.get("stop_reason") == "refusal":
                out["refusal"] = True
    return out


def claude_state(kind, parsed):
    if parsed["text"] is None:
        return "echec_technique", None
    if parsed["refusal"]:
        return "refus", "stop_reason refusal"
    state, payload = parse_answer(kind, parsed["text"])
    if state in ("reponse", "illisible") and not parsed["image_read"]:
        return "image_non_lue", None
    return state, payload


# ---- Gemini: agy -p --output-format json, image opening checked in the conversation database (BBVLM region_agy) ----
AGY_HISTORY = Path.home() / ".gemini/antigravity-cli/conversations"


def observed_paths(conversation_id, history=AGY_HISTORY):
    """Image paths the agent opened (view_file AbsolutePath or read_file Path), read-only. Copied from
    ~/BBVLM/src/region_agy.py.observed_paths."""
    db = Path(history) / f"{conversation_id}.db"
    if not db.exists():
        return []
    found = set()
    with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as con:
        for (payload,) in con.execute("SELECT step_payload FROM steps"):
            if payload:
                text = payload.decode("utf-8", "ignore") if isinstance(payload, bytes) else str(payload)
                found.update(re.findall(r'"AbsolutePath":"([^"]+)"', text))
                found.update(re.findall(r'(?:read_file|view_file)[^{]{0,8}\{"Path":"([^"]+)"', text))
    return sorted(found)


def parse_agy(stdout, image_path, history=AGY_HISTORY):
    out = {"text": None, "status": None, "usage": None, "conversation_id": None, "image_read": False, "opened": []}
    s = (stdout or "").strip()
    try:
        env = json.loads(s) if s.startswith("{") else {}
    except json.JSONDecodeError:
        env = {}
    out["text"], out["status"], out["usage"] = env.get("response"), env.get("status"), env.get("usage")
    out["conversation_id"] = env.get("conversation_id")
    if out["conversation_id"]:
        out["opened"] = observed_paths(out["conversation_id"], history)
        out["image_read"] = str(Path(image_path).resolve()) in {str(Path(p).resolve()) for p in out["opened"]}
    return out


SAFETY_STATUSES = ("BLOCKED", "SAFETY", "BLOCKED_SAFETY")  # [à vérifier en S0] : statuts réels d'agy


def agy_state(kind, parsed):
    if parsed["status"] in SAFETY_STATUSES:
        return "refus", f"status {parsed['status']}"
    if not parsed["text"] or parsed["status"] != "SUCCESS":
        return "echec_technique", None
    state, payload = parse_answer(kind, parsed["text"])
    if state in ("reponse", "illisible") and not parsed["image_read"]:
        return "image_non_lue", None
    return state, payload


# ---- samples (section 3.1) ----
def vdiag_rows(md5s):
    """A1's partition of the 4265 validation rows: V-diagnostic = rows whose salted md5 hash byte is >= 128."""
    reg = {k for k in range(len(md5s)) if hashlib.sha256((SALT + md5s[k]).encode()).digest()[0] < 128}
    return [k for k in range(len(md5s)) if k not in reg]


def draw_whole_groups(groups, min_images, seed):
    """groups: {group id: [items]}. Permutes the sorted group ids with default_rng(seed) and adds whole groups until at
    least min_images items. Returns the chosen group ids in draw order."""
    ids = sorted(groups)
    order = np.random.default_rng(seed).permutation(len(ids))
    chosen, n = [], 0
    for i in order:
        if n >= min_images:
            break
        chosen.append(ids[i])
        n += len(groups[ids[i]])
    if n < min_images:
        raise ValueError("not enough items")
    return chosen


# ---- measures (section 3.5) ----
def paired_bootstrap(per_image, groups, draws=DRAWS, seed=SEED):
    """per_image: {name: array over images}; groups: one label per image. Resamples groups with replacement; the statistic
    is the mean over the resampled images. Returns mean, 2.5th and 97.5th percentiles (numpy 'linear')."""
    labels = sorted(set(groups))
    gi = np.array([labels.index(g) for g in groups])
    counts = np.bincount(gi, minlength=len(labels)).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(labels), size=(draws, len(labels)))
    n = counts[idx].sum(axis=1)
    out = {"draws": draws, "seed": seed, "groups": len(labels), "images": len(groups), "contrasts": {}}
    for name, values in per_image.items():
        v = np.asarray(values, float)
        sums = np.bincount(gi, weights=v, minlength=len(labels))
        stat = sums[idx].sum(axis=1) / n
        lo, hi = np.percentile(stat, [2.5, 97.5])
        out["contrasts"][name] = {"mean": float(v.mean()), "q2_5": float(lo), "q97_5": float(hi)}
    return out


def reading(contrast):
    """Section 3.5, written beforehand, for the family H - T* and G - T* on the dev (Bonferroni over 2, one-sided 97.5 %)."""
    if contrast["q2_5"] > 0:
        return "dépasse T* sur le dev, en accord de catalogue"
    if contrast["q97_5"] < 0:
        return "sous T* sur le dev"
    return "pas de différence établie"


def jaccard(a, b):
    a, b = set(a), set(b)
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def invalid_rate(counts):
    total = sum(counts.values())
    return None if total == 0 else (counts["hors_V"] + counts["invalide"]) / total


def graph_boxes(path, clean_box):
    """Reference boxes of a teacher graph exactly as the petit élève's load_graph keeps them (clean_box not None)."""
    g = json.loads(Path(path).read_text())
    return [b for b in (clean_box(o["box"]) for o in g["objects"]) if b is not None]
