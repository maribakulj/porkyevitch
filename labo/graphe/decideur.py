#!/usr/bin/env python3
"""Écrit la file des candidats : ce que la boucle pourrait faire ensuite. Il ne décide rien, il propose.

Usage :
    python3 decideur.py [--config config.toml] [--graphe graphe.ttl] [--sortie DOSSIER]

Lit le graphe (reconstruit en mémoire depuis la configuration, ou un Turtle donné par --graphe) et écrit
`file-candidats.json` et `file-candidats.md` dans le dossier de sortie (par défaut [sortie] candidats, sinon
« candidats » à côté du graphe). Sources de la politique de décision (§ 2) couvertes :

1. le cycle en cours : carte de recherche sans relecture (un RELECTURE-CONCEPTION.md à côté de la carte ; les cartes
   dont une course existe déjà ne sont pas listées), course réussie sans verdict, verdict « soutenue » ou « réfutée »
   porté par une seule course (pas de recalcul) ;
2. les réouvertures : dernier verdict non concluant, invalide ou suspendu de chaque hypothèse, avec sa condition
   `reouvrirSi`, à afficher ; une lignée (prov:wasRevisionOf) qui compte deux verdicts non concluants sur les mêmes
   données (lab:donnees) voit ses nouvelles cartes et réouvertures marquées « écartée (règle d'arrêt) » ;
3. le portefeuille : idées gardées par les deux notateurs, sans hypothèse, rangées par S réconcilié (moyenne des deux
   notateurs) ; si les notations ne sont pas dans le graphe, le dit.
Pour chaque prémisse non vérifiée d'une hypothèse ouverte, un candidat « vérifier la prémisse ». Il compte les
chantiers actifs (limite 3) et écrit `dossier-relecture.json` : les cinq premiers candidats non écartés et
l'empreinte SHA-256 de `file-candidats.json`, à recopier dans la décision (champ dossier_empreinte).
Les sources 4 (instruments) et 5 (suites déclarées) ne sont pas lues ici.
Code de sortie : 0, 2 usage.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graphe  # noqa: E402
from graphe import LAB, Config, ErreurContenu  # noqa: E402

PREFIXES = """
PREFIX lab: <https://labo.invalid/ns#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX dcterms: <http://purl.org/dc/terms/>
"""
MAX_PORTEFEUILLE_MD = 20
K_DOSSIER = 5          # taille du dossier de relecture : les cinq premiers candidats
MAX_CHANTIERS = 3


def _id(g, noeud) -> str:
    v = g.value(noeud, graphe.DCTERMS.identifier)
    return str(v) if v is not None else str(noeud).rsplit("/", 1)[-1]


def dossiers_cartes(cfg: Config) -> dict[str, Path]:
    """nom de carte -> dossier qui la porte."""
    sortie = {}
    for motif in cfg.brut.get("cartes", {}).get("motifs", []):
        for f in sorted(glob.glob(str(cfg.racine / motif))):
            sortie[Path(f).parent.name] = Path(f).parent
    return sortie


def arretees(g) -> dict:
    """Hypothèse -> motif, pour toute lignée ayant au moins deux verdicts « non concluante » sur les mêmes données."""
    sortie = {}
    for row in g.query(PREFIXES + """
        SELECT ?h ?d (COUNT(DISTINCT ?v) AS ?n) WHERE {
          ?h a lab:Hypothese .
          ?h (prov:wasRevisionOf|^prov:wasRevisionOf)* ?h2 .
          ?v lab:portesur ?h2 ; lab:statut lab:NonConcluante ; lab:donnees ?d .
        } GROUP BY ?h ?d HAVING (COUNT(DISTINCT ?v) >= 2)"""):
        sortie[row.h] = (f"écartée (règle d'arrêt) : {int(row.n)} verdicts non concluants sur la même lignée et les "
                         f"mêmes données ({_id(g, row.d)})")
    return sortie


def ouvertes(g) -> list:
    """Hypothèses sans verdict soutenu ni réfuté."""
    return sorted((h for h in g.subjects(graphe.RDF.type, LAB.Hypothese)
                   if not any(g.value(v, LAB.statut) in (LAB.Soutenue, LAB.RefuteeIci)
                              for v in g.subjects(LAB.portesur, h))), key=str)


def premisses(g) -> list[dict]:
    """Un candidat « vérifier la prémisse » pour chaque prémisse non vérifiée d'une hypothèse ouverte."""
    cands = []
    for h in ouvertes(g):
        for cr in g.subjects(LAB.teste, h):
            for p in g.objects(cr, LAB.premisse):
                if g.value(p, LAB.etatPremisse) == LAB.non_verifiee:
                    cands.append({"source": 1, "type": "verifier-premisse", "cible": _id(g, p),
                                  "hypothese": _id(g, h),
                                  "texte": f"Vérifier la prémisse {_id(g, p)} de {_id(g, h)} : "
                                           f"{g.value(p, graphe.DCTERMS.description)}"})
    return cands


def chantiers(g) -> dict:
    """Chantiers actifs : au moins une hypothèse ouverte, et aucune décision « ferme_chantier » écrite dessus."""
    ouv = set(ouvertes(g))
    actifs = []
    for c in sorted(g.subjects(graphe.RDF.type, graphe.PROV.Collection), key=str):
        membres = set(g.objects(c, graphe.PROV.hadMember))
        ferme = any(str(g.value(m, LAB.effet)) == "ferme_chantier" for m in membres
                    if (m, graphe.RDF.type, LAB.Decision) in g)
        if not ferme and membres & ouv:
            actifs.append(_id(g, c))
    return {"actifs": actifs, "n": len(actifs), "limite": MAX_CHANTIERS, "depasse": len(actifs) > MAX_CHANTIERS}


def cycle(g, cfg: Config) -> list[dict]:
    cands = []
    stop = arretees(g)
    dossiers = dossiers_cartes(cfg)
    # carte sans relecture, sans course encore
    for row in g.query(PREFIXES + """
        SELECT ?cr ?nom WHERE { ?cr a lab:CarteRecherche ; dcterms:identifier ?nom .
          FILTER NOT EXISTS { ?cc lab:carteRecherche ?cr . ?co prov:qualifiedAssociation/prov:hadPlan ?cc }
        } ORDER BY ?nom"""):
        nom = str(row.nom)
        d = dossiers.get(nom)
        if d is not None and not (d / "RELECTURE-CONCEPTION.md").is_file():
            c = {"source": 1, "type": "relecture-conception", "cible": nom,
                 "texte": f"Carte « {nom} » : pas de RELECTURE-CONCEPTION.md à côté de la carte."}
            for h in g.objects(row.cr, LAB.teste):
                if h in stop:
                    c["ecartee"] = stop[h]
            cands.append(c)
    # course réussie sans verdict
    for row in g.query(PREFIXES + """
        SELECT ?co ?id WHERE { ?co a lab:Course ; lab:etat lab:REUSSIE ; dcterms:identifier ?id .
          FILTER NOT EXISTS { ?v a lab:Verdict ; lab:fondeSur ?co }
          FILTER NOT EXISTS { ?v a lab:Verdict ; lab:fondeSur ?r . ?r prov:wasDerivedFrom/prov:wasGeneratedBy ?co }
        } ORDER BY ?id"""):
        cands.append({"source": 1, "type": "verdict", "cible": str(row.id),
                      "texte": f"Course {row.id} réussie, sans verdict."})
    # verdict soutenue / réfutée porté par une seule course
    for row in g.query(PREFIXES + """
        SELECT ?v ?h ?st (COUNT(DISTINCT ?co) AS ?n) WHERE {
          ?v lab:statut ?st ; lab:portesur ?h . FILTER (?st IN (lab:Soutenue, lab:RefuteeIci))
          OPTIONAL { ?cr lab:teste ?h . ?cc lab:carteRecherche ?cr . ?co prov:qualifiedAssociation/prov:hadPlan ?cc }
        } GROUP BY ?v ?h ?st ORDER BY ?v"""):
        if int(row.n) < 2:
            mot = "soutenue" if row.st == LAB.Soutenue else "réfutée"
            cands.append({"source": 1, "type": "recalcul", "cible": _id(g, row.h),
                          "texte": f"Verdict {_id(g, row.v)} « {mot} » sur {_id(g, row.h)} : une seule course, "
                                   "pas de recalcul."})
    return cands


def reouvertures(g) -> list[dict]:
    stop = arretees(g)
    """Le dernier verdict de chaque hypothèse, s'il n'a pas conclu, avec sa condition de réouverture."""
    dernier: dict = {}
    for v in g.subjects(graphe.RDF.type, LAB.Verdict):
        h, d = g.value(v, LAB.portesur), str(g.value(v, graphe.DCTERMS.created) or "")
        if h is not None and (h not in dernier or (d, str(v)) > dernier[h][0]):
            dernier[h] = ((d, str(v)), v)
    cands = []
    for h, (_, v) in sorted(dernier.items(), key=lambda kv: str(kv[0])):
        st = g.value(v, LAB.statut)
        if st not in (LAB.NonConcluante, LAB.Suspendue, LAB.TestInvalide):
            continue
        cond = g.value(v, LAB.reouvrirSi) or g.value(h, LAB.reouvrirSi)
        mot = str(g.value(st, graphe.SKOS.prefLabel) or st)
        cands.append({"source": 2, "type": "reouverture", "cible": _id(g, h), "verdict": _id(g, v), "statut": mot,
                      **({"ecartee": stop[h]} if h in stop else {}),
                      "reouvrir_si": str(cond) if cond else None,
                      "texte": f"{_id(g, h)} : dernier verdict {_id(g, v)} « {mot} »."
                               + (f" Rouvrir si : {cond}" if cond else " Aucune condition de réouverture écrite.")})
    return cands


def portefeuille(g) -> tuple[list[dict], str | None]:
    """Idées gardées par les deux notateurs, sans hypothèse, par S réconcilié décroissant."""
    S = LAB["score_S"]
    notations = set(g.subjects(graphe.RDF.type, graphe.PROV.Entity)) & set(g.subjects(LAB.notePar, None))
    if not notations:
        return [], "les notations du tri ne sont pas dans le graphe : source 3 non évaluée."
    sortie, sans_s = [], 0
    for idee in sorted(set(g.subjects(graphe.RDF.type, LAB.Idee)), key=str):
        if (None, graphe.PROV.wasDerivedFrom, idee) in g:
            continue
        ns = list(g.objects(idee, LAB.notation))
        if len(ns) < 2 or any(g.value(n, LAB.elimine) is not None and bool(g.value(n, LAB.elimine)) for n in ns):
            continue
        scores = []
        for n in ns:
            try:
                scores.append(float(g.value(n, S)))
            except (TypeError, ValueError):
                pass
        if len(scores) < len(ns):
            sans_s += 1
            continue
        sortie.append({"source": 3, "type": "portefeuille", "cible": _id(g, idee),
                       "s_reconcilie": sum(scores) / len(scores), "notes": scores,
                       "texte": str(g.value(idee, graphe.DCTERMS.description) or "")})
    sortie.sort(key=lambda c: (-c["s_reconcilie"], c["cible"]))
    note = None
    if not sortie:
        note = "aucune idée gardée par les deux notateurs avec un S numérique et sans hypothèse."
    elif sans_s:
        note = f"{sans_s} idée(s) gardée(s) sans S numérique chez les deux notateurs, non rangées."
    return sortie, note


def file_candidats(g, cfg: Config) -> dict:
    port, note = portefeuille(g)
    return {"cycle": cycle(g, cfg) + premisses(g), "chantiers": chantiers(g), "reouvertures": reouvertures(g), "portefeuille": port,
            "note_portefeuille": note,
            "sources_non_lues": ["4 (instruments)", "5 (suites déclarées)"]}


def en_markdown(f: dict) -> str:
    L = ["# File des candidats", "",
         "Proposée par `decideur.py` ; il ne décide rien. Le choix, la prédiction et la relecture passent par "
         "`decision.py`.", "", "## 1. Cycle en cours", ""]
    L += [f"- **{c['type']}** — {c['texte']}" + (f" **[{c['ecartee']}]**" if c.get("ecartee") else "")
          for c in f["cycle"]] or ["Rien de prêt."]
    ch = f["chantiers"]
    L += ["", f"Chantiers actifs : {ch['n']} ({', '.join(ch['actifs']) or '—'}), limite {ch['limite']}."
          + (" **LIMITE DÉPASSÉE.**" if ch["depasse"] else "")]
    L += ["", "## 2. Réouvertures", ""]
    if f["reouvertures"]:
        L += ["| hypothèse | dernier verdict | statut | rouvrir si | |", "|---|---|---|---|---|"]
        L += [f"| {c['cible']} | {c['verdict']} | {c['statut']} | {(c['reouvrir_si'] or '—').replace('|', '/')} | "
              f"{c.get('ecartee', '')} |"
              for c in f["reouvertures"]]
    else:
        L.append("Aucune.")
    L += ["", "## 3. Portefeuille", ""]
    if f["note_portefeuille"]:
        L += [f"_{f['note_portefeuille']}_", ""]
    if f["portefeuille"]:
        L += ["| rang | idée | S réconcilié | description |", "|---|---|---|---|"]
        for i, c in enumerate(f["portefeuille"][:MAX_PORTEFEUILLE_MD], 1):
            L.append(f"| {i} | {c['cible']} | {c['s_reconcilie']:.2f} | {c['texte'][:90].replace('|', '/')} |")
        if len(f["portefeuille"]) > MAX_PORTEFEUILLE_MD:
            L.append(f"\n{len(f['portefeuille'])} idées au total ; les {MAX_PORTEFEUILLE_MD} premières ici, "
                     "la liste complète dans le JSON.")
    L += ["", "Sources non lues : " + ", ".join(f["sources_non_lues"]) + ".", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="decideur", description="Écrire la file des candidats.")
    p.add_argument("--config", default="config.toml")
    p.add_argument("--graphe", help="lire ce Turtle au lieu de reconstruire le graphe")
    p.add_argument("--sortie", help="dossier de sortie")
    a = p.parse_args(argv)
    try:
        cfg = Config(Path(a.config))
        if a.graphe:
            g = graphe.Graph().parse(a.graphe, format="turtle")
        else:
            g, _ = graphe.construire(cfg)
        f = file_candidats(g, cfg)
    except (ErreurContenu, OSError) as e:
        print("erreur :", e, file=sys.stderr)
        return 2
    dossier = Path(a.sortie) if a.sortie else cfg.sortie("candidats", str(cfg.sortie("graphe", "graphe.ttl").parent / "candidats"))
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "file-candidats.json").write_text(json.dumps(f, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dossier / "file-candidats.md").write_text(en_markdown(f), encoding="utf-8")
    # dossier de relecture : les K premiers candidats non écartés, avec l'empreinte du fichier de candidats
    empreinte = hashlib.sha256((dossier / "file-candidats.json").read_bytes()).hexdigest()
    premiers = [c for c in f["cycle"] + f["reouvertures"] + f["portefeuille"] if not c.get("ecartee")][:K_DOSSIER]
    (dossier / "dossier-relecture.json").write_text(json.dumps(
        {"empreinte_fichier_candidats": empreinte, "candidats": premiers}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"file écrite : {len(f['cycle'])} étape(s) du cycle, {len(f['reouvertures'])} réouverture(s), "
          f"{len(f['portefeuille'])} idée(s) du portefeuille -> {dossier}")
    if f["chantiers"]["depasse"]:
        print(f"ATTENTION : {f['chantiers']['n']} chantiers actifs, limite {MAX_CHANTIERS}")
    if f["note_portefeuille"]:
        print("portefeuille :", f["note_portefeuille"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
