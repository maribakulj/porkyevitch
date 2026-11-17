"""La porte scientifique, lue par le guichet : une course GPU doit nommer sa carte de recherche.

La carte de recherche est un fichier Markdown (gabarit `gabarits/carte-de-recherche.md`) qui contient un bloc lisible
par machine :

    ```toml recherche
    decision = "si le gain dépasse 0,02 on garde la tête IR, sinon on garde T*"
    premisse = "verifiee"        # verifiee | sans_objet | non_verifiee
    [puissance]
    ic = [0.021, 0.140]          # IC95 déjà mesuré sur le même banc (ou se = 0.03)
    effet_plausible = 0.05       # tiré d'une mesure citée dans la carte
    n = "3000:3000"              # facultatif : effectif de la mesure source : effectif prévu
    famille = 1                  # facultatif : nombre de comparaisons (Bonferroni)
    unilateral = false           # facultatif : règle « borne basse > 0 »
    ```

ou, pour un calcul qui ne prétend rien conclure :

    ```toml recherche
    decision = "…"
    premisse = "sans_objet"
    exploratoire = "pourquoi ce calcul vaut d'être fait sans conclure"
    ```

Le guichet ne croit pas un verdict écrit : il recalcule la puissance avec `puissance.py`. Une carte absente,
illisible ou incomplète fait refuser la course. Une course qui ne peut pas conclure, une course exploratoire et une
prémisse non vérifiée demandent un accord humain. La carte ne fait pas partie de l'identité du calcul : la réécrire ne
fait pas un calcul nouveau.
"""

from __future__ import annotations

import hashlib
import importlib.util
import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

try:  # copie installée à côté du guichet par installer.sh
    from . import puissance  # type: ignore[attr-defined]
except ImportError:  # dépôt : labo/puissance.py
    import sys

    _spec = importlib.util.spec_from_file_location("puissance", Path(__file__).resolve().parents[2] / "puissance.py")
    puissance = importlib.util.module_from_spec(_spec)
    sys.modules["puissance"] = puissance  # avant l'exécution : sous 3.11-3.13, @dataclass l'y cherche
    _spec.loader.exec_module(puissance)

_BLOC = re.compile(r"^```toml recherche[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
PREMISSES = ("verifiee", "sans_objet", "non_verifiee")


class CarteRechercheInvalide(Exception):
    pass


@dataclass
class Evaluation:
    sha256: str
    accords_requis: list[str] = field(default_factory=list)  # raisons qui demandent un accord humain
    note: str = ""  # ce que le guichet ajoute à sa réponse (puissance, verdict)


def evaluer(chemin: Path) -> Evaluation:
    try:
        texte = chemin.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise CarteRechercheInvalide(f"carte de recherche illisible ({chemin.name}) : {type(e).__name__}") from None
    blocs = _BLOC.findall(texte)
    if len(blocs) != 1:
        raise CarteRechercheInvalide(f"carte de recherche {chemin.name} : il faut exactement un bloc "
                                     "```toml recherche``` (voir gabarits/carte-de-recherche.md)")
    try:
        d = tomllib.loads(blocs[0])
    except tomllib.TOMLDecodeError as e:
        raise CarteRechercheInvalide(f"bloc recherche invalide : {e}") from None

    inconnus = set(d) - {"decision", "premisse", "puissance", "exploratoire"}
    if inconnus:
        raise CarteRechercheInvalide(f"bloc recherche : champs inconnus {sorted(inconnus)}")
    if not (isinstance(d.get("decision"), str) and d["decision"].strip()):
        raise CarteRechercheInvalide("bloc recherche : « decision » manque. Quelle décision ce calcul change-t-il ? "
                                     "Si toutes les issues mènent à la même décision, ne pas lancer")
    if d.get("premisse") not in PREMISSES:
        raise CarteRechercheInvalide(f"bloc recherche : « premisse » parmi {PREMISSES}")
    if ("puissance" in d) == ("exploratoire" in d):
        raise CarteRechercheInvalide("bloc recherche : soit une table [puissance], soit « exploratoire », pas les deux "
                                     "ni aucun")

    ev = Evaluation(sha256=hashlib.sha256(texte.encode("utf-8")).hexdigest())
    if d["premisse"] == "non_verifiee":
        ev.accords_requis.append("prémisse non vérifiée : le diagnostic le moins cher de ce fait passe d'abord")
    if "exploratoire" in d:
        if not (isinstance(d["exploratoire"], str) and d["exploratoire"].strip()):
            raise CarteRechercheInvalide("bloc recherche : « exploratoire » doit dire pourquoi ce calcul vaut d'être "
                                         "fait sans pouvoir conclure")
        ev.accords_requis.append(f"calcul exploratoire, qui ne peut rien conclure : {d['exploratoire'].strip()}")
        ev.note = "exploratoire"
        return ev

    p = d["puissance"]
    if not isinstance(p, dict):
        raise CarteRechercheInvalide("[puissance] : table")
    inconnus = set(p) - {"ic", "se", "effet_plausible", "n", "famille", "unilateral", "alpha"}
    if inconnus:
        raise CarteRechercheInvalide(f"[puissance] : champs inconnus {sorted(inconnus)}")
    try:
        if ("ic" in p) == ("se" in p):
            raise ValueError("soit « ic = [bas, haut] », soit « se »")
        if "ic" in p:
            bas, haut = (float(x) for x in p["ic"])
            se = puissance.se_depuis_ic(bas, haut)
        else:
            se = float(p["se"])
            if not se > 0:
                raise ValueError("se doit être positive")
        if "n" in p:
            n0, n1 = (float(x) for x in str(p["n"]).split(":"))
            if not (n0 > 0 and n1 > 0):
                raise ValueError("n = \"N0:N1\" avec deux effectifs positifs")
            se *= math.sqrt(n0 / n1)
        effet = float(p["effet_plausible"])
        if effet == 0:
            raise ValueError("effet_plausible nul : rien à détecter")
        famille = int(p.get("famille", 1))
        if famille < 1:
            raise ValueError("famille ≥ 1")
        b = puissance.bilan(se, effet, float(p.get("alpha", 0.05)), famille, bool(p.get("unilateral", False)))
    except KeyError as e:
        raise CarteRechercheInvalide(f"[puissance] : {e.args[0]} manque") from None
    except (TypeError, ValueError) as e:
        raise CarteRechercheInvalide(f"[puissance] : {e}") from None
    ev.note = f"puissance {b.puissance:.0%} à {effet:g}, effet minimal {b.effet_minimal:.3g} : {b.verdict}"
    if b.code == 2:
        ev.accords_requis.append(f"ne peut pas conclure (puissance {b.puissance:.0%} à l'effet plausible {effet:g} ; "
                                 f"il faudrait × {b.facteur:.3g} l'effectif)")
    return ev
