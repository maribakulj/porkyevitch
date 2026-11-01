"""D11: build pe-scelle.bin, the sealed folder of the full run (12 JPEG plates included) as ONE uncompressed,
reproducible tar, for the measures stage.

Usage: construire_scelle_bin.py SEALED OUT [--manifest-sha256 S]
  SEALED  the folder written by the full stage (MANIFEST_PREDICTIONS.json at its root)
  OUT     the .bin to write (must not exist)
Exactly the files listed by MANIFEST_PREDICTIONS.json, each sha-checked, plus the manifest itself; any other file in the
folder is refused (the archive is the seal, nothing more). With --manifest-sha256, the manifest must be that one (the one
the plate receipt names). Members are sorted, with mtime 0, uid/gid 0, mode 0644, USTAR format.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

MANIFEST = "MANIFEST_PREDICTIONS.json"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def members(sealed, manifest_sha256=None):
    sealed = Path(sealed)
    raw = (sealed / MANIFEST).read_bytes()
    assert manifest_sha256 is None or sha(raw) == manifest_sha256, "manifest is not the one of the receipt"
    manifest = json.loads(raw)
    assert manifest.get("stage") == "predictions_sealed", "not a sealed predictions folder"
    out = {MANIFEST: raw}
    for rel, digest in manifest["files"].items():
        b = (sealed / rel).read_bytes()
        assert sha(b) == digest, f"{rel}: sha differs from the manifest"
        out[rel] = b
    present = {str(p.relative_to(sealed)) for p in sealed.rglob("*") if p.is_file()}
    assert present == set(out), f"files outside the seal: {sorted(present - set(out))} / missing: {sorted(set(out) - present)}"
    return out


def build(sealed, out_path, manifest_sha256=None):
    out_path = Path(out_path)
    assert not out_path.exists(), "output exists"
    files = members(sealed, manifest_sha256)
    with tarfile.open(out_path, "w", format=tarfile.USTAR_FORMAT) as tar:
        for name in sorted(files):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode, info.uid, info.gid, info.uname, info.gname = (
                len(files[name]), 0, 0o644, 0, 0, "", "")
            tar.addfile(info, io.BytesIO(files[name]))
    return sha(out_path.read_bytes()), len(files)


if __name__ == "__main__":
    want = sys.argv[sys.argv.index("--manifest-sha256") + 1] if "--manifest-sha256" in sys.argv else None
    digest, n = build(sys.argv[1], sys.argv[2], want)
    print(n, "members", digest)
