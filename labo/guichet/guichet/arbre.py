"""Copie et empreinte d'un dossier de calcul.

Le guichet ne lance jamais le dossier de l'agent : il en fait une copie dans son propre espace, calcule l'empreinte
**sur la copie**, et lance la copie. Ce qui est lancé est donc exactement ce qui a été haché, même si l'agent modifie
son dossier pendant ou après la soumission.

Les liens symboliques sont refusés, à tous les niveaux : un lien vers un fichier du guichet (identifiants Kaggle,
jeton Google) ferait partir ce fichier avec le calcul. La copie ouvre chaque fichier par rapport à son dossier, sans
suivre de lien (`os.fwalk`, `O_NOFOLLOW`), pour qu'un lien posé entre la vérification et la lecture ne passe pas.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

# Enveloppe propre à Kaggle : elle ne change pas le calcul et reste hors de l'empreinte, pour qu'un même dossier
# lancé sur Kaggle ou sur Colab ait la même clé. Son empreinte est relevée à part.
ENVELOPPE_KAGGLE = "kernel-metadata.json"
IGNORES = {"__pycache__", ".DS_Store", ".ipynb_checkpoints"}


class DossierRefuse(Exception):
    pass


def copier_et_hacher(source: Path, destination: Path, taille_max: int) -> tuple[str, str | None]:
    """Copie `source` dans `destination` (qui ne doit pas exister) et rend (empreinte de l'arbre, empreinte de
    l'enveloppe Kaggle ou None). Lève DossierRefuse sur un lien, un fichier spécial ou un dépassement de taille."""
    racine = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        destination.mkdir(parents=True)
        lignes: list[str] = []
        enveloppe: str | None = None
        total = 0
        for dossier, sous_dossiers, fichiers, fd in os.fwalk(dir_fd=racine, follow_symlinks=False):
            sous_dossiers[:] = sorted(d for d in sous_dossiers if d not in IGNORES)
            for nom in sous_dossiers:
                if stat.S_ISLNK(os.stat(nom, dir_fd=fd, follow_symlinks=False).st_mode):
                    raise DossierRefuse(f"lien symbolique refusé : {os.path.join(dossier, nom)}")
            for nom in sorted(fichiers):
                if nom in IGNORES or nom.endswith(".pyc"):
                    continue
                relatif = os.path.normpath(os.path.join(dossier, nom))
                st = os.stat(nom, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(st.st_mode):
                    raise DossierRefuse(f"lien symbolique refusé : {relatif}")
                if not stat.S_ISREG(st.st_mode):
                    raise DossierRefuse(f"fichier spécial refusé : {relatif}")
                if st.st_nlink > 1:
                    # Un lien physique vers un fichier du guichet passerait pour un fichier ordinaire. macOS ne les
                    # interdit pas ; le dossier 700 du compte du guichet en est la première défense, celle-ci la seconde.
                    raise DossierRefuse(f"fichier à liens physiques multiples refusé : {relatif}")
                total += st.st_size
                if total > taille_max:
                    raise DossierRefuse(f"dossier trop gros (plus de {taille_max // 2**20} Mo) : les données passent "
                                        "par des entrées déclarées, pas par le dossier de code")
                cible = destination / relatif
                cible.parent.mkdir(parents=True, exist_ok=True)
                h = hashlib.sha256()
                f = os.open(nom, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
                with os.fdopen(f, "rb") as lu, open(cible, "wb") as ecrit:
                    while morceau := lu.read(1 << 20):
                        h.update(morceau)
                        ecrit.write(morceau)
                if relatif == ENVELOPPE_KAGGLE:
                    enveloppe = h.hexdigest()
                else:
                    lignes.append(f"{relatif}\0{h.hexdigest()}\n")
        if not lignes:
            raise DossierRefuse("dossier vide")
        return hashlib.sha256("".join(lignes).encode()).hexdigest(), enveloppe
    finally:
        os.close(racine)


def est_sous(chemin: Path, parent: Path) -> bool:
    try:
        chemin.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
