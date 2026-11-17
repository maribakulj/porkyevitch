"""La carte de calcul : ce que l'agent déclare avant de demander une course.

Format TOML, un fichier par calcul :

    experience = "etude-encodeurs"
    dossier = "noyau"                  # relatif à la carte ; copié et haché par le guichet
    point_entree = "run.py"            # lancé par `python run.py` sur Colab ; `code_file` de Kaggle doit le nommer
    gpu = true
    duree_estimee_s = 2900
    duree_mesuree_par = ""             # course réussie qui a mesuré la durée ; requise au-delà du seuil (3 h)
    artefacts_attendus = ["recu.json", "etats/*.pt"]   # relatifs à la sortie ; une course sans eux échoue
    plateformes = ["kaggle", "colab"]  # celles qui sont permises pour ce calcul

    [[entrees]]                        # données lues par le calcul, avec leur empreinte
    nom = "vecteurs-v3"
    sha256 = "<64 caractères hexadécimaux>"

    [kaggle]
    accelerateur = "NvidiaTeslaT4"     # facultatif

    [colab]
    gpu = "T4"                         # facultatif

La clé d'un calcul ne dépend que de l'arbre du dossier (hors enveloppe Kaggle), du point d'entrée et des entrées : ni du nom de
l'expérience, ni de la plateforme. Renommer une expérience ou changer de plateforme ne fait pas un calcul nouveau.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path

PLATEFORMES = ("kaggle", "colab")
_SHA = re.compile(r"^[0-9a-f]{64}$")


class CarteInvalide(Exception):
    pass


@dataclass
class Carte:
    experience: str
    dossier: Path
    point_entree: str
    gpu: bool
    duree_estimee_s: int
    artefacts_attendus: list[str]
    plateformes: list[str]
    entrees: list[dict] = field(default_factory=list)
    duree_mesuree_par: str = ""
    kaggle: dict = field(default_factory=dict)
    colab: dict = field(default_factory=dict)

    def en_json(self) -> str:
        d = asdict(self)
        d["dossier"] = str(self.dossier)
        return json.dumps(d, ensure_ascii=False, sort_keys=True)

    @classmethod
    def depuis_json(cls, texte: str) -> "Carte":
        d = json.loads(texte)
        d["dossier"] = Path(d["dossier"])
        return cls(**d)


def lire(chemin: Path) -> Carte:
    try:
        d = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        raise CarteInvalide(f"carte illisible : {type(e).__name__}") from None
    except tomllib.TOMLDecodeError as e:
        raise CarteInvalide(f"carte TOML invalide : {e}") from None

    connus = {"experience", "dossier", "point_entree", "gpu", "duree_estimee_s", "duree_mesuree_par",
              "artefacts_attendus", "plateformes", "entrees", "kaggle", "colab"}
    inconnus = set(d) - connus
    if inconnus:
        raise CarteInvalide(f"champs inconnus : {sorted(inconnus)}")
    manquants = {"experience", "dossier", "point_entree", "gpu", "duree_estimee_s", "artefacts_attendus",
                 "plateformes"} - set(d)
    if manquants:
        raise CarteInvalide(f"champs manquants : {sorted(manquants)}")

    def exiger(cond: bool, message: str) -> None:
        if not cond:
            raise CarteInvalide(message)

    exiger(isinstance(d["experience"], str) and re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", d["experience"]) is not None,
           "experience : minuscules, chiffres, . _ -, 80 caractères au plus")
    exiger(isinstance(d["point_entree"], str) and d["point_entree"].endswith(".py") and "/" not in d["point_entree"],
           "point_entree : un fichier .py à la racine du dossier")
    exiger(isinstance(d["gpu"], bool), "gpu : vrai ou faux")
    exiger(isinstance(d["duree_estimee_s"], int) and d["duree_estimee_s"] > 0,
           "duree_estimee_s : entier positif ; une durée inconnue se mesure d'abord par un essai chronométré")
    arts = d["artefacts_attendus"]
    exiger(isinstance(arts, list) and arts and all(isinstance(a, str) and a for a in arts),
           "artefacts_attendus : liste non vide. Nomme tout ce dont la suite aura besoin, modèles compris : "
           "une course qui ne les produit pas échoue")
    for a in arts:
        exiger(not a.startswith("/") and ".." not in Path(a).parts, f"artefact hors de la sortie : {a}")
    pl = d["plateformes"]
    exiger(isinstance(pl, list) and pl and all(p in PLATEFORMES for p in pl), f"plateformes parmi {PLATEFORMES}")
    entrees = d.get("entrees", [])
    exiger(isinstance(entrees, list), "entrees : liste de tables [[entrees]]")
    for e in entrees:
        exiger(isinstance(e, dict) and set(e) == {"nom", "sha256"} and isinstance(e["nom"], str)
               and isinstance(e["sha256"], str) and _SHA.match(e["sha256"]) is not None,
               "chaque entrée : nom et sha256 (64 caractères hexadécimaux), rien d'autre")
    exiger(len({e["nom"] for e in entrees}) == len(entrees), "entrées en double")
    mesuree = d.get("duree_mesuree_par", "")
    exiger(isinstance(mesuree, str), "duree_mesuree_par : identifiant de course")
    for nom in ("kaggle", "colab"):
        exiger(isinstance(d.get(nom, {}), dict), f"[{nom}] : table")

    dossier = (chemin.parent / d["dossier"]).resolve()
    return Carte(experience=d["experience"], dossier=dossier, point_entree=d["point_entree"], gpu=d["gpu"],
                 duree_estimee_s=d["duree_estimee_s"], artefacts_attendus=list(arts), plateformes=list(pl),
                 entrees=[dict(e) for e in entrees], duree_mesuree_par=mesuree,
                 kaggle=dict(d.get("kaggle", {})), colab=dict(d.get("colab", {})))


def cle(empreinte_arbre: str, carte: Carte) -> str:
    """Identité du calcul : arbre du dossier, point d'entrée et entrées déclarées. Rien d'autre."""
    contenu = {"arbre": empreinte_arbre, "point_entree": carte.point_entree,
               "entrees": sorted((e["nom"], e["sha256"]) for e in carte.entrees)}
    return hashlib.sha256(json.dumps(contenu, sort_keys=True).encode()).hexdigest()
