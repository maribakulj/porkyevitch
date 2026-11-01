"""VLM comparison v2.5: fetch the drawn V-diagnostic ICAI images on Kaggle (fast network), CPU, internet on, NO token.

The local network (~130 kB/s, 30/10) cannot read the image column of the ICAI shards: each shard is one row group of 8000 rows
(~300 MB per image column), and the datasets-server refuses them ("scan size limit"). This kernel draws the same sample with
the SEALED functions of vlm_prepare (vdiag_truth, vdiag_sample: imported, not copied), reads the image bytes of those rows from
the pinned TRAIN shards only (vlm_prepare.Shards and shard_path, which refuse any test shard), checks each md5 against the
validation identities, stages the files OUTSIDE /kaggle/working and writes one uncompressed tar archive (.bin, D11) plus a
manifest without image. No image is written in clear under /kaggle/working. Nothing is scored.

Inputs, found under /kaggle/input by file name AND SHA-256 (exactly one match each, no fixed path): vlm_prepare.py,
vlm_core.py, a1_core.py, identites_validation.json.
Outputs in /kaggle/working: icai-vdiag.bin, fetch_manifest.json.
"""
import hashlib
import io
import json
import os
import sys
import tarfile
import time
from pathlib import Path

PINS = {"vlm_prepare.py": "89b00a351b10c5c0b69bbc1c6c645bf082d28a996824023e5b70fdbee18b97f5",
        "vlm_core.py": "9fb5096cd2245f8530df10a3becdc07ff3644a73207bf7e0f221477c81efc223",
        "a1_core.py": "177ef54243fd6dfed0aa557561aa365f41b2c992379aef6d4fab4c5e27ab205a",
        "identites_validation.json": "9ce6a35f4b82c237cb992b7c1106d7ab3ffe68045b8c54cae91f9c529df83312"}
INPUT, WORKING, STAGE = Path("/kaggle/input"), Path("/kaggle/working"), Path("/tmp/pkyevitch-icai")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def find(root, name, want):
    """The single file named `name` under root whose SHA-256 is `want`."""
    hits = [p for p in Path(root).rglob(name) if p.is_file() and sha(p) == want]
    if len(hits) != 1:
        raise SystemExit(f"REFUSED: input_{name}_{len(hits)}_matches")
    return hits[0]


def no_token():
    """Public dataset: never send a token (no Kaggle secret is attached; implicit tokens are disabled)."""
    for k in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HF_HUB_TOKEN"):
        os.environ.pop(k, None)
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"


def fetch(ids, rows, shards, stage):
    """Bytes of the drawn rows, md5-checked, staged as <md5><ext> outside the working folder. Returns the manifest rows."""
    import vlm_prepare as vp
    stage.mkdir(parents=True, exist_ok=True)
    by_shard, out = {}, []
    for k in rows:
        by_shard.setdefault(ids[k]["shard"], []).append(k)
    for tag, ks in sorted(by_shard.items()):
        got = shards.rows(tag, [ids[k]["row"] for k in ks], ["image"])
        for k in ks:
            body = got[ids[k]["row"]]["image"]["bytes"]
            vp.require(hashlib.md5(body).hexdigest() == ids[k]["md5"], f"icai_image_md5_row_{k}")
            name = f"{ids[k]['md5']}{vp.image_ext(body)}"
            (stage / name).write_bytes(body)
            out.append({"validation_row": k, "shard": tag, "row": ids[k]["row"], "member": name, "bytes": len(body)})
    return out


def write_bin(stage, members, target):
    """Uncompressed tar of the staged files, regular members only, sorted names, fixed metadata. One member per md5: rows of
    a doubled md5 group share their bytes, so the member is written once (Codex, v2.5); the manifest keeps every row."""
    with tarfile.open(target, "w:") as tar:
        for m in sorted(set(members)):
            body = (stage / m).read_bytes()
            info = tarfile.TarInfo(m)
            info.size, info.mtime, info.mode = len(body), 0, 0o644
            tar.addfile(info, io.BytesIO(body))


def main(input_root=INPUT, working=WORKING, stage=STAGE, shards=None):
    started = time.time()
    no_token()
    code = {n: find(input_root, n, w) for n, w in PINS.items()}
    sys.path.insert(0, str(code["vlm_prepare.py"].parent))
    for n in ("vlm_core.py", "a1_core.py"):
        if code[n].parent != code["vlm_prepare.py"].parent:
            raise SystemExit(f"REFUSED: {n}_not_next_to_vlm_prepare")
    import vlm_prepare as vp
    ids = json.loads(code["identites_validation.json"].read_text())
    vp.require(len(ids) == 4265, "validation_rows")
    shards = shards or vp.Shards()
    evaluable, _ = vp.vdiag_truth(ids, shards)  # labels of V-diagnostic from the TRAIN shards; 2100 evaluable required
    _, chosen, rows = vp.vdiag_sample(ids, evaluable)
    manifest_rows = fetch(ids, rows, shards, stage)
    target = working / "icai-vdiag.bin"
    write_bin(stage, [r["member"] for r in manifest_rows], target)
    import huggingface_hub
    import numpy
    import pyarrow
    manifest = {"dataset": [vp.REPO, vp.REV], "shards_read": sorted({r["shard"] for r in manifest_rows}),
                "groups": len(chosen), "images": len(manifest_rows), "rows": manifest_rows, "bin_sha256": sha(target),
                "bin_bytes": target.stat().st_size, "inputs_sha256": PINS, "token_sent": False,
                "versions": {"python": sys.version.split()[0], "numpy": numpy.__version__,
                             "pyarrow": pyarrow.__version__, "huggingface_hub": huggingface_hub.__version__},
                "wall_seconds": round(time.time() - started, 1)}
    (working / "fetch_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: manifest[k] for k in ("groups", "images", "bin_sha256", "bin_bytes", "wall_seconds")}))
    return manifest


if __name__ == "__main__":
    main()
