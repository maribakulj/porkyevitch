#!/usr/bin/env python3
"""Enregistre les décisions du projet, les note après coup et en tire un bilan.

Usage :
    python3 decision.py [--config config.toml] proposer FICHIER.toml
    python3 decision.py [--config config.toml] noter D-ID --issue TEXTE --realisee true|false
        [--changement-realise true|false] [--statut-obtenu STATUT] [--heures-mesurees H] [--heures-agent-mesurees H]
    python3 decision.py [--config config.toml] executer D-ID
    python3 decision.py [--config config.toml] renverser D-ID --par D-ID2
    python3 decision.py [--config config.toml] bilan

proposer : FICHIER.toml décrit une décision (champs au premier niveau, ou dans un bloc [[decision]]) :
    id (facultatif), description, auteur (un rôle), fonde_sur (verdicts, résultats ou décisions),
    options = [{libelle = "…", valeur_v = 1.5}, …] (dont « ne rien faire »), choix (un libellé), regle,
    prediction_issue (un des six statuts) ou prediction_branche (une branche du tableau issue → décision), et prediction_proba (dans [0,1]), p_changement (dans [0,1]),
    poids (1 à 5), chantier (« C-n »), effet (ouvre_chantier, ferme_chantier, clot_piste, production, suite,
    instrument), statut_propose, heures_agent, heures_calcul, remplace (décision remplacée), etat (proposee,
    en_attente_humain, relue ; par défaut relue si la relecture est jointe),
    et pour une décision importante : relecture_verdict, relecture_date, relecture_auteur (autre que l'auteur) et
    dossier_empreinte (SHA-256 du fichier de candidats dont les cinq premiers sont le dossier de relecture).
L'importance n'est jamais choisie : decision.py la calcule (poids ≥ 4 ; effet ouvre_chantier, ferme_chantier,
clot_piste ou production ; statut réfuté ou suspendu proposé ; plus de 3 h de calcul du chantier sur 24 h ; verdict
exploratoire pour une mise en production) et écrase ce que le fichier dirait.
La décision est ajoutée au fichier des décisions déclaré par la configuration ([jugements] decisions), le graphe est
reconstruit en mémoire et validé. Si elle crée une violation, le fichier est remis dans son état d'origine et la
commande sort avec le code 1 en disant laquelle.

noter : écrit l'issue réelle d'une décision (la prédiction s'est-elle réalisée) et la date de notation.
bilan : nombre de décisions, score de Brier des décisions notées, part courantes/importantes, écart moyen entre
heures de calcul mesurées et estimées.
Code de sortie : 0 accepté, 1 refusé, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graphe  # noqa: E402
from graphe import Config, ErreurContenu  # noqa: E402

ENTETE = "# Décisions du projet. Écrit par decision.py (proposer, noter) ; ne pas modifier à la main.\n"
MARQUE = "[[decision]]"


def maintenant() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def toml_valeur(v) -> str:
    """Valeur TOML : json.dumps convient aux chaînes, nombres, booléens et listes, pas aux tables en ligne."""
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {toml_valeur(x)}" for k, x in v.items()) + " }"
    if isinstance(v, list):
        return "[" + ", ".join(toml_valeur(x) for x in v) + "]"
    return json.dumps(v, ensure_ascii=False)


def bloc_decision(d: dict) -> str:
    """Un tableau TOML [[decision]]."""
    lignes = ["", MARQUE]
    for cle, val in d.items():
        lignes.append(f"{cle} = {toml_valeur(val)}")
    return "\n".join(lignes) + "\n"


def _chemin(cfg: Config) -> Path:
    try:
        return cfg.chemin(cfg.brut["jugements"]["decisions"])
    except KeyError as e:
        raise ErreurContenu("la configuration ne déclare pas [jugements] decisions = …") from e


def _lire(chemin: Path) -> str:
    return chemin.read_text(encoding="utf-8") if chemin.is_file() else ""


def _verifier(cfg: Config, ancien: str, nouveau: str, ciblees: set[str]):
    """Retourne (graphe, nouvelles violations) : celles qui n'existaient pas, ou qui touchent les décisions visées."""
    g0, _ = graphe.construire(cfg, decisions_texte=ancien)
    g1, _ = graphe.construire(cfg, decisions_texte=nouveau)
    avant, apres = set(graphe.violations(g0)), set(graphe.violations(g1))
    cibles = {cfg.espace + c for c in ciblees}
    # les noeuds Option et Relecture d'une décision comptent comme la décision elle-même
    nouvelles = sorted(v for v in apres if v not in avant or any(v[0] == c or v[0].startswith(c + "-") for c in cibles))
    return g1, nouvelles


IMPORTANTS_EFFETS = {"ouvre_chantier", "ferme_chantier", "clot_piste", "production"}


def _horodatage(t: str) -> datetime:
    return datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def calculer_importance(cfg: Config, d: dict, anciennes: list[dict], g0) -> None:
    """Pose heures_cumulees_24h et importance. L'importance est calculée, jamais choisie."""
    cumul = float(d.get("heures_calcul", 0))
    if d.get("chantier"):
        t = _horodatage(d["date"])
        for a in anciennes:
            if a.get("chantier") == d["chantier"] and a.get("date") and a["id"] != d["id"]:
                dt = (t - _horodatage(a["date"])).total_seconds()
                if 0 <= dt <= 86400:
                    cumul += float(a.get("heures_calcul", 0))
    if "heures_calcul" in d or d.get("chantier"):
        d["heures_cumulees_24h"] = cumul
    exploratoire = False
    if d.get("effet") == "production":
        for ref in d.get("fonde_sur", []):
            exploratoire |= bool(g0.query(graphe_prefixes() + f"""ASK {{ <{cfg.espace}{ref}> lab:fondeSur ?r .
                ?r prov:wasDerivedFrom/prov:wasGeneratedBy/prov:qualifiedAssociation/prov:hadPlan/lab:carteRecherche ?cr .
                ?cr lab:exploratoire true }}""").askAnswer)
    statut = graphe.STATUTS.get(d.get("statut_propose", ""))
    importante = (float(d.get("poids", 0)) >= 4 or d.get("effet") in IMPORTANTS_EFFETS
                  or statut in (graphe.LAB.RefuteeIci, graphe.LAB.Suspendue) or cumul > 3 or exploratoire)
    d["importance"] = "importante" if importante else "courante"


def graphe_prefixes() -> str:
    return ("PREFIX lab: <https://labo.invalid/ns#> PREFIX prov: <http://www.w3.org/ns/prov#> ")


def proposer(cfg: Config, d: dict) -> tuple[bool, list[tuple[str, str]]]:
    chemin = _chemin(cfg)
    ancien = _lire(chemin)
    if f'id = "{d["id"]}"' in ancien:
        raise ErreurContenu(f"décision {d['id']} déjà enregistrée")
    g0, _ = graphe.construire(cfg, decisions_texte=ancien)
    anciennes = tomllib.loads(ancien).get("decision", []) if ancien.strip() else []
    d.setdefault("etat", "relue" if d.get("relecture_verdict") else "proposee")
    calculer_importance(cfg, d, anciennes, g0)
    nouveau = (ancien or ENTETE) + bloc_decision(d)
    g1, nouvelles = _verifier(cfg, ancien, nouveau, {d["id"]})
    if nouvelles:
        return False, nouvelles
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(nouveau, encoding="utf-8")
    graphe.ecrire(g1, cfg.sortie("graphe", "graphe.ttl"))
    return True, []


def modifier(cfg: Config, ident: str, champs: dict, deja_present: str | None = None):
    """Écrit ou remplace des champs d'une décision existante, refusé si cela crée une violation."""
    chemin = _chemin(cfg)
    ancien = _lire(chemin)
    morceaux = ancien.split("\n" + MARQUE)
    trouve = [i for i, m in enumerate(morceaux) if i > 0 and f"\nid = {json.dumps(ident)}\n" in m + "\n"]
    if not trouve:
        raise ErreurContenu(f"décision {ident} inconnue")
    i = trouve[0]
    if deja_present and f"\n{deja_present} = " in morceaux[i]:
        raise ErreurContenu(f"décision {ident} : {deja_present} déjà écrit")
    bloc = morceaux[i].rstrip("\n") + "\n"
    for k, v in champs.items():
        ligne = f"{k} = {toml_valeur(v)}"
        if f"\n{k} = " in bloc:
            bloc = re.sub(rf"(?m)^{re.escape(k)} = .*$", lambda _: ligne, bloc, count=1)
        else:
            bloc += ligne + "\n"
    morceaux[i] = bloc
    nouveau = ("\n" + MARQUE).join(morceaux)
    tomllib.loads(nouveau)
    g1, nouvelles = _verifier(cfg, ancien, nouveau, {ident})
    if nouvelles:
        return False, nouvelles
    chemin.write_text(nouveau, encoding="utf-8")
    graphe.ecrire(g1, cfg.sortie("graphe", "graphe.ttl"))
    return True, []


def noter(cfg: Config, ident: str, issue: str, realisee: bool, changement: bool | None,
          statut_obtenu: str | None, heures_mesurees: float | None, heures_agent_mesurees: float | None):
    ch = {"issue": issue, "realisee": realisee, "date_notation": maintenant(), "etat": "notee"}
    for cle, val in (("changement_realise", changement), ("statut_obtenu", statut_obtenu),
                     ("heures_mesurees", heures_mesurees), ("heures_agent_mesurees", heures_agent_mesurees)):
        if val is not None:
            ch[cle] = val
    return modifier(cfg, ident, ch, deja_present="issue")


def executer(cfg: Config, ident: str):
    return modifier(cfg, ident, {"etat": "executee", "date_execution": maintenant()}, deja_present="date_execution")


def renverser(cfg: Config, ident: str, par: str):
    return modifier(cfg, ident, {"renversee_par": par})


def _mediane(xs: list[float]) -> float | None:
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def _brier(paires: list[tuple[float, bool]]) -> tuple[float | None, float | None]:
    """(score de Brier, score de compétence 1 − Brier/Brier du taux de base)."""
    if not paires:
        return None, None
    b = sum((p - (1.0 if o else 0.0)) ** 2 for p, o in paires) / len(paires)
    taux = sum(1.0 for _, o in paires if o) / len(paires)
    b0 = taux * (1 - taux)
    return b, (1 - b / b0) if b0 > 0 else None


def bilan(cfg: Config) -> dict:
    g, _ = graphe.construire(cfg)
    L = graphe.LAB
    decs = sorted(set(g.subjects(graphe.RDF.type, L.Decision)))
    issue, chg, ratios, diffs, importantes, obtenus = [], [], [], [], 0, []
    for dn in decs:
        if str(g.value(dn, L.importance)) == "importante":
            importantes += 1
        p, r = g.value(dn, L.predictionProba), g.value(dn, L.realisee)
        if p is not None and r is not None:
            issue.append((float(p), bool(r)))
        p, r = g.value(dn, L.predictionChangement), g.value(dn, L.changementRealise)
        if p is not None and r is not None:
            chg.append((float(p), bool(r)))
        so = g.value(dn, L.statutObtenu)
        if so is not None:
            obtenus.append(so == L.NonConcluante)
        est = sum(float(g.value(dn, x) or 0) for x in (L.heuresAgent, L.heuresCalcul))
        mes = [g.value(dn, x) for x in (L.heuresAgentMesurees, L.heuresMesurees)]
        if est > 0 and any(m is not None for m in mes):
            m = sum(float(x or 0) for x in mes)
            ratios.append(m / est)
            diffs.append(m - est)
    n = len(decs)
    # verdicts conclusifs renversés : un verdict d'un autre statut est posé plus tard sur la même hypothèse
    par_h: dict = {}
    for v in g.subjects(graphe.RDF.type, L.Verdict):
        par_h.setdefault(g.value(v, L.portesur), []).append((str(g.value(v, graphe.DCTERMS.created) or ""), str(v),
                                                              g.value(v, L.statut)))
    concl = renv = 0
    for vs in par_h.values():
        vs.sort()
        for i, (_, _, st) in enumerate(vs):
            if st in (L.Soutenue, L.RefuteeIci):
                concl += 1
                renv += any(s2 != st for _, _, s2 in vs[i + 1:])
    brier, comp = _brier(issue)
    brier_c, comp_c = _brier(chg)
    return {
        "decisions": n, "notees": len(issue), "brier": brier, "competence": comp,
        "brier_changement": brier_c, "competence_changement": comp_c,
        "importantes": importantes, "courantes": n - importantes,
        "part_importantes": importantes / n if n else None,
        "part_non_concluantes": sum(obtenus) / len(obtenus) if obtenus else None, "avec_statut_obtenu": len(obtenus),
        "decisions_renversees": sum(1 for dn in decs if g.value(dn, L.renverseePar) is not None),
        "verdicts_conclusifs": concl, "verdicts_renverses": renv,
        "cout_ratio_median": _mediane(ratios), "cout_ecart_median_h": _mediane(diffs), "avec_cout_mesure": len(ratios),
    }


def afficher_bilan(b: dict) -> None:
    def f(x, fmt="{:.3f}"):
        return "—" if x is None else fmt.format(x)

    def taux(a, n):
        return f"{a}/{n}" + (f" ({a / n:.0%})" if n else "")
    print(f"décisions : {b['decisions']} (notées : {b['notees']})")
    print(f"score de Brier (issue) : {f(b['brier'])} ; compétence relative au taux de base : {f(b['competence'])}")
    print(f"score de Brier (p_changement) : {f(b['brier_changement'])} ; compétence : {f(b['competence_changement'])}")
    print(f"courantes : {b['courantes']} ; importantes : {b['importantes']} (part importante : "
          f"{f(b['part_importantes'], '{:.0%}')})")
    print(f"part d'issues non concluantes : {f(b['part_non_concluantes'], '{:.0%}')} "
          f"({b['avec_statut_obtenu']} avec statut obtenu)")
    print(f"décisions renversées : {taux(b['decisions_renversees'], b['decisions'])} ; "
          f"verdicts conclusifs renversés : {taux(b['verdicts_renverses'], b['verdicts_conclusifs'])}")
    print(f"coût mesuré/estimé, médiane : {f(b['cout_ratio_median'], '{:.2f}')} ; écart signé médian : "
          f"{f(b['cout_ecart_median_h'], '{:+.2f}')} h ({b['avec_cout_mesure']} décision(s))")


def _bool(x: str) -> bool:
    if x.lower() in ("true", "vrai", "oui", "1"):
        return True
    if x.lower() in ("false", "faux", "non", "0"):
        return False
    raise argparse.ArgumentTypeError("true ou false")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="decision", description="Enregistrer, noter et bilanter les décisions.")
    p.add_argument("--config", default="config.toml")
    sp = p.add_subparsers(dest="cmd", required=True)
    a1 = sp.add_parser("proposer")
    a1.add_argument("fichier")
    a2 = sp.add_parser("noter")
    a2.add_argument("id")
    a2.add_argument("--issue", required=True)
    a2.add_argument("--realisee", required=True, type=_bool)
    a2.add_argument("--changement-realise", type=_bool, help="l'issue a-t-elle changé une décision suivante")
    a2.add_argument("--statut-obtenu")
    a2.add_argument("--heures-mesurees", type=float, help="heures de calcul mesurées")
    a2.add_argument("--heures-agent-mesurees", type=float)
    a3 = sp.add_parser("executer")
    a3.add_argument("id")
    a4 = sp.add_parser("renverser")
    a4.add_argument("id")
    a4.add_argument("--par", required=True)
    sp.add_parser("bilan")
    a = p.parse_args(argv)
    try:
        cfg = Config(Path(a.config))
        if a.cmd == "bilan":
            afficher_bilan(bilan(cfg))
            return 0
        if a.cmd == "noter":
            ok, nouvelles = noter(cfg, a.id, a.issue, a.realisee, a.changement_realise, a.statut_obtenu,
                                  a.heures_mesurees, a.heures_agent_mesurees)
            ident = a.id
        elif a.cmd == "executer":
            ok, nouvelles = executer(cfg, a.id)
            ident = a.id
        elif a.cmd == "renverser":
            ok, nouvelles = renverser(cfg, a.id, a.par)
            ident = a.id
        else:
            brut = tomllib.loads(Path(a.fichier).read_text(encoding="utf-8"))
            d = brut.get("decision", brut)
            if isinstance(d, list):
                d = d[0]
            d = dict(d)
            if not d.get("id"):
                n = _lire(_chemin(cfg)).count(MARQUE) + 1
                d = {"id": f"D-{n}", **d}
            d.setdefault("date", maintenant())
            ident = d["id"]
            ok, nouvelles = proposer(cfg, d)
    except (ErreurContenu, KeyError, OSError, tomllib.TOMLDecodeError) as e:
        print("erreur :", e, file=sys.stderr)
        return 1
    if ok:
        print(f"décision {ident} { {'noter': 'notée', 'executer': 'exécutée', 'renverser': 'renversée'}.get(a.cmd, 'acceptée') } ; graphe reconstruit")
        return 0
    print(f"décision {ident} REFUSÉE : fichier inchangé")
    for noeud, msg in nouvelles:
        print(f"  {noeud} : {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
