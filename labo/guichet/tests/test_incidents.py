"""Incidents types d'une boucle de calcul autonome, rejoués à vide. Lancer : python3 -I tests/test_incidents.py

Chacun est un cas réellement observé, décrit sans le projet où il s'est produit. Chaque test dit ce que le guichet
empêche, et le dernier de la première classe dit ce qu'il laisse passer.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outils import Banc, Distant, Releve  # noqa: E402


class DoublonsEnCascade(unittest.TestCase):
    """Une étude de trois encodeurs, faite en dix courses GPU au lieu de trois.

    La file Kaggle tarde ; l'agent prépare Colab, « le premier à démarrer sera gardé », sans annuler Kaggle. Un calcul
    lent sur Colab est aussi poussé sur Kaggle, « doublon de sûreté ». À la fin, les états des modèles n'avaient pas été
    sauvegardés : tout est relancé avec l'export, et encore doublé « en secours ».
    """

    def setUp(self):
        self.b = Banc(max_gpu_simultanes=3)

    def tearDown(self):
        self.b.fermer()

    def test_file_bloquee_pas_de_second_lancement_ailleurs(self):
        carte = self.b.carte("etude-a", slug="compte/etude-a")
        r = self.b.g.soumettre(carte, "kaggle")
        self.b.horloge.avancer(3600)
        self.b.g.reconcilier()
        doublon = self.b.g.soumettre(carte, "colab")
        self.assertEqual(doublon.code, "REFUS")
        self.assertIn("demander-bascule", doublon.message)
        bascule = self.b.g.demander_bascule(r.course, "colab", "file GPU chargée depuis 1 h")
        self.assertEqual(bascule.code, "ACCORD_REQUIS")  # Kaggle ne sait pas annuler : l'humain décide
        self.assertEqual(len(self.b.colab.lances), 0)

    def test_doublon_de_surete_refuse(self):
        carte = self.b.carte("etude-b", slug="compte/etude-b")
        r = self.b.g.soumettre(carte, "colab")
        slug = self.b.course(r.course)["slug"]
        self.b.colab.etats[slug] = Releve(Distant.EN_COURS)
        self.b.g.reconcilier()
        self.assertEqual(self.b.g.soumettre(carte, "kaggle").code, "REFUS")
        self.assertEqual(self.b.g.demander_bascule(r.course, "kaggle", "Colab lent").code, "REFUS")  # elle tourne

    def test_sans_les_etats_nommes_par_la_carte_la_course_n_est_pas_reussie(self):
        carte = self.b.carte("etude-a", slug="compte/etude-a", artefacts=("recu.json", "etats/*.pt"))
        r = self.b.g.soumettre(carte, "kaggle")
        self.b.finir(self.b.kaggle, "compte/etude-a", {"recu.json": b'{"succes": true}'})
        self.assertEqual(self.b.course(r.course)["etat"], "ECHOUEE_ARTEFACTS")

    def test_limite_un_artefact_non_declare_n_est_pas_devine(self):
        # Si la carte ne nomme que le reçu, la course est réussie, et la relance avec export (code modifié, donc calcul
        # nouveau) est permise. Nommer ce dont la suite aura besoin reste le travail de l'agent ; le résumé montre à
        # l'humain les artefacts déclarés de chaque demande.
        carte = self.b.carte("etude-a", slug="compte/etude-a", artefacts=("recu.json",))
        r = self.b.g.soumettre(carte, "kaggle")
        self.b.finir(self.b.kaggle, "compte/etude-a", {"recu.json": b"{}"})
        self.assertEqual(self.b.course(r.course)["etat"], "REUSSIE")

    def test_le_controle_croise_est_une_replication_qui_demande_un_accord(self):
        carte = self.b.carte("etude-c", slug="compte/etude-c")
        self.b.g.soumettre(carte, "kaggle")
        self.b.finir(self.b.kaggle, "compte/etude-c", {"recu.json": b"{}"})
        self.assertEqual(self.b.g.soumettre(carte, "colab").code, "REFUS")
        self.assertEqual(self.b.g.soumettre(carte, "colab", replication="contrôle croisé").code, "ACCORD_REQUIS")

    def test_bilan_trois_courses_et_pas_dix(self):
        for nom in ("a", "b", "c"):
            carte = self.b.carte(f"etude-{nom}", code=f"# {nom}\n", slug=f"compte/etude-{nom}",
                                 artefacts=("recu.json", "etats/*.pt"))
            self.assertEqual(self.b.g.soumettre(carte, "kaggle").code, "ACCEPTEE")
            for tentative in ("kaggle", "colab"):
                self.assertEqual(self.b.g.soumettre(carte, tentative).code, "REFUS")
        self.assertEqual(len(self.b.kaggle.lances) + len(self.b.colab.lances), 3)


class DureeJamaisMesuree(unittest.TestCase):
    """Trois noyaux CPU coupés par Kaggle à la limite de 12 h, sans sortie : la durée de 6 à 8 h était une estimation
    jamais mesurée, et un relecteur l'avait signalé."""

    def test_six_heures_non_mesurees_refusees(self):
        b = Banc()
        try:
            r = b.g.soumettre(b.carte("etude", gpu=False, duree=7 * 3600), "kaggle")
            self.assertEqual(r.code, "REFUS")
            self.assertIn("essai chronométré", r.message)
        finally:
            b.fermer()


class SecondePousseeIdentique(unittest.TestCase):
    """Une sonde reste QUEUED plus de 9 h ; on en pousse une seconde « à l'identique », alors que le CLI ne sait pas
    annuler la première : si les deux s'exécutent, le calcul est fait deux fois."""

    def test_seconde_poussee_identique_refusee(self):
        b = Banc()
        try:
            carte = b.carte("sonde", gpu=False, duree=600)
            b.g.soumettre(carte, "kaggle")
            b.horloge.avancer(9 * 3600)
            b.g.reconcilier()
            self.assertEqual(b.g.soumettre(carte, "kaggle").code, "REFUS")
            self.assertEqual(len(b.kaggle.lances), 1)
        finally:
            b.fermer()


if __name__ == "__main__":
    unittest.main()
