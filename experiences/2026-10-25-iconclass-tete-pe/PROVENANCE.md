# Provenance — 2026-10-25-iconclass-tete-pe

Même tête sur PE-Spatial (T-PE) et comparaison par usage ; C-RADIO reste la version recommandée.

- Source : `https://github.com/maribakulj/caypollard.git`, commit `c0bfe6c587452aba77cc552b9f43799839c81fc8` (branche pilote-figures), copie du 25/10/2026 par `tools/migrer.py`.
- Copie à l'identique (empreintes vérifiées) des fichiers suivis par git ; rien n'a été modifié.
- Les scripts copiés sont une archive : ils s'exécutent depuis un clone de caypollard à ce commit.
- Arbre de travail au moment de la copie : fichiers non suivis ou modifiés présents :
  - `?? results/xanto-parties/kaggle/caypollard-xanto-parts-run.log`

## Ce qui a réellement tourné

- `resultats/full/run.json` : script `ad7cb459336d…` — identique au `scripts/remote_iconclass_head.py` copié.

## Dépendances restées dans caypollard

- `scripts/iconclass_par_usage.py` : lit des fichiers relatifs à la racine du dépôt (ROOT)

## Fichiers copiés (ancien chemin → nouveau chemin, sha256)

| caypollard | porkyevitch | sha256 |
|---|---|---|
| `scripts/remote_iconclass_head.py` | `scripts/remote_iconclass_head.py` | `ad7cb459336ddeb6…` |
| `scripts/iconclass_par_usage.py` | `scripts/iconclass_par_usage.py` | `9d25d0cd816a0948…` |
| `results/iconclass-tete-pe/PREINSCRIPTION.md` | `resultats/PREINSCRIPTION.md` | `185fe6ad7ab07b5e…` |
| `results/iconclass-tete-pe/RESULTAT.md` | `resultats/RESULTAT.md` | `68148bd45d9bc206…` |
| `results/iconclass-tete-pe/externe/predictions.json` | `resultats/externe/predictions.json` | `951f133f25d62567…` |
| `results/iconclass-tete-pe/externe/reference.json` | `resultats/externe/reference.json` | `6af61e03f4caa35c…` |
| `results/iconclass-tete-pe/externe/resultats.json` | `resultats/externe/resultats.json` | `c80339adcef57c13…` |
| `results/iconclass-tete-pe/full/chain.log` | `resultats/full/chain.log` | `828d0cd061b5e360…` |
| `results/iconclass-tete-pe/full/journal.jsonl` | `resultats/full/journal.jsonl` | `39e807333124491a…` |
| `results/iconclass-tete-pe/full/predictions.json` | `resultats/full/predictions.json` | `ef0a9ea97cd77002…` |
| `results/iconclass-tete-pe/full/preflight.json` | `resultats/full/preflight.json` | `c7c64b89b98756e7…` |
| `results/iconclass-tete-pe/full/resultats.json` | `resultats/full/resultats.json` | `8123b5837bb4b49e…` |
| `results/iconclass-tete-pe/full/run.json` | `resultats/full/run.json` | `710efd4c8180a508…` |
| `results/iconclass-tete-pe/par_usage.json` | `resultats/par_usage.json` | `0997b9e20f6adc44…` |

## Laissés dans caypollard (non suivis par git : données lourdes ou sous licence)

- Aucun.
