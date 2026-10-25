#!/usr/bin/env python3
"""Rijksmuseum bench: the eligible objects of the notice collection, stripped to what the remote image step needs (no codes).

Usage: liste_eligibles.py NOTICES_JSONL OUT_JSONL
One line per eligible object, in PID order (Unicode code points): pid, types, sampled_from, visual, digital, iiif. Codes, actors and
rights stay on the Mac; the remote step only downloads, hashes and encodes images. Prints counts and the sha256 of the output.
"""

import hashlib
import json
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
rows = []
for line in open(src):
    r = json.loads(line)
    if r.get("eligible"):
        im = r["image"]
        rows.append({"pid": r["pid"], "types": r["types"], "sampled_from": r["sampled_from"], "visual": im["visual"],
                     "digital": im["digital"], "iiif": im["iiif"]})
rows.sort(key=lambda r: r["pid"])
assert len({r["pid"] for r in rows}) == len(rows)
tmp = out.with_suffix(".tmp")
with open(tmp, "w") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
tmp.replace(out)
print(len(rows), "eligible objects;", hashlib.sha256(out.read_bytes()).hexdigest())
