#!/usr/bin/env python3
"""Rejouer la règle de décision d'une expérience sur son reçu d'agrégats.

Usage :
    python3 rejouer.py --regle regle.py --recu recu.json [--complement NOM=chemin.json ...]
                       [--attendu STATUT] [--sortie DOSSIER]

La règle est un fichier `regle.py` qui définit `issue(recu: dict) -> dict` : fonction pure, qui lit seulement le reçu
d'agrégats publié et rend l'issue écrite dans la carte (`{"statut": ..., "motifs": [...]}`, d'autres clés
descriptives sont permises). Elle n'importe rien du noyau de calcul : seuls les modules de la bibliothèque standard
sont admis, et un import dont le nom commence par `noyau` est refusé.

`--complement NOM=chemin.json` ajoute un second reçu d'agrégats ; la règle le lit sous `recu["complements"][NOM]`.

Écrit `issue-recalculee.json` (empreintes SHA-256 de la règle, du reçu et des compléments, puis l'issue) dans
`--sortie`, par défaut à côté du reçu. Le fichier ne contient ni date ni chemin : rejouer deux fois donne les mêmes
octets. Code de sortie : 0 ; 1 si l'issue diffère de `--attendu` ; 2 pour une erreur d'usage ou de règle.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def verifier_imports(chemin: Path) -> None:
    """Refuse une règle qui importe autre chose que la bibliothèque standard, ou quoi que ce soit de `noyau`."""
    arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=chemin.name)
    for n in ast.walk(arbre):
        noms = [a.name for a in n.names] if isinstance(n, ast.Import) else \
            ([n.module or ""] if isinstance(n, ast.ImportFrom) and n.level == 0 else [])
        if isinstance(n, ast.ImportFrom) and n.level > 0:
            raise ValueError(f"{chemin.name} : import relatif interdit")
        for nom in noms:
            racine = nom.split(".")[0]
            if racine.startswith("noyau") or racine not in sys.stdlib_module_names:
                raise ValueError(f"{chemin.name} : import interdit « {nom} » (bibliothèque standard seulement)")


def charger_regle(chemin: Path):
    verifier_imports(chemin)
    spec = importlib.util.spec_from_file_location("regle_chargee", chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "issue", None)):
        raise ValueError(f"{chemin.name} : pas de fonction issue(recu)")
    return module


def verifier_issue(issue) -> None:
    if not isinstance(issue, dict) or not isinstance(issue.get("statut"), str) or \
            not isinstance(issue.get("motifs"), list):
        raise ValueError("l'issue doit être un dict avec « statut » (texte) et « motifs » (liste)")


def rejouer(regle: Path, recu: Path, complements: dict[str, Path] | None = None) -> dict:
    """Retourne le contenu de issue-recalculee.json."""
    module = charger_regle(regle)
    donnees = json.loads(recu.read_text(encoding="utf-8"))
    comp = {nom: p for nom, p in sorted((complements or {}).items())}
    if comp:
        donnees["complements"] = {nom: json.loads(p.read_text(encoding="utf-8")) for nom, p in comp.items()}
    issue = module.issue(donnees)
    verifier_issue(issue)
    return {"regle": {"fichier": regle.name, "sha256": sha256(regle)},
            "recu": {"fichier": recu.name, "sha256": sha256(recu)},
            "complements": {nom: {"fichier": p.name, "sha256": sha256(p)} for nom, p in comp.items()},
            "issue": issue}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rejouer", description="Rejouer une règle de décision sur son reçu.")
    p.add_argument("--regle", required=True)
    p.add_argument("--recu", required=True)
    p.add_argument("--complement", action="append", default=[], metavar="NOM=CHEMIN")
    p.add_argument("--attendu")
    p.add_argument("--sortie", help="dossier de sortie (par défaut : celui du reçu)")
    a = p.parse_args(argv)
    try:
        comp = {}
        for c in a.complement:
            nom, _, chemin = c.partition("=")
            if not nom or not chemin:
                raise ValueError(f"--complement attend NOM=CHEMIN, reçu « {c} »")
            comp[nom] = Path(chemin)
        resultat = rejouer(Path(a.regle), Path(a.recu), comp)
    except (ValueError, OSError, SyntaxError, json.JSONDecodeError) as e:
        print("erreur :", e, file=sys.stderr)
        return 2
    dossier = Path(a.sortie) if a.sortie else Path(a.recu).resolve().parent
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "issue-recalculee.json").write_text(
        json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    statut = resultat["issue"]["statut"]
    print(f"issue recalculée : {statut}")
    if a.attendu is not None and statut != a.attendu:
        print(f"DIFFÈRE de l'issue attendue « {a.attendu} »", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
