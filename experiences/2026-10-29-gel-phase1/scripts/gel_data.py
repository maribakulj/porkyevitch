"""Prediction inputs. Test annotations never leave their opaque source file.

Training annotations are needed only for the historical nearest-neighbour vote.
Rijks rows are projected immediately onto image/provenance keys, never truths.
"""
from collections import Counter
import gc
import hashlib
import http.client
import io
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime

import numpy as np
import torch
from PIL import Image

from gel_common import (DATASET, FEATURE_CONFIG, FROZEN_SHA, GRID_CONFIG, RADIO, REVISION,
                        TEST, TRAIN, ancestors, bound, legacy_sha, object_sha, read_json,
                        require, sha, write_json)


def metadata(binding, inventory):
    documents = {}
    for name, expected in inventory["documents"].items():
        if name == "reference.json":
            p = bound(binding["reference_json"])
        else:
            group, filename = name.split("/")
            p = bound(Path(binding[group + "_root"]) / filename)
        require(sha(p) == expected, "published_document_sha")
        documents[name] = read_json(p)
    reference = documents["reference.json"]
    require(reference["encoder"]["feature_config"] == FEATURE_CONFIG and reference["T_star"]["name"] == "T-long",
            "reference_identity")
    for n in range(4):
        result, run = documents[f"e{n}/e{n}.json"], documents[f"e{n}/run.json"]
        require(result["technical_only"] is False and result["controls"]["passed"] is True,
                "phase1_not_complete")
        require(run["smoke"] == 0 and run["torch"] == "2.11.0+cu128" and run["numpy"] == "2.1.3",
                "historical_environment_identity")
        filename = ("e0_reference.py", "e1_decision.py", "e2_th.py", "e3_spatial.py")[n]
        require(run["script_sha256"] == inventory["source_scripts"][filename], "historical_script_identity")
    e0, e1, e2, e3 = (documents[f"e{n}/e{n}.json"] for n in range(4))
    require(e0["T_star"] == "T-long" and e0["t_long_sha256"] == inventory["weights"]["T_star"], "tstar_identity")
    require(e2["t_h_sha256"] == inventory["weights"]["T-H"] and
            all(e3[c]["sha256"] == inventory["weights"][c] for c in ("T-Z", "T-D")), "published_weights_identity")
    # Parameters are read, never searched or re-selected. No validation scores used.
    recipe = {"T0": {"epoch": reference["T0"]["epoch"], "threshold": reference["T0"]["threshold"]},
              "T_star": {"epoch": reference["T_star"]["epoch"], "threshold": reference["T_star"]["threshold"]},
              "TK": {k: e1["TK"][k] for k in ("alpha", "threshold")},
              "T-niv": {"thresholds": e1["T-niv"]["thresholds"]},
              "TK-niv": {k: e1["TK-niv"][k] for k in ("alpha", "thresholds")},
              "T-H": {k: e2["T-H"][k] for k in ("epoch", "threshold")},
              "T-Z": {k: e3["T-Z"][k] for k in ("epoch", "threshold")},
              "T-D": {k: e3["T-D"][k] for k in ("epoch", "threshold")}}
    paths = {"T0": Path(binding["t0_root"]) / "head.pt", "T_star": Path(binding["e0_root"]) / "t_long.pt",
             "T-H": Path(binding["e2_root"]) / "t_h.pt", "T-Z": Path(binding["e3_root"]) / "t_z.pt",
             "T-D": Path(binding["e3_root"]) / "t_d.pt"}
    for name, p in paths.items():
        require(sha(bound(p)) == inventory["weights"][name], "published_checkpoint_sha")
    require(sha(bound(binding["mldec_py"])) == inventory["mldec_sha256"], "decoder_source_sha")
    return recipe, paths


class TrainingReference:
    def __init__(self, root, inventory, vocab, monitor):
        self.root = bound(root)
        xs, labels, md5s, where = [], [], [], []
        for shard, tag in enumerate(TRAIN):
            expected = inventory["shards"][tag]
            for sub, extension, key in (("feats", "npz", "vec_sha256"), ("feats", "json", "feats_json_sha256"),
                                        ("grid", "json", "grid_json_sha256")):
                require(sha(bound(self.root / sub / f"{tag}.{extension}")) == expected[key], "train_source_sha")
            side = read_json(self.root / "grid" / f"{tag}.json")  # train-only labels
            manifest = read_json(self.root / "feats" / f"{tag}.json")
            n = 8000 if shard < 10 else 6216
            require(side["manifest"] == manifest and manifest["dataset"] == DATASET and manifest["smoke"] == 0
                    and manifest["feature_config"] == FEATURE_CONFIG and side["grid_config"] == GRID_CONFIG,
                    "train_source_configuration")
            require(manifest["rows"] == n == side["rows"] and len(side["labels"]) == n and
                    manifest["shard"] == f"data/{tag}.parquet", "train_source_alignment")
            require(legacy_sha(side["labels"]) == manifest["labels_sha256"], "train_annotation_sha")
            with np.load(self.root / "feats" / f"{tag}.npz", allow_pickle=False) as z:
                x, md5 = z["x"], z["md5"].tolist()
                require(x.shape == (n, 4096) and x.dtype == np.float16 and np.isfinite(x).all(), "train_vector_shape")
                require(len(md5) == n and legacy_sha(md5) == side["md5_sha256"], "train_md5_alignment")
                xs.append(x)
                md5s.extend(md5)
            labels.extend(side["labels"])
            where.extend((shard, row) for row in range(n))
            monitor.check("training_reference_verification")
        groups = sorted(set(md5s))
        gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
        validation = np.array([m in gval for m in md5s])
        require(int(validation.sum()) == 4265 and int((~validation).sum()) == 81951, "historical_training_split")
        counts = Counter(c for y, v in zip(labels, validation, strict=True) if not v for c in set(y))
        require(sorted({a for c, n in counts.items() if n >= 5 for a in ancestors(c)}) == vocab, "training_vocabulary_changed")
        self.vi = {c: j for j, c in enumerate(vocab)}
        self.ancestor_indices = []
        for y, v in zip(labels, validation, strict=True):
            if not v:
                indices = {self.vi[a] for c in y for a in ancestors(c) if a in self.vi}
                self.ancestor_indices.append(np.array(sorted(indices), dtype=np.int64))
        all_x = np.concatenate(xs)
        xs.clear()
        self.x = all_x[~validation].astype(np.float32)
        self.smoke_rows = np.flatnonzero(validation)[:32]
        self.smoke_x = all_x[self.smoke_rows].astype(np.float32)
        self.smoke_ids = [{"index": j, "shard": TRAIN[where[i][0]], "row": where[i][1], "md5": md5s[i]}
                          for j, i in enumerate(self.smoke_rows)]
        self.smoke_where = [where[i] for i in self.smoke_rows]
        self.fit_order_sha = object_sha([[TRAIN[where[i][0]], where[i][1], md5s[i]] for i in np.flatnonzero(~validation)])
        del all_x, labels
        gc.collect()
        monitor.check("training_reference_ready")

    def smoke_bank(self, inventory):
        grids = np.empty((32, 64, 1024), dtype=np.float16)
        for shard in sorted({s for s, _ in self.smoke_where}):
            tag = TRAIN[shard]
            p = bound(self.root / "grid" / f"{tag}.npy")
            require(sha(p) == inventory["shards"][tag]["grid_sha256"], "smoke_real_grid_sha")
            g = np.load(p, mmap_mode="r", allow_pickle=False)
            require(g.shape == (8000 if shard < 10 else 6216, 64, 1024) and g.dtype == np.float16, "smoke_grid_shape")
            for pos, (s, row) in enumerate(self.smoke_where):
                if s == shard:
                    grids[pos] = g[row]
            del g
        require(np.isfinite(grids).all(), "smoke_grid_nonfinite")
        return {"vectors": self.smoke_x, "grids": grids, "identities": self.smoke_ids}


def icai_test_bank(root, inventory):
    root = bound(root)
    expected = inventory["shards"][TEST]
    for folder, extension, key in (("feats", "npz", "vec_sha256"), ("feats", "json", "feats_json_sha256"),
                                   ("grid", "npy", "grid_sha256"), ("grid", "json", "grid_json_sha256")):
        require(sha(bound(root / folder / f"{TEST}.{extension}")) == expected[key], "icai_test_source_sha")
    # The grid JSON contains test annotations: hash its opaque bytes above,
    # NEVER parse it. The feature manifest has only provenance and a label hash.
    provenance = read_json(root / "feats" / f"{TEST}.json")
    require(provenance["dataset"] == DATASET and provenance["feature_config"] == FEATURE_CONFIG and
            provenance["rows"] == 788 and provenance["smoke"] == 0 and
            provenance["shard"] == f"data/{TEST}.parquet", "icai_test_provenance")
    with np.load(root / "feats" / f"{TEST}.npz", allow_pickle=False) as z:
        x, md5 = z["x"], z["md5"].tolist()
    g = np.load(root / "grid" / f"{TEST}.npy", mmap_mode="r", allow_pickle=False)
    require(x.shape == (788, 4096) and x.dtype == np.float16 and len(md5) == 788 and
            g.shape == (788, 64, 1024) and g.dtype == np.float16, "icai_test_shape")
    require(np.isfinite(x).all(), "icai_test_nonfinite_vectors")
    for start in range(0, 788, 64):
        require(np.isfinite(g[start:start + 64]).all(), "icai_test_nonfinite_grids")
    return {"vectors": x.astype(np.float32), "grids": g,
            "identities": [{"index": j, "shard": TEST, "row": j, "md5": m} for j, m in enumerate(md5)]}


def frozen_image_rows(path, mode):
    path = bound(path)
    require(sha(path) == FROZEN_SHA, "rijks_frozen_sha")
    document = read_json(path)
    splits = ("dev",) if mode == "smoke" else ("dev", "test")
    result = {}
    for split in splits:
        # Explicit whitelist: no truth, codes, support, actors or component edges.
        result[split] = [{k: row[k] for k in ("pid", "iiif", "image_sha256", "width", "height")}
                         for row in document[split]["items"]]
        require((300 <= len(result[split]) <= 319) if split == "dev" else (1200 <= len(result[split]) <= 1219),
                "rijks_frozen_structural_count")
        if mode == "smoke":
            result[split] = result[split][:32]
        for row in result[split]:
            u = urllib.parse.urlsplit(row["iiif"])
            require(u.scheme == "https" and u.netloc == "iiif.micr.io" and not u.query and not u.fragment and
                    u.path.endswith("/full/!800,800/0/default.jpg"), "rijks_frozen_image_url")
            require(re.fullmatch(r"[0-9a-f]{64}", row["image_sha256"]) is not None and
                    isinstance(row["pid"], str) and row["width"] > 0 and row["height"] > 0, "rijks_frozen_image_fields")
        require(len({r["pid"] for r in result[split]}) == len(result[split]), "rijks_duplicate_identifier")
    if mode != "smoke":
        require(not ({r["pid"] for r in result["dev"]} & {r["pid"] for r in result["test"]}), "rijks_split_overlap")
    del document
    return result


def verify_radio(cache, inventory):
    from huggingface_hub import hf_hub_download
    require(inventory["radio_repo"] == RADIO and inventory["radio_revision"] == REVISION, "radio_revision_identity")
    cache = bound(cache)
    provenance = {}
    for filename, expected in inventory["radio_files"].items():
        path = bound(hf_hub_download(RADIO, filename, revision=REVISION, cache_dir=str(cache),
                                    local_files_only=True, token=False))
        require(path.stat().st_size == expected["bytes"], "radio_file_size")
        digest = sha(path)
        if expected["kind"] == "git_blob_sha1":
            content = path.read_bytes()
            actual = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        else:
            actual = digest
        require(actual == expected["digest"], "radio_file_digest")
        provenance[filename] = digest
    return provenance


def square(image):
    image = image.convert("RGB")
    size = max(image.size)
    canvas = Image.new("RGB", (size, size), (128, 128, 128))
    canvas.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    return canvas.resize((448, 448), Image.BICUBIC)


@torch.no_grad()
def encode(model, processor, images):
    px = processor(images=[square(im) for im in images], return_tensors="pt", do_resize=False).pixel_values.cuda()
    with torch.autocast("cuda", dtype=torch.float16):
        summary, spatial = model(px)
    b = len(images)
    require(spatial.shape == (b, 784, 1024), "radio_patch_shape")
    v = torch.cat([torch.nn.functional.normalize(summary.float(), dim=-1),
                   torch.nn.functional.normalize(spatial.float().mean(1), dim=-1)], 1)
    v = torch.nn.functional.normalize(v, dim=-1).cpu().numpy().astype(np.float16)
    g = spatial.float().reshape(b, 28, 28, 1024).permute(0, 3, 1, 2)
    g = torch.nn.functional.adaptive_avg_pool2d(g, 8).permute(0, 2, 3, 1).reshape(b, 64, 1024)
    g = g.cpu().numpy().astype(np.float16)
    require(v.shape == (b, 4096) and np.isfinite(v).all() and np.isfinite(g).all(), "radio_output_invalid")
    return v, g


class Downloader:
    def __init__(self):
        self.last = 0.0

    def image(self, row):
        body = None
        for attempt in range(5):
            time.sleep(max(0.0, 1.0 - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            try:
                request = urllib.request.Request(row["iiif"], headers={"User-Agent": "caypollard/0.1 (research prototype)"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = response.read(64 * (1 << 20) + 1)
                break
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504):
                    break
                retry = error.headers.get("Retry-After", "0") if error.headers else "0"
                try:
                    delay = float(retry)
                except ValueError:
                    try:
                        delay = max(0.0, parsedate_to_datetime(retry).timestamp() - time.time())
                    except (TypeError, ValueError):
                        delay = 0.0
                if attempt < 4:
                    time.sleep(max(delay, 10 * (attempt + 1)))
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.HTTPException):
                if attempt < 4:
                    time.sleep(10 * (attempt + 1))
        require(body is not None and len(body) <= 64 * (1 << 20), "rijks_download_failed")
        require(hashlib.sha256(body).hexdigest() == row["image_sha256"], "rijks_image_bytes_changed")
        with Image.open(io.BytesIO(body)) as im:
            im.load()
            require(im.size == (row["width"], row["height"]), "rijks_image_size_changed")
            return im.copy()
