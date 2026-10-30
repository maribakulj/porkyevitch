"""Original bytes of the 100 « confident absent » VALIDATION images of B = T-Z, for the look « cataloguer's omission or
true error » by wA:p1 then Grok (porkyevitch-maths, experiences/2026-10-30-diagnostic-tete). Kaggle CPU.
Same scheme as the reviewed tirage_pilote.py (graphes-gemini, sha 42e6efc4...).

Usage: extraire_confiants_absents.py DIAG ENC ICONCLASS OUT
  DIAG       diagnostic.json of the full diagnostic run (pinned sha below); sample = systems.B_TZ.confident_absent_p_ge_0.9
  ENC        full output of caypollard-encode-cradio v3 (feats/<train shard>.npz, md5 field only)
  ICONCLASS  root of the Iconclass data repository holding txt/en/*.txt (git blobs pinned as in P9-A)
  OUT        images/vNNN.<ext> (original bytes, sample order), regard.json, run.json
Steps:
  (1) the sample is read from the pinned diagnostic.json; each (shard, row, md5) must be a train-* row of the series'
      VALIDATION (default_rng(0).random(len(groups)) < 0.05 on the sorted md5 of the 86,216 train rows), checked on the
      encoder's md5 field; never the test shard;
  (2) each image read from the dataset at the pinned revision, md5 checked against the sample, bytes written unchanged;
      its raw labels read from the same parquet row;
  (3) descriptions from the official English Iconclass texts (pinned blobs); a code without its own text gets
      « Iconclass notation: C. Broader concepts: ... » built from its ancestors, as P9-A's texts_for_vocab; keys with two
      different official texts are dropped (rule of P9-A);
  (4) control: the predicted code is absent from the closure of the truth without 86 (definition of the sample).
regard.json holds, per image: file, md5, shard, row, predicted code, p, its description, and the truth (codes and
descriptions). It is for looking, not for scoring; it is never given to a model.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import sys

import numpy as np

REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
TRAIN = [f"train-{i:05d}-of-00011" for i in range(11)]
DIAG_SHA256 = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
ENGLISH_BLOBS = {  # as p9a_prepare.py
    "txt/en/txt_en_0_1.txt": "4335f2fd430b656509916b6952e12e3f39af0b92",
    "txt/en/txt_en_2_3.txt": "7938c9017de7755d907e2c8a747abceb7f45ce4e",
    "txt/en/txt_en_4.txt": "7b524547b7f3b5594de6d5bdbdb275668e43c668",
    "txt/en/txt_en_5_6_7_8.txt": "321cb4b88e9401a91926e05d3e44ff00d7c6ffbd",
    "txt/en/txt_en_9.txt": "1015fa24c62e2c2f08cef2509908a9fcebd6d5a4",
    "txt/en/txt_en_keys.txt": "9df9e30fdd327b10d4c0bdfbed19ffaeb593e009",
    "txt/en/txt_en_shakespeare.txt": "dcd1cf8320ba1e40e2e723ae411b55aea4d2baee",
}
# Parser of the series (E3), unchanged
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
TOKEN = re.compile(r"\([^)]*\)|[A-Z]{1,2}|\d")


def ancestors(code):
    code = code.strip()
    parts = code.split(":")
    out = {code}
    if all(PART.fullmatch(p) for p in parts):
        for p in parts:
            cur = ""
            for t in TOKEN.findall(p):
                cur += t
                out.add(cur)
    return out


def drop86(codes):
    return [c for c in codes if not c.strip().startswith("86")]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def dictionary(root):
    texts, provenance = {}, []
    for relative, expected in ENGLISH_BLOBS.items():
        content = (root / relative).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest() == expected, relative
        provenance.append({"path": relative, "git_blob": expected})
        for line in content.decode("utf-8-sig").splitlines():
            if line:
                code, sep, text = line.partition("|")
                assert sep == "|" and code and text, relative
                texts.setdefault(code, set()).add(text)
    return {c: t.pop() for c, t in texts.items() if len(t) == 1}, provenance


def describe(code, texts):
    if code in texts:
        return {"exact": True, "text": texts[code]}
    broader = sorted(ancestors(code) - {code}, key=lambda a: (len(ancestors(a)), a))
    found = [texts[a] for a in broader if a in texts]
    text = f"Iconclass notation: {code}."
    if found:
        text += " Broader concepts: " + " ; ".join(found)
    return {"exact": False, "text": text}


def main(diag, enc, iconclass, out):
    diag, enc, iconclass, out = map(Path, (diag, enc, iconclass, out))
    assert sha(diag) == DIAG_SHA256, "diagnostic.json is not the pinned one"
    sample = json.load(open(diag))["systems"]["B_TZ"]["confident_absent_p_ge_0.9"]["sample"]
    assert len(sample) == 100 and all(s["shard"] in TRAIN for s in sample)
    (out / "images").mkdir(parents=True, exist_ok=True)

    # (1) validation membership, on the encoder's md5 field
    md5_of = {}
    for tag in TRAIN:
        with np.load(enc / "feats" / f"{tag}.npz", allow_pickle=False) as z:
            md5_of[tag] = [str(m) for m in z["md5"]]
    groups = sorted({m for v in md5_of.values() for m in v})
    assert sum(map(len, md5_of.values())) == 86216
    gval = set(np.array(groups)[np.random.default_rng(0).random(len(groups)) < 0.05])
    for s in sample:
        assert md5_of[s["shard"]][s["row"]] == s["md5"] and s["md5"] in gval, (s["shard"], s["row"])

    # (2) images and raw labels at the pinned revision
    import pyarrow.parquet as pq  # noqa: E402
    from huggingface_hub import hf_hub_download  # noqa: E402
    from PIL import Image  # noqa: E402
    need = {}
    for k, s in enumerate(sample):
        need.setdefault(s["shard"], []).append(k)
    files, labels = {}, {}
    for tag, items in need.items():
        path = hf_hub_download(REPO, f"data/{tag}.parquet", repo_type="dataset", revision=REV, cache_dir="/tmp/regard_hf")
        table = pq.read_table(path, columns=["image", "label"])
        img, lab = table.column("image"), table.column("label")
        for k in items:
            b = img[sample[k]["row"]].as_py()["bytes"]
            assert hashlib.md5(b).hexdigest() == sample[k]["md5"], (tag, sample[k]["row"])
            ext = {"JPEG": "jpg", "PNG": "png"}.get(Image.open(io.BytesIO(b)).format, "img")
            files[k] = f"v{k:03d}.{ext}"
            (out / "images" / files[k]).write_bytes(b)
            labels[k] = lab[sample[k]["row"]].as_py()
        del table, img, lab

    # (3) descriptions, (4) control
    texts, provenance = dictionary(iconclass)
    rows = []
    for k, s in enumerate(sample):
        truth = drop86(labels[k])
        closure = set().union(*map(ancestors, truth)) if truth else set()
        assert s["code"] not in closure, f"{files[k]}: predicted code inside the truth closure"
        rows.append({"file": files[k], "md5": s["md5"], "shard": s["shard"], "row": s["row"],
                     "predicted": {"code": s["code"], "p": s["p"], "description": describe(s["code"], texts)},
                     "truth": [{"code": c, "description": describe(c, texts)} for c in labels[k]],
                     "truth_codes_86_kept_for_reading": [c for c in labels[k] if c not in truth]})
    write_json({"source": {"diagnostic_sha256": DIAG_SHA256, "system": "B_TZ", "dataset": [REPO, REV],
                           "iconclass_texts": provenance},
                "look": "oubli du catalogueur ou vraie erreur, by wA:p1 then Grok; not a score", "images": rows},
               out / "regard.json")
    write_json({"script_sha256": sha(__file__), "numpy": np.__version__, "python": sys.version.split()[0]}, out / "run.json")
    print("done", len(rows), "images")


if __name__ == "__main__":
    main(*sys.argv[1:5])
