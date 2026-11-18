"""Décisions, notation, bilan et décideur, sur données synthétiques. Lancer : python3 -I labo/graphe/tests/test_decision.py"""

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI))
try:
    import decideur
    import decision
    import graphe
    import test_graphe as T
    import verdict
    import pyshacl  # noqa: F401
    DISPO = True
except ImportError:
    DISPO = False

H64 = "ab" * 32
IDEES = T.IDEES + "I3;Idée trois;article C;t;P1;\nI4;Idée quatre;article D;t;P1;\nI5;Idée cinq;article E;t;P1;\n"
NOT1 = "id;elimine;S\nI1;non;3\nI2;non;3\nI3;non;4\nI4;non;5\nI5;non;5\n"
NOT2 = "id;elimine;S\nI1;non;3\nI2;non;3\nI3;non;2\nI4;non;5\nI5;oui;\n"
CONFIG = T.CONFIG.replace('[[notations]]\nfichier = "sources/n1.csv"\nnotateur = "notateur-1"\nscores = ["G"]\n',
    '[[notations]]\nfichier = "sources/n1.csv"\nnotateur = "notateur-1"\nscores = ["S"]\n'
    '[[notations]]\nfichier = "sources/n2.csv"\nnotateur = "notateur-2"\nscores = ["S"]\n').replace(
    'verdicts = "jugements/verdicts.toml"', 'verdicts = "jugements/verdicts.toml"\ndecisions = "jugements/decisions.toml"')
HYP = T.HYPOTHESES.replace('carte = "a"', 'carte = "a"\nchantier = "C-1"').replace(
    'idee = "I2"', 'idee = "I2"\nrevision_de = "H-A"')
CARTE_PREMISSE = T.CARTE.replace('premisse = "verifiee"', 'premisse = "non_verifiee"')

OPTIONS = [{"libelle": "lancer", "valeur_v": 2.0}, {"libelle": "ne rien faire", "valeur_v": 0.0}]


def dec(**kw):
    d = {"id": "D-1", "description": "essai", "auteur": "orchestrateur", "fonde_sur": ["I1"], "options": OPTIONS,
         "choix": "lancer", "regle": "politique § 3", "prediction_issue": "non-concluante",
         "prediction_proba": 0.7, "p_changement": 0.4}
    d.update(kw)
    return {k: v for k, v in d.items() if v is not None}


RELECTURE = {"relecture_verdict": "Aucune objection.", "relecture_date": "2026-01-01T00:00:00Z",
             "relecture_auteur": "relecteur", "dossier_empreinte": H64}


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Base(unittest.TestCase):
    carte_a = T.CARTE

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        for rel, txt in {
            "graphe/config.toml": CONFIG, "graphe/sources/idees.csv": IDEES, "graphe/sources/n1.csv": NOT1,
            "graphe/sources/n2.csv": NOT2, "graphe/jugements/hypotheses.toml": HYP,
            "experiences/a/recherche.md": self.carte_a, "experiences/a/carte.toml": T.CARTE_CALCUL,
            "experiences/b/recherche.md": T.CARTE_FAIBLE,
        }.items():
            p = self.d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt, encoding="utf-8")
        T.git(self.d, "init", "-q")
        T.git(self.d, "add", "-A")
        T.git(self.d, "commit", "-q", "-m", "départ")
        self.cfg = graphe.Config(self.d / "graphe/config.toml")
        self.fichier = self.cfg.chemin("jugements/decisions.toml")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def proposer(self, **kw):
        d = dec(**kw)
        d.setdefault("date", "2026-01-01T10:00:00Z")
        return decision.proposer(self.cfg, d)

    def refuse(self, motif, **kw):
        avant = self.fichier.read_text() if self.fichier.is_file() else ""
        ok, nouvelles = self.proposer(**kw)
        self.assertFalse(ok)
        self.assertTrue(any(motif in m for _, m in nouvelles), nouvelles)
        self.assertEqual(self.fichier.read_text() if self.fichier.is_file() else "", avant)

    def valeur(self, ident, prop):
        g, _ = graphe.construire(self.cfg)
        return g.value(graphe.URIRef(self.cfg.espace + ident), prop)


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Decisions(Base):
    def test_decision_courante_acceptee(self):
        ok, _ = self.proposer()
        self.assertTrue(ok)
        self.assertEqual(str(self.valeur("D-1", graphe.LAB.importance)), "courante")
        self.assertEqual(str(self.valeur("D-1", graphe.LAB.etatDecision)), "proposee")

    def test_r10_fonde_sur_idee_resultat_ou_decision(self):
        self.assertTrue(self.proposer(fonde_sur=["I1"])[0])
        self.assertTrue(self.proposer(id="D-2", fonde_sur=["D-1"])[0])
        self.refuse("sans fondement", id="D-3", fonde_sur=[])
        self.refuse("sans fondement", id="D-4", fonde_sur=["H-A"])      # une hypothèse n'est pas un fondement

    def test_moins_de_deux_options(self):
        self.refuse("moins de deux options", options=OPTIONS[:1], choix="lancer")

    def test_ne_rien_faire_obligatoire(self):
        self.refuse("ne rien faire", options=[{"libelle": "a", "valeur_v": 1}, {"libelle": "b", "valeur_v": 2}],
                    choix="a")

    def test_choix_parmi_les_options(self):
        self.refuse("Choix qui n'est pas", choix="autre chose")

    def test_option_sans_valeur_v(self):
        self.refuse("valeur V", options=[{"libelle": "lancer"}, {"libelle": "ne rien faire", "valeur_v": 0}])

    def test_prediction_obligatoire(self):
        self.refuse("issue attendue", prediction_issue=None)
        self.refuse("probabilité", prediction_proba=1.5)
        self.refuse("p_changement", p_changement=None)

    def test_importance_calculee_jamais_choisie(self):
        ok, nouvelles = self.proposer(effet="ouvre_chantier", importance="courante")
        self.assertFalse(ok)                       # importante malgré le fichier, donc exige une relecture
        self.assertTrue(any("sans relecture" in m for _, m in nouvelles))
        ok, _ = self.proposer(effet="ouvre_chantier", importance="courante", **RELECTURE)
        self.assertTrue(ok)
        self.assertEqual(str(self.valeur("D-1", graphe.LAB.importance)), "importante")

    def test_conditions_d_importance(self):
        for i, kw in enumerate([{"poids": 4}, {"effet": "production"}, {"effet": "clot_piste"},
                                {"statut_propose": "suspendue"}, {"statut_propose": "refutee"},
                                {"heures_calcul": 3.5}]):
            self.refuse("importante", id=f"D-{i + 10}", **kw)
        self.assertTrue(self.proposer(id="D-20", poids=3, effet="suite", heures_calcul=3)[0])

    def test_cumul_24_h_sur_le_chantier(self):
        self.assertTrue(self.proposer(id="D-1", chantier="C-1", heures_calcul=2)[0])
        self.assertTrue(self.proposer(id="D-2", chantier="C-2", heures_calcul=2)[0])     # autre chantier
        self.refuse("importante", id="D-3", chantier="C-1", heures_calcul=2)             # 4 h sur 24 h
        self.assertTrue(self.proposer(id="D-4", chantier="C-1", heures_calcul=2, date="2026-01-03T10:00:00Z")[0])

    def test_relecture_par_un_autre(self):
        self.refuse("Relecteur identique", poids=5, **{**RELECTURE, "relecture_auteur": "orchestrateur"})
        ok, _ = self.proposer(poids=5, **RELECTURE)
        self.assertTrue(ok)

    def test_empreinte_du_dossier_exigee(self):
        r = dict(RELECTURE)
        del r["dossier_empreinte"]
        self.refuse("empreinte", poids=5, **r)

    def test_execution_apres_relecture(self):
        self.assertTrue(self.proposer(poids=5, **RELECTURE)[0])
        ok, _ = decision.executer(self.cfg, "D-1")
        self.assertTrue(ok)
        self.assertEqual(str(self.valeur("D-1", graphe.LAB.etatDecision)), "executee")
        # relecture datée après l'exécution : refusée par la forme
        texte = self.fichier.read_text().replace("2026-01-01T00:00:00Z", "2999-01-01T00:00:00Z")
        g, _ = graphe.construire(self.cfg, decisions_texte=texte)
        self.assertTrue(any("avant l'exécution" in m for _, m in graphe.violations(g)))

    def test_forme_importance_forcee_sur_graphe_ecrit_a_la_main(self):
        texte = decision.bloc_decision({**dec(), "date": "2026-01-01T10:00:00Z", "etat": "proposee",
                                        "importance": "courante", "poids": 5})
        g, _ = graphe.construire(self.cfg, decisions_texte=texte)
        self.assertTrue(any("remplit une condition d'importance" in m for _, m in graphe.violations(g)))

    def test_remplacement_et_etat(self):
        self.assertTrue(self.proposer()[0])
        self.assertTrue(self.proposer(id="D-2", remplace="D-1", etat="en_attente_humain")[0])
        g, _ = graphe.construire(self.cfg)
        U = graphe.URIRef
        self.assertIn((U(self.cfg.espace + "D-2"), graphe.PROV.wasRevisionOf, U(self.cfg.espace + "D-1")), g)
        self.refuse("proposee", id="D-3", etat="inconnu")

    # ---- noter et bilan
    def test_brier_a_la_main(self):
        # prédictions 0,8 réalisée ; 0,6 non ; 0,9 réalisée : Brier = (0,04 + 0,36 + 0,01) / 3
        for i, (p, r) in enumerate([(0.8, True), (0.6, False), (0.9, True)], 1):
            self.assertTrue(self.proposer(id=f"D-{i}", prediction_proba=p, heures_calcul=1, heures_agent=1)[0])
            ok, _ = decision.noter(self.cfg, f"D-{i}", "issue", r, i != 2, "non-concluante" if i == 1 else "soutenue",
                                   4.0 if i == 1 else 1.0, 0.0)
            self.assertTrue(ok)
        b = decision.bilan(self.cfg)
        self.assertEqual((b["decisions"], b["notees"]), (3, 3))
        self.assertAlmostEqual(b["brier"], 0.41 / 3, places=6)
        self.assertAlmostEqual(b["competence"], 1 - (0.41 / 3) / (2 / 9), places=6)     # taux de base 2/3
        self.assertAlmostEqual(b["part_non_concluantes"], 1 / 3)
        # p_changement 0,4 ; réalisé pour D-1 et D-3, pas D-2 : (0,36 + 0,16 + 0,36) / 3
        self.assertAlmostEqual(b["brier_changement"], 0.88 / 3, places=6)
        self.assertEqual(b["courantes"], 3)
        # coûts : estimé 2 h ; mesuré 4, 1, 1 -> ratios 2, 0,5, 0,5 -> médiane 0,5 ; écart médian −1 h
        self.assertAlmostEqual(b["cout_ratio_median"], 0.5)
        self.assertAlmostEqual(b["cout_ecart_median_h"], -1.0)

    def test_noter_deux_fois_refuse_et_decision_inconnue(self):
        self.assertTrue(self.proposer()[0])
        self.assertTrue(decision.noter(self.cfg, "D-1", "x", True, None, None, None, None)[0])
        with self.assertRaises(graphe.ErreurContenu):
            decision.noter(self.cfg, "D-1", "x", True, None, None, None, None)
        with self.assertRaises(graphe.ErreurContenu):
            decision.noter(self.cfg, "D-9", "x", True, None, None, None, None)

    def test_decisions_renversees(self):
        self.assertTrue(self.proposer()[0])
        self.assertTrue(self.proposer(id="D-2")[0])
        self.assertTrue(decision.renverser(self.cfg, "D-1", "D-2")[0])
        self.assertEqual(decision.bilan(self.cfg)["decisions_renversees"], 1)

    def test_ligne_de_commande(self):
        c = str(self.d / "graphe/config.toml")
        f = self.d / "d.toml"
        f.write_text('description = "x"\nauteur = "o"\nfonde_sur = ["I1"]\nchoix = "lancer"\nregle = "r"\n'
                     'prediction_issue = "soutenue"\nprediction_proba = 0.5\np_changement = 0.5\n'
                     'options = [{libelle = "lancer", valeur_v = 1}, {libelle = "ne rien faire", valeur_v = 0}]\n',
                     encoding="utf-8")
        self.assertEqual(decision.main(["--config", c, "proposer", str(f)]), 0)
        self.assertEqual(decision.main(["--config", c, "noter", "D-1", "--issue", "ok", "--realisee", "true"]), 0)
        self.assertEqual(decision.main(["--config", c, "bilan"]), 0)
        f.write_text(f.read_text().replace('"lancer", valeur_v = 1}, {libelle = "ne rien faire", valeur_v = 0}',
                                           '"lancer", valeur_v = 1}'))
        self.assertEqual(decision.main(["--config", c, "proposer", str(f)]), 1)


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Premisse(Base):
    carte_a = CARTE_PREMISSE

    def test_course_sur_carte_confirmatoire_a_premisse_non_verifiee(self):
        (self.d / "graphe/sources").mkdir(exist_ok=True)
        (self.d / "graphe/sources/guichet.json").write_text(json.dumps({"courses": [{
            "id": "R-1", "cle": hashlib.sha256(b"k").hexdigest(), "etat": "REUSSIE", "carte_calcul": "a",
            "debut": "2999-01-01T00:00:00Z", "fin": "2999-01-01T01:00:00Z",
            "artefacts": [{"nom": "recu.json", "sha256": H64}]}]}), encoding="utf-8")
        g, _ = graphe.construire(self.cfg)
        self.assertTrue(any("prémisse n'est pas vérifiée" in m for _, m in graphe.violations(g)))

    def course(self, debut):
        (self.d / "graphe/sources/guichet.json").write_text(json.dumps({"courses": [{
            "id": "R-1", "cle": hashlib.sha256(b"k").hexdigest(), "etat": "REUSSIE", "carte_calcul": "a",
            "debut": debut, "fin": debut, "artefacts": [{"nom": "recu.json", "sha256": H64}]}]}), encoding="utf-8")
        g, _ = graphe.construire(self.cfg)
        return [m for _, m in graphe.violations(g) if "prémisse n'est pas vérifiée" in m]

    def test_r17_date_d_entree_en_vigueur(self):
        self.assertEqual(self.course("2026-11-18T12:00:00Z"), [])       # avant : un constat, pas une violation
        self.assertTrue(self.course("2026-11-19T12:00:00Z"))            # après : violation

    def test_decideur_propose_de_verifier_la_premisse(self):
        g, _ = graphe.construire(self.cfg)
        f = decideur.file_candidats(g, self.cfg)
        self.assertTrue(any(c["type"] == "verifier-premisse" and c["cible"] == "P-A" for c in f["cycle"]))


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Decideur(Base):
    def file(self):
        g, _ = graphe.construire(self.cfg)
        return decideur.file_candidats(g, self.cfg)

    def test_cycle_carte_sans_relecture_puis_avec(self):
        f = self.file()
        self.assertIn("a", [c["cible"] for c in f["cycle"] if c["type"] == "relecture-conception"])
        (self.d / "experiences/a/RELECTURE-CONCEPTION.md").write_text("ok", encoding="utf-8")
        f = self.file()
        self.assertNotIn("a", [c["cible"] for c in f["cycle"] if c["type"] == "relecture-conception"])

    def test_course_reussie_sans_verdict(self):
        (self.d / "graphe/sources/guichet.json").write_text(json.dumps({"courses": [{
            "id": "R-1", "cle": hashlib.sha256(b"k").hexdigest(), "etat": "REUSSIE", "carte_calcul": "a",
            "debut": "2999-01-01T00:00:00Z", "artefacts": [{"nom": "recu.json", "sha256": H64}]}]}), encoding="utf-8")
        self.assertIn("R-1", [c["cible"] for c in self.file()["cycle"] if c["type"] == "verdict"])

    def test_reouverture_et_regle_d_arret(self):
        c = str(self.d / "graphe/config.toml")
        for h in ("H-A", "H-B"):         # H-B est une révision de H-A : même lignée, mêmes données
            self.assertEqual(verdict.main(["--config", c, h, "suspendue", "--auteur", "orchestrateur",
                                           "--reouvrir-si", "plus de données", "--donnees", "partition-1"]), 0)
        # deux verdicts « non concluante » sur les mêmes données, écrits sans passer par le refus
        texte = "".join(f'\n[[verdict]]\nid = "V-{h}-9"\nhypothese = "{h}"\nstatut = "non-concluante"\n'
                        f'auteur = "orchestrateur"\ndate = "2026-01-0{i}T00:00:00Z"\nconditions = ["x"]\n'
                        f'donnees = ["partition-1"]\n' for i, h in enumerate(("H-A", "H-B"), 1))
        (self.d / "graphe/jugements/verdicts.toml").write_text(texte, encoding="utf-8")
        f = self.file()
        self.assertEqual(len(f["reouvertures"]), 2)
        self.assertTrue(all("règle d'arrêt" in r.get("ecartee", "") for r in f["reouvertures"]))
        # une nouvelle carte de la lignée est écartée aussi
        carte = [x for x in f["cycle"] if x["type"] == "relecture-conception" and x["cible"] == "a"]
        self.assertTrue(carte and "règle d'arrêt" in carte[0]["ecartee"])

    def test_un_seul_verdict_non_concluant_n_arrete_pas(self):
        texte = '\n[[verdict]]\nid = "V-1"\nhypothese = "H-A"\nstatut = "non-concluante"\nauteur = "o"\n' \
                'date = "2026-01-01T00:00:00Z"\nconditions = ["x"]\ndonnees = ["partition-1"]\n'
        (self.d / "graphe/jugements/verdicts.toml").write_text(texte, encoding="utf-8")
        self.assertFalse(any(r.get("ecartee") for r in self.file()["reouvertures"]))

    def hyp(self, texte):
        (self.d / "graphe/jugements/hypotheses.toml").write_text(texte, encoding="utf-8")

    def test_premisse_infirmee_une_seule_reouverture(self):
        # une prémisse partagée par deux hypothèses de la même carte : un seul candidat
        carte = self.carte_a.replace('premisse = "verifiee"', 'premisse = "infirmee"')
        (self.d / "experiences/a/recherche.md").write_text(carte, encoding="utf-8")
        T.git(self.d, "commit", "-qam", "infirmee")
        self.hyp(HYP + '\n[[hypothese]]\nid = "H-C"\nidee = "I3"\ndescription = "d"\nmesure = "m"\n'
                 'effet_minimal = 0.1\ncarte = "a"\n[[hypothese.premisse]]\nid = "P-A"\ndescription = "partagée"\n')
        f = self.file()
        r = [c for c in f["reouvertures"] if c["type"] == "reouverture-premisse"]
        self.assertEqual([(c["cible"], c["hypotheses"]) for c in r], [("P-A", ["H-A", "H-C"])])
        self.assertFalse(any(c["type"] == "verifier-premisse" for c in f["cycle"]))

    def test_verdict_remplace_n_est_plus_candidat(self):
        v = ('\n[[verdict]]\nid = "V-1"\nhypothese = "H-A"\nstatut = "suspendue"\nauteur = "o"\n'
             'date = "2026-01-01T00:00:00Z"\nreouvrir_si = "ancienne condition"\n'
             '\n[[verdict]]\nid = "V-2"\nhypothese = "H-A"\nstatut = "suspendue"\nauteur = "o"\n'
             'date = "2026-01-02T00:00:00Z"\nreouvrir_si = "nouvelle condition"\nremplace = "V-1"\n')
        (self.d / "graphe/jugements/verdicts.toml").write_text(v, encoding="utf-8")
        r = [c for c in self.file()["reouvertures"] if c["cible"] == "H-A"]
        self.assertEqual([c["verdict"] for c in r], ["V-2"])
        # remplacé par un verdict plus ancien en date : le remplacé ne l'emporte jamais
        (self.d / "graphe/jugements/verdicts.toml").write_text(v.replace("2026-01-02", "2025-12-01"), encoding="utf-8")
        r = [c for c in self.file()["reouvertures"] if c["cible"] == "H-A"]
        self.assertEqual([c["verdict"] for c in r], ["V-2"])
        self.assertEqual(r[0]["statut"], "Suspendue")                     # statut court, pas l'IRI

    def test_idees_couvertes(self):
        self.hyp(HYP + '\n[[idee_interne]]\nid = "I-INT-9"\ndescription = "interne"\nproche_de = ["I3"]\n'
                 '[[hypothese]]\nid = "H-D"\nidee = "I-INT-9"\ndescription = "d"\nmesure = "m"\n'
                 'effet_minimal = 0.1\ncouvre = ["I4"]\n')
        f = self.file()
        self.assertEqual(f["portefeuille"], [])
        self.assertEqual(f["idees_couvertes"], 4)      # I1, I2 (sources), I3 (proche_de), I4 (couvre)

    def test_course_technique_sans_candidat_verdict(self):
        (self.d / "graphe/sources/guichet.json").write_text(json.dumps({"courses": [{
            "id": "R-1", "cle": hashlib.sha256(b"k").hexdigest(), "etat": "REUSSIE", "carte_calcul": "a",
            "debut": "2999-01-01T00:00:00Z", "artefacts": [{"nom": "recu.json", "sha256": H64}]}]}), encoding="utf-8")
        self.assertIn("R-1", [c["cible"] for c in self.file()["cycle"] if c["type"] == "verdict"])
        self.hyp(HYP + '\n[[course_technique]]\nid = "R-1"\nmotif = "essai du guichet"\n')
        self.assertNotIn("R-1", [c["cible"] for c in self.file()["cycle"] if c["type"] == "verdict"])

    def test_instruments_non_faits(self):
        (self.d / "graphe/jugements/instruments.toml").write_text(
            '[[instrument]]\nid = "a"\ndescription = "x"\nfait = false\npoids = 2\n'
            '[[instrument]]\nid = "b"\ndescription = "y"\nfait = true\npoids = 5\n'
            '[[instrument]]\nid = "c"\ndescription = "z"\nfait = false\npoids = 4\n', encoding="utf-8")
        cfg = self.d / "graphe/config.toml"
        cfg.write_text(cfg.read_text().replace('decisions = ', 'instruments = "jugements/instruments.toml"\ndecisions = '))
        self.cfg = graphe.Config(cfg)
        self.assertEqual([c["cible"] for c in self.file()["instruments"]], ["c", "a"])

    def test_portefeuille_s_reconcilie(self):
        p = self.file()["portefeuille"]
        # I1, I2 ont une hypothèse ; I5 est éliminée par un notateur ; I4 : 5, I3 : (4 + 2) / 2 = 3
        self.assertEqual([(c["cible"], c["s_reconcilie"]) for c in p], [("I4", 5.0), ("I3", 3.0)])

    def test_portefeuille_absent_le_dit(self):
        g = graphe.Graph()
        p, note = decideur.portefeuille(g)
        self.assertEqual(p, [])
        self.assertIn("pas dans le graphe", note)

    def test_chantiers_et_limite(self):
        ch = self.file()["chantiers"]
        self.assertEqual((ch["actifs"], ch["depasse"]), (["C-1"], False))
        extra = "".join(f'\n[[hypothese]]\nid = "H-X{i}"\nidee = "I3"\ndescription = "d"\nmesure = "m"\n'
                        f'effet_minimal = 0.1\nchantier = "C-{i + 1}"\nauteur = "o"\n' for i in range(1, 4))
        (self.d / "graphe/jugements/hypotheses.toml").write_text(HYP + extra, encoding="utf-8")
        ch = self.file()["chantiers"]
        self.assertEqual(ch["n"], 4)
        self.assertTrue(ch["depasse"])

    def test_dossier_de_relecture_et_empreinte(self):
        c = str(self.d / "graphe/config.toml")
        out = self.d / "sortie"
        self.assertEqual(decideur.main(["--config", c, "--sortie", str(out)]), 0)
        dossier = json.loads((out / "dossier-relecture.json").read_text())
        f = json.loads((out / "file-candidats.json").read_text())
        total = len(f["cycle"]) + len(f["reouvertures"]) + len(f["portefeuille"])
        self.assertEqual(len(dossier["candidats"]), min(decideur.K_DOSSIER, total))
        self.assertEqual(dossier["empreinte_fichier_candidats"],
                         hashlib.sha256((out / "file-candidats.json").read_bytes()).hexdigest())
        self.assertTrue((out / "file-candidats.md").is_file())


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Formes(unittest.TestCase):
    def test_regles_des_decisions(self):
        texte = (ICI.parent / "formes.ttl").read_text(encoding="utf-8")
        for r in range(13, 19):
            self.assertIn(f"# R{r} ", texte)

    def test_neuf_classes(self):
        self.assertEqual(len(graphe.CLASSES), 9)


if __name__ == "__main__":
    unittest.main()
