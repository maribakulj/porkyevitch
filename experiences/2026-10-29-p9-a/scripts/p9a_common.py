"""P9-A: protocol constants, exact E3 semantics, atomic IO and resource limits.

No module has an import-time experiment. CLI entry points are Kaggle-only.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import time

TRAIN = tuple(f"train-{i:05d}-of-00011" for i in range(11))
DATASET = ["davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"]
ICON_REV = "737ce365e3e6ab5302bafc22428ee37e57becee1"
TEXT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TEXT_REV = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
PREREG_SHA = "25f1040f5b657d7b94896cba41852f59c2f6e3042a555f798c126ca8698d3585"
B_SHA = "06e3de0fa7c2871f6ff132791aa7594ce22614a13dc5609cebf2c2a33019bcd6"
E3_SHA = "c954947c098621f053966e3023264fb6b716c169e5b5b653db68556976bb7f3a"
RUN_SHA = "8ad8479a9a24831ac78fb1ca0ba2bb32b4c989c82cba8f0e82cc4c1adb6046ec"
B_H = 0.5890847528448202
FEATURE_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|"
                  "square-grey128|448|bicubic|autocast-fp16|summary+meanspatial|l2-each-then-l2")
GRID_CONFIG = ("nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906|"
               "square-grey128|448|bicubic|autocast-fp16|spatial28x28|adaptive-avg-8x8|fp16")
ARMS = ("F", "controle_global", "A", "C")
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
TOKEN = re.compile(r"\([^)]*\)|[A-Z]{1,2}|\d")
_anc = {}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def ancestors(code):
    # Exact E3 behavior, including strip and colon handling.
    code = code.strip()
    if code not in _anc:
        parts, out = code.split(":"), {code}
        if all(PART.fullmatch(p) for p in parts):
            for p in parts:
                cur = ""
                for token in TOKEN.findall(p):
                    cur += token
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


def predictions(prob, vocab, threshold):
    import numpy as np
    return [drop86(most_specific([vocab[j] for j in np.flatnonzero(row >= threshold)])) for row in prob]


def alpha_zero(frozen_predictions, alpha, threshold):
    require(alpha == 0 and threshold == 0.65, "alpha=0 only permits the frozen B threshold")
    # Return directly: do not reconstruct probabilities or apply an envelope here.
    return frozen_predictions


def code_f1(truth, pred, codes):
    """Every fixed code stays in the denominator, including unsupported codes."""
    import numpy as np
    ix = {c: i for i, c in enumerate(codes)}
    tp = np.zeros(len(ix), dtype=np.int64)
    fp, fn = tp.copy(), tp.copy()
    for g, p in zip(truth, pred, strict=True):
        g, p = set(g), set(p)
        for collection, count in ((g & p, tp), (p - g, fp), (g - p, fn)):
            for c in collection:
                if c in ix:
                    count[ix[c]] += 1
    den = 2 * tp + fp + fn
    f = np.divide(2 * tp, den, out=np.zeros(len(ix), dtype=float), where=den != 0)
    return {"codes": len(ix), "supported_codes": int(((tp + fn) > 0).sum()),
            "positive_occurrences": int((tp + fn).sum()), "TP": int(tp.sum()),
            "FP": int(fp.sum()), "FN": int(fn.sum()),
            "macro_F1": float(f.mean()) if len(ix) else None,
            "micro_F1": float(2 * tp.sum() / den.sum()) if den.sum() else (0.0 if len(ix) else None)}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while data := f.read(8 << 20):
            h.update(data)
    return h.hexdigest()


def e3_hash(obj):
    return hashlib.sha256(json.dumps(obj).encode()).hexdigest()


def object_hash(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def input_path(path):
    p = Path(path).resolve(strict=True)
    require(Path("/kaggle/input") in p.parents, f"input outside Kaggle mount: {p}")
    require(not any(x.lower().startswith(("test-", "emb")) or "rijksmuseum" in x.lower()
                    or x.lower() == "lermolieff" for x in p.parts), f"forbidden input: {p}")
    return p


def output_dir(path):
    p = Path(path).resolve()
    require(Path("/kaggle/working") in p.parents, "output must be below /kaggle/working")
    require(shutil.disk_usage("/kaggle/working").free > 6_000_000_000, "less than 6 GB free")
    p.mkdir(parents=True, exist_ok=False)
    return p


def runtime_gate(stage):
    require(os.environ.get("P9A_REVIEWED_STAGE") == stage, "use the reviewed Kaggle pilot, not a direct entry point")
    require(re.fullmatch(r"[0-9a-f]{64}", os.environ.get("P9A_CONFIG_SHA256", "")) is not None,
            "missing reviewed pilot configuration identity")


class Budget:
    """External driver also kills the process at the hard wall deadline.

    Checks after every transfer/forward/backward/update; a resource violation is
    never an OOM fallback. No resource evidence is inferred from estimates.
    """
    def __init__(self, out, seconds):
        self.out, self.started, self.limit = Path(out), time.monotonic(), seconds
        self.events = []
        self.peak_disk = 0

    def check(self, phase, gpu=False):
        import psutil
        elapsed = time.monotonic() - self.started
        rss = psutil.Process().memory_info().rss
        # Linux ru_maxrss is KiB; Kaggle is mandatory for these entry points.
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        allocated = reserved = peak_allocated = peak_reserved = 0
        if gpu:
            import torch
            torch.cuda.synchronize()
            allocated, reserved = torch.cuda.memory_allocated(), torch.cuda.memory_reserved()
            peak_allocated = torch.cuda.max_memory_allocated()
            peak_reserved = torch.cuda.max_memory_reserved()
        size = sum(p.stat().st_size for p in self.out.rglob("*") if p.is_file())
        self.peak_disk = max(size, self.peak_disk)
        self.events.append({"phase": phase, "elapsed_s": elapsed, "rss_bytes": rss,
                            "rss_peak_bytes": peak_rss, "allocated_bytes": allocated,
                            "reserved_bytes": reserved, "peak_allocated_bytes": peak_allocated,
                            "peak_reserved_bytes": peak_reserved, "output_bytes": size})
        write_json(self.out / "budget.json", {"events": self.events, "peak_output_bytes": self.peak_disk,
                   "wall_limit_s": self.limit, "technical_only": True})
        require(elapsed <= self.limit, "wall budget exceeded")
        require(peak_rss <= 15 * (1 << 30), "RAM peak exceeds 15 GiB")
        require(psutil.virtual_memory().available >= 512 * (1 << 20), "insufficient system RAM")
        require(peak_allocated <= 12 * (1 << 30), "allocated VRAM peak exceeds 12 GiB")
        require(size <= 5_000_000_000, "output exceeds 5 GB")
        return self.events[-1]
