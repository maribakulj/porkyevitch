#!/usr/bin/env python3
"""Rijksmuseum bench, amendment 1 steps 1-4 (PREINSCRIPTION.md): sampling frame, sample, records, eligibility. Metadata only.

Usage: collecte_notices.py CACHE OUT [essai]
With "essai" (dry run): the frame stops after the first 3 pages of each search and 20 PIDs per type are sampled from them; the report
says so. A dry run never yields a population.
1. Frame: the complete list of PIDs of each search type={painting|print|drawing}&imageAvailable=true, page by page (`next`) to the
   end; a page URL met twice or a failed page stops the script (a partial search is never taken as a population). A complete
   pagination whose count differs from totalItems by more than 1 % also stops it; a difference of at most 1 % is reported.
2. Sample: per type, 3 000 PIDs drawn without replacement from the list sorted by PID, numpy default_rng(0), types in the order
   painting, print, drawing, one choice(n, 3000, replace=False) per type on the same generator (all PIDs if n < 3000); numpy 2.5.4
   is required. Union deduplicated by PID, each object
   keeping the list of its types.
3. Records: object, visual items (`shows`), digital objects (`digitally_shown_by`), profile la-framed, cache of raw bytes + sidecar
   (as in etape0_disponibilite.py, sha256 checked before decoding), one request per second at most (monotonic clock), retries on
   429/5xx/network errors honouring Retry-After.
4. Eligibility: CC0 on the record (subject_of[].subject_to); the chosen digital object = in record order, the first digital object
   with an access point on host iiif.micr.io and PDM on it or on its visual item, shown by the visual item that carries the codes;
   codes on several visual items with different digital objects = not alignable; any other rights statement on record, visual item
   or digital object excludes; projected truth (chapter 86 removed) non-empty with at least one readable code; no failed resolution.
   Truth keeps every notation (unreadable and out-of-vocabulary ones included) with its URI and visual item; the log keeps every
   URI (`codes_all`), the truth the deduplicated notations (`codes`).
   Dependency keys for the groups (B1) are extracted here, edges by internal copies come later (after the images).
OUT/cadre/<type>.json (ordered PIDs met, totalItems, pages), OUT/echantillon.json, OUT/notices.jsonl (one line per sampled object,
candidate data: kept out of git, never printed), OUT/collecte.json (counts only, script sha256, config, cache keys sha256). Only
counts are printed.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime
from pathlib import Path

import numpy as np

assert np.__version__ == "2.5.4", f"numpy {np.__version__}: the preregistered draw needs numpy 2.5.4"

CACHE, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ESSAI = len(sys.argv) > 3 and sys.argv[3] == "essai"
CACHE.mkdir(parents=True, exist_ok=True)
(OUT / "cadre").mkdir(parents=True, exist_ok=True)
UA = "caypollard/0.1 (research prototype)"
SEARCH = "https://data.rijksmuseum.nl/search/collection"
PROFILE = "la-framed"
ACCEPT = "application/ld+json"
TYPES = ["painting", "print", "drawing"]
PER_TYPE = 20 if ESSAI else 3000
MAX_PAGES = 3 if ESSAI else None
PDM = "https://creativecommons.org/publicdomain/mark/1.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
IIIF_HOST = "iiif.micr.io"
ICONCLASS_HOST = "iconclass.org"
SIZE = "!800,800"
# Roles (technique notation, English or Dutch) that link two objects, and roles that never do (B1). Any other role links (prudence)
# and is counted.
LINK_ROLES = {"painter", "schilder", "printmaker", "prentmaker", "draftsman (artist)", "tekenaar", "maker", "vervaardiger",
              "photographer", "fotograaf", "knipkunstenaar", "after painting by", "naar schilderij van", "after design by",
              "naar ontwerp van", "after drawing by", "naar tekening van", "after print by", "naar prent van"}
NO_LINK_ROLES = {"publisher", "uitgever", "vendor", "verkoper", "printer (person)", "drukker", "compiler (person in literature)",
                 "samensteller", "clichémaker", "writer (clerical worker)", "schrijver"}
GENERIC = re.compile(r"anoni|anonym|onbekend|unknown|unidentified", re.I)
# The head's notation reader (lermolieff/hierarchy.py): a code is readable if every part matches.
PART = re.compile(r"\d\d?[A-Z]{0,2}\d*(?:\([^)]*\)\d*)*")
_last = [0.0]
_used: list[str] = []
_requests = [0]


class Failure(Exception):
    pass


def readable(code: str) -> bool:
    return all(PART.fullmatch(p) for p in code.strip().split(":"))


def host(u: str) -> str:
    return urllib.parse.urlsplit(u).netloc.lower() if isinstance(u, str) else ""


def with_profile(url: str) -> str:
    """Records get the fixed profile; search pages are fetched as given."""
    if url.startswith(SEARCH):
        return url
    return url + ("&" if "?" in url else "?") + urllib.parse.urlencode({"_profile": PROFILE})


def retry_after(e: urllib.error.HTTPError) -> float:
    v = e.headers.get("Retry-After") if e.headers else None
    if not v:
        return 0.0
    try:
        return float(v)
    except ValueError:
        try:
            return max(0.0, parsedate_to_datetime(v).timestamp() - time.time())
        except (TypeError, ValueError):
            return 0.0


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
        wait = 1.0 - (time.monotonic() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()
        _requests[0] += 1
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
                time.sleep(max(retry_after(e), 10 * (attempt + 1)))
                continue
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException, json.JSONDecodeError, Failure) as e:
            last = type(e).__name__
            time.sleep(10 * (attempt + 1))
    raise Failure(last)


def as_list(x) -> list:
    return x if isinstance(x, list) else [x] if x else []


def notation(node) -> list[str]:
    out = []
    for e in as_list(node.get("notation") if isinstance(node, dict) else None):
        v = e.get("@value") if isinstance(e, dict) else e
        if isinstance(v, str):
            out.append(v.strip())
    return out


def rights(node: dict) -> list[str]:
    """URIs declared in this resource's own subject_to (the Right's id and its classified_as ids), nothing deeper."""
    out = []
    for r in as_list(node.get("subject_to")):
        if isinstance(r, dict):
            out += [r.get("id", "")] + [c.get("id", "") for c in as_list(r.get("classified_as")) if isinstance(c, dict)]
    return [u for u in out if u]


def other_rights(uris: list[str]) -> list[str]:
    """Rights statements other than CC0 and PDM (the Right node's own id, when it is not a licence URI, is ignored)."""
    return [u for u in uris if host(u) in ("creativecommons.org", "rightsstatements.org") and u not in (CC0, PDM)]


def resolve(node, needed: str) -> dict:
    if not isinstance(node, dict) or not node.get("id") and needed not in node:
        raise Failure("reference without id")
    return node if needed in node else get(node["id"])


def codes_of(visual: dict, counts: dict) -> list[dict]:
    """Every iconclass.org notation under represents_instance_of_type / equivalent, decoded once keeping '+', with its URI."""
    out = []
    for t in as_list(visual.get("represents_instance_of_type")):
        for eq in as_list(t.get("equivalent")) if isinstance(t, dict) else []:
            u = eq.get("id", "") if isinstance(eq, dict) else ""
            if host(u) != ICONCLASS_HOST:
                if "iconclass" in u:
                    counts["iconclass_uri_unsupported"] += 1
                continue
            path = urllib.parse.urlsplit(u).path.lstrip("/")
            if not path:
                counts["iconclass_uri_unsupported"] += 1
                continue
            out.append({"code": urllib.parse.unquote(path), "uri": u, "visual": visual.get("id")})
    return out


def actor_keys(obj: dict, counts: dict) -> tuple[list[dict], list[str]]:
    """Dependency keys of the production (B1): actors with their role, how they are named, and whether they link; generic actors."""
    keys, generic = [], []
    for part in as_list((obj.get("produced_by") or {}).get("part")):
        if not isinstance(part, dict):
            continue
        roles = [r for t in as_list(part.get("technique")) for r in notation(t)]
        first = [(a, "direct") for a in as_list(part.get("carried_out_by"))]
        for s in as_list(part.get("assigned_by")):
            first += [(a, "assigned") for a in as_list(s.get("assigned") if isinstance(s, dict) else None)]
        named = []
        for a, how in first:
            # places never link; an influence source is read on direct and attributed actors alike
            if isinstance(a, dict) and a.get("type") == "Place":
                counts["place_skipped"] += 1
                continue
            named.append((a, how))
            if isinstance(a, dict):
                for b in as_list((a.get("formed_by") or {}).get("influenced_by")):
                    if isinstance(b, dict) and b.get("type") == "Place":
                        counts["place_skipped"] += 1
                    else:
                        named.append((b, "influence"))
        role_set = {r.lower() for r in roles}
        if role_set & LINK_ROLES:
            links, why = True, "role"
        elif role_set and role_set <= NO_LINK_ROLES:
            links, why = False, "role_no_link"
        else:
            links, why = True, "role_other"
            counts["parts_role_other"] += 1
        for a, how in named:
            if not isinstance(a, dict) or not a.get("id"):
                counts["actor_without_id"] += 1
                continue
            label = " ".join(notation(a) + [str(a.get("_label", ""))])
            if GENERIC.search(label):
                generic.append(a["id"])
                continue
            # an influence source (circle/follower of X) links whatever the role of the part
            keys.append({"actor": a["id"], "how": how, "roles": roles, "links": links or how == "influence",
                         "why": "influence" if how == "influence" else why})
    return keys, list(dict.fromkeys(generic))


def frame(t: str) -> dict:
    url, pids, seen, pages, total = f"{SEARCH}?{urllib.parse.urlencode({'type': t, 'imageAvailable': 'true'})}", [], set(), 0, None
    met: set[str] = set()
    while url:
        if url in seen:
            sys.exit(f"search {t}: page met twice, stopping")
        seen.add(url)
        try:
            page = get(url)
        except Failure as e:
            sys.exit(f"search {t}: page {pages + 1} failed ({e}), stopping: a partial search is not a population")
        pages += 1
        part = page.get("partOf") or {}
        total = part.get("totalItems", total) if isinstance(part, dict) else total
        for item in as_list(page.get("orderedItems")):
            pid = item.get("id") if isinstance(item, dict) else None
            if pid and pid not in met:
                met.add(pid)
                pids.append(pid)
        nxt = page.get("next")
        url = nxt.get("id") if isinstance(nxt, dict) else nxt
        if MAX_PAGES and pages >= MAX_PAGES:
            break
    if not MAX_PAGES:
        if not isinstance(total, int) or abs(len(pids) - total) > 0.01 * total:
            sys.exit(f"search {t}: {len(pids)} PIDs against totalItems {total}: more than 1 %, stopping")
    return {"type": t, "total_items": total, "pids_met": len(pids), "pages": pages, "pids": pids,
            "pids_order_sha256": hashlib.sha256(json.dumps(pids).encode()).hexdigest()}


def record(pid: str, types: list[str], c: dict) -> dict:
    """One sampled object: rights, codes, chosen image, dependency keys and eligibility; failures recorded, never read as 'no code'."""
    rec = {"pid": pid, "types": types, "failed": [], "excluded": []}
    try:
        obj = get(pid)
    except Failure as e:
        rec["failed"].append(f"object: {e}")
        return rec
    rec["cc0_record"] = [{"uri": u, "path": f"subject_of[{i}].subject_to"} for i, s in enumerate(as_list(obj.get("subject_of")))
                         if isinstance(s, dict) for u in rights(s) if u == CC0]
    others = [("record", u) for s in as_list(obj.get("subject_of")) if isinstance(s, dict) for u in other_rights(rights(s))]
    codes, candidates, visuals_with_codes, digitals_of = [], [], set(), {}
    for v in as_list(obj.get("shows")):
        try:
            both = isinstance(v, dict) and "represents_instance_of_type" in v and "digitally_shown_by" in v
            vis = v if both else resolve({"id": v.get("id")} if isinstance(v, dict) else v, "-")
        except Failure as e:
            rec["failed"].append(f"visual: {e}")
            continue
        vc = codes_of(vis, c)
        codes += vc
        if vc:
            visuals_with_codes.add(vis.get("id"))
        pdm_vis = PDM in rights(vis)
        others += [("visual", u) for u in other_rights(rights(vis))]
        digitals_of.setdefault(vis.get("id"), set())
        for d in as_list(vis.get("digitally_shown_by")):
            try:
                dig = resolve(d, "access_point")
            except Failure as e:
                rec["failed"].append(f"digital: {e}")
                continue
            digitals_of[vis.get("id")].add(dig.get("id"))
            others += [("digital", u) for u in other_rights(rights(dig))]
            aps = [a.get("id", "") for a in as_list(dig.get("access_point")) if isinstance(a, dict)]
            aps = [a for a in aps if host(a) == IIIF_HOST and "/full/" in a]
            pdm_dig = PDM in rights(dig)
            if aps and (pdm_dig or pdm_vis):
                base = aps[0].split("/full/", 1)[0]
                candidates.append({"visual": vis.get("id"), "digital": dig.get("id"), "access_point": aps[0],
                                   "iiif": f"{base}/full/{SIZE}/0/default.jpg",
                                   "pdm_on": "digital" if pdm_dig else "visual"})
    rec["codes_all"] = codes
    seen = set()
    rec["codes"] = [x for x in codes if not (x["code"] in seen or seen.add(x["code"]))]
    projected = [x["code"] for x in rec["codes"] if not x["code"].strip().startswith("86")]
    rec["projected"] = projected
    rec["other_rights"] = [{"node": n, "uri": u} for n, u in others]
    # Alignment is decided on every coded visual item and every digital object it resolves to, before rights or IIIF are looked at:
    # one single digital object for all the coded views, or the object is not alignable (a coded view without digital object
    # included). Only then is that digital object checked for PDM + IIIF.
    image = None
    coded_digitals = set().union(*(digitals_of.get(v, set()) for v in visuals_with_codes)) if visuals_with_codes else set()
    if visuals_with_codes and (len(coded_digitals) > 1 or any(not digitals_of.get(v) for v in visuals_with_codes)):
        rec["excluded"].append("not_alignable")
    else:
        image = next((x for x in candidates if x["visual"] in visuals_with_codes and x["digital"] in coded_digitals), None)
    rec["image"] = image
    rec["actors"], rec["generic_actors"] = actor_keys(obj, c)
    rec["parents"] = [p.get("id") for p in as_list(obj.get("part_of")) if isinstance(p, dict) and p.get("id")]
    rec["eligible"] = False
    if rec["failed"]:
        return rec  # a failed resolution is the object's only class: never read as an absence (no code, no image, no right)
    if not rec["cc0_record"]:
        rec["excluded"].append("no_cc0_record")
    if image is None and "not_alignable" not in rec["excluded"]:
        rec["excluded"].append("no_pdm_iiif_image_for_coded_visual" if rec["codes"] else "no_code")
    if rec["other_rights"]:
        rec["excluded"].append("other_rights")
    if rec["codes"] and not any(readable(x) for x in projected):
        rec["excluded"].append("projected_truth_empty_or_unreadable")
    rec["eligible"] = not rec["failed"] and not rec["excluded"]
    return rec


script_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
report = {"date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "script_sha256": script_sha,
          "essai": ESSAI,
          "config": {"types": TYPES, "per_type": PER_TYPE, "seed": 0, "profile": PROFILE, "accept": ACCEPT, "search": SEARCH,
                     "size": SIZE, "link_roles": sorted(LINK_ROLES), "no_link_roles": sorted(NO_LINK_ROLES),
                     "generic": GENERIC.pattern, "numpy": np.__version__},
          "frame": {}, "sample": {}, "records": {}}


def write_report():
    report["cache_keys_sha256"] = hashlib.sha256(json.dumps(_used).encode()).hexdigest()
    report["requests_sent"] = _requests[0]
    tmp = OUT / "collecte.json.tmp"
    json.dump(report, open(tmp, "w"), indent=1)
    tmp.replace(OUT / "collecte.json")


lists = {}
for t in TYPES:
    f = frame(t)
    tmp = OUT / "cadre" / f"{t}.json.tmp"
    json.dump(f, open(tmp, "w"))
    tmp.replace(OUT / "cadre" / f"{t}.json")
    lists[t] = sorted(f["pids"])
    report["frame"][t] = {k: v for k, v in f.items() if k != "pids"}
    write_report()
    print("frame", t, report["frame"][t], flush=True)

rng = np.random.default_rng(0)
sample: dict[str, list[str]] = {}
for t in TYPES:
    idx = rng.choice(len(lists[t]), min(PER_TYPE, len(lists[t])), replace=False)
    sample[t] = [lists[t][i] for i in sorted(idx)]
# provenance of the draw (sampled_from) and membership of the complete frame lists (types, in the fixed order)
sampled_from: dict[str, list[str]] = {}
for t in TYPES:
    for pid in sample[t]:
        sampled_from.setdefault(pid, []).append(t)
sets = {t: set(lists[t]) for t in TYPES}
types_of = {pid: [t for t in TYPES if pid in sets[t]] for pid in sampled_from}
union = sorted(sampled_from)
tmp = OUT / "echantillon.json.tmp"
json.dump({"per_type": sample, "union": [{"pid": p, "types": types_of[p], "sampled_from": sampled_from[p]} for p in union]},
          open(tmp, "w"))
tmp.replace(OUT / "echantillon.json")
report["sample"] = {"per_type": {t: len(sample[t]) for t in TYPES}, "union": len(union),
                    "unique_pids_sampled_in_several_types": sum(len(v) > 1 for v in sampled_from.values()),
                    "unique_pids_in_several_frame_lists": sum(len(v) > 1 for v in types_of.values()),
                    "union_sha256": hashlib.sha256(json.dumps(union).encode()).hexdigest()}
write_report()
print("sample", report["sample"], flush=True)

COUNTS = ["objects", "failed", "eligible", "no_cc0_record", "no_code", "no_pdm_iiif_image_for_coded_visual", "not_alignable",
          "other_rights", "projected_truth_empty_or_unreadable", "codes_total", "codes_unreadable", "codes_86", "with_link_actor",
          "only_generic_actor", "no_actor", "with_parent", "parts_role_other", "actor_without_id", "iconclass_uri_unsupported", "place_skipped"]
by_type = {t: dict.fromkeys(COUNTS, 0) for t in TYPES}
tmp = OUT / "notices.jsonl.tmp"
with open(tmp, "w") as fh:
    for n, pid in enumerate(union):
        c = {"parts_role_other": 0, "actor_without_id": 0, "iconclass_uri_unsupported": 0, "place_skipped": 0}
        rec = record(pid, types_of[pid], c)
        rec["sampled_from"] = sampled_from[pid]
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        for t in rec["types"]:
            b = by_type[t]
            b["objects"] += 1
            b["failed"] += bool(rec["failed"])
            b["eligible"] += rec.get("eligible", False)
            for e in rec["excluded"]:
                b[e] += 1
            b["codes_total"] += len(rec.get("codes", []))
            b["codes_unreadable"] += sum(not readable(x["code"]) for x in rec.get("codes", []))
            b["codes_86"] += sum(x["code"].strip().startswith("86") for x in rec.get("codes", []))
            links = any(a["links"] for a in rec.get("actors", []))
            b["with_link_actor"] += links
            b["only_generic_actor"] += not links and bool(rec.get("generic_actors"))
            b["no_actor"] += not links and not rec.get("generic_actors")
            b["with_parent"] += bool(rec.get("parents"))
            for k, v in c.items():
                b[k] += v
        if (n + 1) % 500 == 0:
            report["records"] = {"done": n + 1, "by_type": by_type}
            write_report()
            print("records", n + 1, "/", len(union), flush=True)
tmp.replace(OUT / "notices.jsonl")
report["records"] = {"done": len(union), "by_type": by_type,
                     "notices_sha256": hashlib.sha256((OUT / "notices.jsonl").read_bytes()).hexdigest()}
write_report()
print("records", json.dumps(by_type), flush=True)
