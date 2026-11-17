"""Le graphe de recherche, sur des données synthétiques. Lancer : python3 -I labo/graphe/tests/test_graphe.py

Demande rdflib et pyshacl ; sans eux, les tests sont sautés (le graphe est un outil facultatif).
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
try:
    import graphe
    import verdict
    import pyshacl  # noqa: F401
    DISPO = True
except ImportError:
    DISPO = False

H64 = "ab" * 32
IDEES = "id;idée;source;thème;priorité;dépendances\nI1;Une idée sourcée;article A;t1;P1;\nI2;Une autre;;t2;P2;I1, I9\n"
NOTATION = "id;elimine;motif;doublon_de;G;justification\nI1;non;;;3;garder\nI2;oui;sans_decision;I1;;redondante\n"
CARTE = """# Carte de recherche — essai A

## 1. Décision

Une règle.

```toml recherche
decision = "borne haute sous 0,02 : réfutée ; sinon non concluant"
premisse = "verifiee"
[puissance]
se = 0.005
effet_plausible = 0.05
famille = 1
```
"""
CARTE_FAIBLE = CARTE.replace("se = 0.005", "se = 0.05").replace("essai A", "essai B")
CARTE_CALCUL = 'experience = "essai"\ncarte_recherche = "recherche.md"\n'
CONFIG = """
[projet]
racine = ".."
[sortie]
graphe = "graphe.ttl"
rapports = "rapports"
[idees]
fichier = "sources/idees.csv"
[idees.colonnes]
identifiant = "id"
description = "idée"
source = "source"
theme = "thème"
priorite = "priorité"
dependances = "dépendances"
[[notations]]
fichier = "sources/n1.csv"
notateur = "notateur-1"
scores = ["G"]
[cartes]
motifs = ["experiences/*/recherche.md"]
[calculs]
motifs = ["experiences/*/carte.toml"]
[guichet]
export = "sources/guichet.json"
[jugements]
hypotheses = "jugements/hypotheses.toml"
verdicts = "jugements/verdicts.toml"
"""
HYPOTHESES = """
[[hypothese]]
id = "H-A"
idee = "I1"
description = "Le bras testé gagne au moins 0,02."
mesure = "Différence de M."
effet_minimal = 0.02
carte = "a"
auteur = "orchestrateur"
[[hypothese.premisse]]
id = "P-A"
description = "Chaque classe a assez d'exemples."

[[hypothese]]
id = "H-B"
idee = "I2"
description = "Variante sous-puissante."
mesure = "Différence de M."
effet_minimal = 0.02
carte = "b"
auteur = "orchestrateur"
[[hypothese.premisse]]
id = "P-B"
description = "Une prémisse."
"""


def git(d, *a):
    subprocess.run(["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@t.t", *a], check=True,
                   capture_output=True)


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Graphe(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        for rel, txt in {
            "graphe/config.toml": CONFIG, "graphe/sources/idees.csv": IDEES, "graphe/sources/n1.csv": NOTATION,
            "graphe/jugements/hypotheses.toml": HYPOTHESES,
            "experiences/a/recherche.md": CARTE, "experiences/a/carte.toml": CARTE_CALCUL,
            "experiences/b/recherche.md": CARTE_FAIBLE,
        }.items():
            p = self.d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt, encoding="utf-8")
        git(self.d, "init", "-q")
        git(self.d, "add", "-A")
        git(self.d, "commit", "-q", "-m", "départ")
        self.cfg = graphe.Config(self.d / "graphe" / "config.toml")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def export(self, etat="REUSSIE"):
        (self.d / "graphe/sources/guichet.json").write_text(json.dumps({"courses": [{
            "id": "R-1", "cle": hashlib.sha256(b"k").hexdigest(), "etat": etat, "carte_calcul": "a",
            "debut": "2999-01-01T00:00:00Z", "fin": "2999-01-01T01:00:00Z",
            "artefacts": [{"nom": "recu.json", "sha256": H64}]}]}), encoding="utf-8")
        # le fichier d'export n'est pas une carte : il n'a pas besoin d'être commité

    def verdict(self, *args):
        return verdict.main(["--config", str(self.d / "graphe/config.toml"), *args])

    def test_construction_valide_et_deterministe(self):
        g, avert = graphe.construire(self.cfg)
        self.assertEqual(graphe.violations(g), [])
        n = graphe.compter(g)
        self.assertEqual((n["Idee"], n["Hypothese"], n["Premisse"], n["CarteRecherche"], n["CarteCalcul"]), (2, 2, 2, 2, 1))
        self.assertEqual(n["Course"], 0)
        self.assertTrue(any("emplacement prévu" in a for a in avert))   # export du guichet absent : dit, pas inventé
        self.assertTrue(any("dépendance" in a for a in avert))          # I9 n'existe pas
        graphe.ecrire(g, self.d / "1.ttl")
        graphe.ecrire(graphe.construire(self.cfg)[0], self.d / "2.ttl")
        self.assertEqual((self.d / "1.ttl").read_bytes(), (self.d / "2.ttl").read_bytes())

    def test_puissance_recalculee_pas_recopiee(self):
        g, _ = graphe.construire(self.cfg)
        cr = graphe.URIRef(self.cfg.espace + "CR-a")
        self.assertGreater(float(g.value(cr, graphe.LAB.puissance)), 0.99)
        cr = graphe.URIRef(self.cfg.espace + "CR-b")
        self.assertLess(float(g.value(cr, graphe.LAB.puissance)), 0.5)

    def test_source_absente(self):
        (self.d / "graphe/sources/idees.csv").unlink()
        with self.assertRaises(graphe.ErreurContenu):
            graphe.construire(self.cfg)

    def test_carte_modifiee_sans_date(self):
        (self.d / "experiences/a/recherche.md").write_text(CARTE + "\nmodifiée\n", encoding="utf-8")
        g, avert = graphe.construire(self.cfg)
        self.assertTrue(any("sans date" in a for a in avert))
        self.assertNotEqual(graphe.violations(g), [])   # une carte sans date n'est pas une préinscription

    def test_non_concluante_acceptee_sans_resultat(self):
        self.assertEqual(self.verdict("H-A", "non-concluante", "--auteur", "orchestrateur", "--condition", "jeu J",
                                      "--course", "R-1"), 1)  # fondement sur une course inconnue : refusé
        self.assertEqual(self.verdict("H-A", "non-testee", "--auteur", "orchestrateur"), 0)

    def test_refutee_refusee_sans_puissance_puis_acceptee(self):
        self.export()
        # carte sous-puissante (H-B n'a pas de course) : refus
        self.assertEqual(self.verdict("H-B", "refutee", "--auteur", "orchestrateur", "--condition", "jeu J",
                                      "--course", "R-1", "--artefact", "recu.json", "--valeur", "0.004",
                                      "--ic-bas", "-0.006", "--ic-haut", "0.014"), 1)
        # IC qui n'exclut pas l'effet minimal : refus
        self.assertEqual(self.verdict("H-A", "refutee", "--auteur", "orchestrateur", "--condition", "jeu J",
                                      "--course", "R-1", "--artefact", "recu.json", "--valeur", "0.01",
                                      "--ic-bas", "-0.01", "--ic-haut", "0.03"), 1)
        self.assertFalse((self.d / "graphe/jugements/verdicts.toml").exists())
        # carte confirmatoire, prémisse vérifiée, puissance 1, IC sous 0,02 : accepté
        self.assertEqual(self.verdict("H-A", "refutee", "--auteur", "orchestrateur", "--condition", "jeu J",
                                      "--course", "R-1", "--artefact", "recu.json", "--valeur", "0.004",
                                      "--ic-bas", "-0.006", "--ic-haut", "0.014"), 0)
        g = graphe.Graph().parse(self.d / "graphe/graphe.ttl")
        self.assertEqual(graphe.violations(g), [])
        self.assertEqual(len(list(g.subject_objects(graphe.LAB.refuteIci))), 1)   # dérivé, jamais écrit à la main

    def test_course_avant_la_carte_n_est_pas_une_preinscription(self):
        self.export()
        p = self.d / "graphe/sources/guichet.json"
        p.write_text(p.read_text(encoding="utf-8").replace("2999-01-01T00:00:00Z", "2000-01-01T00:00:00Z"), encoding="utf-8")
        self.assertEqual(self.verdict("H-A", "non-concluante", "--auteur", "orchestrateur", "--condition", "jeu J",
                                      "--course", "R-1", "--artefact", "recu.json", "--valeur", "0.0",
                                      "--ic-bas", "-0.1", "--ic-haut", "0.1"), 1)

    def test_soutenue_sans_resultat_refusee(self):
        self.assertEqual(self.verdict("H-A", "soutenue", "--auteur", "orchestrateur", "--condition", "jeu J"), 1)

    def test_resultat_d_une_course_echouee_refuse(self):
        self.export("ECHOUEE")
        self.assertEqual(self.verdict("H-A", "non-concluante", "--auteur", "orchestrateur", "--condition", "jeu J",
                                      "--course", "R-1", "--artefact", "recu.json", "--valeur", "0.0",
                                      "--ic-bas", "-0.1", "--ic-haut", "0.1"), 1)
        self.assertEqual(self.verdict("H-A", "test-invalide", "--auteur", "orchestrateur", "--condition", "jeu J",
                                      "--course", "R-1"), 0)   # une course échouée justifie « test invalide »

    def test_test_invalide_sans_motif_refuse(self):
        self.assertEqual(self.verdict("H-A", "test-invalide", "--auteur", "orchestrateur", "--condition", "x"), 1)
        self.assertEqual(self.verdict("H-A", "test-invalide", "--auteur", "orchestrateur", "--condition", "x",
                                      "--motif-invalidite", "contrôle direct manqué"), 0)

    def test_suspendue_exige_la_condition_de_reouverture(self):
        self.assertEqual(self.verdict("H-A", "suspendue", "--auteur", "orchestrateur"), 1)
        self.assertEqual(self.verdict("H-A", "suspendue", "--auteur", "orchestrateur", "--reouvrir-si",
                                      "un regard humain devient disponible"), 0)

    def test_hypothese_inconnue(self):
        self.assertEqual(self.verdict("H-Z", "non-testee", "--auteur", "orchestrateur"), 1)

    def test_rapport_et_interpretation_conservee(self):
        self.verdict("H-A", "non-testee", "--auteur", "orchestrateur")
        g = graphe.Graph().parse(self.d / "graphe/graphe.ttl")
        chemin = graphe.ecrire_rapport(g, "H-A", self.cfg)
        txt = chemin.read_text(encoding="utf-8")
        for rubrique in ("D'où vient l'idée", "Prémisse", "carte de recherche", "courses", "Résultats", "rouvrir", "Décision"):
            self.assertIn(rubrique, txt)
        self.assertIn("article A", txt)
        self.assertIn("non testée", txt)
        chemin.write_text(txt + "Mon interprétation.\n", encoding="utf-8")
        graphe.ecrire_rapport(g, "H-A", self.cfg)
        self.assertIn("Mon interprétation.", chemin.read_text(encoding="utf-8"))
        with self.assertRaises(graphe.ErreurContenu):
            graphe.rapport(g, "H-Z", self.cfg)

    def test_ligne_de_commande(self):
        c = str(self.d / "graphe/config.toml")
        self.assertEqual(graphe.main(["--config", c, "valider"]), 2)       # pas encore construit
        self.assertEqual(graphe.main(["--config", c, "construire"]), 0)
        self.assertEqual(graphe.main(["--config", c, "valider"]), 0)
        self.assertEqual(graphe.main(["--config", c, "compter"]), 0)
        self.assertEqual(graphe.main(["--config", c, "rapport", "H-A"]), 0)


@unittest.skipUnless(DISPO, "rdflib et pyshacl absents")
class Formes(unittest.TestCase):
    def test_les_douze_regles_et_la_suspension(self):
        texte = (ICI.parent / "formes.ttl").read_text(encoding="utf-8")
        for r in range(13):
            self.assertIn(f"# R{r} ", texte)

    def test_six_statuts(self):
        g = graphe.Graph().parse(ICI.parent / "vocab.ttl")
        statuts = set(g.subjects(graphe.SKOS.inScheme, graphe.LAB.statuts))
        self.assertEqual(len(statuts), 6)


if __name__ == "__main__":
    unittest.main()
