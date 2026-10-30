"""VLM comparison, step 1 (PREINSCRIPTION-v2.4.md section 6): samples, images, truths, B and T* references, identity
controls, call plan and preparation seal. No model call, no score of a VLM.

Reads only validation rows of the ICAI train shards (never data/test-*), the "dev" member of the Rijksmuseum frozen bank
(D10's decoding: the test member is never decoded), the two dev files of the phase-1 seal, and the petit élève inputs.

Usage: vlm_prepare.py --diag DIAG --frozen FROZEN.json --seal SEAL --pe PE_UPLOAD --out OUT
  DIAG  = porky-diag-run/diag-full (diagnostic.json, identites_validation.json, probabilites_validation.npz, vocabulaire.json)
  SEAL  = phase1_freeze_2 (MANIFEST.json 3c468faa...)   PE_UPLOAD = petit-eleve/upload (listes.json, images, graphes, s1b)
"""
import argparse
import hashlib
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import a1_core as a1  # noqa: E402
import vlm_core as vc  # noqa: E402

REPO, REV = "davanstrien/iconclass-vlm-brillfull", "8045366ff092a06e8e1c4e47f1eb43cb2a54d732"
DIAG_SHA256 = "312d5a40affb6a399e807dec318e2bd8b569b7c8fcfecfb3552cd1f4cc4457d3"
CACHE_SHA256 = "c7df9d3dd28acea7454cf7609cf083fe961fa5ff5a7ef121a85fc1d7c2eedbe9"
FROZEN_SHA = "2424b778d0a3e7c36e0aeea7ce5db60fcc52bc1eaa6c52a057fd957b142de0ca"
SEAL_SHA256 = "3c468faa7bec5ac7a98104a4ac47d3f7be24ec9ef76e0855f49b42aad12fad0c"
THRESHOLDS = {"B_TZ": 0.65, "T_star": 0.6}
VDIAG_B_H = 0.5860487335040372  # a1/resultats/diagnostic/diagnostic.json H.B (6adb2404), on the 2100 evaluable rows
DEV_H = {"T-Z": 0.4190608607340926, "T_star": 0.42054172423289}  # a1-dev-rijks/resultats/dev.json H (3cc297f4)
LISTES_SHA256 = "87e45b418ace7a4f1a15857456d3d40d107ee3a9c286962e9c19723ecfb065af"  # pe_kaggle.py, as committed (v2.4)
DEV_KEY = b'\n "dev": '
PINNED = {"a1_core.py": "177ef54243fd6dfed0aa557561aa365f41b2c992379aef6d4fab4c5e27ab205a",
          "pe_common.py": "20034ce4f6a71cca72787d53e8d5e6d420d89613ed6b61ba134e9fd5529061af"}
CODE = ("vlm_core.py", "vlm_prepare.py", "vlm_call.py", "vlm_measure.py", "a1_core.py", "pe_common.py")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(8 << 20):
            h.update(chunk)
    return h.hexdigest()


def legacy_sha(obj):
    return hashlib.sha256(json.dumps(obj).encode()).hexdigest()


def require(cond, what):
    if not cond:
        raise SystemExit(f"REFUSED: {what}")


def write_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    tmp.replace(path)


def check_pins():
    for name, want in PINNED.items():
        require(sha(HERE / name) == want, f"pinned_{name}")


# ---------------------------------------------------------------- ICAI validation
def load_diag(diag):
    diag = Path(diag)
    require(sha(diag / "diagnostic.json") == DIAG_SHA256, "diagnostic_sha")
    d = json.loads((diag / "diagnostic.json").read_text())
    for f in ("probabilites_validation.npz", "identites_validation.json", "vocabulaire.json"):
        require(sha(diag / f) == d["files_sha256"][f], f"diag_file_{f}")
    require(d["files_sha256"]["probabilites_validation.npz"] == CACHE_SHA256, "cache_identity")
    vocab = json.loads((diag / "vocabulaire.json").read_text())
    require(len(vocab) == 7907 and legacy_sha(vocab) == d["probability_cache"]["vocabulary_sha256"], "vocabulary")
    ids = json.loads((diag / "identites_validation.json").read_text())
    require(len(ids) == 4265, "validation_rows")
    preds = {}
    with np.load(diag / "probabilites_validation.npz", allow_pickle=False) as z:
        for system, t in THRESHOLDS.items():
            p = np.asarray(z[system])
            require(p.shape == (4265, 7907) and p.dtype == np.float32, f"cache_shape_{system}")
            cache = d["probability_cache"]["systems"][system]
            require(cache["threshold"] == t, f"threshold_{system}")
            preds[system] = a1.project(p, vocab, t)
            require(legacy_sha([sorted(q) for q in preds[system]]) == cache["decisions_sha256"], f"decisions_{system}")
    return vocab, ids, preds


def shard_path(tag):
    require(tag.startswith("train-") and "test" not in tag, "never_a_test_shard")
    return f"datasets/{REPO}@{REV}/data/{tag}.parquet"


class Shards:
    """Row-group reads of the pinned ICAI train shards through HfFileSystem (no full download)."""
    def __init__(self):
        import pyarrow.parquet as pq
        from huggingface_hub import HfFileSystem
        self.fs, self.pq, self.files = HfFileSystem(), pq, {}

    def _file(self, tag):
        if tag not in self.files:
            self.files[tag] = self.pq.ParquetFile(self.fs.open(shard_path(tag), "rb"))
        return self.files[tag]

    def rows(self, tag, rows, columns):
        """{row: {column: value}} for the requested rows of one shard."""
        f, out, start = self._file(tag), {}, 0
        wanted = sorted(set(rows))
        for g in range(f.metadata.num_row_groups):
            n = f.metadata.row_group(g).num_rows
            inside = [r for r in wanted if start <= r < start + n]
            if inside:
                t = f.read_row_group(g, columns=list(columns)).to_pydict()
                for r in inside:
                    out[r] = {c: t[c][r - start] for c in columns}
            start += n
        require(set(out) == set(wanted), f"rows_found_{tag}")
        return out


def icai_vdiag(ids, preds, shards):
    """V-diagnostic rows with their projected truth (labels read from the shards; image md5 checked later)."""
    vd = vc.vdiag_rows([x["md5"] for x in ids])
    by_shard = {}
    for k in vd:
        by_shard.setdefault(ids[k]["shard"], []).append(k)
    truth = {}
    for tag, ks in sorted(by_shard.items()):
        got = shards.rows(tag, [ids[k]["row"] for k in ks], ["label"])
        for k in ks:
            truth[k] = a1.drop86(got[ids[k]["row"]]["label"])
    evaluable = [k for k in vd if truth[k]]
    require(len(evaluable) == 2100, "vdiag_evaluable_2100")
    h_b = float(np.mean([a1.hier_f1(truth[k], preds["B_TZ"][k]) for k in evaluable]))
    require(abs(h_b - VDIAG_B_H) <= 1e-9, "vdiag_B_H_not_reproduced")
    return evaluable, truth


def icai_images(ids, chosen, shards, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    by_shard, files = {}, {}
    for k in chosen:
        by_shard.setdefault(ids[k]["shard"], []).append(k)
    for tag, ks in sorted(by_shard.items()):
        got = shards.rows(tag, [ids[k]["row"] for k in ks], ["image"])
        for k in ks:
            body = got[ids[k]["row"]]["image"]["bytes"]
            require(hashlib.md5(body).hexdigest() == ids[k]["md5"], "icai_image_md5")
            ext = ".png" if body[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg"
            path = out_dir / f"{ids[k]['md5']}{ext}"
            path.write_bytes(body)
            files[k] = path.name
    return files


# ---------------------------------------------------------------- Rijksmuseum dev
def dev_items(path):
    """D10's nt_run.dev_items, unchanged in substance: the "dev" member of frozen.json decoded alone; the test member,
    which precedes it, is never JSON-decoded nor UTF-8-decoded."""
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FROZEN_SHA, "rijks_frozen_sha")
    require(raw.count(DEV_KEY) == 1, "dev_member_not_unique")
    start = raw.index(DEV_KEY) + len(DEV_KEY)
    tail = raw[start:].decode("utf-8")
    dev, end = json.JSONDecoder().raw_decode(tail)
    require(tail[end:].startswith(',\n "'), "dev_member_boundary")
    del raw, tail
    items = dev["items"]
    require(300 <= len(items) <= 319 and len({it["pid"] for it in items}) == len(items), "dev_structure")
    for it in items:
        require(it["truth_projected"] == list(dict.fromkeys(a1.drop86(it["truth"]))) and it["truth_projected"],
                "dev_projection")
    return dev, items


def sealed_dev(seal, dev):
    seal = Path(seal)
    require(sha(seal / "MANIFEST.json") == SEAL_SHA256, "seal_identity")
    files = json.loads((seal / "MANIFEST.json").read_text())["files"]
    out = {}
    for system in ("T-Z", "T_star"):
        name = f"predictions__rijks_dev__{system}.json"  # only these two dev files of the seal are opened
        info = files[name]
        require(info["bank"] == "rijks_dev" and info["system"] == system and sha(seal / name) == info["sha256"],
                "sealed_dev_file")
        rows = json.loads((seal / name).read_text())["rows"]
        require([{k: x[k] for k in ("index", "id", "image_sha256")} for x in rows] == dev["identities"], "dev_identity_order")
        out[system] = [x["codes"] for x in rows]
    return out


def dev_controls(items, sealed):
    truth = [it["truth_projected"] for it in items]
    for system, want in DEV_H.items():
        h = float(np.mean([a1.hier_f1(t, p) for t, p in zip(truth, sealed[system], strict=True)]))
        require(abs(h - want) <= 1e-9, f"dev_H_{system}_not_reproduced")


def download(row, last=[0.0]):
    """The phase-1 gel Downloader, one request per second, bytes checked against the frozen image_sha256."""
    body = None
    for attempt in range(5):
        time.sleep(max(0.0, 1.0 - (time.monotonic() - last[0])))
        last[0] = time.monotonic()
        try:
            req = urllib.request.Request(row["iiif"], headers={"User-Agent": "caypollard/0.1 (research prototype)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read(64 * (1 << 20) + 1)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                break
            time.sleep(10 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.HTTPException):
            time.sleep(10 * (attempt + 1))
    require(body is not None and len(body) <= 64 * (1 << 20), "rijks_download_failed")
    require(hashlib.sha256(body).hexdigest() == row["image_sha256"], "rijks_image_bytes_changed")
    return body


# ---------------------------------------------------------------- petit élève evaluation images
def pe_evaluation(pe, out_dir):
    pe = Path(pe)
    require(sha(pe / "listes.json") == LISTES_SHA256, "pe_listes_not_the_approved_file")  # v2.4, Codex note 1
    listes = json.loads((pe / "listes.json").read_text())
    rows = [r for r in listes["evaluation"] if r.get("gemini_graph_sha256")]
    require(len(rows) == 26, "pe_26_evaluation_graphs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for r in rows:
        img = pe / "images" / f"{r['name']}.jpg"
        require(sha(img) == r["image_sha256"], f"pe_image_{r['name']}")
        require(sha(pe / "graphes" / f"{r['name']}.json") == r["gemini_graph_sha256"], f"pe_graph_{r['name']}")
        require(r.get("s1b_graph_sha256") and sha(pe / "s1b" / f"{r['name']}.json") == r["s1b_graph_sha256"],
                f"pe_s1b_{r['name']}")
        (out_dir / img.name).write_bytes(img.read_bytes())
        out.append({"name": r["name"], "image": img.name, "image_sha256": r["image_sha256"],
                    "gemini_graph": str(pe / "graphes" / f"{r['name']}.json"), "gemini_graph_sha256": r["gemini_graph_sha256"],
                    "s1b_graph": str(pe / "s1b" / f"{r['name']}.json"), "s1b_graph_sha256": r["s1b_graph_sha256"]})
    return out


# ---------------------------------------------------------------- plan
BLOCKS = ("dev", "opus", "vdiag", "graphes")  # S1 order (v2.2, B2): the family first


def plan_calls(vdiag, dev, opus, repeat, pe):
    """Call specs per stage. S0: 5 dev images per system and 2 graph images for H and G (never scored). S1 in blocks,
    in the order of BLOCKS; vdiag items are given in the draw order of their groups."""
    calls = {"S0": [], "S1": [], "R": []}
    for s in vc.MAIN_SYSTEMS:
        calls["S1"] += [{"system": s, "kind": "codes", "bank": "rijks_dev", "item": x, "block": "dev"} for x in dev]
    calls["S1"] += [{"system": "O", "kind": "codes", "bank": "rijks_dev", "item": x, "block": "opus"} for x in opus]
    for s in vc.MAIN_SYSTEMS:
        calls["S1"] += [{"system": s, "kind": "codes", "bank": "icai_vdiag", "item": x, "block": "vdiag"} for x in vdiag]
    for s in vc.MAIN_SYSTEMS:
        calls["S1"] += [{"system": s, "kind": "boites", "bank": "pe_eval", "item": x, "block": "graphes"} for x in pe]
    for s in vc.MAIN_SYSTEMS:
        calls["R"] += [{"system": s, "kind": "codes", "bank": "rijks_dev", "item": x, "block": "repet"} for x in repeat]
        calls["S0"] += [{"system": s, "kind": "codes", "bank": "rijks_dev", "item": x, "block": "s0"} for x in dev[:5]]
        calls["S0"] += [{"system": s, "kind": "boites", "bank": "pe_eval", "item": x, "block": "s0"} for x in pe[:2]]
    calls["S0"] += [{"system": "O", "kind": "codes", "bank": "rijks_dev", "item": x, "block": "s0"} for x in dev[:5]]
    for stage, lst in calls.items():
        for c in lst:
            c["id"] = f"{stage}:{c['system']}:{c['bank']}:{c['item']}"
        require(len({c["id"] for c in lst}) == len(lst), f"unique_call_ids_{stage}")
    return calls


def main(a):
    check_pins()
    out = Path(a.out)
    require(not (out / "prep.json").exists(), "preparation_already_sealed")
    (out / "images").mkdir(parents=True, exist_ok=True)

    vocab, ids, preds = load_diag(a.diag)
    shards = Shards()
    evaluable, truth = icai_vdiag(ids, preds, shards)
    groups = {}
    for k in evaluable:
        groups.setdefault(ids[k]["md5"], []).append(k)
    chosen_groups = vc.draw_whole_groups(groups, vc.MIN_IMAGES["vdiag"], vc.SEED)
    vdiag_rows = [k for g in chosen_groups for k in sorted(groups[g])]  # draw order of the groups (v2.2 reduction rule)
    files = icai_images(ids, vdiag_rows, shards, out / "images" / "icai")

    dev, items = dev_items(a.frozen)
    sealed = sealed_dev(a.seal, dev)
    dev_controls(items, sealed)
    (out / "images" / "rijks").mkdir(exist_ok=True)
    for it in items:
        path = out / "images" / "rijks" / f"{it['pid']}.jpg"
        if not (path.exists() and sha(path) == it["image_sha256"]):
            path.write_bytes(download(it))
    comps = {}
    for it in items:
        comps.setdefault(str(it["component"]), []).append(it["pid"])
    opus = sorted(p for c in vc.draw_whole_groups(comps, vc.MIN_IMAGES["opus"], vc.SEED) for p in comps[c])
    repeat = sorted(p for c in vc.draw_whole_groups(comps, vc.MIN_IMAGES["repeat"], vc.SEED_REPEAT) for p in comps[c])
    pe = pe_evaluation(a.pe, out / "images" / "pe")

    rank = {g: i for i, g in enumerate(chosen_groups)}
    icai = [{"key": f"v{k}", "row": k, "md5": ids[k]["md5"], "image": f"icai/{files[k]}", "truth": truth[k],
             "group": ids[k]["md5"], "draw_rank": rank[ids[k]["md5"]], "B": preds["B_TZ"][k], "T_star": preds["T_star"][k]}
            for k in vdiag_rows]
    rijks = [{"key": it["pid"], "image": f"rijks/{it['pid']}.jpg", "image_sha256": it["image_sha256"],
              "truth": it["truth_projected"], "group": str(it["component"]), "B": sealed["T-Z"][i],
              "T_star": sealed["T_star"][i]} for i, it in enumerate(items)]
    calls = plan_calls([x["key"] for x in icai], [x["key"] for x in rijks], opus, repeat, [x["name"] for x in pe])
    prep = {"preinscription": "PREINSCRIPTION-v2.4.md", "models": vc.MODELS, "seed": vc.SEED, "seed_repeat": vc.SEED_REPEAT,
            "vocabulary": vocab, "prompts_sha256": vc.prompts_sha256(vocab),
            "code_sha256": {n: sha(HERE / n) for n in CODE},
            "banks": {"icai_vdiag": icai, "rijks_dev": rijks, "pe_eval": pe},
            "samples": {"vdiag_groups": len(chosen_groups), "vdiag_images": len(icai),
                        "vdiag_groups_order": [[g, len(groups[g])] for g in chosen_groups], "dev_images": len(rijks),
                        "dev_components": len(comps), "opus": opus, "repeat": repeat},
            "calls": calls, "planned": {k: len(v) for k, v in calls.items()},
            "controls": {"vdiag_evaluable": 2100, "vdiag_B_H": VDIAG_B_H, "dev_H": DEV_H, "decisions": "cache sha256 equal",
                         "test_rows": 0},
            "image_sha256": {str(p.relative_to(out / "images")): sha(p) for p in sorted((out / "images").rglob("*"))
                             if p.is_file()}}
    write_json(out / "prep.json", prep)
    print("prep.json", sha(out / "prep.json"), prep["planned"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for k in ("diag", "frozen", "seal", "pe", "out"):
        ap.add_argument(f"--{k}", required=True)
    main(ap.parse_args())
