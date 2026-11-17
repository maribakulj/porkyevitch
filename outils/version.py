#!/usr/bin/env python3
"""La version du plugin monte-t-elle avec ses changements ?

Usage : python3 -I outils/version.py REF

REF est la révision de comparaison (la branche visée, ou le commit précédent). Si un fichier livré par le plugin a
changé depuis REF, la version de `.claude-plugin/plugin.json` doit différer de celle de REF : une version figée fige
aussi les projets qui ont installé le plugin, qui ne reçoivent alors aucune correction.
Code de sortie : 0 conforme, 1 version à monter, 2 usage.
"""

from __future__ import annotations

import json
import subprocess
import sys

LIVRE = (".claude-plugin/", "skills/", "agents/", "hooks/", "bin/", "labo/", "porky/", "gabarits/", "outils/")
MANIFESTE = ".claude-plugin/plugin.json"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    ref = argv[0]
    try:
        changes = [n for n in git("diff", "--name-only", ref, "HEAD").splitlines() if n.startswith(LIVRE)]
        avant = json.loads(git("show", f"{ref}:{MANIFESTE}"))["version"]
    except subprocess.CalledProcessError as e:
        print(f"révision {ref} illisible : {e.stderr.strip()}", file=sys.stderr)
        return 2
    apres = json.loads(open(MANIFESTE, encoding="utf-8").read())["version"]
    if changes and apres == avant:
        print(f"version {apres} inchangée alors que {len(changes)} fichier(s) livré(s) ont changé depuis {ref}, "
              f"par exemple {changes[0]} : monte la version dans {MANIFESTE}.")
        return 1
    print(f"version {avant} → {apres} ; {len(changes)} fichier(s) livré(s) changé(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
