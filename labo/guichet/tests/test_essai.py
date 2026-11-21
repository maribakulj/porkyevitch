"""Paramètres de course, essai exigé avant une longue course GPU, bilan des durées vues, attente d'une course."""

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outils import Banc, Distant, Releve, bloc_recherche  # noqa: E402

from guichet import carte as cartes, registre  # noqa: E402

CODE = '"""Docstring du noyau."""\nfrom __future__ import annotations\nimport json, os\nprint(json.loads(os.environ.get("GUICHET_PARAMETRES", "{}")))\n'


class Base(unittest.TestCase):
    def setUp(self):
        self.b = Banc()

    def tearDown(self):
        self.b.fermer()

    def reussir(self, r, nom):
        self.b.finir(self.b.kaggle, f"compte/{nom}", {"recu.json": b"{}"}, duree=600)
        self.assertEqual(self.b.course(r.course)["etat"], "REUSSIE")


class Parametres(Base):
    def test_sans_parametre_la_cle_est_la_cle_de_code(self):
        c = cartes.lire(self.b.carte())
        self.assertEqual(cartes.cle("e" * 64, c), cartes.cle_code("e" * 64, c))

    def test_les_parametres_font_un_calcul_nouveau(self):
        a = self.b.g.soumettre(self.b.carte("a", code=CODE, parametres={"PARTIE": 1}), "kaggle")
        b = self.b.g.soumettre(self.b.carte("b", code=CODE, parametres={"PARTIE": 2}), "kaggle")
        self.assertEqual((a.code, b.code), ("ACCEPTEE", "ACCEPTEE"), b.message)
        ra, rb = self.b.course(a.course), self.b.course(b.course)
        self.assertNotEqual(ra["cle"], rb["cle"])
        self.assertEqual(ra["cle_code"], rb["cle_code"])
        doublon = self.b.g.soumettre(self.b.carte("c", code=CODE, parametres={"PARTIE": 1}), "kaggle")
        self.assertEqual(doublon.code, "REFUS")
        self.assertIn("déjà actif", doublon.message)

    def test_injection_dans_la_copie_seulement(self):
        chemin = self.b.carte("a", code=CODE, parametres={"PARTIE": 2, "NOM": "l'été \"x\""})
        r = self.b.g.soumettre(chemin, "kaggle")
        lance = Path(self.b.course(r.course)["instantane"]) / "run.py"
        texte = lance.read_text()
        self.assertEqual(texte.splitlines()[2].split("  #")[0][:30], "import os as _guichet_os; _gui")
        self.assertEqual((chemin.parent / "noyau" / "run.py").read_text(), CODE)   # le dossier de l'agent est intact
        sortie = subprocess.run([sys.executable, "-I", str(lance)], capture_output=True, text=True, check=True,
                                env={k: v for k, v in os.environ.items() if k != "GUICHET_PARAMETRES"}).stdout
        self.assertEqual(sortie.strip(), str({"NOM": "l'été \"x\"", "PARTIE": 2}))

    def test_parametre_invalide_refuse(self):
        r = self.b.g.soumettre(self.b.carte("a", parametres={"PARTIE": [1, 2]}), "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("paramètre PARTIE", r.message)

    def test_syntaxe_invalide_refusee_avant_le_depart(self):
        r = self.b.g.soumettre(self.b.carte("a", code="def f(:\n"), "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("illisible par Python", r.message)
        self.assertEqual(self.b.kaggle.lances, [])


class EssaiExige(Base):
    def test_longue_course_gpu_sans_essai_refusee(self):
        r = self.b.g.soumettre(self.b.carte(duree=2 * 3600), "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("essai_par", r.message)

    def test_essai_reussi_du_meme_code_ouvre_la_course(self):
        e = self.b.g.soumettre(self.b.carte("essai", code=CODE, duree=600, parametres={"LIMITE": 20}), "kaggle")
        self.reussir(e, "essai")
        r = self.b.g.soumettre(self.b.carte("long", code=CODE, duree=2 * 3600, essai=e.course), "kaggle")
        self.assertEqual(r.code, "ACCEPTEE", r.message)

    def test_essai_d_un_autre_code_ne_compte_pas(self):
        e = self.b.g.soumettre(self.b.carte("essai", code="print(1)\n", duree=600), "kaggle")
        self.reussir(e, "essai")
        r = self.b.g.soumettre(self.b.carte("long", code=CODE, duree=2 * 3600, essai=e.course), "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("pas une course réussie de ce code", r.message)

    def test_essai_echoue_ne_compte_pas(self):
        e = self.b.g.soumettre(self.b.carte("essai", code=CODE, duree=600, parametres={"LIMITE": 20}), "kaggle")
        self.b.finir(self.b.kaggle, "compte/essai", {})          # sans artefact : ECHOUEE_ARTEFACTS
        r = self.b.g.soumettre(self.b.carte("long", code=CODE, duree=2 * 3600, essai=e.course), "kaggle")
        self.assertEqual(r.code, "REFUS")

    def test_cpu_et_courses_courtes_sans_exigence(self):
        self.assertEqual(self.b.g.soumettre(self.b.carte("cpu", gpu=False, duree=2 * 3600), "kaggle").code, "ACCEPTEE")
        self.assertEqual(self.b.g.soumettre(self.b.carte("court", code="print(2)\n", duree=3600), "kaggle").code,
                         "ACCEPTEE")

    def test_exigence_desactivable(self):
        b = Banc(essai_requis_gpu_h=0)
        try:
            self.assertEqual(b.g.soumettre(b.carte(duree=2 * 3600), "kaggle").code, "ACCEPTEE")
        finally:
            b.fermer()


class Bilan(Base):
    def test_duree_vue_et_totaux(self):
        r = self.b.g.soumettre(self.b.carte("a"), "kaggle")
        self.b.finir(self.b.kaggle, "compte/a", {"recu.json": b"{}"}, duree=1800)
        e = self.b.g.soumettre(self.b.carte("b", code="print(3)\n"), "kaggle")
        self.b.finir(self.b.kaggle, "compte/b", {}, duree=600)
        texte = self.b.g.bilan().message
        self.assertIn(r.course, texte)
        self.assertIn(e.course, texte)
        self.assertIn("30 min / 10 min", texte)   # GPU sans chantier : réussies / autres

    def test_borne_haute_si_jamais_vue_tourner(self):
        r = self.b.g.soumettre(self.b.carte("a"), "kaggle")
        self.b.horloge.avancer(900)
        self.b.kaggle.fichiers["compte/a"] = {"recu.json": b"{}"}
        self.b.kaggle.etats["compte/a"] = Releve(Distant.TERMINEE)
        self.b.g.reconcilier()
        self.assertIn("≤ 15 min", self.b.g.bilan().message)
        self.assertEqual(self.b.course(r.course)["etat"], "REUSSIE")

    def test_date_invalide(self):
        self.assertEqual(self.b.g.bilan("21/11").code, "REFUS")

    def test_chantier_de_la_carte_de_recherche(self):
        b = Banc(chantiers=["tete-objets"], sprint_fin="2099-12-31")
        try:
            carte = bloc_recherche('decision = "d"\npremisse = "sans_objet"\nchantier = "tete-objets"\n')
            r = b.g.soumettre(b.carte("a", recherche=carte), "kaggle")
            self.assertEqual(b.course(r.course)["chantier"], "tete-objets")
            self.assertIn("GPU tete-objets", b.g.bilan().message)
        finally:
            b.fermer()


class Attendre(Base):
    def test_rend_la_fin(self):
        r = self.b.g.soumettre(self.b.carte("a"), "kaggle")
        appels = []

        def sommeil(s):
            appels.append(s)
            self.b.horloge.avancer(s)
            if len(appels) == 2:
                self.b.kaggle.fichiers["compte/a"] = {"recu.json": b"{}"}
                self.b.kaggle.etats["compte/a"] = Releve(Distant.TERMINEE)
        rep = self.b.g.attendre(r.course, 3600, 60, sommeil)
        self.assertEqual((rep.code, len(appels)), ("OK", 2))
        self.assertIn("REUSSIE", rep.message)

    def test_echeance(self):
        r = self.b.g.soumettre(self.b.carte("a"), "kaggle")
        rep = self.b.g.attendre(r.course, 300, 60, self.b.horloge.avancer)
        self.assertEqual(rep.code, "INCERTAINE")
        self.assertIn("ne rien relancer", rep.message)

    def test_fin_en_echec(self):
        r = self.b.g.soumettre(self.b.carte("a"), "kaggle")
        self.b.finir(self.b.kaggle, "compte/a", {})
        self.assertEqual(self.b.g.attendre(r.course, 60, 60, self.b.horloge.avancer).code, "REFUS")


class Migration(unittest.TestCase):
    def test_registre_ancien_recoit_les_colonnes(self):
        with tempfile.TemporaryDirectory() as t:
            chemin = Path(t) / "registre.sqlite"
            ancien = sqlite3.connect(chemin)
            schema = registre._SCHEMA
            ancien.executescript(schema)
            ancien.close()
            c = registre.ouvrir(chemin)
            colonnes = {r["name"] for r in c.execute("PRAGMA table_info(courses)")}
            self.assertTrue({"cle_code", "chantier"} <= colonnes)
            registre.ouvrir(chemin).close()          # une seconde ouverture ne refait rien
            c.close()


if __name__ == "__main__":
    unittest.main()
