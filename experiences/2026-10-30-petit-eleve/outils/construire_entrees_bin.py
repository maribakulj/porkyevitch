"""D11: build pe-entrees.bin, the inputs of the student (images included) as ONE uncompressed, reproducible tar.

Usage: construire_entrees_bin.py SOURCE OUT
  SOURCE  the former upload folder (~/porkyevitch-donnees/petit-eleve/upload): images/, graphes/, s1b/
  OUT     the .bin to write (must not exist)
listes.json, noms.json and the scripts come from this experiment folder, sha-checked against CODE_SHA256.json; every
image, Gemini graph and S1b graph is sha-checked against listes.json (as the original upload). The closed sets
(exemples, test20) are refused. kaggle_pe_run.py is NOT in the archive (its sha pins the archive). Members are sorted,
with mtime 0, uid/gid 0, mode 0644, USTAR format: the same inputs always give the same bytes.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

HERE = Path(__file__).resolve().parents[1]
SCRIPTS = ("scripts/pe_common.py", "scripts/pe_kaggle.py", "scripts/pe_listes.py")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def members(source):
    code = json.loads((HERE / "CODE_SHA256.json").read_text())["files"]
    out = {}
    for f in ("listes.json", "noms.json") + SCRIPTS:
        b = (HERE / f).read_bytes()
        assert sha(b) == code[f], f"{f}: not the reviewed bytes"
        out[f] = b
    listes = json.loads(out["listes.json"])
    closed = set(listes["fermes"]["exemples"]) | set(listes["fermes"]["test20"])
    for r in listes["entrainement"] + listes["reglage"] + listes["evaluation"]:
        n = r["name"]
        assert n not in closed, n
        wanted = [(f"images/{n}.jpg", r["image_sha256"])]
        if r["gemini_graph_sha256"]:
            wanted.append((f"graphes/{n}.json", r["gemini_graph_sha256"]))
        if r.get("s1b_graph_sha256"):
            wanted.append((f"s1b/{n}.json", r["s1b_graph_sha256"]))
        for rel, want in wanted:
            b = (Path(source) / rel).read_bytes()
            assert sha(b) == want, f"{rel}: sha differs from listes.json"
            out[rel] = b
    assert not {Path(k).stem for k in out if k.startswith(("images/", "graphes/", "s1b/"))} & closed
    return out


def build(source, out_path):
    out_path = Path(out_path)
    assert not out_path.exists(), "output exists"
    files = members(source)
    with tarfile.open(out_path, "w", format=tarfile.USTAR_FORMAT) as tar:
        for name in sorted(files):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = (
                len(files[name]), 0, 0o644, 0, 0, "", "")
            tar.addfile(info, io.BytesIO(files[name]))
    return sha(out_path.read_bytes()), len(files)


if __name__ == "__main__":
    digest, n = build(sys.argv[1], sys.argv[2])
    print(n, "members", digest)
