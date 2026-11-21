"""Essai local complet du noyau : tout le programme, lancé comme sur la plateforme (`python run.py`), sur un faux dossier
d'entrées. À adapter avec le noyau (faux FICHIERS, petits paramètres) et à faire passer avant toute course.

Usage : python3 -I tests/test_essai_local.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

NOYAU = Path(__file__).resolve().parents[1] / "run.py"


def lancer(racine: Path, parametres: dict | None = None, fichier=NOYAU):
    """Lance le noyau dans un processus neuf, avec les variables que posent le guichet et la plateforme."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GUICHET_")}
    env.update(GUICHET_ENTREES=str(racine / "entrees"), GUICHET_SORTIE=str(racine / "sortie"))
    if parametres is not None:
        env["GUICHET_PARAMETRES"] = json.dumps(parametres)
    return subprocess.run([sys.executable, "-I", str(fichier)], env=env, capture_output=True, text=True)


class EssaiLocal(unittest.TestCase):
    def monde(self, t: str, contenu: str = "un\ndeux\ntrois\n") -> Path:
        racine = Path(t)
        (racine / "entrees" / "jeu-exemple").mkdir(parents=True)
        (racine / "entrees" / "jeu-exemple" / "exemple.txt").write_text(contenu)
        return racine

    def etapes(self, racine: Path) -> list[str]:
        return [json.loads(l)["etape"] for l in (racine / "sortie" / "etapes.jsonl").read_text().splitlines()
                if l.startswith("{")]

    def test_programme_entier_avec_parametres(self):
        with tempfile.TemporaryDirectory() as t:
            racine = self.monde(t)
            r = lancer(racine, {"LIMITE": 2})
            self.assertEqual(r.returncode, 0, r.stderr)
            recu = json.loads((racine / "sortie" / "recu.json").read_text())
            self.assertEqual((recu["lignes"], recu["parametres"]), (2, {"LIMITE": 2}))
            self.assertEqual(self.etapes(racine), ["debut", "entrees", "fin"])

    def test_entree_alteree_arrete_la_course_avec_un_repere(self):
        with tempfile.TemporaryDirectory() as t:
            racine = self.monde(t, contenu="autre chose\n")
            r = lancer(racine)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(self.etapes(racine)[-1], "erreur")
            self.assertFalse((racine / "sortie" / "recu.json").exists())

    def test_parametres_injectes_par_le_guichet(self):
        """Le noyau lit aussi les paramètres posés par la ligne qu'injecte le guichet (sans variable d'environnement)."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "labo" / "guichet"))
        from guichet import arbre
        with tempfile.TemporaryDirectory() as t:
            racine = self.monde(t)
            copie = racine / "run.py"
            copie.write_text(NOYAU.read_text())
            arbre.injecter_parametres(copie, json.dumps({"LIMITE": 1}))
            r = lancer(racine, None, copie)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads((racine / "sortie" / "recu.json").read_text())["lignes"], 1)


if __name__ == "__main__":
    unittest.main()
