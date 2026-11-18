"""Tests de rejouer.py et temoin.py. Lancer : python3 -I labo/regle/tests/test_regle.py"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
import rejouer  # noqa: E402
import temoin  # noqa: E402

REGLE = '''
CONCLUSIFS = {"conclut"}

def issue(recu):
    ic = recu["ic"]
    if ic[1] - ic[0] > 0.2:
        return {"statut": "imprecis", "motifs": ["IC trop large"]}
    return {"statut": "conclut" if recu["x"] > 0.5 else "non_concluante", "motifs": []}
'''


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.regle = self.d / "regle.py"
        self.regle.write_text(REGLE, encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def json(self, nom, obj):
        p = self.d / nom
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p


class Rejouer(Base):
    def test_cas_qui_passe_et_ecrit_l_issue(self):
        recu = self.json("recu.json", {"x": 0.9, "ic": [0.8, 0.95]})
        self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu), "--attendu", "conclut"]), 0)
        ecrit = json.loads((self.d / "issue-recalculee.json").read_text())
        self.assertEqual(ecrit["issue"]["statut"], "conclut")
        self.assertEqual(ecrit["recu"]["sha256"], rejouer.sha256(recu))
        self.assertEqual(ecrit["regle"]["sha256"], rejouer.sha256(self.regle))

    def test_cas_qui_echoue_sort_1(self):
        recu = self.json("recu.json", {"x": 0.1, "ic": [0.0, 0.1]})
        self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu), "--attendu", "conclut"]), 1)
        self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu)]), 0)  # sans attendu

    def test_empreintes_et_octets_stables(self):
        recu = self.json("recu.json", {"x": 0.9, "ic": [0.8, 0.95]})
        sortie = self.d / "o"
        rejouer.main(["--regle", str(self.regle), "--recu", str(recu), "--sortie", str(sortie)])
        a = (sortie / "issue-recalculee.json").read_bytes()
        rejouer.main(["--regle", str(self.regle), "--recu", str(recu), "--sortie", str(sortie)])
        self.assertEqual(a, (sortie / "issue-recalculee.json").read_bytes())
        self.regle.write_text(REGLE + "\n# commentaire\n", encoding="utf-8")       # un octet de règle change l'empreinte
        rejouer.main(["--regle", str(self.regle), "--recu", str(recu), "--sortie", str(sortie)])
        self.assertNotEqual(a, (sortie / "issue-recalculee.json").read_bytes())
        self.assertNotIn(str(self.d), a.decode())                                  # aucun chemin absolu

    def test_import_du_noyau_ou_hors_stdlib_refuse(self):
        recu = self.json("recu.json", {"x": 1, "ic": [0, 0]})
        for imp in ("import noyau.pipeline", "from noyau import carte_erreurs", "import numpy", "from . import x"):
            self.regle.write_text(imp + "\n" + REGLE, encoding="utf-8")
            self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu)]), 2, imp)
        self.regle.write_text("import json, math\n" + REGLE, encoding="utf-8")
        self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu)]), 0)

    def test_issue_mal_formee_ou_regle_sans_issue(self):
        recu = self.json("recu.json", {})
        self.regle.write_text("def issue(r):\n    return {'statut': 1}\n", encoding="utf-8")
        self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu)]), 2)
        self.regle.write_text("x = 1\n", encoding="utf-8")
        self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu)]), 2)

    def test_complement_lu_sous_complements(self):
        self.regle.write_text("def issue(r):\n    return {'statut': str(r['complements']['c']['v']), 'motifs': []}\n",
                              encoding="utf-8")
        recu = self.json("recu.json", {})
        c = self.json("c.json", {"v": 7})
        self.assertEqual(rejouer.main(["--regle", str(self.regle), "--recu", str(recu),
                                       "--complement", f"c={c}", "--attendu", "7"]), 0)
        ecrit = json.loads((self.d / "issue-recalculee.json").read_text())
        self.assertEqual(ecrit["complements"]["c"]["sha256"], rejouer.sha256(c))


class Temoin(Base):
    def dossier(self, **cas):
        t = self.d / "temoins"
        t.mkdir(exist_ok=True)
        for nom, obj in cas.items():
            (t / f"{nom}.json").write_text(json.dumps(obj), encoding="utf-8")
        return t

    def test_temoins_qui_ne_passent_pas(self):
        t = self.dossier(
            nul={"doit_conclure": False, "recu": {"x": 0.1, "ic": [0.0, 0.1]}},
            imprecis={"doit_conclure": False, "recu": {"x": 0.9, "ic": [0.0, 0.9]}})
        self.assertEqual(temoin.main(["--regle", str(self.regle), "--recus-temoins", str(t)]), 0)
        ecrit = json.loads((self.d / "controle-temoin.json").read_text())
        self.assertEqual(ecrit["temoins_qui_passent"], [])
        self.assertEqual([r["statut_obtenu"] for r in ecrit["temoins"]], ["imprecis", "non_concluante"])

    def test_temoin_qui_passe_est_nomme_et_sort_1(self):
        t = self.dossier(
            bon={"doit_conclure": False, "recu": {"x": 0.1, "ic": [0.0, 0.1]}},
            mauvais={"doit_conclure": False, "recu": {"x": 0.9, "ic": [0.8, 0.9]}})
        self.assertEqual(temoin.main(["--regle", str(self.regle), "--recus-temoins", str(t)]), 1)
        ecrit = json.loads((self.d / "controle-temoin.json").read_text())
        self.assertEqual(ecrit["temoins_qui_passent"], ["mauvais"])

    def test_issues_interdites_explicites_et_empreintes_stables(self):
        t = self.dossier(a={"doit_conclure": False, "issues_interdites": ["non_concluante"],
                            "recu": {"x": 0.1, "ic": [0.0, 0.1]}})
        self.assertEqual(temoin.main(["--regle", str(self.regle), "--recus-temoins", str(t)]), 1)
        a = (self.d / "controle-temoin.json").read_bytes()
        temoin.main(["--regle", str(self.regle), "--recus-temoins", str(t)])
        self.assertEqual(a, (self.d / "controle-temoin.json").read_bytes())
        r = json.loads(a)
        self.assertEqual(r["temoins"][0]["sha256"], rejouer.sha256(t / "a.json"))
        self.assertEqual(r["regle"]["sha256"], rejouer.sha256(self.regle))

    def test_erreurs_d_usage(self):
        vide = self.d / "temoins"
        vide.mkdir()
        self.assertEqual(temoin.main(["--regle", str(self.regle), "--recus-temoins", str(vide)]), 2)
        (vide / "x.json").write_text(json.dumps({"recu": {}}), encoding="utf-8")
        self.assertEqual(temoin.main(["--regle", str(self.regle), "--recus-temoins", str(vide)]), 2)


if __name__ == "__main__":
    unittest.main()
