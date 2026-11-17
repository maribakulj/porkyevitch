"""Crochet garde_calcul. Lancer : python3 -I hooks/tests/test_garde_calcul.py"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ICI))
from garde_calcul import verdict  # noqa: E402


class Bloque(unittest.TestCase):
    def test_lancements_directs(self):
        for c in ("kaggle kernels push -p noyau",
                  "cd noyau && kaggle kernels push -p . --accelerator NvidiaTeslaT4",
                  "~/venv/bin/kaggle kernels push -p .",
                  "nice -n 5 kaggle kernels push -p .",
                  "env KAGGLE_CONFIG_DIR=/x kaggle kernels push -p .",
                  "colab new -s mc --gpu T4",
                  "~/.local/bin/colab --auth=adc exec -s mc -f run.py",
                  "true; colab run notebook.ipynb"):
            self.assertIsNotNone(verdict(c), c)

    def test_guichet_agent_dans_un_tube(self):
        for c in ("sudo -u labo guichet-agent soumettre c.toml | tail -1",
                  "guichet-agent resume | grep R-"):
            self.assertIn("tube", verdict(c), c)


class Laisse(unittest.TestCase):
    def test_commandes_ordinaires_et_citations(self):
        for c in ("grep -rn 'kaggle kernels push' docs/",
                  'echo "ne lance jamais colab new toi-même"',
                  "kaggle kernels status compte/x",
                  "kaggle kernels output compte/x -p sortie",
                  "kaggle datasets version -p . -m maj",
                  "colab sessions",
                  "sudo -u labo guichet-agent soumettre carte.toml --plateforme kaggle",
                  "sudo -u labo guichet-agent reconcilier; echo $?",
                  "python3 -I labo/puissance.py --ic 0.02 0.14 --effet-plausible 0.05",
                  "ls | wc -l",
                  ""):
            self.assertIsNone(verdict(c), c)

    def test_entree_illisible_laisse_passer(self):
        self.assertIsNone(verdict("echo 'guillemet non fermé"))


class Processus(unittest.TestCase):
    def appeler(self, entree: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-I", str(ICI / "garde_calcul.py")], input=entree,
                              capture_output=True, text=True)

    def test_code_2_et_message_sur_stderr(self):
        r = self.appeler(json.dumps({"tool_name": "Bash", "tool_input": {"command": "kaggle kernels push -p ."}}))
        self.assertEqual(r.returncode, 2)
        self.assertIn("guichet", r.stderr)

    def test_code_0_sinon_et_sur_entree_invalide(self):
        self.assertEqual(self.appeler(json.dumps({"tool_input": {"command": "ls"}})).returncode, 0)
        self.assertEqual(self.appeler("pas du json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
