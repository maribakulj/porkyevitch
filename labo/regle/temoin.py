#!/usr/bin/env python3
"""Témoin avant la course : la règle de décision laisse-t-elle passer des données nulles ?

Usage :
    python3 temoin.py --regle regle.py --recus-temoins DOSSIER [--sortie DOSSIER]

Le dossier `temoins/` de l'expérience contient un JSON par cas, écrit par la carte avant la course :
    {"description": "...", "doit_conclure": false, "issues_interdites": ["statut", ...], "recu": {...}}
`recu` est un reçu d'agrégats simulé (témoin, données nulles), au format que lit la règle ; un champ facultatif
`complements` ({nom: reçu}) est passé à la règle comme par `rejouer.py`. Avec `"doit_conclure": false`, un témoin
« passe la règle » s'il atteint une issue interdite : celles de `issues_interdites` si présent, sinon celles de la
constante `CONCLUSIFS` de la règle. Un témoin sans l'une ni l'autre est une erreur. Avec `"doit_conclure": true`, le
cas est une vérification de sensibilité : il échoue si l'issue n'est pas dans `issues_attendues`.

Écrit `controle-temoin.json` (empreintes de la règle et de chaque témoin, issue obtenue, verdict du contrôle) dans
`--sortie`, par défaut le dossier parent du dossier de témoins. Code de sortie : 0 si aucun témoin ne passe la
règle ; 1 sinon, en nommant les témoins ; 2 pour une erreur d'usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rejouer  # noqa: E402


def controler(regle: Path, dossier: Path) -> dict:
    module = rejouer.charger_regle(regle)
    fichiers = sorted(dossier.glob("*.json"))
    if not fichiers:
        raise ValueError(f"aucun témoin (*.json) dans {dossier.name}")
    resultats = []
    for f in fichiers:
        t = json.loads(f.read_text(encoding="utf-8"))
        if "recu" not in t or "doit_conclure" not in t:
            raise ValueError(f"{f.name} : champs « recu » et « doit_conclure » obligatoires")
        recu = dict(t["recu"])
        if t.get("complements"):
            recu["complements"] = t["complements"]
        issue = module.issue(recu)
        rejouer.verifier_issue(issue)
        statut = issue["statut"]
        if t["doit_conclure"]:
            attendues = t.get("issues_attendues")
            if attendues is None:
                raise ValueError(f"{f.name} : doit_conclure vrai exige issues_attendues")
            passe, interdites = False, None
            ok = statut in attendues
        else:
            interdites = t.get("issues_interdites", getattr(module, "CONCLUSIFS", None))
            if interdites is None:
                raise ValueError(f"{f.name} : ni issues_interdites ni CONCLUSIFS dans la règle")
            interdites = sorted(interdites)
            passe = statut in interdites
            ok = not passe
        resultats.append({"temoin": f.stem, "sha256": rejouer.sha256(f), "statut_obtenu": statut,
                          "doit_conclure": t["doit_conclure"], "issues_interdites": interdites,
                          "passe_la_regle": passe, "controle_ok": ok})
    return {"regle": {"fichier": regle.name, "sha256": rejouer.sha256(regle)},
            "temoins": resultats,
            "temoins_qui_passent": [r["temoin"] for r in resultats if not r["controle_ok"]]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="temoin", description="Appliquer la règle à des reçus témoins.")
    p.add_argument("--regle", required=True)
    p.add_argument("--recus-temoins", required=True)
    p.add_argument("--sortie")
    a = p.parse_args(argv)
    dossier = Path(a.recus_temoins)
    try:
        resultat = controler(Path(a.regle), dossier)
    except (ValueError, OSError, SyntaxError, json.JSONDecodeError) as e:
        print("erreur :", e, file=sys.stderr)
        return 2
    sortie = Path(a.sortie) if a.sortie else dossier.resolve().parent
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "controle-temoin.json").write_text(
        json.dumps(resultat, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for r in resultat["temoins"]:
        print(f"{r['temoin']} : {r['statut_obtenu']} -> {'ok' if r['controle_ok'] else 'ÉCHEC'}")
    if resultat["temoins_qui_passent"]:
        print("TÉMOIN(S) QUI PASSENT LA RÈGLE : " + ", ".join(resultat["temoins_qui_passent"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
