# Provenance — 2026-10-25-iconclass-tete

Tête Iconclass sur C-RADIOv3-L (T) et voisins (K), test ICAI 788 ; banc de vitesse et de fidélité du VLM 4B.

- Source : `https://github.com/maribakulj/caypollard.git`, commit `c0bfe6c587452aba77cc552b9f43799839c81fc8` (branche pilote-figures), copie du 25/10/2026 par `tools/migrer.py`.
- Copie à l'identique (empreintes vérifiées) des fichiers suivis par git ; rien n'a été modifié.
- Les scripts copiés sont une archive : ils s'exécutent depuis un clone de caypollard à ce commit.
- Arbre de travail au moment de la copie : fichiers non suivis ou modifiés présents :
  - `?? results/xanto-parties/kaggle/caypollard-xanto-parts-run.log`

## Ce qui a réellement tourné

- `resultats/colab/vlm_bench.json` : script `6d3697f5b84b…` — identique au `scripts/remote_iconclass_vlm_bench.py` copié.
- `resultats/full/run.json` : script `22c674d47821…` — version antérieure : `scripts/remote_iconclass_head.py@210d1c4079a8e4997f1a73af1e7c92b1cb3fc1b7` (copiée ici dans `scripts/executes/`).

## Dépendances restées dans caypollard

- Aucune.

## Fichiers copiés (ancien chemin → nouveau chemin, sha256)

| caypollard | porkyevitch | sha256 |
|---|---|---|
| `scripts/remote_iconclass_head.py` | `scripts/remote_iconclass_head.py` | `ad7cb459336ddeb6…` |
| `scripts/remote_iconclass_vlm_bench.py` | `scripts/remote_iconclass_vlm_bench.py` | `6d3697f5b84b12c8…` |
| `results/iconclass-tete/PREINSCRIPTION.md` | `resultats/PREINSCRIPTION.md` | `5a26aa71191e9a4a…` |
| `results/iconclass-tete/RESULTAT.md` | `resultats/RESULTAT.md` | `a4eaae50e0400be0…` |
| `results/iconclass-tete/colab/vlm_bench.json` | `resultats/colab/vlm_bench.json` | `bf5158201c9cec02…` |
| `results/iconclass-tete/full/journal.jsonl` | `resultats/full/journal.jsonl` | `c19a4e454cb552d6…` |
| `results/iconclass-tete/full/predictions.json` | `resultats/full/predictions.json` | `84283a881ed15747…` |
| `results/iconclass-tete/full/preflight.json` | `resultats/full/preflight.json` | `c7c64b89b98756e7…` |
| `results/iconclass-tete/full/resultats.json` | `resultats/full/resultats.json` | `d207d0c4ade1d1ba…` |
| `results/iconclass-tete/full/run.json` | `resultats/full/run.json` | `968d44e93a02a225…` |

## Laissés dans caypollard (non suivis par git : données lourdes ou sous licence)

- Aucun.
