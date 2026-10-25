#!/usr/bin/env python3
"""Step 0 of the Rijksmuseum bench (PREINSCRIPTION.md): availability, metadata only, no image downloaded, no candidate displayed.

Usage: etape0_disponibilite.py CACHE OUT
For each type (painting, print, drawing): the first 300 objects returned by the museum's search (type, imageAvailable=true), in the
order met. Scope: availability among these first results only, not a proportion of the whole catalogue.
Records are resolved with the fixed profile la-framed (?_profile=la-framed). Path followed, as documented by the museum (IIIF Image
API page): object --shows--> visual item --digitally_shown_by--> digital object --access_point--> IIIF image (iiif.micr.io).
Rights are read only from the `subject_to` of the resource concerned:
- metadata CC0: `subject_to` of the object record;
- reproduction PDM: `subject_to` of the digital object whose access point is the IIIF image.
`eligible_verified` = CC0 on the object + at least one digital object with IIIF access point AND PDM on that same digital object +
non-empty readable truth without chapter 86 + no failed resolution for that object. Counts of "found anywhere in the JSON" are kept
apart, named `exploratory_*`, and never enter `eligible_verified`.
Cache: one raw response per (URL, profile) in CACHE, raw bytes + sidecar (URL, UTC date, profile, Accept, HTTP status, content type,
sha256 of the bytes); on resume the sha256 is checked before decoding, a mismatch stops the run. A change of profile or Accept opens a
new cache key. At most one request per second, User-Agent "caypollard/0.1 (research prototype)", timeouts and retries on 429/5xx/
network errors; a failure is counted as a failure, never as "no code". A search that stops before 300 PIDs is reported as partial.
OUT/etape0.json (written atomically): counts per type only, search status and pages, sha256 of the ordered list of every PID met,
sha256 of this script, configuration, and sha256 of the list of cache keys used. No identifier of a candidate is printed.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CACHE, OUT = Path(sys.argv[1]), Path(sys.argv[2])
CACHE.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
UA = "caypollard/0.1 (research prototype)"
SEARCH = "https://data.rijksmuseum.nl/search/collection"
PROFILE = "la-framed"
ACCEPT = "application/ld+json"
TYPES = ["painting", "print", "drawing"]
PER_TYPE = 300
PDM = "creativecommons.org/publicdomain/mark/1.0"
CC0 = "creativecommons.org/publicdomain/zero/1.0"
IIIF_HOST = "iiif.micr.io/"
# The head's notation reader (lermolieff/hierarchy.py): a code is readable if every part matches.
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
_last = [0.0]
_used: list[str] = []


class Failure(Exception):
    pass


def readable(code: str) -> bool:
    return all(PART.fullmatch(p) for p in code.strip().split(":"))


def with_profile(url: str) -> str:
    """Records (id.rijksmuseum.nl / data.rijksmuseum.nl PIDs) get the fixed profile; search pages are fetched as given."""
    if url.startswith(SEARCH):
        return url
    return url + ("&" if "?" in url else "?") + urllib.parse.urlencode({"_profile": PROFILE})


def get(url: str) -> dict:
    """One GET of url (profile added for records), cached as raw bytes + sidecar; raises Failure after repeated failure."""
    full = with_profile(url)
    key = hashlib.sha256(f"{full}\n{ACCEPT}".encode()).hexdigest()
    raw_path, side_path = CACHE / f"{key}.raw", CACHE / f"{key}.json"
    _used.append(key)
    if side_path.exists():
        side = json.load(open(side_path))
        raw = raw_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != side["sha256"] or side["url"] != full or side["accept"] != ACCEPT:
            sys.exit(f"cache entry {key} does not match its sidecar: stopping")
        return json.loads(raw)
    last = "no attempt"
    for attempt in range(5):
        wait = 1.0 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(full, headers={"User-Agent": UA, "Accept": ACCEPT})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw, status, ctype = r.read(), r.status, r.headers.get("Content-Type", "")
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise Failure("not a JSON object")
            tmp = raw_path.with_suffix(".tmp")
            tmp.write_bytes(raw)
            tmp.replace(raw_path)
            side = {"url": full, "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "profile": PROFILE,
                    "accept": ACCEPT, "status": status, "content_type": ctype, "sha256": hashlib.sha256(raw).hexdigest()}
            tmp = side_path.with_suffix(".jtmp")
            json.dump(side, open(tmp, "w"))
            tmp.replace(side_path)
            return body
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(10 * (attempt + 1))
                continue
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, Failure) as e:
            last = type(e).__name__
            time.sleep(10 * (attempt + 1))
    raise Failure(last)


def as_list(x) -> list:
    return x if isinstance(x, list) else [x] if x else []


def strings(x) -> list[str]:
    if isinstance(x, dict):
        return [s for v in x.values() for s in strings(v)]
    if isinstance(x, list):
        return [s for v in x for s in strings(v)]
    return [x] if isinstance(x, str) else []


def rights(node: dict) -> list[str]:
    """URIs declared in this resource's own subject_to (the Right's id and its classified_as ids), nothing deeper."""
    out = []
    for r in as_list(node.get("subject_to")):
        if isinstance(r, dict):
            out += [r.get("id", "")] + [c.get("id", "") for c in as_list(r.get("classified_as")) if isinstance(c, dict)]
    return [u for u in out if u]


def resolve(node, needed: str) -> dict:
    """An embedded resource, fetched by its id when the field needed is absent (references are allowed by Linked Art)."""
    if not isinstance(node, dict) or not node.get("id") and needed not in node:
        raise Failure("reference without id")
    return node if needed in node else get(node["id"])


def iconclass_codes(visual: dict) -> list[str]:
    """Notations of every iconclass.org URI under represents_instance_of_type / equivalent, decoded keeping '+' (keys)."""
    codes = []
    for t in as_list(visual.get("represents_instance_of_type")):
        for eq in as_list(t.get("equivalent")) if isinstance(t, dict) else []:
            u = eq.get("id", "") if isinstance(eq, dict) else ""
            if "iconclass.org/" in u:
                codes.append(urllib.parse.unquote(u.split("iconclass.org/", 1)[1]))
    return list(dict.fromkeys(codes))


def creators(obj: dict) -> list[str]:
    prod = obj.get("produced_by") or {}
    ids = [a.get("id") for a in as_list(prod.get("carried_out_by")) if isinstance(a, dict)]
    for part in as_list(prod.get("part")):
        ids += [a.get("id") for a in as_list(part.get("carried_out_by")) if isinstance(a, dict)]
    return [i for i in dict.fromkeys(ids) if i]


def search_pids(t: str, n: int) -> tuple[list[str], list[str], dict]:
    """PIDs in the order met (deduplicated), pages requested, and status: complete (n reached), exhausted, or failed."""
    url, pids, pages, status = f"{SEARCH}?{urllib.parse.urlencode({'type': t, 'imageAvailable': 'true'})}", [], [], None
    while url and len(pids) < n:
        pages.append(url)
        try:
            page = get(url)
        except Failure as e:
            status = {"state": "failed", "error": str(e), "page": len(pages)}
            break
        for item in as_list(page.get("orderedItems")):
            pid = item.get("id") if isinstance(item, dict) else None
            if pid and pid not in pids:
                pids.append(pid)
        nxt = page.get("next")
        url = nxt.get("id") if isinstance(nxt, dict) else nxt
    if status is None:
        status = {"state": "complete" if len(pids) >= n else "exhausted"}
    return pids, pages, status


COUNTERS = ["record_ok", "record_failed", "visual_failed", "digital_failed", "metadata_cc0_on_object", "shows_items",
            "digital_objects", "iiif_access_point", "pdm_on_digital_with_iiif", "with_iconclass", "all_readable",
            "some_unreadable", "truth_non_empty_without_86", "creator_identified", "codes_total", "eligible_verified",
            "eligibility_unknown", "exploratory_cc0_anywhere", "exploratory_pdm_anywhere", "exploratory_iiif_anywhere"]

script_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
report = {"date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "script_sha256": script_sha,
          "config": {"per_type": PER_TYPE, "types": TYPES, "profile": PROFILE, "accept": ACCEPT, "search": SEARCH,
                     "scope": "first results of the museum's search per type, not the whole catalogue"},
          "types": {}}
for t in TYPES:
    pids, pages, status = search_pids(t, PER_TYPE)
    met = list(pids)
    pids = pids[:PER_TYPE]
    c = dict.fromkeys(COUNTERS, 0)
    for pid in pids:
        try:
            obj = get(pid)
        except Failure:
            c["record_failed"] += 1
            continue
        c["record_ok"] += 1
        s = strings(obj)
        c["exploratory_cc0_anywhere"] += any(CC0 in x for x in s)
        c["exploratory_pdm_anywhere"] += any(PDM in x for x in s)
        c["exploratory_iiif_anywhere"] += any("iiif" in x for x in s)
        cc0 = any(CC0 in u for u in rights(obj))
        c["metadata_cc0_on_object"] += cc0
        codes, failed, image_ok = [], False, False
        for v in as_list(obj.get("shows")):
            c["shows_items"] += 1
            try:
                both = isinstance(v, dict) and "represents_instance_of_type" in v and "digitally_shown_by" in v
                vis = v if both else resolve({"id": v.get("id")} if isinstance(v, dict) else v, "-")
            except Failure:
                failed = True
                c["visual_failed"] += 1
                continue
            codes += iconclass_codes(vis)
            for d in as_list(vis.get("digitally_shown_by")):
                c["digital_objects"] += 1
                try:
                    dig = resolve(d, "access_point")
                except Failure:
                    failed = True
                    c["digital_failed"] += 1
                    continue
                iiif = any(isinstance(a, dict) and IIIF_HOST in a.get("id", "") for a in as_list(dig.get("access_point")))
                pdm = iiif and any(PDM in u for u in rights(dig))
                c["iiif_access_point"] += iiif
                c["pdm_on_digital_with_iiif"] += pdm
                image_ok |= pdm
        codes = list(dict.fromkeys(codes))
        if codes:
            c["with_iconclass"] += 1
            c["codes_total"] += len(codes)
            ok = all(readable(x) for x in codes)
            c["all_readable"] += ok
            c["some_unreadable"] += not ok
        projected = [x for x in codes if not x.strip().startswith("86")]
        c["truth_non_empty_without_86"] += bool(projected)
        c["creator_identified"] += bool(creators(obj))
        truth_ok = any(readable(x) for x in projected)
        if failed:
            c["eligibility_unknown"] += 1
        else:
            c["eligible_verified"] += cc0 and image_ok and truth_ok
    report["types"][t] = {"search": status, "search_pages": pages, "pids_met": len(met), "pids_examined": len(pids), **c,
                          "pids_met_order_sha256": hashlib.sha256(json.dumps(met).encode()).hexdigest()}
    report["cache_keys_sha256"] = hashlib.sha256(json.dumps(_used).encode()).hexdigest()
    tmp = OUT / "etape0.json.tmp"
    json.dump(report, open(tmp, "w"), indent=1)
    tmp.replace(OUT / "etape0.json")
    print(t, status["state"], {k: v for k, v in c.items()}, flush=True)
