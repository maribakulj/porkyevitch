"""Phase-1 prediction seal. Deliberately contains no evaluation measure."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

import numpy as np

TRAIN = tuple(f"train-{i:05d}-of-00011" for i in range(11))
TEST = "test-00000-of-00001"
SYSTEMS = ("T0", "T_star", "TK", "T-niv", "TK-niv", "T-H", "T-Z", "T-D")
FULL_BANKS = ("icai_test", "rijks_dev", "rijks_test")
SMOKE_BANKS = ("icai_validation_smoke", "rijks_dev_smoke")
DATASET = ["davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"]
RADIO = "nvidia/C-RADIOv3-L"
REVISION = "9d0413465e8a91e67bbf2c1ad342815478d1b906"
FEATURE_CONFIG = f"{RADIO}@{REVISION}|square-grey128|448|bicubic|autocast-fp16|summary+meanspatial|l2-each-then-l2"
GRID_CONFIG = f"{RADIO}@{REVISION}|square-grey128|448|bicubic|autocast-fp16|spatial28x28|adaptive-avg-8x8|fp16"
FROZEN_SHA = "2424b778d0a3e7c36e0aeea7ce5db60fcc52bc1eaa6c52a057fd957b142de0ca"
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
TOKEN = re.compile(r"\([^)]*\)|[A-Z]{1,2}|\d")
_anc = {}


def require(condition, code):
    # Never interpolate a row, URL, object identifier or annotation in errors.
    if not condition:
        raise RuntimeError(code)


def ancestors(code):
    # Exact legacy E0-E3 notation parser, needed for inference and training votes.
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


def projected_predictions(probability, vocab, thresholds):
    require(probability.shape[1] == len(vocab), "prediction_vocabulary_shape")
    return [[c for c in most_specific([vocab[j] for j in np.flatnonzero(row >= thresholds)])
             if not c.strip().startswith("86")] for row in probability]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def object_sha(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def legacy_sha(obj):
    return hashlib.sha256(json.dumps(obj).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def bound(path):
    p = Path(path).resolve(strict=True)
    require(Path("/kaggle/input") in p.parents, "input_outside_kaggle_mount")
    return p


def fresh_or_resumable_output(path, identity):
    p = Path(path).resolve()
    require(Path("/kaggle/working") in p.parents, "output_outside_kaggle_working")
    p.mkdir(parents=True, exist_ok=True)
    if (p / "MANIFEST.json").exists():
        m = read_json(p / "MANIFEST.json")
        require(m["run_identity"] == identity, "sealed_run_identity_changed")
        expected = set(m["files"]) | {"MANIFEST.json"}
        require({f.name for f in p.iterdir()} == expected, "sealed_output_has_unexpected_files")
        for filename, info in m["files"].items():
            require(sha(p / filename) == info["sha256"], "sealed_prediction_sha_changed")
        return p, True
    workspace = p / ".work"
    if workspace.exists():
        require(read_json(workspace / "identity.json") == identity, "resume_identity_changed")
    else:
        require(not any(p.iterdir()), "unidentified_partial_output")
        workspace.mkdir()
        write_json(workspace / "identity.json", identity)
    return p, False


class Monitor:
    def __init__(self, root, seconds):
        self.root, self.start, self.seconds = Path(root), time.monotonic(), seconds
        self.events = []

    def check(self, phase):
        import psutil
        import torch
        torch.cuda.synchronize()
        elapsed = time.monotonic() - self.start
        rss = psutil.Process().memory_info().rss
        event = {"phase": phase, "wall_seconds": elapsed, "rss_bytes": rss,
                 "allocated_bytes": torch.cuda.memory_allocated(), "reserved_bytes": torch.cuda.memory_reserved(),
                 "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                 "peak_reserved_bytes": torch.cuda.max_memory_reserved()}
        self.events.append(event)
        write_json(self.root / ".work" / "resources.json", self.events)
        require(elapsed <= self.seconds, "wall_budget_exceeded")
        require(rss < 15 * (1 << 30) and psutil.virtual_memory().available > 512 * (1 << 20), "ram_budget_exceeded")
        require(event["peak_allocated_bytes"] <= 14 * (1 << 30), "gpu_memory_budget_exceeded")
        return event
