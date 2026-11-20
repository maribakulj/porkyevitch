"""Deux portes en ligne de commande.

- `guichet-agent` : ce que l'agent peut faire (soumettre, suivre, demander une bascule, annuler, purger un artefact, lire le résumé).
  Il l'appelle par `sudo -u labo guichet-agent …`, seule commande que sudoers lui permet sous ce compte.
- `guichet` : tout, y compris approuver, refuser, trancher et ouvrir un sprint. L'humain l'appelle par `sudo -u labo guichet …`, et
  sudoers exige son mot de passe à chaque fois (`timestamp_timeout=0`). C'est ce mot de passe, que l'agent n'a pas,
  qui sépare les deux portes : l'agent et l'humain partagent le même compte Unix.

Codes de sortie : 0 accepté ou fait, 2 refus, 3 accord humain requis, 4 état incertain. Ne jamais passer cette
commande dans un tube : le code de sortie deviendrait celui de la dernière commande du tube.
"""

from __future__ import annotations

import argparse
import os
import pwd
import sys
from pathlib import Path

from .guichet import Config, Guichet
from .plateformes import Colab, Kaggle


def maison() -> Path:
    # Le compte effectif, jamais $HOME : sous sudo, HOME peut rester celui de l'appelant.
    return Path(pwd.getpwuid(os.geteuid()).pw_dir)


def verifier_compte() -> str | None:
    """L'installation écrit le nom du compte du guichet à côté du code. Lancé sous un autre compte, le guichet
    ouvrirait un registre vide et n'aurait pas les identifiants : on refuse plutôt que de faire semblant."""
    fichier = Path(__file__).resolve().parents[1] / "compte.txt"
    if not fichier.exists():
        return None
    attendu = fichier.read_text().strip()
    reel = pwd.getpwuid(os.geteuid()).pw_name
    if reel != attendu:
        return f"[REFUS] le guichet tourne sous le compte {attendu}, pas {reel} : `sudo -u {attendu} …`"
    return None


def construire(racine: Path | None = None) -> Guichet:
    m = maison()
    racine = racine or m / "guichet"
    config = Config.lire(racine / "config.toml")
    plateformes = {"kaggle": Kaggle(config.kaggle_cli, m)}
    colab_cli = config.colab_cli or str(m / ".local/bin/colab")
    if Path(colab_cli).exists():
        plateformes["colab"] = Colab(colab_cli, m)
    return Guichet(racine, config, plateformes, maison_protegee=m)


def _commun(sous) -> None:
    s = sous.add_parser("soumettre", help="demander une course pour une carte")
    s.add_argument("carte", type=Path)
    s.add_argument("--plateforme", choices=("kaggle", "colab"))
    s.add_argument("--motif", help="relance d'un calcul identique qui a échoué : la cause extérieure")
    s.add_argument("--replication", metavar="MOTIF", help="refaire un calcul réussi : pourquoi (accord humain)")
    sous.add_parser("reconcilier", help="relever l'état distant de toutes les courses suivies")
    sous.add_parser("resume", help="budget, demandes, courses suivies, fins des dernières 24 h")
    e = sous.add_parser("etat", help="une course")
    e.add_argument("course")
    b = sous.add_parser("demander-bascule", help="changer de plateforme une course EN_FILE")
    b.add_argument("course")
    b.add_argument("--vers", required=True, choices=("kaggle", "colab"))
    b.add_argument("--motif", required=True)
    a = sous.add_parser("annuler", help="annuler une course active (Colab seulement)")
    a.add_argument("course")
    pu = sous.add_parser("purger", help="supprimer un artefact purgeable de la sortie d'une course REUSSIE")
    pu.add_argument("course")
    pu.add_argument("nom")
    pu.add_argument("--sha256", required=True, metavar="HEX")


def _humain(sous) -> None:
    a = sous.add_parser("approuver", help="accorder une demande et lancer")
    a.add_argument("demande")
    r = sous.add_parser("refuser")
    r.add_argument("demande")
    r.add_argument("--motif", required=True)
    t = sous.add_parser("trancher", help="fixer l'état d'une course après vérification sur le site")
    t.add_argument("course")
    t.add_argument("etat")
    t.add_argument("--motif", required=True)
    t.add_argument("--version")
    sp = sous.add_parser("sprint", help="ouvrir un sprint de construction (sans chantier : l'arrêter)")
    sp.add_argument("chantiers", nargs="*")
    sp.add_argument("--jusqu-au", dest="fin", metavar="AAAA-MM-JJ")


def executer(args, g: Guichet):
    match args.cmd:
        case "soumettre":
            return g.soumettre(args.carte, args.plateforme, args.motif, args.replication)
        case "reconcilier":
            return g.reconcilier()
        case "resume":
            return g.resume()
        case "etat":
            return g.etat(args.course)
        case "demander-bascule":
            return g.demander_bascule(args.course, args.vers, args.motif)
        case "annuler":
            return g.annuler(args.course)
        case "purger":
            return g.purger(args.course, args.nom, args.sha256)
        case "approuver":
            return g.approuver(args.demande)
        case "refuser":
            return g.refuser(args.demande, args.motif)
        case "trancher":
            return g.trancher(args.course, args.etat, args.motif, args.version)
        case "sprint":
            return g.ouvrir_sprint(args.chantiers, args.fin)


def _sortir(rep) -> int:
    texte = "\n".join([rep.message] + rep.lignes) if rep.message else "\n".join(rep.lignes)
    print(f"[{rep.code}] {texte}" if rep.code not in ("OK",) else texte)
    return rep.sortie


def agent(argv=None) -> int:
    p = argparse.ArgumentParser(prog="guichet-agent", description="Porte de l'agent vers Kaggle et Colab.")
    sous = p.add_subparsers(dest="cmd", required=True)
    _commun(sous)
    args = p.parse_args(argv)
    if refus := verifier_compte():
        print(refus)
        return 2
    return _sortir(executer(args, construire()))


def humain(argv=None) -> int:
    p = argparse.ArgumentParser(prog="guichet", description="Porte complète du guichet (humain).")
    p.add_argument("--racine", type=Path, help="dossier du guichet (défaut ~/guichet du compte)")
    sous = p.add_subparsers(dest="cmd", required=True)
    _commun(sous)
    _humain(sous)
    args = p.parse_args(argv)
    if refus := verifier_compte():
        print(refus)
        return 2
    return _sortir(executer(args, construire(args.racine)))


if __name__ == "__main__":
    sys.exit(humain())
