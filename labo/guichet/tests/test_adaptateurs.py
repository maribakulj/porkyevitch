"""Adaptateurs Kaggle et Colab contre de faux CLI. Lancer : python3 -I tests/test_adaptateurs.py

Les faux CLI imitent les sorties des vrais (formats relevés à l'usage et dans porky/colab.py). Le faux Colab
exécute réellement la chaîne que le guichet envoie, en remplaçant /content par un dossier temporaire : l'assemblage des
morceaux, l'extraction, le calcul, l'archive de sortie et le rapatriement sont donc exercés de bout en bout.
Ce que ces tests ne prouvent pas : que les vrais CLI répondent encore dans ces formats.
"""

import json
import os
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from outils import Banc  # noqa: E402

from guichet.plateformes import Colab, Distant, Kaggle  # noqa: E402

FAUX_KAGGLE = textwrap.dedent("""\
    import json, os, sys
    etat = os.environ["HOME"] + "/faux-kaggle"
    os.makedirs(etat, exist_ok=True)
    open(etat + "/appels", "a").write(json.dumps({"argv": sys.argv[1:], "env": sorted(os.environ)}) + "\\n")
    a = sys.argv[1:]
    if a[:2] == ["kernels", "push"]:
        print("Kernel version 3 successfully pushed.  Please check progress at https://www.kaggle.com/code/x")
    elif a[:2] == ["kernels", "status"]:
        print(open(etat + "/statut").read() if os.path.exists(etat + "/statut") else "404 - Not Found")
    elif a[:2] == ["kernels", "output"]:
        dest = a[a.index("-p") + 1]
        open(os.path.join(dest, "recu.json"), "w").write("{}")
        print("Output file downloaded to " + dest)
""")

FAUX_COLAB = textwrap.dedent("""\
    import os, shutil, subprocess, sys
    racine = os.environ["HOME"] + "/faux-colab"
    a = [x for x in sys.argv[1:] if x != "--auth=adc"]
    def chemin(session, distant):
        return os.path.join(racine, session, distant.lstrip("/"))
    cmd = a[0]
    if cmd == "new":
        os.makedirs(os.path.join(racine, a[2], "content"), exist_ok=True)
        print("Session READY")
    elif cmd == "sessions":
        for s in (os.listdir(racine) if os.path.isdir(racine) else []):
            print(f"[{s}] T4")
    elif cmd == "upload":
        dest = chemin(a[2], a[4]); os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy(a[3], dest); print("Uploaded")
    elif cmd == "download":
        src = chemin(a[2], a[3])
        if os.path.exists(src):
            shutil.copy(src, a[4]); print("Downloaded")
        else:
            print("No such file")
    elif cmd == "exec":
        code = sys.stdin.read().replace("/content", os.path.join(racine, a[2], "content"))
        subprocess.run([sys.executable, "-c", code])
    elif cmd == "stop":
        shutil.rmtree(os.path.join(racine, a[2]), ignore_errors=True)
""")


def ecrire_cli(dossier: Path, nom: str, source: str) -> str:
    p = dossier / nom
    p.write_text(f"#!{sys.executable}\n" + source)
    p.chmod(0o755)
    return str(p)


class AdaptateurKaggle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.maison = Path(self.tmp.name)
        self.k = Kaggle(ecrire_cli(self.maison, "kaggle", FAUX_KAGGLE), self.maison)

    def tearDown(self):
        self.tmp.cleanup()

    def test_push_lit_la_version_et_n_herite_rien(self):
        b = Banc()
        try:
            carte_chemin = b.carte()
            from guichet import carte as cartes
            c = cartes.lire(carte_chemin)
            os.environ["KAGGLE_KEY"] = "fuite"  # une variable de l'appelant ne doit pas passer
            try:
                slug, version = self.k.lancer(c.dossier, c, "R-1")
            finally:
                del os.environ["KAGGLE_KEY"]
            self.assertEqual((slug, version), ("compte/calcul", "3"))
            appel = json.loads((self.maison / "faux-kaggle" / "appels").read_text().splitlines()[0])
            self.assertNotIn("KAGGLE_KEY", appel["env"])
            self.assertEqual(appel["argv"][:3], ["kernels", "push", "-p"])
        finally:
            b.fermer()

    def test_cli_absent_rien_n_est_parti(self):
        b = Banc()
        try:
            b.g.plateformes["kaggle"] = Kaggle(str(self.maison / "pas-de-cli"), self.maison)
            carte = b.carte()
            r = b.g.soumettre(carte, "kaggle")
            self.assertEqual(r.code, "REFUS")
            self.assertEqual(b.g.c.execute("SELECT etat FROM courses").fetchone()["etat"], "REFUSEE")
            b.g.plateformes["kaggle"] = Kaggle(ecrire_cli(self.maison, "kaggle", FAUX_KAGGLE), self.maison)
            self.assertEqual(b.g.soumettre(carte, "kaggle").code, "ACCEPTEE")  # pas de motif exigé : rien n'avait tourné
            self.assertIs(b.g.plateformes["kaggle"].etat("compte/x", "1").etat, Distant.INCONNU)
        finally:
            b.fermer()

    def test_statut_absent_est_inconnu(self):
        self.assertIs(self.k.etat("compte/x", "3").etat, Distant.INCONNU)

    def test_statut_et_sortie(self):
        (self.maison / "faux-kaggle").mkdir(exist_ok=True)
        (self.maison / "faux-kaggle" / "statut").write_text('compte/x has status "KernelWorkerStatus.COMPLETE"')
        self.assertIs(self.k.etat("compte/x", "3").etat, Distant.TERMINEE)
        dest = self.maison / "sortie"
        self.k.rapatrier("compte/x", "3", dest)
        self.assertTrue((dest / "recu.json").exists())


class AdaptateurColab(unittest.TestCase):
    def test_de_bout_en_bout_par_le_guichet(self):
        b = Banc()
        try:
            cli = ecrire_cli(b.maison, "colab", FAUX_COLAB)
            b.g.plateformes["colab"] = Colab(cli, b.maison)
            code = ("import os, json\n"
                    "s = os.environ['GUICHET_SORTIE']\n"
                    "os.makedirs(s + '/etats', exist_ok=True)\n"
                    "json.dump({'ok': 1}, open(s + '/recu.json', 'w'))\n"
                    "open(s + '/etats/t0.pt', 'wb').write(b'poids')\n")
            carte = b.carte(code=code, artefacts=("recu.json", "etats/*.pt"))
            r = b.g.soumettre(carte, "colab")
            self.assertEqual(r.code, "ACCEPTEE", r.message)
            for _ in range(100):
                b.g.reconcilier()
                if b.course(r.course)["etat"] not in ("EN_FILE", "EN_COURS"):
                    break
                time.sleep(0.1)
            course = b.course(r.course)
            self.assertEqual(course["etat"], "REUSSIE", course["detail"])
            self.assertEqual((Path(course["sortie"]) / "etats" / "t0.pt").read_bytes(), b"poids")
            self.assertTrue((Path(course["sortie"]) / "calcul.log").exists())  # le journal revient avec la sortie
            self.assertFalse((b.maison / "faux-colab" / course["slug"]).exists())  # machine arrêtée
        finally:
            b.fermer()

    def test_echec_du_calcul_rapporte_et_journal_rapatrie(self):
        b = Banc()
        try:
            b.g.plateformes["colab"] = Colab(ecrire_cli(b.maison, "colab", FAUX_COLAB), b.maison)
            r = b.g.soumettre(b.carte(code="raise SystemExit('perte NaN')\n"), "colab")
            for _ in range(100):
                b.g.reconcilier()
                if b.course(r.course)["etat"] not in ("EN_FILE", "EN_COURS"):
                    break
                time.sleep(0.1)
            course = b.course(r.course)
            self.assertEqual(course["etat"], "ECHOUEE")
            self.assertIn("perte NaN", (Path(course["sortie"]) / "calcul.log").read_text())
        finally:
            b.fermer()


if __name__ == "__main__":
    unittest.main()
