#!/usr/bin/env python3
"""Conditions de levée : relie le motif d'écartement d'une idée à la condition qui, une fois remplie, la rouvrirait.

Usage :
    python3 levees.py [--config config.toml]        # écrit [levees] fichier (par défaut jugements/levees.toml)

Les conditions sont des données (`[conditions] fichier`, TOML) : chacune porte un `id`, une `description`, un `etat`
(`vraie` ou `fausse`) et `levee_quand` (l'état qui lève l'écartement ; `vraie` par défaut). Une idée écartée dont la
condition est dans l'état `levee_quand` est à réexaminer.

La correspondance est PROPOSÉE par des règles de mots-clés appliquées au motif et à la justification de chaque
notation qui élimine l'idée ; l'orchestrateur relit le fichier écrit. Une entrée qu'il a marquée `relu = true` est
conservée telle quelle à la régénération. Une idée sans règle applicable n'a pas de condition. Aucune dépendance
au graphe : ce module ne lit que du TOML et des CSV.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def norm(texte: str) -> str:
    """Minuscules, sans accents, « _ » lu comme une espace."""
    t = unicodedata.normalize("NFKD", texte.lower().replace("_", " "))
    return "".join(c for c in t if not unicodedata.combining(c))


CATEGORIES = ("sans decision", "doublon", "hors cap", "deja teste", "impossible")


def categorie(motif: str) -> str | None:
    """Catégorie du motif (« sans decision », « doublon », « hors cap », « deja teste », « impossible »)."""
    m = norm(motif).strip()
    for c in CATEGORIES:
        if m.startswith(c):
            return c
    return None


# (nom de la règle, condition, catégories où elle s'applique, expression sur le texte normalisé)
REGLES: list[tuple[str, str, tuple[str, ...], re.Pattern]] = [
    ("juge-gemini", "juge-gemini", ("impossible", "hors cap", "deja teste"), re.compile(r"\bgemini\b")),
    ("juge-grok", "juge-grok", ("impossible", "hors cap", "deja teste"), re.compile(r"\bgrok\b")),
    ("quota-codex", "codex-quota", ("impossible", "hors cap", "deja teste"), re.compile(r"\bcodex\b")),
    ("vlm-d24", "vlm-candidat-production", ("hors cap", "impossible"),
     re.compile(r"\bvlm\b.*(d24|plus (la )?(cible|candidat))|(d24|plus (la )?(cible|candidat)).*\bvlm\b")),
    ("jeu-reserve", "jeu-reserve-cbdd", ("impossible", "hors cap"), re.compile(r"cbdd|jeu reserve")),
    ("encodeur-fige", "encodeur-affinable", ("impossible",), re.compile(r"encodeur fige")),
    ("calcul-gpu", "gpu-kaggle", ("impossible", "hors cap"), re.compile(r"\b(gpu|kaggle|colab)\b")),
    ("humain-q1", "Q1-jugement-humain", ("impossible",),
     re.compile(r"\bq1\b|humain|annotat|catalogueur|historien|expert|crowdsourc|evaluateur|relecteur|"
                r"a la main|manuel")),
    ("xanto-3d2d", "chantiers-xanto-3d2d-separes", ("hors cap",),
     re.compile(r"xanto|3d2d|\bd56\b|copies?\b|appariement|\bsift\b|loftr|lightglue|homographie|projet a part")),
]


def proposer(motif: str, justification: str = "") -> tuple[str, str] | None:
    """(condition, nom de la règle) pour un motif et sa justification, ou None. Première règle applicable."""
    cat = categorie(motif)
    if cat is None:
        return None
    texte = norm(motif + " " + justification)
    for nom, cond, cats, rx in REGLES:
        if cat in cats and rx.search(texte):
            return cond, nom
    return None


RX_DOUBLON = re.compile(r"\bI\d+\b")


def doublon_de(motif: str, justification: str, propre: str) -> str | None:
    """L'idée dont celle-ci est le doublon, lue dans « même … que I011 » quand la colonne dédiée est vide."""
    if categorie(motif) != "doublon":
        return None
    for m in RX_DOUBLON.findall(motif + " " + justification):
        if m != propre:
            return m
    return None


# ---------------------------------------------------------------- fichiers

def lire_conditions(chemin: Path) -> dict[str, dict]:
    brut = tomllib.loads(chemin.read_text(encoding="utf-8"))
    sortie = {}
    for c in brut.get("condition", []):
        etat = c.get("etat")
        if etat not in ("vraie", "fausse"):
            raise ValueError(f"condition {c.get('id')} : état « {etat} » (attendu vraie ou fausse)")
        if c.get("levee_quand", "vraie") not in ("vraie", "fausse"):
            raise ValueError(f"condition {c.get('id')} : levee_quand invalide")
        sortie[c["id"]] = c
    return sortie


def condition_levee(c: dict) -> bool:
    return c["etat"] == c.get("levee_quand", "vraie")


def lire_levees(chemin: Path) -> list[dict]:
    if not chemin.is_file():
        return []
    return tomllib.loads(chemin.read_text(encoding="utf-8")).get("levee", [])


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def ecrire_levees(chemin: Path, entrees: list[dict]) -> None:
    L = ["# Correspondances motif -> condition de levée, PROPOSÉES par labo/graphe/levees.py (règles de mots-clés).",
         "# L'orchestrateur relit ; une entrée marquée relu = true est conservée telle quelle à la régénération.",
         "# Une idée absente de ce fichier n'a pas de condition de levée.", ""]
    for e in entrees:
        L += ["[[levee]]", f"idee = {_q(e['idee'])}", f"notateur = {_q(e['notateur'])}", f"motif = {_q(e['motif'])}",
              f"condition = {_q(e['condition'])}", f"regle = {_q(e.get('regle', ''))}",
              f"extrait = {_q(e.get('extrait', ''))}", f"relu = {'true' if e.get('relu') else 'false'}", ""]
    chemin.write_text("\n".join(L), encoding="utf-8")


def proposer_depuis_config(brut: dict, dossier: Path, conditions: dict, existantes: list[dict]) -> list[dict]:
    """Applique les règles à toutes les notations qui éliminent ; garde les entrées relues."""
    gardees = {(e["idee"], e["notateur"]): e for e in existantes if e.get("relu")}
    entrees = dict(gardees)
    col_id = brut.get("idees", {}).get("colonnes", {}).get("identifiant", "id")
    for c in brut.get("notations", []):
        with open((dossier / c["fichier"]).resolve(), encoding=c.get("encodage", "utf-8-sig"), newline="") as f:
            for lig in csv.DictReader(f, delimiter=c.get("separateur", ";")):
                ident = lig.get(c.get("identifiant", col_id), "").strip()
                if lig.get(c.get("elimine", "elimine"), "").strip().lower() not in ("oui", "true", "1", "o"):
                    continue
                if (ident, c["notateur"]) in gardees:
                    continue
                motif = lig.get(c.get("motif", "motif"), "").strip()
                just = lig.get(c.get("justification", "justification"), "").strip()
                p = proposer(motif, just)
                if p is None or p[0] not in conditions:
                    continue
                entrees[(ident, c["notateur"])] = {
                    "idee": ident, "notateur": c["notateur"], "motif": categorie(motif) or motif, "condition": p[0],
                    "regle": p[1], "extrait": (just or motif)[:160], "relu": False}
    return [entrees[k] for k in sorted(entrees)]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="levees", description="Proposer les conditions de levée des idées écartées.")
    p.add_argument("--config", default="config.toml")
    a = p.parse_args(argv)
    try:
        import graphe
        cfg = graphe.Config(Path(a.config))
        cch = cfg.brut.get("conditions", {}).get("fichier")
        if not cch:
            print("erreur : pas de [conditions] fichier dans la configuration", file=sys.stderr)
            return 2
        conditions = lire_conditions(cfg.chemin(cch))
        sortie = cfg.chemin(cfg.brut.get("levees", {}).get("fichier", "jugements/levees.toml"))
        entrees = proposer_depuis_config(cfg.brut, cfg.dossier, conditions, lire_levees(sortie))
        ecrire_levees(sortie, entrees)
    except (graphe.ErreurContenu, OSError, ValueError, KeyError, tomllib.TOMLDecodeError) as e:
        print("erreur :", e, file=sys.stderr)
        return 1
    n = {}
    for e in entrees:
        n[e["condition"]] = n.get(e["condition"], 0) + 1
    print(f"{sortie} écrit : {len(entrees)} correspondance(s)")
    for k, v in sorted(n.items()):
        print(f"  {k:32} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
