"""Lancer : python3 -I outils/tests/test_neutralite.py"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import neutralite  # noqa: E402


class Neutralite(unittest.TestCase):
    def examiner(self, texte: str, termes=()):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "note.md").write_text(texte)
            return neutralite.examiner(Path(tmp), list(termes))

    def test_traces_generiques(self):
        for texte in ("voir /Users/alice/projet", "écrire à alice@exemple.org", "suivant la D17",  # neutralite: ok
                      "relu par wA:p4", "dans /home/bob/data"):  # neutralite: ok
            self.assertTrue(self.examiner(texte), texte)

    def test_textes_neutres(self):
        for texte in ("git@github.com:org/depot.git", "/Users/Shared/sorties", "3D et 2D", "DINOv3, D4RL",
                      "le décodeur D", "/home/runner/work"):
            self.assertFalse(self.examiner(texte), texte)

    def test_termes_du_projet_insensibles_a_la_casse_et_au_mot_entier(self):
        self.assertTrue(self.examiner("le compte ProjetZ/noyau", ["projetz"]))
        self.assertFalse(self.examiner("projetzX n'est pas le terme", ["projetz"]))

    def test_exemption_explicite(self):
        self.assertFalse(self.examiner("exemple : /Users/alice  # neutralite: ok (exemple)"))


if __name__ == "__main__":
    unittest.main()
