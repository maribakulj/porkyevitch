"""Remote preparation only: pinned public text, full-fit frequencies, real thumbnails.

No image encoder and no image notices. Does not start the smoke runner.
MiniLM must already be cached at the pinned HF revision; network is disabled.
"""
import argparse
import html
import importlib.metadata
import io
import os
from pathlib import Path
import unicodedata
import hashlib

import numpy as np
import torch

from p9a_common import (TEXT_MODEL, TEXT_REV, ICON_REV, PREREG_SHA, DATASET, TRAIN,
                       Budget, ancestors, drop86, input_path, object_hash, output_dir,
                       read_json, require, runtime_gate, sha, write_json)
from p9a_inputs import TrainData, baseline_checkpoint

# Git blob SHA1 at ICON_REV. Only these public description files are opened.
ENGLISH_BLOBS = {
    "txt/en/txt_en_0_1.txt": "4335f2fd430b656509916b6952e12e3f39af0b92",
    "txt/en/txt_en_2_3.txt": "7938c9017de7755d907e2c8a747abceb7f45ce4e",
    "txt/en/txt_en_4.txt": "7b524547b7f3b5594de6d5bdbdb275668e43c668",
    "txt/en/txt_en_5_6_7_8.txt": "321cb4b88e9401a91926e05d3e44ff00d7c6ffbd",
    "txt/en/txt_en_9.txt": "1015fa24c62e2c2f08cef2509908a9fcebd6d5a4",
    "txt/en/txt_en_keys.txt": "9df9e30fdd327b10d4c0bdfbed19ffaeb593e009",
    "txt/en/txt_en_shakespeare.txt": "dcd1cf8320ba1e40e2e723ae411b55aea4d2baee",
}
MINILM_FILES = {
    "config.json": ("git", "72b987fd805cfa2b58c4c8c952b274a11bfd5a00"),
    "model.safetensors": ("sha256", "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"),
    "special_tokens_map.json": ("git", "e7b0375001f109a6b8873d756ad4f7bbb15fbaa5"),
    "tokenizer.json": ("git", "cb202bfe2e3c98645018a6d12f182a434c9d3e02"),
    "tokenizer_config.json": ("git", "c79f2b6a0cea6f4b564fed1938984bace9d30ff0"),
    "vocab.txt": ("git", "fb140275c155a9c7c5a3b3e0e77a9e839594a938"),
}


def descriptions(root):
    root = input_path(root)
    result, provenance = {}, []
    for relative, expected in ENGLISH_BLOBS.items():
        p = input_path(root / relative)
        require(p.is_relative_to(root), "description symlink escape")
        content = p.read_bytes()
        gitsha = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        require(gitsha == expected, f"pinned Iconclass blob mismatch: {relative}")
        provenance.append({"path": relative, "git_blob": gitsha, "sha256": sha(p)})
        for line in content.decode("utf-8-sig").splitlines():
            if not line:
                continue
            code, sep, description = line.partition("|")
            require(sep == "|" and bool(code) and bool(description), "invalid official description line")
            require(code not in result or result[code] == description, f"conflicting exact description: {code}")
            result[code] = description
    return result, provenance


def texts_for_vocab(data, dictionary):
    records = []
    for c in data.vocab:
        exact = c in dictionary
        if exact:
            text = dictionary[c]
        else:
            broader = sorted(ancestors(c) - {c}, key=lambda a: (len(ancestors(a)), a))
            descriptions_ = [dictionary[a] for a in broader if a in dictionary]
            text = f"Iconclass notation: {c}."
            if descriptions_:
                text += " Broader concepts: " + " ; ".join(descriptions_)
        records.append({"code": c, "exact": exact, "fallback": not exact,
                        "text": unicodedata.normalize("NFC", text)})
    return records


@torch.no_grad()
def prototypes(data, records, cache, budget, device):
    from transformers import AutoModel, AutoTokenizer
    from huggingface_hub import hf_hub_download
    # Verify bytes against public revision metadata BEFORE loading the model.
    model_sources = []
    for filename, (kind, expected) in MINILM_FILES.items():
        path = input_path(hf_hub_download(TEXT_MODEL, filename, revision=TEXT_REV, cache_dir=str(input_path(cache)),
                                         local_files_only=True, token=False))
        digest = sha(path)
        if kind == "git":
            content = path.read_bytes()
            observed = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        else:
            observed = digest
        require(observed == expected, f"pinned MiniLM file mismatch: {filename}")
        model_sources.append({"filename": filename, "sha256": digest, "revision_digest": expected})
    # local_files_only + fixed repo/revision: no trust_remote_code or credentials.
    kwargs = dict(revision=TEXT_REV, cache_dir=str(input_path(cache)), local_files_only=True,
                  trust_remote_code=False, token=False)
    tokenizer = AutoTokenizer.from_pretrained(TEXT_MODEL, **kwargs)
    tokenizer.truncation_side = "right"
    model = AutoModel.from_pretrained(TEXT_MODEL, use_safetensors=True, **kwargs).to(device).eval()
    require(model.config.hidden_size == 384, "MiniLM dimension")
    vectors = []
    for start in range(0, len(records), 64):
        batch = records[start:start + 64]
        texts = [r["text"] for r in batch]
        lengths = tokenizer(texts, padding=False, truncation=False, verbose=False)["input_ids"]
        for record, tokens in zip(batch, lengths, strict=True):
            record["wordpieces_with_specials"] = len(tokens)
            record["truncated"] = len(tokens) > 256
        encoded = tokenizer(texts, padding=True, truncation=True, max_length=256, return_tensors="pt").to(device)
        hidden = model(**encoded).last_hidden_state.float()
        mask = encoded.attention_mask.unsqueeze(-1).float()
        pooled = (hidden * mask).sum(1) / mask.sum(1).clamp_min(1e-9)
        vectors.append(torch.nn.functional.normalize(pooled, dim=-1).cpu().numpy())
        budget.check(f"text/{start}", gpu=device == "cuda")
    e = np.concatenate(vectors).astype(np.float32)
    d = e.copy()
    for c, parents in enumerate(data.parents):
        if parents:
            d[c] -= e[parents].mean(0)
    require(e.shape == d.shape == (7907, 384) and np.isfinite(d).all(), "prototype arrays")
    del model
    if device == "cuda":
        torch.cuda.empty_cache()
    return e, d, model_sources


def initial_board(data, binding, out):
    from PIL import Image, ImageOps
    first = [int(i) for i in data.reg if drop86(data.labels[i])][:12]
    require(len(first) == 12, "initial board needs twelve eligible V-reg rows")
    cache = input_path(binding["image_cache"])
    manifest_path = input_path(cache / "manifest.json")
    require(sha(manifest_path) == binding["image_manifest_sha256"], "image cache manifest SHA")
    manifest = read_json(manifest_path)
    require(manifest["dataset"] == DATASET, "image cache dataset revision")
    by_key = {}
    for r in manifest["rows"]:
        key = (r["shard"], r["row"], r["md5"])
        require(key not in by_key, "duplicate thumbnail provenance")
        by_key[key] = r
    directory = out / "planche_initiale"
    directory.mkdir()
    records, cards = [], []
    for position, i in enumerate(first):
        tag, row, md5 = data.identities([i])[0]
        require((tag, row, md5) in by_key, "missing required image: defer smoke")
        entry = by_key[tag, row, md5]
        require(entry["file"] == md5 + ".image", "image cache file must be md5.image")
        p = input_path(cache / entry["file"])
        require(p.is_relative_to(cache), "image cache symlink escape")
        content = p.read_bytes()
        require(hashlib.md5(content).hexdigest() == md5, "image bytes do not match feature md5")
        with Image.open(io.BytesIO(content)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((320, 320))
            image_path = directory / f"{position:02d}.png"
            im.save(image_path)
        record = {"global_row": i, "shard": tag, "parquet": f"data/{tag}.parquet", "row": row,
                  "md5": md5, "raw_labels": data.labels[i], "projected_truth": drop86(data.labels[i]),
                  "thumbnail": image_path.name, "thumbnail_sha256": sha(image_path)}
        records.append(record)
        cards.append(f'<article><img src="{image_path.name}" alt="image {position}"><p>' +
                     html.escape(f"{tag}:{row} md5={md5}") + "</p><p>" +
                     html.escape(" ; ".join(record["projected_truth"])) + "</p></article>")
    page = '<!doctype html><meta charset="utf-8"><title>P9-A — matériau initial V-réglage</title>'
    page += '<style>body{font:15px sans-serif}main{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}'
    page += 'article{border:1px solid #bbb;padding:10px;overflow-wrap:anywhere}img{max-width:100%}</style>'
    page += '<h1>P9-A : douze premières images V-réglage évaluables</h1><p>Aucune prédiction.</p><main>'
    (directory / "index.html").write_text(page + "".join(cards) + "</main>")
    board = {"dataset": DATASET, "rows": records, "html_sha256": sha(directory / "index.html")}
    write_json(directory / "manifest.json", board)
    return sha(directory / "manifest.json")


def prepare(args):
    runtime_gate("prepare")
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    binding = read_json(input_path(args.binding))
    out = output_dir(args.out)
    budget = Budget(out, 1800 if args.device == "cuda" else 3600)
    require(args.device in ("cpu", "cuda"), "device must be explicit")
    if args.device == "cuda":
        require(torch.cuda.is_available() and torch.cuda.device_count() == 1 and
                "T4" in torch.cuda.get_device_name(), "one visible T4 required")
    data = TrainData(binding, input_path(args.inventory), budget)
    baseline_checkpoint(binding, data)  # vocabulary equality before any text preparation
    manifest = data.manifest()
    write_json(out / "donnees.json", manifest)
    dictionary, dictionary_sources = descriptions(binding["iconclass_root"])
    records = texts_for_vocab(data, dictionary)
    e, d, model_sources = prototypes(data, records, binding["hf_cache"], budget, args.device)
    np.savez(out / "prototypes.npz", e=e, d=d)
    write_json(out / "textes.json", records)
    # Permutations for a future reviewed full runner; smoke itself uses canonical 128.
    for seed in range(3):
        rng = np.random.default_rng(seed)
        np.save(out / f"permutations_seed{seed}.npy", np.stack([rng.permutation(data.fit) for _ in range(10)]))
    board_sha = initial_board(data, binding, out)
    result = {"technical_only": True, "prereg_sha256": PREREG_SHA,
              "binding_sha256": sha(input_path(args.binding)), "inventory_sha256": sha(input_path(args.inventory)),
              "donnees_sha256": sha(out / "donnees.json"), "prototypes_sha256": sha(out / "prototypes.npz"),
              "texts_sha256": sha(out / "textes.json"), "initial_board_manifest_sha256": board_sha,
              "text_model": [TEXT_MODEL, TEXT_REV], "iconclass_revision": ICON_REV,
              "dictionary_sources": dictionary_sources, "model_sources": model_sources,
              "coverage": {"exact": sum(r["exact"] for r in records),
                           "fallback": sum(r["fallback"] for r in records),
                           "truncated": sum(r["truncated"] for r in records)},
              "permutations": {str(s): sha(out / f"permutations_seed{s}.npy") for s in range(3)},
              "versions": {p: importlib.metadata.version(p) for p in ("torch", "numpy", "transformers", "tokenizers")},
              "script_sha256": sha(__file__), "no_new_head_inference": True}
    write_json(out / "preparation.json", result)
    budget.check("preparation_finished", gpu=args.device == "cuda")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), required=True)
    prepare(parser.parse_args())
