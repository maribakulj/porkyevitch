#!/usr/bin/env python3
"""Crochet PreToolUse sur Bash : un calcul passe par le guichet, pas directement par Kaggle ou Colab.

Bloque, avec la bonne commande en réponse :
- `kaggle kernels push` : un lancement direct contourne le registre des courses (doublons, budget, sorties) ;
- `colab new|run|exec` : idem pour Colab ;
- `guichet-agent …` dont la sortie passe dans un tube : le code de sortie (0, 2, 3, 4) est alors perdu, or c'est lui
  qui dit si la course est partie, refusée, en attente d'accord ou incertaine.

Ce n'est pas une frontière de sécurité (les identifiants, détenus par le compte du guichet, le sont) : il évite des
tours perdus à essayer, échouer, puis comprendre. La commande est découpée en segments (`;`, `&&`, `||`, `|`, retour
à la ligne) et chaque segment est lu mot à mot : citer `kaggle kernels push` dans un `grep` ou un texte n'est pas bloqué.

Entrée : le JSON de Claude Code sur stdin (`tool_input.command`). Sortie : code 2 et message sur stderr pour bloquer,
code 0 sinon. Une entrée illisible laisse passer : le crochet ne doit jamais empêcher le travail par erreur.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

_SEPARATEURS = re.compile(r"\|\||&&|[;\n&|]")
_PREFIXES = {"sudo", "env", "nice", "nohup", "time", "command", "exec", "caffeinate", "timeout", "gtimeout"}


def _segments(commande: str) -> list[tuple[list[str], bool]]:
    """(mots, suivi d'un tube) pour chaque segment ; les chaînes entre guillemets ne coupent pas."""
    sortie: list[tuple[list[str], bool]] = []
    lex = shlex.shlex(commande, posix=True, punctuation_chars=";&|\n")
    lex.whitespace_split = True
    lex.whitespace = " \t\r"
    mots: list[str] = []
    for jeton in lex:
        if _SEPARATEURS.fullmatch(jeton):
            sortie.append((mots, jeton == "|"))
            mots = []
        else:
            mots.append(jeton)
    sortie.append((mots, False))
    return sortie


def _programme(mots: list[str]) -> tuple[str, list[str]]:
    """Le programme réellement lancé et ses arguments, après les préfixes (sudo -u x, env A=b, nice -n 5…)."""
    i = 0
    while i < len(mots):
        m = mots[i]
        if "=" in m and not m.startswith("-"):  # affectation A=b en tête de commande
            i += 1
        elif os.path.basename(m) in _PREFIXES:
            i += 1
            while i < len(mots) and mots[i].startswith("-"):
                i += 2 if mots[i] in ("-u", "-g", "-n", "-c") else 1
            while i < len(mots) and "=" in mots[i] and not mots[i].startswith("-"):
                i += 1
        else:
            break
    if i >= len(mots):
        return "", []
    return os.path.basename(mots[i]), mots[i + 1:]


def verdict(commande: str) -> str | None:
    """Le motif de refus, ou None si la commande peut passer."""
    try:
        segments = _segments(commande)
    except ValueError:
        return None
    for mots, tube in segments:
        prog, args = _programme(mots)
        sans_options = [a for a in args if not a.startswith("-")]
        if prog == "kaggle" and sans_options[:2] == ["kernels", "push"]:
            return ("lancement direct refusé : un calcul Kaggle passe par le guichet, qui tient le registre des "
                    "courses (pas de doublon, budget GPU, sorties vérifiées). Soumets sa carte : "
                    "`sudo -u labo guichet-agent soumettre CARTE.toml --plateforme kaggle` (skill guichet).")
        if prog == "colab" and sans_options[:1] and sans_options[0] in ("new", "run", "exec"):
            return ("lancement direct refusé : un calcul Colab passe par le guichet. Soumets sa carte : "
                    "`sudo -u labo guichet-agent soumettre CARTE.toml --plateforme colab` (skill guichet).")
        if prog == "guichet-agent" and tube:
            return ("`guichet-agent` ne se lit pas à travers un tube : le code de sortie (0 lancé, 2 refus, 3 accord "
                    "requis, 4 incertain) serait perdu. Lance-le seul, puis lis `$?`.")
    return None


def main() -> int:
    try:
        entree = json.load(sys.stdin)
        commande = entree.get("tool_input", {}).get("command", "")
    except (ValueError, AttributeError):
        return 0
    if not isinstance(commande, str):
        return 0
    motif = verdict(commande)
    if motif:
        print(motif, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
