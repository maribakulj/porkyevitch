#!/usr/bin/env python3
"""Vérifie qu'un dépôt reste neutre : aucune trace d'un projet particulier dans le code ni la documentation.

Usage : python3 -I outils/neutralite.py [RACINE] [--termes FICHIER]

Deux sortes de règles :
- **génériques**, toujours appliquées : chemins personnels (`/Users/nom`, `/home/nom`), adresses électroniques,  <!-- neutralite: ok (exemples) -->
  identifiants de décision (`D17`) et d'onglet d'agent (`wA:p1`). Elles attrapent ce qui fuit d'un journal ;  <!-- neutralite: ok (exemples) -->
- **termes d'un projet**, lus dans FICHIER (un par ligne, `#` pour commenter), insensibles à la casse. Ce fichier
  appartient au projet privé et ne vient jamais ici : publier la liste serait publier ce qu'elle protège.

Une ligne qui doit garder un motif porte `neutralite: ok` en commentaire, avec sa raison.
Code de sortie : 0 neutre, 1 trace trouvée, 2 usage.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

GENERIQUES = {
    "chemin personnel": re.compile(r"/(?:Users|home)/(?!Shared\b|runner\b)[A-Za-z][\w.-]*"),
    "adresse électronique": re.compile(r"(?<!git)@?\b[\w.+-]+@(?!github\.com\b)[\w-]+\.[a-z]{2,}\b"),
    "identifiant de décision": re.compile(r"\bD\d{1,3}\b"),
    "onglet d'agent": re.compile(r"\bwA:p\w*"),
}
EXEMPTION = "neutralite: ok"
EXTENSIONS_TEXTE = {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".sh", ".txt", ".cfg", ".ini", ""}


def fichiers(racine: Path) -> list[Path]:
    """Les fichiers suivis par git, ou tout l'arbre hors .git si ce n'est pas un dépôt."""
    try:
        r = subprocess.run(["git", "-C", str(racine), "ls-files", "-z"], capture_output=True, text=True, check=True)
        noms = [n for n in r.stdout.split("\0") if n]
        if noms:
            return [racine / n for n in noms]
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in racine.rglob("*") if p.is_file() and ".git" not in p.parts]


def lire_termes(chemin: Path) -> list[str]:
    termes = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if ligne:
            termes.append(ligne)
    return termes


def examiner(racine: Path, termes: list[str]) -> list[str]:
    motifs = dict(GENERIQUES)
    for t in termes:
        motifs[f"terme du projet « {t} »"] = re.compile(rf"(?<![\w]){re.escape(t)}(?![\w])", re.IGNORECASE)
    traces = []
    for f in fichiers(racine):
        if f.suffix not in EXTENSIONS_TEXTE or not f.is_file():
            continue
        try:
            texte = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for n, ligne in enumerate(texte.splitlines(), 1):
            if EXEMPTION in ligne:
                continue
            for nom, motif in motifs.items():
                if motif.search(ligne):
                    traces.append(f"{f.relative_to(racine)}:{n}: {nom} : {ligne.strip()[:120]}")
    return traces


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Le dépôt est-il neutre ?")
    a.add_argument("racine", nargs="?", default=".", type=Path)
    a.add_argument("--termes", type=Path, help="fichier des termes du projet privé, un par ligne")
    args = a.parse_args(argv)
    termes = lire_termes(args.termes) if args.termes else []
    traces = examiner(args.racine.resolve(), termes)
    for t in traces:
        print(t)
    if traces:
        print(f"{len(traces)} trace(s) d'un projet particulier.", file=sys.stderr)
        return 1
    print(f"neutre ({len(GENERIQUES)} règles génériques, {len(termes)} terme(s) de projet).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
