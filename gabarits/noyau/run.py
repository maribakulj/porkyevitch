"""Gabarit de noyau pour le guichet : à copier dans le dossier de l'expérience, puis remplir FICHIERS et calculer().

Ce qu'il apporte dès le départ, parce que chaque oubli a déjà coûté une course :
- les paramètres de la carte ([parametres]) lus dans GUICHET_PARAMETRES, posé par le guichet : le même code sert à
  l'essai court et à la course longue ;
- les entrées cherchées par dossier et nom, et vérifiées par SHA-256 AVANT toute lecture ;
- des repères d'étape écrits sur disque (etapes.jsonl), avec la mémoire, et la pile de tous les fils en cas de plantage
  (faulthandler) : une course morte sans message dit où elle s'est arrêtée ;
- un repère « erreur » (type et message) quand une exception remonte ;
- un contrôle final : la sortie contient tous les fichiers attendus, et rien d'autre.

Le dossier des entrées (GUICHET_ENTREES, défaut /kaggle/input) se remplace par un faux dossier pour l'essai local :
voir tests/test_essai_local.py, à garder à côté et à faire passer avant toute course (essai local, puis essai court).
"""
import faulthandler
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

PARAMETRES = json.loads(os.environ.get("GUICHET_PARAMETRES", "{}"))
ENTREES = Path(os.environ.get("GUICHET_ENTREES", "/kaggle/input"))
SORTIE = Path(os.environ.get("GUICHET_SORTIE", "/kaggle/working"))

# Données lues : clé -> (dossier du jeu, nom du fichier, sha256 attendu). Exemple à remplacer.
FICHIERS = {"texte": ("jeu-exemple", "exemple.txt", "29a1b713a4d58290b0fc4efc6206ea9574ea9e2e7332277e745a52780f1a3dd3")}
# Ce que la carte déclare dans artefacts_attendus ; la sortie ne doit contenir que cela (plus le carnet de Kaggle).
ATTENDUS = {"recu.json", "etapes.jsonl"}
TOLERES = {"__notebook_source__.ipynb"}


def etape(nom, **x):
    """Repère imprimé et ajouté à etapes.jsonl (la mémoire est le maximum atteint par le processus)."""
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1e9 if sys.platform == "darwin" else 1e6)
    ligne = json.dumps({"t": round(time.time(), 1), "etape": nom, "rss_go": round(rss, 2), **x}, ensure_ascii=False)
    print(ligne, flush=True)
    with open(SORTIE / "etapes.jsonl", "a", encoding="utf-8") as f:
        f.write(ligne + "\n")


def sha(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for morceau in iter(lambda: f.read(1 << 20), b""):
            h.update(morceau)
    return h.hexdigest()


def chercher(dossier, nom, attendu):
    """Le fichier `nom` sous un dossier `dossier` des entrées : un seul, de SHA-256 `attendu`."""
    trouves = [Path(d) / nom for d, _, fs in os.walk(ENTREES) if nom in fs and dossier in Path(d).relative_to(ENTREES).parts]
    if len(trouves) != 1:
        raise RuntimeError(f"entrée {dossier}/{nom} : {len(trouves)} trouvée(s)")
    if sha(trouves[0]) != attendu:
        raise RuntimeError(f"entrée {dossier}/{nom} : SHA-256 inattendu")
    return trouves[0]


def ecrire_json(nom, obj):
    provisoire = SORTIE / (nom + ".provisoire")
    provisoire.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(provisoire, SORTIE / nom)


def calculer(e, p):
    """À REMPLIR. `e` : chemins vérifiés des FICHIERS ; `p` : paramètres. Rend le reçu (agrégats seulement)."""
    lignes = e["texte"].read_text(encoding="utf-8").splitlines()
    limite = p.get("LIMITE")
    lues = lignes[:limite] if limite else lignes
    return {"lignes": len(lues), "limite": limite}


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    pile = open(SORTIE / "etapes.jsonl", "a", encoding="utf-8")
    faulthandler.enable(file=pile, all_threads=True)
    t0 = time.time()
    etape("debut", parametres=PARAMETRES)
    e = {cle: chercher(*v) for cle, v in FICHIERS.items()}
    etape("entrees", n=len(e))
    recu = calculer(e, PARAMETRES)
    recu.update(parametres=PARAMETRES, duree_s=round(time.time() - t0, 1))
    ecrire_json("recu.json", recu)
    presents = {q.name for q in SORTIE.iterdir() if q.is_file()}
    if not ATTENDUS <= presents or presents - ATTENDUS - TOLERES:
        raise RuntimeError(f"sortie : manquants {sorted(ATTENDUS - presents)}, "
                           f"en trop {sorted(presents - ATTENDUS - TOLERES)}")
    etape("fin")


if __name__ == "__main__":
    try:
        main()
    except BaseException as x:
        etape("erreur", type=type(x).__name__, message=str(x)[:300])
        raise
