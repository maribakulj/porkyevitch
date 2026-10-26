#!/usr/bin/env python3
"""Copy experiments out of a caypollard clone into experiences/, with a PROVENANCE.md for each (plan of 25/10/2026).

Usage: tools/migrer.py <caypollard clone>
Only files tracked by git at the clone's HEAD are copied (never untracked data, never licensed raw files). Nothing in caypollard is
changed. Each PROVENANCE.md gives: the source commit, old path -> new path with sha256, the script hashes recorded by each run
(run.json) and whether the copied script matches them, the untracked artifacts left behind, and what the scripts still read from
caypollard. Migrated scripts are copies for the record: they still run from a caypollard clone at that commit.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# experience folder -> (paths in caypollard, note)
EXPERIENCES = {
    "2026-10-25-iconclass-tete": (
        ["scripts/remote_iconclass_head.py", "scripts/remote_iconclass_vlm_bench.py", "results/iconclass-tete"],
        "Tête Iconclass sur C-RADIOv3-L (T) et voisins (K), test ICAI 788 ; banc de vitesse et de fidélité du VLM 4B.",
    ),
    "2026-10-25-iconclass-externe": (
        ["scripts/build_external_iconclass_bench.py", "scripts/remote_external_iconclass.py", "scripts/remote_external_vlm.py",
         "results/iconclass-externe"],
        "Banc extérieur Emblematica (filtres, tirages gel/gel2, étalonnage) ; T, K et VLM 4B/9B sur ce banc.",
    ),
    "2026-10-25-iconclass-tete-pe": (
        ["scripts/remote_iconclass_head.py", "scripts/iconclass_par_usage.py", "results/iconclass-tete-pe"],
        "Même tête sur PE-Spatial (T-PE) et comparaison par usage ; C-RADIO reste la version recommandée.",
    ),
    "2026-10-17-graphe-de-scene": (
        ["scripts/build_scene_train_set.py", "scripts/remote_train_scene_lora.py", "scripts/remote_scene_qwen.py",
         "scripts/remote_head_scene.py", "scripts/colab_train_scene.sh", "results/decision-graphe"],
        "Décision « graphe de scène » : LoRA Qwen 7B, tête maison, Qwen sans entraînement, revues de sources. "
        "`colab_train_scene.sh` est gardé comme archive, pas comme lanceur (le lanceur actif est porky/colab.py).",
    ),
    "2026-10-25-xanto-parties": (
        ["scripts/remote_xanto_parts.py", "results/xanto-parties"],
        "Test pose/parties pour Xanto. Appartient au projet xanto : copié ici en attendant, à rendre à son agent.",
    ),
    "2026-10-25-notebooks-caypollard": (
        ["notebooks"],
        "Notebooks de la branche pilote-figures. Interfaces sur fixtures, sans execution_count. "
        "Ce ne sont pas les pilotes des entraînements Colab ou Kaggle des autres expériences.",
    ),
}


# Untracked files copied anyway: small scripts and training logs, no licensed data (RichArt raw files and papers stay behind).
EXTRAS = {
    "2026-10-17-graphe-de-scene": ["results/decision-graphe/classify.py", "results/decision-graphe/stats.py",
                                   "results/decision-graphe/verbs.py", "results/decision-graphe/qwen7b-lora/log.json",
                                   "results/decision-graphe/tete-maison/log.json"],
}


def sh(*args: str, cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tracked(src: Path, rel: str) -> list[str]:
    return [f for f in sh("git", "-c", "core.quotepath=off", "ls-files", "-z", "--", rel, cwd=src).split("\0") if f]


def script_hashes(d):
    """Every value recorded under a key named script_sha256 or script (a 64-hex sha256), at any depth."""
    if isinstance(d, dict):
        for k, v in d.items():
            if k in ("script_sha256", "script") and isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v):
                yield v
            else:
                yield from script_hashes(v)
    elif isinstance(d, list):
        for v in d:
            yield from script_hashes(v)


def in_history(src: Path, paths: list[str], want: str) -> str | None:
    """'path@commit' of the first committed version of one of these scripts whose sha256 is `want`."""
    for path in paths:
        for commit in sh("git", "log", "--format=%H", "--", path, cwd=src).split():
            blob = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=src, capture_output=True).stdout
            if hashlib.sha256(blob).hexdigest() == want:
                return f"{path}@{commit}"
    return None


def main() -> None:
    src = Path(sys.argv[1]).resolve()
    head = sh("git", "rev-parse", "HEAD", cwd=src).strip()
    remote = sh("git", "remote", "get-url", "origin", cwd=src).strip()
    dirty = sh("git", "status", "--porcelain", cwd=src).strip()
    for name, (paths, note) in EXPERIENCES.items():
        dest = HERE / "experiences" / name
        rows, scripts, left, reads = [], {}, [], []
        for rel in paths:
            files = tracked(src, rel)
            assert files, f"{rel}: nothing tracked"
            files += [e for e in EXTRAS.get(name, []) if e.startswith(rel + "/") and e not in files]
            for f in files:
                if f.startswith("scripts/"):
                    new = Path("scripts") / Path(f).name
                elif f.startswith("notebooks/"):
                    new = Path("notebooks") / Path(f).name
                else:
                    new = Path("resultats") / Path(f).relative_to(rel)
                (dest / new).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src / f, dest / new)
                h = sha(dest / new)
                assert h == sha(src / f)
                rows.append((f, str(new), h))
                if f.startswith("scripts/"):
                    scripts[h] = f
                    text = (src / f).read_text(errors="replace")
                    deps = sorted(set(re.findall(r"from (caypollard[\w.]*) import", text)))
                    if deps or "ROOT" in text:
                        reads.append(f"`{f}` : " + ", ".join([f"importe `{d}`" for d in deps] +
                                                            (["lit des fichiers relatifs à la racine du dépôt (ROOT)"] if "ROOT" in text else [])))
            if (src / rel).is_dir():
                all_files = {str(p.relative_to(src)) for p in (src / rel).rglob("*") if p.is_file()}
                for f in sorted(all_files - set(files)):
                    size = (src / f).stat().st_size
                    left.append((f, size, sha(src / f) if size < 300e6 else "(trop gros, non haché)"))
        runs = []
        for f, new, _ in rows:
            if f.endswith(".json"):
                try:
                    d = json.loads((dest / new).read_text())
                except ValueError:
                    continue
                for s in sorted(set(script_hashes(d))):
                    runs.append((new, s, scripts.get(s) or in_history(src, [r[0] for r in rows if r[0].startswith("scripts/")], s)))
        out = [f"# Provenance — {name}", "", note, "",
               f"- Source : `{remote}`, commit `{head}` (branche pilote-figures), copie du 25/10/2026 par `tools/migrer.py`.",
               "- Copie à l'identique (empreintes vérifiées) des fichiers suivis par git"
               + (" et de quelques fichiers non suivis légers (scripts, journaux d'entraînement)" if name in EXTRAS else "")
               + " ; rien n'a été modifié.",
               "- Les scripts copiés sont une archive : ils s'exécutent depuis un clone de caypollard à ce commit.",
               "- Arbre de travail au moment de la copie : " + ("propre." if not dirty else "fichiers non suivis ou modifiés présents :"
                                                                  + "".join(f"\n  - `{l}`" for l in dirty.splitlines())),
               "", "## Ce qui a réellement tourné", ""]
        if runs:
            for new, s, match in runs:
                if match is None:
                    verdict = "**introuvable** dans les scripts copiés et leur historique git."
                elif "@" in match:
                    verdict = f"version antérieure : `{match}` (copiée ici dans `scripts/executes/`)."
                else:
                    verdict = f"identique au `{match}` copié."
                out.append(f"- `{new}` : script `{s[:12]}…` — {verdict}")
                if match and "@" in match:
                    path, commit = match.split("@")
                    keep = dest / "scripts" / "executes" / f"{Path(path).stem}@{commit[:10]}{Path(path).suffix}"
                    keep.parent.mkdir(parents=True, exist_ok=True)
                    keep.write_bytes(subprocess.run(["git", "show", f"{commit}:{path}"], cwd=src, capture_output=True,
                                                    check=True).stdout)
                    assert sha(keep) == s
        else:
            out.append("- Aucun `run.json` avec empreinte de script dans cette expérience.")
        out += ["", "## Dépendances restées dans caypollard", ""]
        out += [f"- {r}" for r in reads] or ["- Aucune."]
        out += ["", "## Fichiers copiés (ancien chemin → nouveau chemin, sha256)", "", "| caypollard | porkyevitch | sha256 |", "|---|---|---|"]
        out += [f"| `{a}` | `{b}` | `{h[:16]}…` |" for a, b, h in rows]
        out += ["", "## Laissés dans caypollard (non suivis par git : données lourdes ou sous licence)", ""]
        out += [f"- `{f}` ({size / 1e6:.1f} Mo) `{h[:16]}…`" for f, size, h in left] or ["- Aucun."]
        (dest / "PROVENANCE.md").write_text("\n".join(out) + "\n")
        print(name, len(rows), "fichiers,", len(left), "laissés,", len(runs), "runs")


if __name__ == "__main__":
    main()
