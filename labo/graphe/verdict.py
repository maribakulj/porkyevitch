#!/usr/bin/env python3
"""Écrit un verdict proposé, et le refuse s'il viole les formes du graphe.

Usage :
    python3 verdict.py [--config config.toml] H-ID STATUT --auteur ROLE [--condition TEXTE]...
        [--course R-ID --artefact NOM [--valeur X --ic-bas B --ic-haut H]] [--reouvrir-si TEXTE]
        [--motif-invalidite TEXTE] [--id V-…]

STATUT : non-testee, test-invalide, non-concluante, refutee, soutenue ou suspendue.

Le verdict est ajouté au fichier de verdicts déclaré par la configuration, le graphe est reconstruit en mémoire et
validé. Si le verdict fait apparaître une violation que le graphe n'avait pas avant, le fichier est remis dans son état
d'origine et la commande sort avec le code 1 en disant laquelle : « réfutée » sans puissance suffisante, sans carte
confirmatoire ou sans prémisse vérifiée est refusée ; « non concluante » ne l'est pas. Si le verdict est accepté, le
graphe écrit est reconstruit.
Code de sortie : 0 accepté, 1 refusé, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graphe  # noqa: E402
from graphe import STATUTS, Config, ErreurContenu  # noqa: E402


def bloc_verdict(v: dict) -> str:
    """Un tableau TOML [[verdict]] ; json.dumps fournit des chaînes et des listes TOML valides."""
    lignes = ["", "[[verdict]]"]
    for cle, val in v.items():
        lignes.append(f"{cle} = {json.dumps(val, ensure_ascii=False)}")
    return "\n".join(lignes) + "\n"


def proposer(cfg: Config, v: dict) -> tuple[bool, list[tuple[str, str]]]:
    """Ajoute le verdict s'il ne crée aucune nouvelle violation. Retourne (accepté, nouvelles violations)."""
    chemin = cfg.chemin(cfg.brut["jugements"]["verdicts"])
    ancien = chemin.read_text(encoding="utf-8") if chemin.is_file() else ""
    g0, _ = graphe.construire(cfg, ancien)
    if not any(str(s).endswith(v["hypothese"]) for s in g0.subjects(graphe.RDF.type, graphe.LAB.Hypothese)):
        raise ErreurContenu(f"hypothèse {v['hypothese']} inconnue : déclare-la d'abord dans le fichier des hypothèses")
    avant = set(graphe.violations(g0))
    nouveau = ancien + bloc_verdict(v)
    g1, _ = graphe.construire(cfg, nouveau)
    apres = set(graphe.violations(g1))
    # bloquent : les violations nouvelles, et celles qui touchent ce sur quoi le verdict s'appuie (sa course, les
    # cartes qui la portent, l'hypothèse), même si elles existaient déjà : on ne conclut pas sur une base fautive
    h = graphe.URIRef(cfg.espace + v["hypothese"])
    base = {h}
    if v.get("course"):
        co = graphe.URIRef(cfg.espace + v["course"])
        base.add(co)
        for assoc in g1.objects(co, graphe.PROV.qualifiedAssociation):
            for cc in g1.objects(assoc, graphe.PROV.hadPlan):
                base.add(cc)
                base.update(g1.objects(cc, graphe.LAB.carteRecherche))
    base.update(g1.subjects(graphe.LAB.teste, h))
    nouvelles = sorted(v_ for v_ in apres if v_ not in avant or v_[0] in {str(b) for b in base})
    if nouvelles:
        return False, nouvelles
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(nouveau, encoding="utf-8")
    graphe.ecrire(g1, cfg.sortie("graphe", "graphe.ttl"))
    return True, []


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="verdict", description="Écrire un verdict, refusé s'il viole les formes.")
    p.add_argument("--config", default="config.toml")
    p.add_argument("hypothese")
    p.add_argument("statut", choices=sorted({k for k in STATUTS if k == k.lower() and " " not in k and "é" not in k}))
    p.add_argument("--auteur", required=True, help="un rôle, jamais un nom")
    p.add_argument("--condition", action="append", default=[])
    p.add_argument("--course")
    p.add_argument("--artefact")
    p.add_argument("--valeur", type=float)
    p.add_argument("--ic-bas", type=float)
    p.add_argument("--ic-haut", type=float)
    p.add_argument("--reouvrir-si")
    p.add_argument("--motif-invalidite")
    p.add_argument("--id")
    a = p.parse_args(argv)
    try:
        cfg = Config(Path(a.config))
        chemin = cfg.chemin(cfg.brut["jugements"]["verdicts"])
        ancien = chemin.read_text(encoding="utf-8") if chemin.is_file() else ""
        n = ancien.count("[[verdict]]") + 1
        v: dict = {"id": a.id or f"V-{a.hypothese}-{n}", "hypothese": a.hypothese, "statut": a.statut,
                   "auteur": a.auteur, "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        if a.condition:
            v["conditions"] = a.condition
        for cle in ("course", "artefact", "valeur", "ic_bas", "ic_haut", "reouvrir_si", "motif_invalidite"):
            if getattr(a, cle) is not None:
                v[cle] = getattr(a, cle)
        ok, nouvelles = proposer(cfg, v)
    except (ErreurContenu, KeyError) as e:
        print("erreur :", e, file=sys.stderr)
        return 1
    if ok:
        print(f"verdict {v['id']} accepté ({a.statut}) ; graphe reconstruit")
        return 0
    print(f"verdict {v['id']} REFUSÉ : fichier inchangé")
    for noeud, msg in nouvelles:
        print(f"  {noeud} : {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
