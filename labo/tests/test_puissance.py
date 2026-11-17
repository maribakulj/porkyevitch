"""Lancer : python3 -I labo/tests/test_puissance.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import puissance as pu  # noqa: E402


class Puissance(unittest.TestCase):
    def test_erreur_type_depuis_un_ic95(self):
        self.assertAlmostEqual(pu.se_depuis_ic(-1.96, 1.96), 1.0, places=3)

    def test_effet_minimal_classique(self):
        # α = 5 % bilatéral, 80 % : 2,80 erreurs-types.
        self.assertAlmostEqual(pu.effet_minimal(1.0), 2.80, places=2)

    def test_puissance_a_l_effet_minimal_vaut_la_cible(self):
        se = 0.01
        self.assertAlmostEqual(pu.puissance(pu.effet_minimal(se, cible=0.8), se), 0.8, places=6)

    def test_petit_banc_et_petit_effet_ne_peut_pas_conclure(self):
        # Un IC de ±0,03 sur 300 images, pour un gain plausible de 0,003 : aucune chance.
        b = pu.bilan(pu.se_depuis_ic(-0.034, 0.0205), 0.003)
        self.assertEqual(b.code, 2)
        self.assertLess(b.puissance, 0.1)
        self.assertGreater(b.facteur, 100)  # il faudrait plus de cent fois l'effectif

    def test_famille_et_regle_unilaterale_durcissent(self):
        se = 0.0037  # demi-largeur à 99,29 % unilatéral ≈ 0,009
        seul = pu.puissance(0.009, se, unilateral=True)
        famille = pu.puissance(0.009, se, famille=7, unilateral=True)
        self.assertLess(famille, seul)
        self.assertEqual(pu.bilan(se, 0.0026, famille=7, unilateral=True).code, 2)

    def test_effet_bien_au_dessus_peut_conclure(self):
        self.assertEqual(pu.bilan(0.005, 0.03).code, 0)

    def test_cli_code_de_sortie(self):
        self.assertEqual(pu.main(["--ic", "-0.034", "0.0205", "--effet-plausible", "0.003"]), 2)
        self.assertEqual(pu.main(["--se", "0.005", "--effet-plausible", "0.03"]), 0)
        # quadrupler l'effectif divise l'erreur-type par deux
        self.assertEqual(pu.main(["--se", "0.02", "--n", "300:1200", "--effet-plausible", "0.03"]), 0)


if __name__ == "__main__":
    unittest.main()
