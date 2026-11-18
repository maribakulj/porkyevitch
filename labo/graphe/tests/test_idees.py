"""Conditions de levée, doublons, section « à réexaminer » du décideur et rapport des idées, sur données synthétiques.
Lancer : python3 -I labo/graphe/tests/test_idees.py"""

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
    import graphe
    import idees
    import levees
    import test_graphe as T
    import pyshacl  # noqa: F401
    DISPO = True
except ImportError:
    DISPO = False

LISTE = "id;idée;source;thème;priorité;dépendances\n" + "".join(
    f"I{i};Idée {i};article {i};t{i};P1;\n" for i in range(1, 9))
# notateur 1 : I1 garde (S 4) ; I2 impossible humain ; I3 doublon sans colonne ; I4 hors cap Xanto ; I5 déjà testé ;
# I6 impossible Gemini ; I7 garde ; I8 garde
N1 = ("id;elimine;motif;doublon_de;S;justification\n"
      "I1;non;;;4;ok\nI2;oui;impossible;;;Demande des annotateurs humains (Q1).\n"
      "I3;oui;doublon;;;même instrument que I1\nI4;oui;hors_cap;;;Projet Xanto, appariement de copies.\n"
      "I5;oui;deja_teste;;;Déjà fait.\nI6;oui;impossible;;;Exige Gemini comme juge.\n"
      "I7;non;;;2;ok\nI8;non;;;9;ok\n")
# notateur 2 : accord sur I2..I6 sauf I4 (garde) ; I7 écarte (désaccord) ; I8 écarte (désaccord, couverte par H-A)
N2 = ("id;elimine;motif;doublon_de;S;justification\n"
      "I1;non;;;3;ok\nI2;oui;impossible : bloqué, évaluation humaine (Q1);;;Pas d'annotateurs.\n"
      "I3;oui;doublon : même stratification que I1;I1;;x\nI4;non;;;7;ok\n"
      "I5;oui;déjà testé : D25;;;x\nI6;oui;impossible : juge Gemini exclu;;;x\n"
      "I7;oui;sans_decision;;;x\nI8;oui;sans_decision;;;x\n")
CONDITIONS = """
[[condition]]
id = "Q1-jugement-humain"
description = "Q1 tranchée"
etat = "vraie"
[[condition]]
id = "juge-gemini"
description = "Gemini exclu"
etat = "fausse"
[[condition]]
id = "chantiers-xanto-3d2d-separes"
description = "séparés"
etat = "vraie"
levee_quand = "fausse"
"""
HYP = """
[[hypothese]]
id = "H-A"
idee = "I8"
description = "d"
mesure = "m"
effet_minimal = 0.1
auteur = "o"
"""


def config(base: str) -> str:
    return (base.replace('[idees]\nfichier = "sources/idees.csv"', '[idees]\nfichier = "sources/idees.csv"')
            .replace('[[notations]]\nfichier = "sources/n1.csv"\nnotateur = "notateur-1"\nscores = ["G"]\n',
                     '[[notations]]\nfichier = "sources/n1.csv"\nnotateur = "notateur-1"\nscores = ["S"]\n'
                     '[[notations]]\nfichier = "sources/n2.csv"\nnotateur = "notateur-2"\nscores = ["S"]\n')
            .replace('[cartes]', '[conditions]\nfichier = "jugements/conditions.toml"\n'
                                  '[levees]\nfichier = "jugements/levees.toml"\n[cartes]'))


CONFIG = config(T.CONFIG).replace('experiences/*/recherche.md', 'experiences/*/recherche.md')


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Regles(unittest.TestCase):
    def cond(self, motif, just=""):
        r = levees.proposer(motif, just)
        return r[0] if r else None

    def test_motif_vers_condition(self):
        cas = [
            ("impossible", "Évaluation humaine, indisponible (D5, Q1).", "Q1-jugement-humain"),
            ("impossible : bloqué, exige une vérification humaine (Q1 non tranchée) ; à rouvrir si Q1 oui", "",
             "Q1-jugement-humain"),
            ("impossible : expert iconographe durable", "", "Q1-jugement-humain"),
            ("impossible", "Entraîner un LLM sur 50 M exemples dépasse nos moyens.", None),
            ("hors_cap", "Gemini est sorti du dispositif (D24).", "juge-gemini"),
            ("hors_cap", "Régimes de requêtes VLM : les VLM ne sont plus candidats (D24).", "vlm-candidat-production"),
            ("hors cap : chantiers Xanto et 3D2D séparés (D56)", "", "chantiers-xanto-3d2d-separes"),
            ("hors_cap", "Interface web pour historiens.", None),     # « historiens » ne vaut que pour impossible
            ("impossible : l'équipe n'a plus de quota Codex", "", "codex-quota"),
            ("impossible : juge Grok indisponible", "", "juge-grok"),
            ("hors_cap", "Entraînement sur GPU Kaggle", "gpu-kaggle"),
            ("impossible : jeu réservé CbDD", "", "jeu-reserve-cbdd"),
            ("impossible : incompatible avec l'encodeur figé", "", "encodeur-affinable"),
            ("sans_decision", "Exige des annotateurs humains", None),    # seuls les écartements durs ont une levée
            ("déjà testé : D25", "", None),
            ("doublon : même instrument que I011", "", None),
            ("", "", None),
        ]
        for motif, just, attendu in cas:
            with self.subTest(motif=motif, just=just):
                self.assertEqual(self.cond(motif, just), attendu)

    def test_accents_et_casse(self):
        self.assertEqual(self.cond("IMPOSSIBLE", "Annotation Humaine requise"), "Q1-jugement-humain")
        self.assertEqual(self.cond("Hors cap", "chantier XANTO"), "chantiers-xanto-3d2d-separes")

    def test_doublon_de_dans_le_texte(self):
        self.assertEqual(levees.doublon_de("doublon : rappel moyen par code, même passage que I011", "", "I012"), "I011")
        self.assertEqual(levees.doublon_de("doublon", "même que I011 et I012", "I011"), "I012")   # pas soi-même
        self.assertIsNone(levees.doublon_de("sans_decision", "voir I011", "I012"))
        self.assertIsNone(levees.doublon_de("doublon : sans référence", "", "I012"))


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        for rel, txt in {
            "graphe/config.toml": CONFIG, "graphe/sources/idees.csv": LISTE, "graphe/sources/n1.csv": N1,
            "graphe/sources/n2.csv": N2, "graphe/jugements/hypotheses.toml": HYP,
            "graphe/jugements/conditions.toml": CONDITIONS,
        }.items():
            p = self.d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt, encoding="utf-8")
        self.c = str(self.d / "graphe/config.toml")
        self.cfg = graphe.Config(self.c)
        self.assertEqual(levees.main(["--config", self.c]), 0)
        self.g, self.avert = graphe.construire(self.cfg)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def etat(self):
        return {e["id"]: e for e in idees.etat_idees(self.g)}


class Levees(Base):
    def test_fichier_propose(self):
        lev = levees.lire_levees(self.d / "graphe/jugements/levees.toml")
        paires = {(e["idee"], e["notateur"]): e["condition"] for e in lev}
        self.assertEqual(paires[("I2", "notateur-1")], "Q1-jugement-humain")
        self.assertEqual(paires[("I2", "notateur-2")], "Q1-jugement-humain")
        self.assertEqual(paires[("I4", "notateur-1")], "chantiers-xanto-3d2d-separes")
        self.assertEqual(paires[("I6", "notateur-1")], "juge-gemini")
        self.assertNotIn(("I5", "notateur-1"), paires)      # déjà testé : pas de condition
        self.assertNotIn(("I1", "notateur-1"), paires)      # gardée : pas de condition

    def test_entree_relue_conservee(self):
        f = self.d / "graphe/jugements/levees.toml"
        f.write_text(f.read_text().replace('relu = false', 'relu = true', 1).replace(
            'condition = "Q1-jugement-humain"', 'condition = "juge-gemini"', 1), encoding="utf-8")
        avant = levees.lire_levees(f)[0]
        self.assertEqual(levees.main(["--config", self.c]), 0)
        apres = levees.lire_levees(f)
        self.assertIn((avant["idee"], avant["notateur"], avant["condition"], True),
                      [(e["idee"], e["notateur"], e["condition"], e["relu"]) for e in apres])

    def test_lie_dans_le_graphe_aux_notations_qui_ecartent(self):
        n = self.g.value(graphe.URIRef(str(self.cfg.espace) + "N-notateur-2-I2"), graphe.LAB.leveeSi)
        self.assertEqual(str(self.g.value(n, graphe.DCTERMS.identifier)), "Q1-jugement-humain")
        self.assertIsNone(self.g.value(graphe.URIRef(str(self.cfg.espace) + "N-notateur-1-I1"), graphe.LAB.leveeSi))
        self.assertEqual(graphe.violations(self.g), [])

    def test_doublon_de_colonne_et_texte(self):
        esp = str(self.cfg.espace)
        n1 = graphe.URIRef(esp + "N-notateur-1-I3")        # colonne vide : lu dans « même instrument que I1 »
        n2 = graphe.URIRef(esp + "N-notateur-2-I3")        # colonne remplie
        self.assertEqual(self.g.value(n1, graphe.LAB.doublonDe), graphe.URIRef(esp + "I1"))
        self.assertEqual(self.g.value(n2, graphe.LAB.doublonDe), graphe.URIRef(esp + "I1"))

    def test_condition_inconnue_ignoree_et_dite(self):
        f = self.d / "graphe/jugements/levees.toml"
        f.write_text(f.read_text() + '\n[[levee]]\nidee = "I5"\nnotateur = "notateur-1"\nmotif = "x"\n'
                     'condition = "inconnue"\nrelu = true\n', encoding="utf-8")
        g, avert = graphe.construire(self.cfg)
        self.assertTrue(any("inconnue" in a for a in avert))


class Reexamen(Base):
    def test_statuts(self):
        e = self.etat()
        self.assertEqual([e[f"I{i}"]["statut"] for i in range(1, 9)],
                         ["gardée", "écartée", "écartée", "désaccord", "écartée", "écartée", "désaccord", "couverte"])

    def test_section_du_decideur(self):
        r = decideur.reexamen(self.g)
        ids = [c["cible"] for c in r]
        # I2 : Q1 vraie, levée ; I4 : Xanto « séparés » reste vraie donc pas levée, mais désaccord ; I7 : désaccord ;
        # I6 : Gemini fausse, pas levée ; I8 : couverte, absente
        self.assertEqual(ids, ["I2", "I4", "I7"])
        self.assertEqual(r[0]["conditions"], ["Q1-jugement-humain"])
        self.assertNotIn("I8", ids)
        self.assertNotIn("I6", ids)

    def test_desaccords_ranges_par_s_du_notateur_qui_garde(self):
        r = [c for c in decideur.reexamen(self.g) if not c["conditions"]]
        self.assertEqual([(c["cible"], c["s_garde"]) for c in r], [("I4", 7.0), ("I7", 2.0)])

    def test_condition_qui_change_d_etat(self):
        c = self.d / "graphe/jugements/conditions.toml"
        c.write_text(CONDITIONS.replace('id = "juge-gemini"\ndescription = "Gemini exclu"\netat = "fausse"',
                                        'id = "juge-gemini"\ndescription = "Gemini exclu"\netat = "vraie"'))
        g, _ = graphe.construire(self.cfg)
        self.assertIn("I6", [x["cible"] for x in decideur.reexamen(g)])

    def test_markdown_et_json(self):
        out = self.d / "sortie"
        self.assertEqual(decideur.main(["--config", self.c, "--sortie", str(out)]), 0)
        md = (out / "file-candidats.md").read_text()
        self.assertIn("## 5. Idées à réexaminer", md)
        self.assertIn("1 écartée(s) dont la condition de levée est remplie, 2 en désaccord", md)
        self.assertEqual(len(json.loads((out / "file-candidats.json").read_text())["a_reexaminer"]), 3)


class Rapport(Base):
    def test_comptes(self):
        self.assertEqual(idees.comptes(list(self.etat().values())),
                         {"gardée": 1, "écartée": 4, "désaccord": 2, "couverte": 1, "à réexaminer": 3})

    def test_fichiers_ecrits(self):
        self.assertEqual(graphe.main(["--config", self.c, "construire"]), 0)
        self.assertEqual(graphe.main(["--config", self.c, "rapport-idees"]), 0)
        md = (self.d / "graphe/rapports/IDEES.md").read_text()
        ht = (self.d / "graphe/rapports/idees.html").read_text()
        self.assertIn("8 idées : gardée 1, écartée 4, désaccord 2, couverte 1, à réexaminer 3.", md)
        self.assertIn("H-A (aucun verdict)", md)
        self.assertIn("Q1-jugement-humain (levée)", md)
        self.assertIn("doublon de I1", md)
        for s in idees.STATUTS:
            self.assertIn(f'data-f="{s}"', ht)
        self.assertEqual(ht.count("<tr data-s="), 8)

    def test_html_autonome_clair_sombre_telephone(self):
        ht = idees.en_html(list(self.etat().values()))
        self.assertNotIn("http://", ht)
        self.assertNotIn("https://", ht)
        self.assertNotIn(" src=", ht)
        self.assertNotIn("<link", ht)
        self.assertIn("prefers-color-scheme:dark", ht)
        self.assertIn('name="viewport"', ht)
        self.assertIn("max-width:760px", ht)

    def test_echappement_html(self):
        e = list(self.etat().values())
        e[0]["idee"] = "<b>x</b> & y"
        ht = idees.en_html(e)
        self.assertIn("&lt;b&gt;x&lt;/b&gt; &amp; y", ht)


if __name__ == "__main__":
    unittest.main()
