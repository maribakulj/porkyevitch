"""Règles du guichet, une par test. Lancer : python3 -I tests/test_guichet.py"""

import os
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outils import Banc, Distant, LancementIncertain, Releve  # noqa: E402

from guichet import cli  # noqa: E402
from guichet.plateformes import lire_journal_colab, lire_statut_kaggle  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.b = Banc()

    def tearDown(self):
        self.b.fermer()


class Doublons(Base):
    def test_meme_calcul_actif_refuse_sur_toute_plateforme(self):
        carte = self.b.carte()
        r1 = self.b.g.soumettre(carte, "kaggle")
        self.assertEqual(r1.code, "ACCEPTEE")
        for plateforme in ("kaggle", "colab"):
            r = self.b.g.soumettre(carte, plateforme)
            self.assertEqual(r.code, "REFUS", plateforme)
            self.assertIn(r1.course, r.message)
        self.assertEqual(len(self.b.kaggle.lances) + len(self.b.colab.lances), 1)

    def test_renommer_l_experience_ne_fait_pas_un_calcul_nouveau(self):
        self.b.g.soumettre(self.b.carte("premier"), "kaggle")
        r = self.b.g.soumettre(self.b.carte("autre-nom", slug="compte/autre"), "colab")
        self.assertEqual(r.code, "REFUS")

    def test_un_octet_change_fait_un_calcul_nouveau(self):
        self.b.g.soumettre(self.b.carte("a"), "kaggle")
        r = self.b.g.soumettre(self.b.carte("b", code="print('ok!')\n", slug="compte/b"), "kaggle")
        self.assertEqual(r.code, "ACCEPTEE")

    def test_une_entree_differente_fait_un_calcul_nouveau(self):
        self.b.g.soumettre(self.b.carte("a"), "kaggle")
        r = self.b.g.soumettre(self.b.carte("b", slug="compte/b", entrees=(("vecteurs", "b" * 64),)), "kaggle")
        self.assertEqual(r.code, "ACCEPTEE")

    def test_deja_reussi_refuse_et_renvoie_a_la_sortie(self):
        carte = self.b.carte()
        r1 = self.b.g.soumettre(carte, "kaggle")
        self.b.finir(self.b.kaggle, "compte/calcul", {"recu.json": b"{}"})
        r = self.b.g.soumettre(carte, "colab")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("déjà fait", r.message)
        self.assertIn(r1.course, r.message)

    def test_replication_demande_un_accord_puis_part(self):
        carte = self.b.carte()
        self.b.g.soumettre(carte, "kaggle")
        self.b.finir(self.b.kaggle, "compte/calcul", {"recu.json": b"{}"})
        r = self.b.g.soumettre(carte, "colab", replication="contrôle de déterminisme demandé")
        self.assertEqual(r.code, "ACCORD_REQUIS")
        self.assertEqual(len(self.b.colab.lances), 0)
        a = self.b.g.approuver(r.demande)
        self.assertEqual(a.code, "ACCEPTEE")
        self.assertEqual(len(self.b.colab.lances), 1)

    def test_deux_processus_simultanes_un_seul_lancement(self):
        carte = self.b.carte()
        n = 6
        barriere, reponses = threading.Barrier(n), []

        def soumettre(plateforme):
            g = self.b.nouveau()  # une connexion par fil, comme deux processus distincts
            barriere.wait()
            reponses.append(g.soumettre(carte, plateforme).code)

        fils = [threading.Thread(target=soumettre, args=(("kaggle", "colab")[i % 2],)) for i in range(n)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        self.assertEqual(reponses.count("ACCEPTEE"), 1, reponses)
        self.assertEqual(len(self.b.kaggle.lances) + len(self.b.colab.lances), 1)

    def test_un_noyau_kaggle_ne_porte_qu_une_course(self):
        self.b.g.soumettre(self.b.carte("a", slug="compte/meme"), "kaggle")
        r = self.b.g.soumettre(self.b.carte("b", code="autre\n", slug="compte/meme"), "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("dernière version", r.message)


class Incertitude(Base):
    def test_delai_au_lancement_rend_inconnue_et_bloque(self):
        carte = self.b.carte()
        self.b.kaggle.effet_lancement = LancementIncertain("délai dépassé")
        r = self.b.g.soumettre(carte, "kaggle")
        self.assertEqual(r.code, "INCERTAINE")
        self.b.kaggle.effet_lancement = None
        r2 = self.b.g.soumettre(carte, "colab")
        self.assertEqual(r2.code, "REFUS")
        self.assertIn("inconnu", r2.message)

    def test_inconnue_kaggle_sans_version_n_est_jamais_resolue_seule(self):
        # Le statut Kaggle porte sur la dernière version du noyau, peut-être une ancienne : un COMPLETE ne prouve rien.
        carte = self.b.carte()
        self.b.kaggle.effet_lancement = LancementIncertain("délai dépassé")
        r = self.b.g.soumettre(carte, "kaggle")
        self.b.kaggle.etats["compte/calcul"] = Releve(Distant.TERMINEE)
        self.b.kaggle.fichiers["compte/calcul"] = {"recu.json": b"{}"}
        self.b.g.reconcilier()
        self.assertEqual(self.b.course(r.course)["etat"], "INCONNUE")
        self.b.g.trancher(r.course, "EN_COURS", "version 7 vue sur le site, lancée à 14 h 02", version="7")
        self.b.g.reconcilier()
        self.assertEqual(self.b.course(r.course)["etat"], "REUSSIE")

    def test_releve_illisible_ne_vaut_ni_fini_ni_mort(self):
        r = self.b.g.soumettre(self.b.carte(), "kaggle")
        self.b.kaggle.etats["compte/calcul"] = Releve(Distant.EN_COURS)
        self.b.g.reconcilier()
        self.b.kaggle.etats["compte/calcul"] = Releve(Distant.INCONNU, "401")
        self.b.g.reconcilier()
        self.assertEqual(self.b.course(r.course)["etat"], "EN_COURS")

    def test_soumise_sans_suite_devient_inconnue(self):
        carte = self.b.carte()
        self.b.kaggle.effet_lancement = KeyboardInterrupt()  # processus tué pendant le lancement
        with self.assertRaises(KeyboardInterrupt):
            self.b.g.soumettre(carte, "kaggle")
        self.b.kaggle.effet_lancement = None
        self.b.horloge.avancer(3600)
        self.b.g.reconcilier()
        etats = [r["etat"] for r in self.b.g.c.execute("SELECT etat FROM courses")]
        self.assertEqual(etats, ["INCONNUE"])
        self.assertEqual(self.b.g.soumettre(carte, "colab").code, "REFUS")


class Artefacts(Base):
    def test_sans_les_artefacts_declares_la_course_n_est_pas_reussie(self):
        r = self.b.g.soumettre(self.b.carte(artefacts=("recu.json", "etats/*.pt")), "kaggle")
        self.b.finir(self.b.kaggle, "compte/calcul", {"recu.json": b"{}"})
        self.assertEqual(self.b.course(r.course)["etat"], "ECHOUEE_ARTEFACTS")

    def test_artefact_vide_ne_compte_pas(self):
        r = self.b.g.soumettre(self.b.carte(), "kaggle")
        self.b.finir(self.b.kaggle, "compte/calcul", {"recu.json": b""})
        self.assertEqual(self.b.course(r.course)["etat"], "ECHOUEE_ARTEFACTS")

    def test_rapatriement_rate_ne_relance_pas_le_calcul(self):
        carte = self.b.carte()
        r = self.b.g.soumettre(carte, "kaggle")
        self.b.kaggle.rapatriement_casse = True
        self.b.finir(self.b.kaggle, "compte/calcul", {"recu.json": b"{}"})
        self.assertIn(self.b.course(r.course)["etat"], ("EN_FILE", "EN_COURS"))
        self.assertEqual(self.b.g.soumettre(carte, "colab").code, "REFUS")
        self.b.kaggle.rapatriement_casse = False
        self.b.g.reconcilier()
        self.assertEqual(self.b.course(r.course)["etat"], "REUSSIE")
        self.assertEqual(len(self.b.kaggle.lances), 1)

    def test_relance_identique_apres_echec_exige_un_motif(self):
        carte = self.b.carte()
        self.b.g.soumettre(carte, "kaggle")
        self.b.kaggle.etats["compte/calcul"] = Releve(Distant.ECHOUEE, "ERROR")
        self.b.g.reconcilier()
        self.assertEqual(self.b.g.soumettre(carte, "kaggle").code, "REFUS")
        self.assertEqual(self.b.g.soumettre(carte, "kaggle", motif="machine perdue, journal vide").code, "ACCEPTEE")

    def test_colab_est_liberee_apres_rapatriement(self):
        r = self.b.g.soumettre(self.b.carte(), "colab")
        slug = self.b.course(r.course)["slug"]
        self.b.finir(self.b.colab, slug, {"recu.json": b"{}"})
        self.assertEqual(self.b.colab.liberees, [slug])


class DureeEtBudget(Base):
    def test_duree_non_mesuree_au_dela_du_seuil_refusee(self):
        r = self.b.g.soumettre(self.b.carte(duree=7 * 3600), "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("mesurée", r.message)

    def test_duree_mesuree_et_longue_demande_un_accord(self):
        blanc = self.b.g.soumettre(self.b.carte("blanc", code="blanc\n", duree=600), "kaggle")
        self.b.finir(self.b.kaggle, "compte/blanc", {"recu.json": b"{}"}, duree=600)
        r = self.b.g.soumettre(self.b.carte("complet", duree=7 * 3600, mesuree=blanc.course), "kaggle")
        self.assertEqual(r.code, "ACCORD_REQUIS")
        self.assertEqual(self.b.g.approuver(r.demande).code, "ACCEPTEE")

    def test_budget_hebdomadaire(self):
        b = Banc(budget_gpu_hebdo_h=2)
        try:
            self.assertEqual(b.g.soumettre(b.carte("a", duree=3600), "kaggle").code, "ACCEPTEE")
            r = b.g.soumettre(b.carte("b", code="b\n", slug="compte/b", duree=3600 + 60), "kaggle")
            self.assertEqual(r.code, "REFUS")
            self.assertIn("budget", r.message)
            # Le CPU n'entre pas dans le budget GPU.
            self.assertEqual(b.g.soumettre(b.carte("c", code="c\n", slug="compte/c", gpu=False, duree=3600), "kaggle"
                                           ).code, "ACCEPTEE")
        finally:
            b.fermer()

    def test_nombre_de_gpu_simultanes(self):
        for i in range(2):
            self.assertEqual(self.b.g.soumettre(self.b.carte(f"g{i}", code=f"{i}\n"), "kaggle").code, "ACCEPTEE")
        r = self.b.g.soumettre(self.b.carte("g2", code="2\n"), "colab")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("Attendre", r.message)


class Bascule(Base):
    def test_bascule_depuis_kaggle_exige_un_accord(self):
        r = self.b.g.soumettre(self.b.carte(), "kaggle")
        d = self.b.g.demander_bascule(r.course, "colab", "file Kaggle bloquée depuis 1 h 30")
        self.assertEqual(d.code, "ACCORD_REQUIS")
        self.assertEqual(len(self.b.colab.lances), 0)
        a = self.b.g.approuver(d.demande)
        self.assertEqual(a.code, "ACCEPTEE")
        self.assertEqual(self.b.course(r.course)["etat"], "ABANDONNEE")

    def test_abandonnee_qui_demarre_quand_meme_est_signalee_et_comptee(self):
        r = self.b.g.soumettre(self.b.carte(), "kaggle")
        d = self.b.g.demander_bascule(r.course, "colab", "file bloquée")
        self.b.g.approuver(d.demande)
        self.b.kaggle.etats["compte/calcul"] = Releve(Distant.EN_COURS)
        lignes = self.b.g.reconcilier().lignes
        self.assertTrue(any("doublon" in l for l in lignes), lignes)

    def test_bascule_depuis_colab_annule_d_abord(self):
        r = self.b.g.soumettre(self.b.carte(), "colab")
        slug = self.b.course(r.course)["slug"]
        n = self.b.g.demander_bascule(r.course, "kaggle", "machine Colab trop lente")
        self.assertEqual(n.code, "ACCEPTEE")
        self.assertEqual(self.b.colab.annulees, [slug])
        self.assertEqual(self.b.course(r.course)["etat"], "ANNULEE")

    def test_une_course_qui_tourne_ne_se_bascule_pas(self):
        r = self.b.g.soumettre(self.b.carte(), "kaggle")
        self.b.kaggle.etats["compte/calcul"] = Releve(Distant.EN_COURS)
        self.b.g.reconcilier()
        self.assertEqual(self.b.g.demander_bascule(r.course, "colab", "plus vite").code, "REFUS")

    def test_bascule_sans_objet_si_l_ancienne_a_demarre(self):
        r = self.b.g.soumettre(self.b.carte(), "kaggle")
        d = self.b.g.demander_bascule(r.course, "colab", "file bloquée")
        self.b.kaggle.etats["compte/calcul"] = Releve(Distant.EN_COURS)
        self.b.g.reconcilier()
        self.assertEqual(self.b.g.approuver(d.demande).code, "REFUS")
        self.assertEqual(len(self.b.colab.lances), 0)


class Dossier(Base):
    def test_lien_symbolique_refuse(self):
        carte = self.b.carte()
        secret = self.b.maison / ".kaggle" / "kaggle.json"
        secret.parent.mkdir()
        secret.write_text('{"key": "secret"}')
        os.symlink(secret, carte.parent / "noyau" / "cle.json")
        r = self.b.g.soumettre(carte, "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("lien symbolique", r.message)

    def test_lien_physique_refuse(self):
        carte = self.b.carte()
        cible = self.b.depot / "ailleurs.txt"
        cible.write_text("x")
        os.link(cible, carte.parent / "noyau" / "copie.txt")
        r = self.b.g.soumettre(carte, "kaggle")
        self.assertEqual(r.code, "REFUS")
        self.assertIn("liens physiques", r.message)

    def test_dossier_dans_l_espace_du_guichet_refuse(self):
        carte = self.b.carte()
        cible = self.b.maison / "vol"
        cible.mkdir()
        (cible / "run.py").write_text("x")
        texte = carte.read_text().replace('dossier = "noyau"', f'dossier = "{cible}"')
        carte.write_text(texte)
        self.assertEqual(self.b.g.soumettre(carte, "kaggle").code, "REFUS")

    def test_ce_qui_part_est_l_instantane_pas_le_dossier(self):
        carte = self.b.carte()
        r = self.b.g.soumettre(carte, "kaggle")
        (carte.parent / "noyau" / "run.py").write_text("modifié après coup\n")
        instantane = Path(self.b.course(r.course)["instantane"])
        self.assertEqual((instantane / "run.py").read_text(), "print('ok')\n")

    def test_carte_sans_artefacts_refusee(self):
        r = self.b.g.soumettre(self.b.carte(artefacts=()), "kaggle")
        self.assertEqual(r.code, "REFUS")


class Portes(Base):
    def test_l_agent_ne_peut_pas_approuver(self):
        with self.assertRaises(SystemExit) as e:
            cli.agent(["approuver", "D-1"])
        self.assertEqual(e.exception.code, 2)

    def test_mauvais_compte_refuse(self):
        fichier = Path(cli.__file__).resolve().parents[1] / "compte.txt"
        fichier.write_text("compte-qui-n-existe-pas\n")
        try:
            self.assertEqual(cli.agent(["resume"]), 2)
            self.assertEqual(cli.humain(["resume"]), 2)
        finally:
            fichier.unlink()


class Lecture(unittest.TestCase):
    def test_statuts_kaggle(self):
        self.assertIs(lire_statut_kaggle('compte/x has status "KernelWorkerStatus.COMPLETE"').etat, Distant.TERMINEE)
        self.assertIs(lire_statut_kaggle('compte/x has status "running"').etat, Distant.INCONNU)
        self.assertIs(lire_statut_kaggle('compte/x has status "QUEUED"').etat, Distant.EN_FILE)
        self.assertIs(lire_statut_kaggle('403 - Forbidden').etat, Distant.INCONNU)
        self.assertIs(lire_statut_kaggle('').etat, Distant.INCONNU)

    def test_journal_colab(self):
        self.assertIs(lire_journal_colab("10:00:00 FIN r-1 ok=True\n", "r-1").etat, Distant.TERMINEE)
        self.assertIs(lire_journal_colab("10:00:00 FIN r-0 ok=True\n", "r-1").etat, Distant.EN_FILE)
        self.assertIs(lire_journal_colab("sortie 0 (assemblage)\ndebut calcul\n", "r-1").etat, Distant.EN_COURS)
        self.assertIs(lire_journal_colab("debut calcul\nsortie 1 (calcul)\n", "r-1").etat, Distant.ECHOUEE)


if __name__ == "__main__":
    unittest.main()
