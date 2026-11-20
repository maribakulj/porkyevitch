"""La purge : l'agent supprime une grosse archive rapatriée, et seulement celle que la carte déclare purgeable.
Lancer : python3 -I tests/test_purge.py"""

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from outils import Banc, Distant, Releve  # noqa: E402
from guichet import carte as cartes  # noqa: E402

ARCHIVE = b"images" * 1000
SHA = hashlib.sha256(ARCHIVE).hexdigest()


class Purge(unittest.TestCase):
    def setUp(self):
        self.b = Banc()
        self.carte = self.b.carte("etude", slug="compte/etude", gpu=False, artefacts=("recu.json",),
                                  purgeables=["*.tar"])
        self.ident = self.b.g.soumettre(self.carte, "kaggle").course
        self.b.finir(self.b.kaggle, "compte/etude", {"recu.json": b"{}", "images.tar": ARCHIVE, "autre.txt": b"x"})
        self.sortie = self.b.g.sorties / self.ident

    def tearDown(self):
        self.b.fermer()

    def refus(self, *args, motif=""):
        r = self.b.g.purger(*args)
        self.assertEqual((r.code, r.sortie), ("REFUS", 2), r.message)
        self.assertIn(motif, r.message)

    def test_nominal(self):
        r = self.b.g.purger(self.ident, "images.tar", SHA)
        self.assertEqual((r.code, r.sortie), ("OK", 0))
        self.assertFalse((self.sortie / "images.tar").exists())
        self.assertTrue((self.sortie / "recu.json").exists())
        ligne = self.b.g.c.execute("SELECT * FROM purges").fetchone()
        self.assertEqual((ligne["course"], ligne["nom"], ligne["sha256"], ligne["taille"]),
                         (self.ident, "images.tar", SHA, len(ARCHIVE)))
        self.assertIn("images.tar", self.b.g.etat(self.ident).message)
        self.assertIn(SHA, self.b.g.etat(self.ident).message)

    def test_course_inconnue(self):
        self.refus("R-inconnue", "images.tar", SHA, motif="inconnue")

    def test_course_pas_reussie(self):
        b = self.b
        autre = b.carte("autre", code="print(2)\n", slug="compte/autre", gpu=False, purgeables=["*.tar"])
        ident = b.g.soumettre(autre, "kaggle").course
        self.refus(ident, "images.tar", SHA, motif="REUSSIE")

    def test_fichier_absent(self):
        self.refus(self.ident, "absent.tar", SHA, motif="absent")

    def test_sha_different(self):
        self.refus(self.ident, "images.tar", "0" * 64, motif="SHA-256")
        self.assertTrue((self.sortie / "images.tar").exists())
        self.refus(self.ident, "images.tar", "pas-un-sha", motif="hexad")

    def test_hors_motif(self):
        self.refus(self.ident, "autre.txt", hashlib.sha256(b"x").hexdigest(), motif="artefacts_purgeables")
        self.refus(self.ident, "recu.json", hashlib.sha256(b"{}").hexdigest(), motif="artefacts_purgeables")
        self.assertTrue((self.sortie / "recu.json").exists())

    def test_sans_champ_rien_n_est_purgeable(self):
        carte = self.b.carte("nu", code="print(3)\n", slug="compte/nu", gpu=False)
        ident = self.b.g.soumettre(carte, "kaggle").course
        self.b.finir(self.b.kaggle, "compte/nu", {"recu.json": b"{}", "images.tar": ARCHIVE})
        self.refus(ident, "images.tar", SHA, motif="liste vide")

    def test_noms_dangereux(self):
        (self.sortie / "sous").mkdir()
        (self.sortie / "sous" / "x.tar").write_bytes(ARCHIVE)
        for nom in ("sous/x.tar", "../x.tar", "..", ".", "", "/etc/passwd.tar", "a\\b.tar"):
            self.refus(self.ident, nom, SHA, motif="nom refusé")
        self.assertTrue((self.sortie / "sous" / "x.tar").exists())

    def test_lien_symbolique(self):
        cible = self.b.maison / "ailleurs.tar"
        cible.write_bytes(ARCHIVE)
        (self.sortie / "lien.tar").symlink_to(cible)
        self.refus(self.ident, "lien.tar", SHA, motif="lien symbolique")
        self.assertTrue(cible.exists())

    def test_purge_non_rejouee(self):
        self.assertEqual(self.b.g.purger(self.ident, "images.tar", SHA).code, "OK")
        self.refus(self.ident, "images.tar", SHA, motif="déjà purgé")
        # même un fichier recréé avec le même contenu n'est pas purgé deux fois ni inscrit deux fois
        (self.sortie / "images.tar").write_bytes(ARCHIVE)
        self.refus(self.ident, "images.tar", SHA, motif="déjà purgé")
        self.assertEqual(self.b.g.c.execute("SELECT COUNT(*) FROM purges").fetchone()[0], 1)
        self.assertTrue((self.sortie / "images.tar").exists())

    def test_reconcilier_apres_purge(self):
        self.b.g.purger(self.ident, "images.tar", SHA)
        self.b.kaggle.rapatriement_casse = True  # un nouveau rapatriement échouerait bruyamment
        r = self.b.g.reconcilier()
        self.assertEqual(r.lignes, [])
        self.assertEqual(self.b.course(self.ident)["etat"], "REUSSIE")
        self.assertNotIn("manquant", self.b.course(self.ident)["detail"] or "")

    def test_reconcilier_ignore_une_course_purgee_meme_active(self):
        # défense en profondeur : une course portant une purge n'est jamais ré-examinée ni rapatriée
        self.b.g.c.execute("UPDATE courses SET etat = 'EN_COURS' WHERE id = ?", (self.ident,))
        self.b.kaggle.etats["compte/etude"] = Releve(Distant.TERMINEE)
        self.b.g.c.execute("INSERT INTO purges VALUES (?, 'images.tar', ?, 1, 0)", (self.ident, SHA))
        self.assertEqual(self.b.g.reconcilier().lignes, [])


class CartePurgeable(unittest.TestCase):
    def lire(self, ligne: str):
        b = Banc()
        try:
            chemin = b.carte("c", gpu=False)
            chemin.write_text(ligne + "\n" + chemin.read_text())
            return cartes.lire(chemin)
        finally:
            b.fermer()

    def test_valide(self):
        self.assertEqual(self.lire('artefacts_purgeables = ["*.tar", "img-?.zip"]').artefacts_purgeables,
                         ["*.tar", "img-?.zip"])
        self.assertEqual(self.lire("").artefacts_purgeables, [])

    def test_invalide(self):
        for ligne in ('artefacts_purgeables = ["a/*.tar"]', 'artefacts_purgeables = ["../x"]',
                      'artefacts_purgeables = ["/x"]', 'artefacts_purgeables = [""]',
                      'artefacts_purgeables = "*.tar"', "artefacts_purgeables = [1]"):
            with self.assertRaises(cartes.CarteInvalide, msg=ligne):
                self.lire(ligne)


if __name__ == "__main__":
    unittest.main()
