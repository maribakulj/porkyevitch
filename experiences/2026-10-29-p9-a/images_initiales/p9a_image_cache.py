"""Remote CPU preparation of the twelve preregistered P9-A initial images.

No head, model, encoder, score, test file or Rijksmuseum input. Importing this
module does not prepare anything. Use the separate reviewed pilot.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from p9a_common import (Budget, DATASET, TRAIN, drop86, e3_hash, input_path, object_hash,
                        output_dir, read_json, require, runtime_gate, sha, write_json)

import numpy as np


def select_twelve(encoder, inventory, budget):
    """Read only train vector md5 members and train metadata; never vector x/grids."""
    labels, md5, where = [], [], []
    encoder = input_path(encoder)
    require(inventory["dataset"] == DATASET and inventory["version"] == 3, "train inventory identity")
    for shard, tag in enumerate(TRAIN):
        paths = {}
        for folder, suffix in (("grid", "json"), ("feats", "json"), ("feats", "npz")):
            relative = f"{folder}/{tag}.{suffix}"
            p = input_path(encoder / relative)
            require(p.is_relative_to(encoder) and sha(p) == inventory["files"][relative], "train source SHA")
            paths[folder, suffix] = p
        side = read_json(paths["grid", "json"])
        provenance = read_json(paths["feats", "json"])
        n = 8000 if shard < 10 else 6216
        require(side["manifest"] == provenance and provenance["dataset"] == DATASET and provenance["smoke"] == 0
                and provenance["shard"] == f"data/{tag}.parquet" and provenance["rows"] == side["rows"] == n,
                "train source provenance")
        require(len(side["labels"]) == n and e3_hash(side["labels"]) == provenance["labels_sha256"], "train label SHA")
        with np.load(paths["feats", "npz"], allow_pickle=False) as z:
            m = z["md5"]  # x is deliberately not accessed or unpacked
            require(m.shape == (n,) and m.dtype.kind == "U", "train md5 shape")
            m = m.tolist()
        require(e3_hash(m) == side["md5_sha256"], "train md5 alignment")
        md5.extend(m)
        labels.extend(side["labels"])
        where.extend((tag, row) for row in range(n))
        budget.check("train_metadata")
    require(len(md5) == 86216, "canonical row count")
    groups = sorted(set(md5))
    gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
    val = [i for i, m in enumerate(md5) if m in gval]
    reg = [i for i in val if hashlib.sha256(("p9-a/v1/validation/" + md5[i]).encode()).digest()[0] < 128]
    diag = set(val) - set(reg)
    require(len(val) == 4265 and len(md5) - len(val) == 81951, "historical split changed")
    require(sum(bool(drop86(labels[i])) for i in val) == 4241, "eligible validation count")
    require(all(sum(bool(drop86(labels[i])) for i in part) >= 1000 for part in (reg, diag)), "validation halves too small")
    selected = [i for i in reg if drop86(labels[i])][:12]
    require(len(selected) == 12, "initial selection incomplete")
    return [{"shard": where[i][0], "row": where[i][1], "md5": md5[i], "file": md5[i] + ".image"}
            for i in selected]


def extract(rows, out, budget):
    from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url
    import pyarrow.parquet as pq
    scratch = out / ".scratch"
    scratch.mkdir()
    source_metadata = []
    for tag in TRAIN:  # positive list; no repository listing or glob
        selected = [r for r in rows if r["shard"] == tag]
        if not selected:
            continue
        filename = f"data/{tag}.parquet"
        url = hf_hub_url(DATASET[0], filename, repo_type="dataset", revision=DATASET[1])
        metadata = get_hf_file_metadata(url, token=False)
        free = shutil.disk_usage(out).free
        require(metadata.commit_hash == DATASET[1] and isinstance(metadata.size, int) and
                0 < metadata.size <= 4_000_000_000 and metadata.size + 512 * (1 << 20) < free,
                "parquet provenance or disk budget")
        path = Path(hf_hub_download(DATASET[0], filename, repo_type="dataset", revision=DATASET[1],
                                   cache_dir=str(scratch / "hub"), token=False))
        require(path.resolve().is_relative_to(scratch.resolve()), "download outside owned scratch")
        require(path.stat().st_size == metadata.size, "parquet size mismatch")
        source_metadata.append({"file": filename, "revision": metadata.commit_hash,
                                "etag": metadata.etag, "bytes": metadata.size, "sha256": sha(path)})
        wanted = {r["row"]: r for r in selected}
        found = set()
        parquet = pq.ParquetFile(path)
        shard_index = TRAIN.index(tag)
        require(parquet.metadata.num_rows == (8000 if shard_index < 10 else 6216), "parquet canonical row count")
        base = 0
        for group in range(parquet.num_row_groups):
            size = parquet.metadata.row_group(group).num_rows
            group_rows = {r for r in wanted if base <= r < base + size}
            if group_rows:
                cursor = base
                for batch in parquet.iter_batches(batch_size=32, row_groups=[group], columns=["image"], use_threads=False):
                    for index in sorted(group_rows):
                        if cursor <= index < cursor + batch.num_rows:
                            image = batch.column(0)[index - cursor].as_py()
                            require(isinstance(image, dict) and isinstance(image.get("bytes"), bytes), "missing original image bytes")
                            content = image["bytes"]
                            row = wanted[index]
                            require(hashlib.md5(content).hexdigest() == row["md5"], "image md5 differs from features")
                            target = out / row["file"]
                            if target.exists():
                                require(target.read_bytes() == content, "same md5 has different original bytes")
                            else:
                                tmp = target.with_suffix(".tmp")
                                tmp.write_bytes(content)
                                os.replace(tmp, target)
                            row["bytes"] = len(content)
                            row["sha256"] = hashlib.sha256(content).hexdigest()
                            found.add(index)
                    cursor += batch.num_rows
                    budget.check("selected_parquet_rows")
                    if group_rows <= found:
                        break
            base += size
        require(found == set(wanted), "some exact selected rows are missing")
        parquet.close()
        # Remove this owned parquet/cache before requesting any other shard.
        shutil.rmtree(scratch / "hub")
    shutil.rmtree(scratch)
    require(all("sha256" in r for r in rows), "image cache incomplete")
    return source_metadata


def main(args):
    runtime_gate("image_cache")
    out = output_dir(args.out)
    budget = Budget(out, 3500)
    binding = read_json(input_path(args.binding))
    inventory_path = input_path(args.inventory)
    rows = select_twelve(binding["encoder_root"], read_json(inventory_path), budget)
    sources = extract(rows, out, budget)
    budget.check("cache_complete")
    # All images published first, manifest last. No synthetic fallback or substitute.
    result = {"dataset": DATASET, "rows": rows, "selection_sha256": object_hash(rows),
              "selection_rule": "P9-A v1: canonical first 12 eligible V-reg rows, full historical md5 split",
              "inventory_sha256": sha(inventory_path), "binding_sha256": sha(input_path(args.binding)),
              "source_parquets": sources, "technical_only": True, "no_model_or_scores": True}
    # Budget evidence belongs inside the sole manifest; the consumer ignores extra keys.
    result["resources"] = read_json(out / "budget.json")
    (out / "budget.json").unlink()
    write_json(out / "manifest.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binding", "inventory", "out"):
        parser.add_argument("--" + name, required=True)
    try:
        main(parser.parse_args())
    except Exception:
        print("P9A_IMAGE_CACHE_FAILED", file=sys.stderr)
        sys.exit(1)
