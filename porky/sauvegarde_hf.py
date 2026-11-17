#!/usr/bin/env python3
"""Move a local folder to a private Hugging Face repo, in tar parts that fit a nearly full disk.

Usage: python -m porky.sauvegarde_hf --depot OWNER/REPO ROOT REL [--delete]
Archives ROOT/REL as parts of about 800 MB (each part a plain tar of whole files, written to a temporary folder, uploaded, checked
against the sha256 the Hub records, then removed). Each part and a manifest (path, size of every file, sha256 of every part) go
under <ROOT name>/<REL>/ in the repo. With --delete, ROOT/REL is removed only after every part is verified on the Hub.
Restore: hf download OWNER/REPO --include "<ROOT name>/<REL>/*" --local-dir D, then extract every part
in ROOT (tar -xf part.tar -C ROOT). The token is the one already stored by huggingface_hub; it is never read or printed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

PART = 800 * 1024 * 1024


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def remote_sha(api: HfApi, repo: str, path: str) -> str | None:
    info = api.get_paths_info(repo, [path], expand=True)
    return info[0].lfs.sha256 if info and info[0].lfs else None


def main(argv: list[str] | None = None) -> None:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--depot", required=True, help="private Hugging Face repo, OWNER/REPO")
    a.add_argument("root")
    a.add_argument("rel")
    a.add_argument("--delete", action="store_true")
    args = a.parse_args(argv)
    REPO = args.depot
    root, rel = Path(args.root).resolve(), args.rel.strip("/")
    delete = args.delete
    src = root / rel
    files = sorted(p for p in src.rglob("*") if p.is_file() and not p.is_symlink())
    batches, cur, size = [], [], 0
    for p in files:
        s = p.stat().st_size
        if cur and size + s > PART:
            batches.append(cur)
            cur, size = [], 0
        cur.append(p)
        size += s
    if cur:
        batches.append(cur)
    api = HfApi()
    dest = f"{root.name}/{rel}"
    manifest = {"source": f"{root.name}/{rel}", "files": [[str(p.relative_to(root)), p.stat().st_size] for p in files], "parts": []}
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
        for k, batch in enumerate(batches):
            name = f"part{k:03d}.tar"
            local = Path(tmp) / name
            with tarfile.open(local, "w") as t:
                for p in batch:
                    t.add(p, arcname=str(p.relative_to(root)))
            h = sha(local)
            api.upload_file(path_or_fileobj=str(local), path_in_repo=f"{dest}/{name}", repo_id=REPO,
                            commit_message=f"{dest}/{name}")
            if remote_sha(api, REPO, f"{dest}/{name}") != h:  # not an assert: python -O would skip it
                sys.exit(f"{name}: sha256 differs on the Hub; nothing deleted")
            local.unlink()
            manifest["parts"].append({"name": name, "sha256": h, "files": len(batch)})
            print(f"{dest}/{name}: {len(batch)} files, verified", flush=True)
        m = Path(tmp) / "MANIFEST.json"
        m.write_text(json.dumps(manifest, indent=0))
        api.upload_file(path_or_fileobj=str(m), path_in_repo=f"{dest}/MANIFEST.json", repo_id=REPO,
                        commit_message=f"{dest}/MANIFEST.json")
    if delete:
        for part in manifest["parts"]:
            if remote_sha(api, REPO, f"{dest}/{part['name']}") != part["sha256"]:
                sys.exit(f"{part['name']}: not verified on the Hub; nothing deleted")
        shutil.rmtree(src)
        print(f"removed {src}", flush=True)


if __name__ == "__main__":
    main()
