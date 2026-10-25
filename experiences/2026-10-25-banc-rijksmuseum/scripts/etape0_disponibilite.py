#!/usr/bin/env python3
"""Step 0 of the Rijksmuseum bench (PREINSCRIPTION.md): availability, metadata only, no image downloaded, no candidate displayed.

Usage: etape0_disponibilite.py CACHE OUT
For each type (painting, print, drawing): the first 300 objects returned by the museum's search (type, imageAvailable=true), in the
order met; for each, the object's Linked Art record and the records of what it `shows` (visual items). Every raw response is kept in
CACHE (one file per URL, with date and sha256); a resumed run reuses them. Writes OUT/etape0.json: counts per type only (records
obtained, HTTP/parse failures, image access point, public-domain mark on the reproduction, metadata licence, Iconclass codes found and
readable, truth non-empty after leaving chapter 86 out, creator identifiable), plus the search queries and the order of PIDs met.
At most one request per second, User-Agent "caypollard/0.1 (research prototype)", timeouts and retries on 429/5xx; a failure is
counted as a failure, never as "no code".
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
TYPES = ["painting", "print", "drawing"]
PER_TYPE = 300
PDM = "creativecommons.org/publicdomain/mark/1.0"
CC0 = "creativecommons.org/publicdomain/zero/1.0"
# The head's notation reader (lermolieff/hierarchy.py): a code is readable if every part matches.
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
_last = [0.0]


def readable(code: str) -> bool:
    return all(PART.fullmatch(p) for p in code.strip().split(":"))


def get(url: str, accept: str = "application/ld+json") -> dict | None:
    """One GET, cached; None after repeated failure (recorded by the caller)."""
    key = hashlib.sha256(url.encode()).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.load(open(path))["body"]
    for attempt in range(5):
        wait = 1.0 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
            body = json.loads(raw)
            tmp = path.with_suffix(".tmp")
            json.dump({"url": url, "date": time.strftime("%Y-%m-%dT%H:%M:%S"), "sha256": hashlib.sha256(raw).hexdigest(),
                       "body": body}, open(tmp, "w"))
            tmp.replace(path)
            return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(10 * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(10 * (attempt + 1))
    return None


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def strings(x) -> list[str]:
    out = []
    for d in walk(x):
        out += [v for v in d.values() if isinstance(v, str)]
    return out


def iconclass_codes(visual: dict) -> list[str]:
    """Notations of every iconclass.org URI under represents_instance_of_type / equivalent, decoded keeping '+' (keys)."""
    codes = []
    for t in visual.get("represents_instance_of_type", []) or []:
        for eq in (t.get("equivalent") or []) if isinstance(t, dict) else []:
            u = eq.get("id", "") if isinstance(eq, dict) else ""
            if "iconclass.org/" in u:
                codes.append(urllib.parse.unquote(u.split("iconclass.org/", 1)[1]))
    return list(dict.fromkeys(codes))


def creators(obj: dict) -> list[str]:
    prod = obj.get("produced_by") or {}
    ids = [a.get("id") for a in prod.get("carried_out_by", []) or [] if isinstance(a, dict)]
    for part in prod.get("part", []) or []:
        ids += [a.get("id") for a in part.get("carried_out_by", []) or [] if isinstance(a, dict)]
    return [i for i in dict.fromkeys(ids) if i]


def search_pids(t: str, n: int) -> tuple[list[str], list[str]]:
    url, pids, pages = f"{SEARCH}?{urllib.parse.urlencode({'type': t, 'imageAvailable': 'true'})}", [], []
    while url and len(pids) < n:
        page = get(url)
        pages.append(url)
        if page is None:
            break
        for item in page.get("orderedItems", []) or []:
            pid = item.get("id") if isinstance(item, dict) else None
            if pid and pid not in pids:
                pids.append(pid)
        nxt = page.get("next")
        url = nxt.get("id") if isinstance(nxt, dict) else nxt
    return pids[:n], pages


report = {"date": time.strftime("%Y-%m-%d"), "per_type": PER_TYPE, "types": {}}
for t in TYPES:
    pids, pages = search_pids(t, PER_TYPE)
    c = {"pids": len(pids), "search_pages": pages, "record_ok": 0, "record_failed": 0, "metadata_cc0": 0, "access_point": 0,
         "pdm_on_object_record": 0, "shows_items": 0, "visual_failed": 0, "with_iconclass": 0, "all_readable": 0,
         "some_unreadable": 0, "truth_non_empty_without_86": 0, "creator_identified": 0, "codes_total": 0,
         "eligible": 0}
    order = []
    for pid in pids:
        obj = get(pid)
        if obj is None:
            c["record_failed"] += 1
            continue
        c["record_ok"] += 1
        order.append(pid)
        s = strings(obj)
        cc0 = any(CC0 in x for x in s)
        pdm = any(PDM in x for x in s)
        access = any("iiif" in x and x.startswith("http") for x in s)
        c["metadata_cc0"] += cc0
        c["pdm_on_object_record"] += pdm
        c["access_point"] += access
        codes, failed = [], False
        for v in obj.get("shows", []) or []:
            vid = v.get("id") if isinstance(v, dict) else None
            if not vid:
                continue
            c["shows_items"] += 1
            vis = v if "represents_instance_of_type" in v else get(vid)
            if vis is None:
                failed = True
                continue
            codes += iconclass_codes(vis)
        codes = list(dict.fromkeys(codes))
        c["visual_failed"] += failed
        if codes:
            c["with_iconclass"] += 1
            c["codes_total"] += len(codes)
            ok = all(readable(x) for x in codes)
            c["all_readable"] += ok
            c["some_unreadable"] += not ok
        projected = [x for x in codes if not x.strip().startswith("86")]
        c["truth_non_empty_without_86"] += bool(projected)
        cr = bool(creators(obj))
        c["creator_identified"] += cr
        c["eligible"] += bool(projected) and pdm and access and any(readable(x) for x in projected)
    report["types"][t] = {**c, "pid_order_sha256": hashlib.sha256(json.dumps(order).encode()).hexdigest()}
    json.dump(report, open(OUT / "etape0.json", "w"), indent=1)
    print(t, {k: v for k, v in c.items() if k != "search_pages"}, flush=True)
