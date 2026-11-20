"""Sprint de construction : la porte s'inverse. Les chantiers retenus passent seuls ; le reste attend l'humain."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outils import Banc, bloc_recherche  # noqa: E402

CONSTRUCTION = bloc_recherche('decision = "brancher la tête objets"\npremisse = "sans_objet"\nchantier = "tete-objets"\n')
CONFIRMATION = bloc_recherche('decision = "d"\npremisse = "verifiee"\n[puissance]\nic = [0.02, 0.14]\n'
                              'effet_plausible = 0.15\n')


class Sprint(unittest.TestCase):
    def banc(self, fin="2099-12-31", chantiers=("tete-objets", "donnees-icarus")):
        return Banc(chantiers=list(chantiers), sprint_fin=fin)

    def test_chantier_retenu_passe_sans_puissance(self):
        b = self.banc()
        r = b.g.soumettre(b.carte(recherche=CONSTRUCTION), "kaggle")
        self.assertEqual(r.code, "ACCEPTEE", r.message)

    def test_confirmation_puissante_attend_l_humain(self):
        b = self.banc()
        r = b.g.soumettre(b.carte(recherche=CONFIRMATION), "kaggle")
        self.assertEqual(r.code, "ACCORD_REQUIS")
        self.assertIn("aucun chantier nommé", r.message)

    def test_chantier_non_retenu_attend_l_humain(self):
        b = self.banc()
        autre = CONSTRUCTION.replace("tete-objets", "calibration-juges")
        r = b.g.soumettre(b.carte(recherche=autre), "kaggle")
        self.assertEqual(r.code, "ACCORD_REQUIS")
        self.assertIn("non retenu", r.message)

    def test_cpu_sans_carte_attend_l_humain(self):
        b = self.banc()
        r = b.g.soumettre(b.carte(gpu=False, recherche=None), "kaggle")
        self.assertEqual(r.code, "ACCORD_REQUIS")

    def test_cpu_d_un_chantier_passe(self):
        b = self.banc()
        r = b.g.soumettre(b.carte(gpu=False, recherche=CONSTRUCTION), "kaggle")
        self.assertEqual(r.code, "ACCEPTEE", r.message)

    def test_apres_la_fin_regle_ordinaire(self):
        b = self.banc(fin="2000-01-01")
        self.assertEqual(b.g.soumettre(b.carte(recherche=CONFIRMATION), "kaggle").code, "ACCEPTEE")
        r = b.g.soumettre(b.carte(nom="c2", recherche=CONSTRUCTION), "kaggle")
        self.assertEqual(r.code, "REFUS")  # hors sprint : puissance ou « exploratoire » obligatoire

    def test_sans_chantiers_pas_de_sprint(self):
        b = self.banc(chantiers=())
        self.assertEqual(b.g.soumettre(b.carte(gpu=False, recherche=None), "kaggle").code, "ACCEPTEE")


class CommandeSprint(unittest.TestCase):
    def test_ouvrir_puis_arreter(self):
        b = Banc()
        r = b.g.ouvrir_sprint(["tete-objets"], "2099-01-31")
        self.assertEqual(r.code, "OK", r.message)
        self.assertIn('sprint_fin = "2099-01-31"', (b.maison / "guichet" / "config.toml").read_text())
        self.assertEqual(b.g.soumettre(b.carte(recherche=CONSTRUCTION), "kaggle").code, "ACCEPTEE")
        self.assertIn("Sprint jusqu'au 2099-01-31", b.g.resume().message)
        self.assertEqual(b.g.ouvrir_sprint([], None).code, "OK")
        self.assertNotIn("chantiers", (b.maison / "guichet" / "config.toml").read_text())
        self.assertEqual(b.g.soumettre(b.carte(nom="c2", code="print(2)\n", gpu=False, recherche=None), "kaggle").code,
                         "ACCEPTEE")

    def test_rouvrir_remplace(self):
        b = Banc()
        b.g.ouvrir_sprint(["a"], "2099-01-31")
        b.g.ouvrir_sprint(["b", "c"], "2099-02-28")
        texte = (b.maison / "guichet" / "config.toml").read_text()
        self.assertEqual(texte.count("chantiers ="), 1)
        self.assertEqual(b.g.config.chantiers, ["b", "c"])

    def test_refus(self):
        b = Banc()
        self.assertEqual(b.g.ouvrir_sprint(["tete-objets"], None).code, "REFUS")
        self.assertEqual(b.g.ouvrir_sprint(["tete-objets"], "2000-01-01").code, "REFUS")
        self.assertEqual(b.g.ouvrir_sprint(["Tête objets"], "2099-01-31").code, "REFUS")
        self.assertEqual(b.g.ouvrir_sprint(["a", "b", "c", "d"], "2099-01-31").code, "REFUS")

    def test_l_agent_n_a_pas_la_commande(self):
        from guichet import cli
        with self.assertRaises(SystemExit):
            cli.agent(["sprint", "tete-objets", "--jusqu-au", "2099-01-31"])


if __name__ == "__main__":
    unittest.main()
