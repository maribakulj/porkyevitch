#!/usr/bin/env python3
"""Le graphe de recherche : construire, valider, rapporter. Outil facultatif (rdflib et pyshacl).

Usage :
    python3 graphe.py [--config config.toml] construire    # lit les sources déclarées, écrit le Turtle
    python3 graphe.py [--config config.toml] valider       # formes SHACL ; code 1 s'il y a une violation
    python3 graphe.py [--config config.toml] rapport H-ID  # rapport Markdown d'une hypothèse
    python3 graphe.py [--config config.toml] compter       # nombre de nœuds par classe

Le générateur écrit les FAITS (idées, notations, cartes, courses, artefacts hachés) à partir des sources que le
fichier de configuration du projet déclare. Les JUGEMENTS (hypothèses, verdicts, décisions) viennent de deux fichiers
TOML que les agents écrivent : les verdicts passent par `verdict.py`, qui refuse ce que les formes interdisent.
Le graphe ne contient que des métadonnées, des empreintes et des statuts : aucun fichier de données ni de résultats
n'est ouvert, et les valeurs chiffrées d'un résultat sont celles que l'auteur du verdict déclare.

Dépendances : rdflib et pyshacl (`pip install -r requirements.txt`). Le reste du plugin n'en a pas besoin.
Code de sortie : 0 conforme, 1 violation ou erreur de contenu, 2 usage ou dépendance absente.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

ICI = Path(__file__).resolve().parent

try:
    from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef
    from rdflib.namespace import DCTERMS, PROV, SKOS
except ImportError:  # outil facultatif : le message dit quoi installer
    if __name__ == "__main__":
        print("rdflib et pyshacl sont requis pour le graphe : pip install -r " + str(ICI / "requirements.txt"),
              file=sys.stderr)
        sys.exit(2)
    raise

LAB = Namespace("https://labo.invalid/ns#")
MLS = Namespace("http://www.w3.org/ns/mls#")
SPDX = Namespace("http://spdx.org/rdf/terms#")
CLASSES = ("Idee", "Hypothese", "Premisse", "CarteRecherche", "CarteCalcul", "Course", "Resultat", "Verdict", "Decision")

STATUTS = {  # tout ce qu'on accepte en entrée → le concept SKOS
    "non-testee": LAB.NonTestee, "non testée": LAB.NonTestee, "NonTestee": LAB.NonTestee,
    "test-invalide": LAB.TestInvalide, "test invalide": LAB.TestInvalide, "TestInvalide": LAB.TestInvalide,
    "non-concluante": LAB.NonConcluante, "non concluante": LAB.NonConcluante, "NonConcluante": LAB.NonConcluante,
    "refutee": LAB.RefuteeIci, "réfutée": LAB.RefuteeIci, "réfutée dans ces conditions": LAB.RefuteeIci,
    "RefuteeIci": LAB.RefuteeIci,
    "soutenue": LAB.Soutenue, "Soutenue": LAB.Soutenue,
    "suspendue": LAB.Suspendue, "Suspendue": LAB.Suspendue,
}
ETATS_COURSE = ("SOUMISE", "EN_FILE", "EN_COURS", "REUSSIE", "ECHOUEE", "ECHOUEE_ARTEFACTS", "ANNULEE", "REFUSEE",
                "ABANDONNEE", "INCONNUE")
PROPRIETES_IDEE = {"theme": LAB.theme, "cout": LAB.cout, "risque": LAB.risque, "priorite": LAB.priorite,
                   "orientation": LAB.orientation, "statut_declare": LAB.statutDeclare}
MARQUE_INTERPRETATION = "<!-- interpretation : ce qui suit est écrit à la main et conservé à la régénération -->"


class ErreurContenu(Exception):
    """Une source déclarée est absente ou mal formée : le message dit laquelle."""


# ---------------------------------------------------------------- configuration

class Config:
    def __init__(self, chemin: Path):
        chemin = Path(chemin).resolve()
        try:
            self.brut = tomllib.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as e:
            raise ErreurContenu(f"configuration illisible ({chemin}) : {e}") from e
        self.dossier = chemin.parent
        self.espace = self.brut.get("projet", {}).get("espace", "https://labo.invalid/g/")
        self.racine = self.chemin(self.brut.get("projet", {}).get("racine", "."))

    def chemin(self, rel: str) -> Path:
        return (self.dossier / rel).resolve()

    def sortie(self, cle: str, defaut: str) -> Path:
        return self.chemin(self.brut.get("sortie", {}).get(cle, defaut))


def slug(texte: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", texte).strip("-") or "x"


def sha256_fichier(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def date_git(chemin: Path) -> str | None:
    """Date du dernier commit qui touche le fichier ; rien si le fichier est modifié ou hors dépôt (pas de date
    inventée : une carte sans date est signalée par les formes)."""
    d, nom = str(chemin.parent), chemin.name
    try:
        sale = subprocess.run(["git", "-C", d, "status", "--porcelain", "--", nom], capture_output=True, text=True,
                              check=True).stdout.strip()
        if sale:
            return None
        iso = subprocess.run(["git", "-C", d, "log", "-1", "--format=%aI", "--", nom], capture_output=True,
                             text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    if not iso:
        return None
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def charger_puissance():
    """Le calcul de puissance du plugin (labo/puissance.py), importé par son chemin."""
    chemin = ICI.parent / "puissance.py"
    spec = importlib.util.spec_from_file_location("puissance_labo", chemin)
    if spec is None or spec.loader is None:
        raise ErreurContenu(f"labo/puissance.py introuvable ({chemin})")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # nécessaire aux dataclasses
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- construction

class Constructeur:
    def __init__(self, cfg: Config, verdicts_texte: str | None = None, decisions_texte: str | None = None):
        self.cfg = cfg
        self.verdicts_texte = verdicts_texte
        self.decisions_texte = decisions_texte
        self.ns = Namespace(cfg.espace)
        self.g = Graph()
        for p, n in (("", self.ns), ("lab", LAB), ("prov", PROV), ("dcterms", DCTERMS), ("mls", MLS), ("skos", SKOS),
                     ("spdx", SPDX)):
            self.g.bind(p, n)
        self.idees: set[str] = set()
        self.cartes: dict[str, URIRef] = {}       # nom de dossier -> carte de recherche
        self.calculs: dict[str, URIRef] = {}      # nom de dossier -> carte de calcul
        self.avertissements: list[str] = []
        self.bloc_etat: dict[str, str | None] = {}  # état de prémisse déclaré par chaque carte de recherche
        self.guichet_present = False

    def n(self, ident: str) -> URIRef:
        return URIRef(str(self.ns) + quote(ident, safe="-_.~"))

    def lire_csv(self, fichier: str, sep: str, encodage: str) -> list[dict]:
        chemin = self.cfg.chemin(fichier)
        if not chemin.is_file():
            raise ErreurContenu(f"source absente : {chemin}")
        with open(chemin, encoding=encodage, newline="") as f:
            return list(csv.DictReader(f, delimiter=sep))

    def empreinte(self, sujet: URIRef, hexa: str) -> None:
        noeud = self.n("sha256-" + hexa[:16] + "-" + hashlib.sha256((str(sujet) + hexa).encode()).hexdigest()[:8])
        self.g.add((sujet, SPDX.checksum, noeud))
        self.g.add((noeud, RDF.type, SPDX.Checksum))
        self.g.add((noeud, SPDX.algorithm, SPDX.checksumAlgorithm_sha256))
        self.g.add((noeud, SPDX.checksumValue, Literal(hexa)))

    def agent(self, nom: str) -> URIRef:
        a = self.n("agent-" + slug(nom))
        self.g.add((a, RDF.type, PROV.SoftwareAgent))
        return a

    # -- idées
    def idees_source(self) -> None:
        c = self.cfg.brut.get("idees")
        if not c:
            return
        col = c.get("colonnes", {})
        for lig in self.lire_csv(c["fichier"], c.get("separateur", ";"), c.get("encodage", "utf-8-sig")):
            ident = lig[col.get("identifiant", "id")].strip()
            if not ident:
                continue
            i = self.n(ident)
            self.idees.add(ident)
            self.g.add((i, RDF.type, LAB.Idee))
            self.g.add((i, DCTERMS.identifier, Literal(ident)))
            self.g.add((i, DCTERMS.description, Literal(lig[col["description"]].strip(), lang="fr")))
            source = lig.get(col.get("source", ""), "").strip()
            self.g.add((i, DCTERMS.source, Literal(source) if source else LAB.interne))
            for cle, prop in PROPRIETES_IDEE.items():
                if cle in col and lig.get(col[cle], "").strip():
                    self.g.add((i, prop, Literal(lig[col[cle]].strip())))
        # dépendances : seulement vers des idées connues ; le reste est ignoré, et dit
        if "dependances" in col:
            inconnues = 0
            for lig in self.lire_csv(c["fichier"], c.get("separateur", ";"), c.get("encodage", "utf-8-sig")):
                ident = lig[col.get("identifiant", "id")].strip()
                for dep in re.split(r"[,;\s]+", lig.get(col["dependances"], "")):
                    if not dep:
                        continue
                    if dep in self.idees:
                        self.g.add((self.n(ident), DCTERMS.requires, self.n(dep)))
                    else:
                        inconnues += 1
            if inconnues:
                self.avertissements.append(f"{inconnues} dépendance(s) vers une idée absente du tableau, ignorée(s)")

    # -- notations du tri
    def notations(self) -> None:
        for c in self.cfg.brut.get("notations", []):
            notateur = c["notateur"]
            agent = self.agent(notateur)
            for lig in self.lire_csv(c["fichier"], c.get("separateur", ";"), c.get("encodage", "utf-8-sig")):
                ident = lig[c.get("identifiant", "id")].strip()
                if ident not in self.idees:
                    self.avertissements.append(f"notation {notateur} : idée {ident} absente du tableau, ignorée")
                    continue
                nn = self.n(f"N-{slug(notateur)}-{ident}")
                self.g.add((self.n(ident), LAB.notation, nn))
                self.g.add((nn, RDF.type, PROV.Entity))
                self.g.add((nn, LAB.notePar, agent))
                el = lig.get(c.get("elimine", "elimine"), "").strip().lower()
                if el:
                    self.g.add((nn, LAB.elimine, Literal(el in ("oui", "true", "1", "o"))))
                for cle, prop in (("motif", LAB.motif), ("justification", DCTERMS.description)):
                    v = lig.get(c.get(cle, cle), "").strip()
                    if v:
                        self.g.add((nn, prop, Literal(v)))
                dbl = lig.get(c.get("doublon_de", "doublon_de"), "").strip()
                if dbl:
                    self.g.add((nn, LAB.doublonDe, self.n(dbl) if dbl in self.idees else Literal(dbl)))
                for s in c.get("scores", []):
                    v = lig.get(s, "").strip()
                    if v:
                        try:
                            lit = Literal(float(v.replace(",", ".")))
                        except ValueError:
                            lit = Literal(v)
                        self.g.add((nn, LAB["score_" + slug(s)], lit))

    # -- cartes de recherche
    def cartes_recherche(self) -> None:
        c = self.cfg.brut.get("cartes")
        if not c:
            return
        pw = charger_puissance()
        for motif in c.get("motifs", []):
            for f in sorted(glob.glob(str(self.cfg.racine / motif))):
                chemin = Path(f)
                nom = chemin.parent.name
                texte = chemin.read_text(encoding="utf-8")
                m = re.search(r"```toml recherche\n(.*?)```", texte, re.S)
                if not m:
                    self.avertissements.append(f"{nom} : pas de bloc « toml recherche », carte ignorée")
                    continue
                try:
                    bloc = tomllib.loads(m.group(1))
                except tomllib.TOMLDecodeError as e:
                    raise ErreurContenu(f"{chemin} : bloc « toml recherche » illisible : {e}") from e
                cr = self.n("CR-" + nom)
                self.cartes[nom] = cr
                self.g.add((cr, RDF.type, LAB.CarteRecherche))
                self.g.add((cr, DCTERMS.identifier, Literal(nom)))
                t = re.search(r"^#\s+(.+)$", texte, re.M)
                if t:
                    self.g.add((cr, DCTERMS.title, Literal(t.group(1).strip(), lang="fr")))
                if bloc.get("decision"):
                    self.g.add((cr, LAB.decisionRegle, Literal(bloc["decision"], lang="fr")))
                p = bloc.get("puissance", {})
                self.g.add((cr, LAB.exploratoire, Literal(bool(bloc.get("exploratoire", c.get("exploratoire", False))))))
                if "famille" in p:
                    self.g.add((cr, LAB.famille, Literal(int(p["famille"]))))
                if "effet_plausible" in p:
                    self.g.add((cr, LAB.effetPlausible, Literal(float(p["effet_plausible"]))))
                    se = p.get("se")
                    if se is None and "ic" in p:
                        se = pw.se_depuis_ic(float(p["ic"][0]), float(p["ic"][1]))
                    if se:
                        self.g.add((cr, LAB.erreurType, Literal(round(float(se), 6))))
                        pu = pw.puissance(float(p["effet_plausible"]), float(se), famille=int(p.get("famille", 1)))
                        self.g.add((cr, LAB.puissance, Literal(round(pu, 4))))
                self.empreinte(cr, sha256_fichier(chemin))
                d = date_git(chemin)
                if d:
                    self.g.add((cr, DCTERMS.created, Literal(d, datatype=XSD.dateTime)))
                else:
                    self.avertissements.append(f"{nom} : carte de recherche non commitée, sans date")
                self.bloc_etat[nom] = bloc.get("premisse")

    # -- cartes de calcul
    def cartes_calcul(self) -> None:
        c = self.cfg.brut.get("calculs")
        if not c:
            return
        for motif in c.get("motifs", []):
            for f in sorted(glob.glob(str(self.cfg.racine / motif))):
                chemin = Path(f)
                nom = chemin.parent.name
                try:
                    carte = tomllib.loads(chemin.read_text(encoding="utf-8"))
                except tomllib.TOMLDecodeError as e:
                    raise ErreurContenu(f"{chemin} illisible : {e}") from e
                cc = self.n("CC-" + nom)
                self.calculs[nom] = cc
                self.g.add((cc, RDF.type, LAB.CarteCalcul))
                self.g.add((cc, DCTERMS.identifier, Literal(carte.get("experience", nom))))
                self.empreinte(cc, sha256_fichier(chemin))
                d = date_git(chemin)
                if d:
                    self.g.add((cc, DCTERMS.created, Literal(d, datatype=XSD.dateTime)))
                ref = carte.get("carte_recherche")
                if ref:
                    cible = (chemin.parent / ref).resolve().parent.name
                    if cible in self.cartes:
                        self.g.add((cc, LAB.carteRecherche, self.cartes[cible]))

    # -- guichet
    def guichet(self) -> None:
        c = self.cfg.brut.get("guichet")
        if not c:
            return
        chemin = self.cfg.chemin(c["export"])
        if not chemin.is_file():
            self.avertissements.append(f"registre du guichet : export absent ({chemin.name}), emplacement prévu")
            return
        self.guichet_present = True
        try:
            courses = json.loads(chemin.read_text(encoding="utf-8")).get("courses", [])
        except json.JSONDecodeError as e:
            raise ErreurContenu(f"export du guichet illisible : {e}") from e
        guichet = self.agent("guichet")
        for r in courses:
            if r["etat"] not in ETATS_COURSE:
                raise ErreurContenu(f"course {r['id']} : état inconnu {r['etat']}")
            co = self.n(r["id"])
            self.g.add((co, RDF.type, LAB.Course))
            self.g.add((co, DCTERMS.identifier, Literal(r["id"])))
            self.g.add((co, LAB.etat, LAB[r["etat"]]))
            if r.get("cle"):
                self.g.add((co, LAB.cle, Literal(r["cle"])))
            if r.get("debut"):
                self.g.add((co, PROV.startedAtTime, Literal(r["debut"], datatype=XSD.dateTime)))
            if r.get("fin"):
                self.g.add((co, PROV.endedAtTime, Literal(r["fin"], datatype=XSD.dateTime)))
            self.g.add((co, PROV.wasAssociatedWith, guichet))
            plan = self.calculs.get(r.get("carte_calcul", ""))
            if plan is not None:
                assoc = self.n(r["id"] + "-association")
                self.g.add((co, PROV.qualifiedAssociation, assoc))
                self.g.add((assoc, RDF.type, PROV.Association))
                self.g.add((assoc, PROV.agent, guichet))
                self.g.add((assoc, PROV.hadPlan, plan))
            for a in r.get("artefacts", []):
                an = self.n(f"{r['id']}-{slug(a['nom'])}")
                self.g.add((an, RDF.type, PROV.Entity))
                self.g.add((an, DCTERMS.title, Literal(a["nom"])))
                self.g.add((an, PROV.wasGeneratedBy, co))
                self.empreinte(an, a["sha256"])
            for e in r.get("entrees", []):
                en = self.n(f"{r['id']}-entree-{slug(e['nom'])}")
                self.g.add((en, RDF.type, PROV.Entity))
                self.g.add((en, DCTERMS.title, Literal(e["nom"])))
                self.g.add((co, PROV.used, en))
                self.empreinte(en, e["sha256"])

    # -- jugements
    def jugements(self) -> None:
        c = self.cfg.brut.get("jugements")
        if not c:
            return
        h = self.cfg.chemin(c["hypotheses"])
        if h.is_file():
            self._hypotheses(tomllib.loads(h.read_text(encoding="utf-8")))
        if self.verdicts_texte is not None:
            texte = self.verdicts_texte
        else:
            v = self.cfg.chemin(c["verdicts"]) if c.get("verdicts") else None
            texte = v.read_text(encoding="utf-8") if v and v.is_file() else ""
        self._verdicts(tomllib.loads(texte) if texte.strip() else {})
        self._derives()
        if self.decisions_texte is not None:
            texte = self.decisions_texte
        else:
            dd = self.cfg.chemin(c["decisions"]) if c.get("decisions") else None
            texte = dd.read_text(encoding="utf-8") if dd and dd.is_file() else ""
        self._decisions(tomllib.loads(texte) if texte.strip() else {})

    def _hypotheses(self, d: dict) -> None:
        etats = self.bloc_etat
        for i in d.get("idee_interne", []):  # une idée née d'un travail du projet, qui n'est pas une ligne du tableau
            idn = self.n(i["id"])
            self.idees.add(i["id"])
            self.g.add((idn, RDF.type, LAB.Idee))
            self.g.add((idn, DCTERMS.identifier, Literal(i["id"])))
            self.g.add((idn, DCTERMS.description, Literal(i["description"], lang="fr")))
            self.g.add((idn, DCTERMS.source, LAB.interne))
            for proche in i.get("proche_de", []):
                self.g.add((idn, DCTERMS.relation, self.n(proche)))
        for ct in d.get("course_technique", []):    # course sans hypothèse (essai du guichet) : pas de verdict attendu
            self.g.add((self.n(ct["id"]), LAB.motifTechnique, Literal(ct["motif"], lang="fr")))
        for h in d.get("hypothese", []):
            hn = self.n(h["id"])
            self.g.add((hn, RDF.type, LAB.Hypothese))
            self.g.add((hn, DCTERMS.identifier, Literal(h["id"])))
            self.g.add((hn, DCTERMS.description, Literal(h["description"], lang="fr")))
            self.g.add((hn, LAB.effetMinimal, Literal(float(h["effet_minimal"]))))
            if h.get("idee"):
                if h["idee"] not in self.idees:
                    self.avertissements.append(f"{h['id']} : idée {h['idee']} absente du tableau")
                self.g.add((hn, PROV.wasDerivedFrom, self.n(h["idee"])))
            mesure = self.n("mesure-" + h["id"])
            self.g.add((mesure, RDF.type, MLS.EvaluationMeasure))
            self.g.add((mesure, DCTERMS.description, Literal(h["mesure"], lang="fr")))
            self.g.add((hn, MLS.specifiedBy, mesure))
            if h.get("auteur"):
                self.g.add((hn, PROV.wasAttributedTo, self.agent(h["auteur"])))
            for i_ in h.get("couvre", []):
                self.g.add((hn, LAB.couvre, self.n(i_)))
            if h.get("revision_de"):
                self.g.add((hn, PROV.wasRevisionOf, self.n(h["revision_de"])))
            self._chantier(h.get("chantier"), hn)
            if h.get("reouvrir_si"):
                self.g.add((hn, LAB.reouvrirSi, Literal(h["reouvrir_si"], lang="fr")))
            cr = self.cartes.get(h.get("carte", ""))
            if h.get("carte") and cr is None:
                raise ErreurContenu(f"{h['id']} : carte de recherche « {h['carte']} » introuvable")
            if cr is not None:
                self.g.add((cr, LAB.teste, hn))
            for p in h.get("premisse", []):
                pn = self.n(p["id"])
                self.g.add((pn, RDF.type, LAB.Premisse))
                self.g.add((pn, DCTERMS.description, Literal(p["description"], lang="fr")))
                etat = p.get("etat") or etats.get(h.get("carte", ""))
                if etat in ("verifiee", "non_verifiee", "sans_objet", "infirmee"):
                    self.g.add((pn, LAB.etatPremisse, LAB[etat]))
                if cr is not None:
                    self.g.add((cr, LAB.premisse, pn))

    def _chantier(self, cid: str | None, membre: URIRef) -> None:
        """Un chantier est une prov:Collection (C-n) dont hypothèses et décisions sont membres."""
        if cid:
            cn = self.n(cid)
            self.g.add((cn, RDF.type, PROV.Collection))
            self.g.add((cn, DCTERMS.identifier, Literal(cid)))
            self.g.add((cn, PROV.hadMember, membre))

    def _decisions(self, d: dict) -> None:
        """Décisions du fichier des décisions (écrit par decision.py) : options, choix, règle, prédictions, relecture, issue."""
        def dec(x):
            return Literal(Decimal(str(x)))

        def lit_date(x):
            return Literal(x, datatype=XSD.dateTime)

        for dc in d.get("decision", []):
            dn = self.n(dc["id"])
            self.g.add((dn, RDF.type, LAB.Decision))
            self.g.add((dn, DCTERMS.identifier, Literal(dc["id"])))
            if dc.get("description"):
                self.g.add((dn, DCTERMS.description, Literal(dc["description"], lang="fr")))
            for ref in dc.get("fonde_sur", []):
                self.g.add((dn, LAB.fondeSur, self.n(ref)))
            if dc.get("auteur"):
                self.g.add((dn, PROV.wasAttributedTo, self.agent(dc["auteur"])))
            if dc.get("date"):
                self.g.add((dn, PROV.generatedAtTime, lit_date(dc["date"])))
            self._chantier(dc.get("chantier"), dn)
            for i, o in enumerate(dc.get("options", []), 1):
                on = self.n(f"{dc['id']}-option-{i}")
                self.g.add((on, RDF.type, PROV.Entity))
                self.g.add((on, RDFS.label, Literal(o["libelle"])))
                if "valeur_v" in o:
                    self.g.add((on, LAB.valeurV, dec(o["valeur_v"])))
                self.g.add((dn, LAB.option, on))
                if dc.get("choix") == o["libelle"]:
                    self.g.add((dn, LAB.choix, on))
            if dc.get("choix") and not any(o["libelle"] == dc["choix"] for o in dc.get("options", [])):
                hors = self.n(f"{dc['id']}-choix")        # un choix hors des options : la forme R13 le refuse
                self.g.add((hors, RDF.type, PROV.Entity))
                self.g.add((hors, RDFS.label, Literal(dc["choix"])))
                self.g.add((dn, LAB.choix, hors))
            for cle, prop in (("regle", LAB.regle), ("issue", LAB.issue)):
                if dc.get(cle):
                    self.g.add((dn, prop, Literal(dc[cle], lang="fr")))
            for cle, prop in (("importance", LAB.importance), ("effet", LAB.effet), ("etat", LAB.etatDecision),
                              ("dossier_empreinte", LAB.empreinteCandidats)):
                if dc.get(cle):
                    self.g.add((dn, prop, Literal(dc[cle])))
            for cle, prop in (("poids", LAB.poids), ("heures_agent", LAB.heuresAgent),
                              ("heures_calcul", LAB.heuresCalcul), ("heures_cumulees_24h", LAB.heuresCumulees24h),
                              ("prediction_proba", LAB.predictionProba), ("p_changement", LAB.predictionChangement),
                              ("heures_mesurees", LAB.heuresMesurees),
                              ("heures_agent_mesurees", LAB.heuresAgentMesurees)):
                if cle in dc:
                    self.g.add((dn, prop, dec(dc[cle])))
            for cle, prop in (("prediction_issue", LAB.predictionIssue), ("statut_propose", LAB.statutPropose),
                              ("statut_obtenu", LAB.statutObtenu)):
                if dc.get(cle):
                    statut = STATUTS.get(dc[cle])
                    if statut is None:
                        raise ErreurContenu(f"décision {dc['id']} : statut inconnu « {dc[cle]} » ({cle})")
                    self.g.add((dn, prop, statut))
            for cle, prop in (("realisee", LAB.realisee), ("changement_realise", LAB.changementRealise)):
                if cle in dc:
                    self.g.add((dn, prop, Literal(bool(dc[cle]))))
            for cle, prop in (("date_notation", LAB.dateNotation), ("date_execution", LAB.dateExecution)):
                if dc.get(cle):
                    self.g.add((dn, prop, lit_date(dc[cle])))
            if dc.get("remplace"):
                self.g.add((dn, PROV.wasRevisionOf, self.n(dc["remplace"])))
            if dc.get("renversee_par"):
                self.g.add((dn, LAB.renverseePar, self.n(dc["renversee_par"])))
            if dc.get("relecture_verdict") or dc.get("relecture_date") or dc.get("relecture_auteur"):
                rn = self.n(f"{dc['id']}-relecture")
                self.g.add((rn, RDF.type, PROV.Entity))
                if dc.get("relecture_verdict"):
                    self.g.add((rn, LAB.verdictRelecture, Literal(dc["relecture_verdict"], lang="fr")))
                if dc.get("relecture_date"):
                    self.g.add((rn, DCTERMS.created, lit_date(dc["relecture_date"])))
                if dc.get("relecture_auteur"):
                    self.g.add((rn, PROV.wasAttributedTo, self.agent(dc["relecture_auteur"])))
                self.g.add((dn, LAB.relecture, rn))

    def _verdicts(self, d: dict) -> None:
        for v in d.get("verdict", []):
            statut = STATUTS.get(v["statut"])
            if statut is None:
                raise ErreurContenu(f"verdict {v['id']} : statut inconnu « {v['statut']} »")
            vn = self.n(v["id"])
            self.g.add((vn, RDF.type, LAB.Verdict))
            self.g.add((vn, LAB.portesur, self.n(v["hypothese"])))
            self.g.add((vn, LAB.statut, statut))
            if v.get("auteur"):
                self.g.add((vn, PROV.wasAttributedTo, self.agent(v["auteur"])))
            if v.get("date"):
                self.g.add((vn, DCTERMS.created, Literal(v["date"], datatype=XSD.dateTime)))
            for cond in v.get("conditions", []):
                cn = self.n("condition-" + slug(cond))
                self.g.add((cn, RDFS.label, Literal(cond, lang="fr")))
                self.g.add((vn, LAB.conditions, cn))
            for dn_ in v.get("donnees", []):
                jeu = self.n("donnees-" + slug(dn_))
                self.g.add((jeu, RDF.type, PROV.Entity))
                self.g.add((jeu, DCTERMS.identifier, Literal(dn_)))
                self.g.add((vn, LAB.donnees, jeu))
            if v.get("remplace"):
                self.g.add((vn, PROV.wasRevisionOf, self.n(v["remplace"])))
            if v.get("reouvrir_si"):
                self.g.add((vn, LAB.reouvrirSi, Literal(v["reouvrir_si"], lang="fr")))
            if v.get("motif_invalidite"):
                self.g.add((vn, LAB.motifInvalidite, Literal(v["motif_invalidite"], lang="fr")))
            if v.get("course") and v.get("artefact"):
                rn = self.n("Res-" + v["id"])
                self.g.add((rn, RDF.type, LAB.Resultat))
                self.g.add((rn, PROV.wasDerivedFrom, self.n(f"{v['course']}-{slug(v['artefact'])}")))
                self.g.add((rn, MLS.specifiedBy, self.n("mesure-" + v["hypothese"])))
                if "valeur" in v:
                    self.g.add((rn, MLS.hasValue, Literal(float(v["valeur"]))))
                if "ic_bas" in v:
                    self.g.add((rn, LAB.icBas, Literal(float(v["ic_bas"]))))
                if "ic_haut" in v:
                    self.g.add((rn, LAB.icHaut, Literal(float(v["ic_haut"]))))
                self.g.add((vn, LAB.fondeSur, rn))
            elif v.get("course"):
                self.g.add((vn, LAB.fondeSur, self.n(v["course"])))

    def _derives(self) -> None:
        """Les raccourcis « réfute dans ces conditions » et « soutient » se dérivent des verdicts, jamais à la main."""
        for v in list(self.g.subjects(RDF.type, LAB.Verdict)):
            statut = self.g.value(v, LAB.statut)
            prop = {LAB.RefuteeIci: LAB.refuteIci, LAB.Soutenue: LAB.soutient}.get(statut)
            h = self.g.value(v, LAB.portesur)
            if prop is None or h is None:
                continue
            for res in self.g.objects(v, LAB.fondeSur):
                if (res, RDF.type, LAB.Resultat) in self.g:
                    self.g.add((res, prop, h))

    def construire(self) -> Graph:
        self.idees_source()
        self.notations()
        self.cartes_recherche()
        self.cartes_calcul()
        self.guichet()
        self.jugements()
        return self.g


def construire(cfg: Config, verdicts_texte: str | None = None,
               decisions_texte: str | None = None) -> tuple[Graph, list[str]]:
    c = Constructeur(cfg, verdicts_texte, decisions_texte)
    g = c.construire()
    return g, c.avertissements


def ecrire(g: Graph, chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(chemin), format="turtle")


# ---------------------------------------------------------------- validation

def violations(g: Graph) -> list[tuple[str, str]]:
    """(nœud, message) de chaque violation des formes. Le vocabulaire sert d'ontologie, sans inférence."""
    from pyshacl import validate

    formes, vocab = Graph().parse(ICI / "formes.ttl"), Graph().parse(ICI / "vocab.ttl")
    _, graphe_rapport, _ = validate(g, shacl_graph=formes, ont_graph=vocab, inference="none", advanced=True)
    SH = Namespace("http://www.w3.org/ns/shacl#")
    sortie = []
    for r in graphe_rapport.subjects(RDF.type, SH.ValidationResult):
        noeud = graphe_rapport.value(r, SH.focusNode)
        msg = graphe_rapport.value(r, SH.resultMessage)
        if msg is None:
            msg = f"{graphe_rapport.value(r, SH.sourceConstraintComponent)} sur {graphe_rapport.value(r, SH.resultPath)}"
        sortie.append((str(noeud), str(msg)))
    return sorted(set(sortie))


# ---------------------------------------------------------------- comptage et rapport

def compter(g: Graph) -> dict[str, int]:
    n = {c: len(set(g.subjects(RDF.type, LAB[c]))) for c in CLASSES}
    n["(notations, prov:Entity)"] = len(set(o for _, o in g.subject_objects(LAB.notation)))
    n["(triplets)"] = len(g)
    return n


def _val(g, s, p, defaut="—"):
    v = g.value(s, p)
    if v is None:
        return defaut
    if isinstance(v, Literal) and v.datatype == XSD.dateTime:
        return v.toPython().astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return str(v)


def _etiquette(statut) -> str:
    """Le libellé français d'un statut, lu dans le vocabulaire."""
    v = Graph().parse(ICI / "vocab.ttl")
    return str(v.value(statut, SKOS.prefLabel))


def _hash(g, s):
    return _val(g, g.value(s, SPDX.checksum), SPDX.checksumValue)


def rapport(g: Graph, hid: str, cfg: Config) -> str:
    ns = Namespace(cfg.espace)
    h = URIRef(str(ns) + quote(hid, safe="-_.~"))
    if (h, RDF.type, LAB.Hypothese) not in g:
        raise ErreurContenu(f"hypothèse {hid} absente du graphe")
    L = [f"# {hid}", ""]
    desc = _val(g, h, DCTERMS.description)
    verdicts = sorted(g.subjects(LAB.portesur, h), key=lambda v: _val(g, v, DCTERMS.created, ""))
    courant = g.value(verdicts[-1], LAB.statut) if verdicts else None
    statut = _etiquette(courant) if courant else "non testée (aucun verdict)"
    L += [f"> {desc}", "", f"**Statut courant : {statut}**", ""]

    L += ["## 1. D'où vient l'idée", ""]
    idee = g.value(h, PROV.wasDerivedFrom)
    if idee is None:
        L += ["Aucune idée déclarée.", ""]
    else:
        L += [f"- Idée **{_val(g, idee, DCTERMS.identifier)}** : {_val(g, idee, DCTERMS.description)}",
              f"- Source : {_val(g, idee, DCTERMS.source).replace('https://labo.invalid/ns#', '')}",
              f"- Thème : {_val(g, idee, LAB.theme)} ; coût : {_val(g, idee, LAB.cout)} ; priorité : {_val(g, idee, LAB.priorite)}"]
        for nn in sorted(g.objects(idee, LAB.notation)):
            par = str(g.value(nn, LAB.notePar)).rsplit("/agent-", 1)[-1]
            L.append(f"- Tri, {par} : élimine = {_val(g, nn, LAB.elimine)} ; motif : {_val(g, nn, LAB.motif)}")
        L.append("")

    L += ["## 2. L'hypothèse", "",
          f"- Mesure : {_val(g, g.value(h, MLS.specifiedBy), DCTERMS.description)}",
          f"- Effet minimal d'intérêt : {_val(g, h, LAB.effetMinimal)}",
          f"- Auteur : {str(g.value(h, PROV.wasAttributedTo) or '—').rsplit('/agent-', 1)[-1]}", ""]

    cartes = sorted(g.subjects(LAB.teste, h))
    L += ["## 3. Prémisse et son test", ""]
    premisses = [p for cr in cartes for p in g.objects(cr, LAB.premisse)]
    if not premisses:
        L += ["Aucune prémisse déclarée.", ""]
    for p in premisses:
        etat = g.value(p, LAB.etatPremisse)
        L.append(f"- {_val(g, p, DCTERMS.description)} (état : {str(etat).rsplit('#', 1)[-1] if etat else 'non renseigné'})")
        for src in g.objects(p, PROV.wasDerivedFrom):
            L.append(f"  - vérifiée par : {src}")
    if premisses:
        L.append("")

    L += ["## 4. La carte de recherche, la puissance, la règle", ""]
    if not cartes:
        L += ["Aucune carte de recherche : l'hypothèse ne peut pas être testée.", ""]
    for cr in cartes:
        L += [f"- Carte **{_val(g, cr, DCTERMS.identifier)}** : {_val(g, cr, DCTERMS.title)}",
              f"  - empreinte : `{_hash(g, cr)}` ; datée : {_val(g, cr, DCTERMS.created, 'sans date (non commitée)')}",
              f"  - confirmatoire : {'non' if _val(g, cr, LAB.exploratoire) == 'true' else 'oui'} ; "
              f"famille : {_val(g, cr, LAB.famille)}",
              f"  - effet plausible : {_val(g, cr, LAB.effetPlausible)} ; erreur-type : {_val(g, cr, LAB.erreurType)} ; "
              f"puissance recalculée : {_val(g, cr, LAB.puissance)}",
              f"  - règle de décision : {_val(g, cr, LAB.decisionRegle)}"]
        for cc in sorted(g.subjects(LAB.carteRecherche, cr)):
            L.append(f"  - carte de calcul {_val(g, cc, DCTERMS.identifier)} : empreinte `{_hash(g, cc)}`")
    L.append("")

    L += ["## 5. Les courses et leurs empreintes", ""]
    courses = sorted({co for cr in cartes for cc in g.subjects(LAB.carteRecherche, cr)
                      for assoc in g.subjects(PROV.hadPlan, cc) for co in g.subjects(PROV.qualifiedAssociation, assoc)})
    if not courses:
        L += ["Aucune course enregistrée pour cette hypothèse.", ""]
    for co in courses:
        L += [f"- **{_val(g, co, DCTERMS.identifier)}** : {str(g.value(co, LAB.etat)).rsplit('#', 1)[-1]} ; "
              f"clé `{_val(g, co, LAB.cle)}` ; début {_val(g, co, PROV.startedAtTime)}"]
        for a in sorted(g.subjects(PROV.wasGeneratedBy, co)):
            L.append(f"  - artefact {_val(g, a, DCTERMS.title)} : `{_hash(g, a)}`")
    if courses:
        L.append("")

    L += ["## 6. Résultats, verdicts, statut", ""]
    if not verdicts:
        L += ["Aucun verdict.", ""]
    for v in verdicts:
        s = g.value(v, LAB.statut)
        L.append(f"- **{_etiquette(s)}**, {_val(g, v, DCTERMS.created, 'sans date')}, "
                 f"par {str(g.value(v, PROV.wasAttributedTo) or '—').rsplit('/agent-', 1)[-1]}")
        for res in g.objects(v, LAB.fondeSur):
            if (res, RDF.type, LAB.Resultat) in g:
                L.append(f"  - résultat : {_val(g, res, MLS.hasValue)} ; IC [{_val(g, res, LAB.icBas)} ; "
                         f"{_val(g, res, LAB.icHaut)}] ; tiré de {_val(g, res, PROV.wasDerivedFrom)}")
        conds = [_val(g, c, RDFS.label) for c in g.objects(v, LAB.conditions)]
        if conds:
            L.append("  - conditions : " + " ; ".join(sorted(conds)))
        if g.value(v, LAB.motifInvalidite):
            L.append(f"  - motif d'invalidité : {_val(g, v, LAB.motifInvalidite)}")
    L.append("")

    L += ["## 7. Ce qui permettrait de rouvrir", ""]
    cond = [str(x) for v in verdicts for x in g.objects(v, LAB.reouvrirSi)] + [str(x) for x in g.objects(h, LAB.reouvrirSi)]
    L += [f"- {c}" for c in cond] if cond else ["Rien d'écrit."]
    L.append("")

    L += ["## 8. Décision", ""]
    decs = sorted({d for v in verdicts for d in g.subjects(LAB.fondeSur, v) if (d, RDF.type, LAB.Decision) in g})
    L += [f"- {_val(g, d, DCTERMS.description)}" for d in decs] if decs else ["Aucune décision."]
    L += ["", "## 9. Interprétation", "", MARQUE_INTERPRETATION, ""]
    return "\n".join(L)


def ecrire_rapport(g: Graph, hid: str, cfg: Config) -> Path:
    texte = rapport(g, hid, cfg)
    chemin = cfg.sortie("rapports", "rapports") / f"{hid}.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.is_file():  # l'interprétation écrite à la main survit à la régénération
        ancien = chemin.read_text(encoding="utf-8")
        if MARQUE_INTERPRETATION in ancien:
            texte = texte.split(MARQUE_INTERPRETATION)[0] + MARQUE_INTERPRETATION + ancien.split(MARQUE_INTERPRETATION, 1)[1]
    chemin.write_text(texte, encoding="utf-8")
    return chemin


# ---------------------------------------------------------------- ligne de commande

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="graphe", description="Graphe de recherche : construire, valider, rapporter.")
    p.add_argument("--config", default="config.toml")
    sous = p.add_subparsers(dest="cmd", required=True)
    sous.add_parser("construire")
    sous.add_parser("valider")
    sous.add_parser("compter")
    r = sous.add_parser("rapport")
    r.add_argument("hypothese")
    a = p.parse_args(argv)
    try:
        cfg = Config(Path(a.config))
        if a.cmd == "construire":
            g, avert = construire(cfg)
            sortie = cfg.sortie("graphe", "graphe.ttl")
            ecrire(g, sortie)
            for m in avert:
                print("note :", m)
            print(f"{sortie} écrit : {len(g)} triplets")
            return 0
        if a.cmd in ("valider", "compter", "rapport"):
            sortie = cfg.sortie("graphe", "graphe.ttl")
            if not sortie.is_file():
                print(f"{sortie} absent : lance d'abord « construire ».", file=sys.stderr)
                return 2
            g = Graph().parse(sortie)
            if a.cmd == "compter":
                for k, v in compter(g).items():
                    print(f"{k:28} {v}")
                return 0
            if a.cmd == "rapport":
                print(ecrire_rapport(g, a.hypothese, cfg))
                return 0
            v = violations(g)
            if not v:
                print(f"conforme : {len(g)} triplets, aucune violation")
                return 0
            for noeud, msg in v:
                print(f"VIOLATION {noeud} : {msg}")
            return 1
    except ErreurContenu as e:
        print("erreur :", e, file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
