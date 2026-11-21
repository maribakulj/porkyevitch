"""La carte de calcul : ce que l'agent déclare avant de demander une course.

Format TOML, un fichier par calcul :

    experience = "etude-encodeurs"
    dossier = "noyau"                  # relatif à la carte ; copié et haché par le guichet
    point_entree = "run.py"            # lancé par `python run.py` sur Colab ; `code_file` de Kaggle doit le nommer
    gpu = true
    duree_estimee_s = 2900
    duree_mesuree_par = ""             # course réussie qui a mesuré la durée ; requise au-delà du seuil (3 h)
    essai_par = ""                     # course réussie du MÊME code (paramètres mis à part) ; requise pour une course GPU
                                       # au-delà de `essai_requis_gpu_h` (1 h par défaut)
    carte_recherche = "recherche.md"   # relative à la carte ; requise pour une course GPU (voir recherche.py)
    artefacts_attendus = ["recu.json", "etats/*.pt"]   # relatifs à la sortie ; une course sans eux échoue
    plateformes = ["kaggle", "colab"]  # celles qui sont permises pour ce calcul
    artefacts_purgeables = ["*.tar"]   # facultatif ; motifs glob de noms de fichiers directement dans la sortie (ni "/"
                                       # ni ".."). Seuls ces fichiers peuvent être supprimés par `guichet-agent purger`,
                                       # après une course REUSSIE et avec leur sha256. Défaut vide : rien n'est purgeable.

    [[entrees]]                        # données lues par le calcul, avec leur empreinte
    nom = "vecteurs-v3"
    sha256 = "<64 caractères hexadécimaux>"

    [parametres]                       # facultatif : valeurs simples (texte, entier, réel, booléen) passées au calcul
    PARTIE = 2                         # le guichet les écrit, en JSON, dans la variable d'environnement GUICHET_PARAMETRES
    LIMITE = 300                       # au début du point d'entrée ; le calcul les lit par
                                       # json.loads(os.environ.get("GUICHET_PARAMETRES", "{}"))

    [kaggle]
    accelerateur = "NvidiaTeslaT4"     # facultatif

    [colab]
    gpu = "T4"                         # facultatif

La clé d'un calcul ne dépend que de l'arbre du dossier (hors enveloppe Kaggle), du point d'entrée, des entrées et des
paramètres : ni du nom de l'expérience, ni de la plateforme. Renommer une expérience ou changer de plateforme ne fait pas
un calcul nouveau. La clé de code (`cle_code`) laisse les paramètres de côté : un essai court et la course longue d'un même
code la partagent, ce qui permet au guichet de vérifier qu'un essai a réussi avant la course longue.
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
_NOM_PARAMETRE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")
MAX_PARAMETRES = 32


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
    carte_recherche: str = ""  # chemin absolu, ou vide
    kaggle: dict = field(default_factory=dict)
    colab: dict = field(default_factory=dict)
    artefacts_purgeables: list[str] = field(default_factory=list)
    essai_par: str = ""
    parametres: dict = field(default_factory=dict)
    chantier: str = ""  # rempli par le guichet depuis la carte de recherche, pour le bilan
    cle_code: str = ""  # rempli par le guichet à la soumission (voir cle_code())

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
              "artefacts_attendus", "plateformes", "entrees", "kaggle", "colab", "carte_recherche", "artefacts_purgeables",
              "essai_par", "parametres"}
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
    purgeables = d.get("artefacts_purgeables", [])
    exiger(isinstance(purgeables, list) and all(isinstance(m, str) and m for m in purgeables),
           "artefacts_purgeables : liste de motifs (chaînes non vides)")
    for m in purgeables:
        exiger("/" not in m and "\\" not in m and ".." not in m and "\0" not in m,
               f"artefacts_purgeables : motif relatif à la sortie, sans « / » ni « .. » : {m}")
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
    essai = d.get("essai_par", "")
    exiger(isinstance(essai, str), "essai_par : identifiant de course")
    parametres = d.get("parametres", {})
    exiger(isinstance(parametres, dict) and len(parametres) <= MAX_PARAMETRES,
           f"[parametres] : table de {MAX_PARAMETRES} valeurs au plus")
    for nom, v in parametres.items():
        exiger(_NOM_PARAMETRE.match(nom) is not None, f"paramètre {nom!r} : lettres, chiffres et _, 40 caractères au plus")
        exiger(isinstance(v, (str, int, float, bool)) and not (isinstance(v, str) and len(v) > 200),
               f"paramètre {nom} : texte (200 caractères au plus), entier, réel ou booléen")
    for nom in ("kaggle", "colab"):
        exiger(isinstance(d.get(nom, {}), dict), f"[{nom}] : table")
    recherche = d.get("carte_recherche", "")
    exiger(isinstance(recherche, str), "carte_recherche : chemin du fichier, relatif à la carte")
    recherche = str((chemin.parent / recherche).resolve()) if recherche else ""

    dossier = (chemin.parent / d["dossier"]).resolve()
    return Carte(experience=d["experience"], dossier=dossier, point_entree=d["point_entree"], gpu=d["gpu"],
                 duree_estimee_s=d["duree_estimee_s"], artefacts_attendus=list(arts), plateformes=list(pl),
                 entrees=[dict(e) for e in entrees], duree_mesuree_par=mesuree, carte_recherche=recherche,
                 kaggle=dict(d.get("kaggle", {})), colab=dict(d.get("colab", {})),
                 artefacts_purgeables=list(purgeables), essai_par=essai, parametres=dict(parametres))


def cle_code(empreinte_arbre: str, carte: Carte) -> str:
    """Identité du code : arbre du dossier, point d'entrée et entrées déclarées, sans les paramètres."""
    contenu = {"arbre": empreinte_arbre, "point_entree": carte.point_entree,
               "entrees": sorted((e["nom"], e["sha256"]) for e in carte.entrees)}
    return hashlib.sha256(json.dumps(contenu, sort_keys=True).encode()).hexdigest()


def cle(empreinte_arbre: str, carte: Carte) -> str:
    """Identité du calcul : le code et ses paramètres. Sans paramètre, c'est la clé de code (clés d'avant inchangées)."""
    if not carte.parametres:
        return cle_code(empreinte_arbre, carte)
    contenu = {"code": cle_code(empreinte_arbre, carte), "parametres": carte.parametres}
    return hashlib.sha256(json.dumps(contenu, sort_keys=True).encode()).hexdigest()


def texte_parametres(carte: Carte) -> str:
    return json.dumps(carte.parametres, ensure_ascii=False, sort_keys=True)
