# Provenance — 2026-10-25-iconclass-externe

Banc extérieur Emblematica (filtres, tirages gel/gel2, étalonnage) ; T, K et VLM 4B/9B sur ce banc.

- Source : `https://github.com/maribakulj/caypollard.git`, commit `c0bfe6c587452aba77cc552b9f43799839c81fc8` (branche pilote-figures), copie du 25/10/2026 par `tools/migrer.py`.
- Copie à l'identique (empreintes vérifiées) des fichiers suivis par git ; rien n'a été modifié.
- Les scripts copiés sont une archive : ils s'exécutent depuis un clone de caypollard à ce commit.
- Arbre de travail au moment de la copie : fichiers non suivis ou modifiés présents :
  - `?? results/xanto-parties/kaggle/caypollard-xanto-parts-run.log`

## Ce qui a réellement tourné

- `resultats/gel2/vlm_4b_run.json` : script `77bdcfa50d41…` — identique au `scripts/remote_external_vlm.py` copié.
- `resultats/gel2/vlm_9b_run.json` : script `77bdcfa50d41…` — identique au `scripts/remote_external_vlm.py` copié.

## Dépendances restées dans caypollard

- `scripts/build_external_iconclass_bench.py` : importe `caypollard.datasets.emblematica`, lit des fichiers relatifs à la racine du dépôt (ROOT)

## Fichiers copiés (ancien chemin → nouveau chemin, sha256)

| caypollard | porkyevitch | sha256 |
|---|---|---|
| `scripts/build_external_iconclass_bench.py` | `scripts/build_external_iconclass_bench.py` | `8173df5b7ae22ae1…` |
| `scripts/remote_external_iconclass.py` | `scripts/remote_external_iconclass.py` | `7a0e5ad8627fc06b…` |
| `scripts/remote_external_vlm.py` | `scripts/remote_external_vlm.py` | `77bdcfa50d418c8c…` |
| `results/iconclass-externe/PREINSCRIPTION.md` | `resultats/PREINSCRIPTION.md` | `60e638aa0fac62dd…` |
| `results/iconclass-externe/RESULTAT.md` | `resultats/RESULTAT.md` | `62f14c8c1b1a2a4a…` |
| `results/iconclass-externe/candidats.json` | `resultats/candidats.json` | `658e3d0ad1fc52b1…` |
| `results/iconclass-externe/etalonnage/cos_0.85_0.88.jpg` | `resultats/etalonnage/cos_0.85_0.88.jpg` | `ba750072bba8a956…` |
| `results/iconclass-externe/etalonnage/cos_0.88_0.9.jpg` | `resultats/etalonnage/cos_0.88_0.9.jpg` | `742c6092cafd2a9f…` |
| `results/iconclass-externe/etalonnage/cos_0.92_0.95.jpg` | `resultats/etalonnage/cos_0.92_0.95.jpg` | `81b4a589dcb60961…` |
| `results/iconclass-externe/etalonnage/cos_0.95_1.01.jpg` | `resultats/etalonnage/cos_0.95_1.01.jpg` | `dd6c7eca6c1a21c2…` |
| `results/iconclass-externe/etalonnage/cos_0.9_0.92.jpg` | `resultats/etalonnage/cos_0.9_0.92.jpg` | `161e3b9bdbdbf979…` |
| `results/iconclass-externe/etalonnage/pairs_0_15.jpg` | `resultats/etalonnage/pairs_0_15.jpg` | `903afcbc63a7a552…` |
| `results/iconclass-externe/etalonnage/pairs_15_30.jpg` | `resultats/etalonnage/pairs_15_30.jpg` | `3b7741f6aae5fc17…` |
| `results/iconclass-externe/etalonnage/pairs_30_45.jpg` | `resultats/etalonnage/pairs_30_45.jpg` | `6f8644283f54122b…` |
| `results/iconclass-externe/etalonnage/pairs_45_60.jpg` | `resultats/etalonnage/pairs_45_60.jpg` | `e03bb7559695ab95…` |
| `results/iconclass-externe/etalonnage/pairs_60_80.jpg` | `resultats/etalonnage/pairs_60_80.jpg` | `6ca9495e4d062893…` |
| `results/iconclass-externe/gel/allnear.json` | `resultats/gel/allnear.json` | `dd06f0c800e97c0c…` |
| `results/iconclass-externe/gel/dev.json` | `resultats/gel/dev.json` | `1f530b1a4d2de787…` |
| `results/iconclass-externe/gel/filtre.json` | `resultats/gel/filtre.json` | `ff36429c74eff19f…` |
| `results/iconclass-externe/gel/frozen.json` | `resultats/gel/frozen.json` | `66409282d0964f29…` |
| `results/iconclass-externe/gel/nearest.json` | `resultats/gel/nearest.json` | `298eafec1ab93991…` |
| `results/iconclass-externe/gel/test.json` | `resultats/gel/test.json` | `20b381f0b86afee3…` |
| `results/iconclass-externe/gel2/dev.json` | `resultats/gel2/dev.json` | `079053345265b307…` |
| `results/iconclass-externe/gel2/filtre.json` | `resultats/gel2/filtre.json` | `007128321852ec69…` |
| `results/iconclass-externe/gel2/frozen.json` | `resultats/gel2/frozen.json` | `39b5107746ce5705…` |
| `results/iconclass-externe/gel2/head_resultats_rerun.json` | `resultats/gel2/head_resultats_rerun.json` | `6ea3776c2c01c3c3…` |
| `results/iconclass-externe/gel2/nearest.json` | `resultats/gel2/nearest.json` | `69caaae63240f05b…` |
| `results/iconclass-externe/gel2/planche_12_voisins.jpg` | `resultats/gel2/planche_12_voisins.jpg` | `0faafa23809f7e14…` |
| `results/iconclass-externe/gel2/predictions.json` | `resultats/gel2/predictions.json` | `543a556f7a0dc784…` |
| `results/iconclass-externe/gel2/resultats.json` | `resultats/gel2/resultats.json` | `f6a26d126d538429…` |
| `results/iconclass-externe/gel2/test.json` | `resultats/gel2/test.json` | `44cc03f936a58a82…` |
| `results/iconclass-externe/gel2/vlm_4b.jsonl` | `resultats/gel2/vlm_4b.jsonl` | `ed55ca73896dffd1…` |
| `results/iconclass-externe/gel2/vlm_4b_run.json` | `resultats/gel2/vlm_4b_run.json` | `d04adde0748fa453…` |
| `results/iconclass-externe/gel2/vlm_9b.jsonl` | `resultats/gel2/vlm_9b.jsonl` | `a8f69aa13c6205c4…` |
| `results/iconclass-externe/gel2/vlm_9b_run.json` | `resultats/gel2/vlm_9b_run.json` | `82d70e96b12430ba…` |
| `results/iconclass-externe/gel2/vu.json` | `resultats/gel2/vu.json` | `a089112443112172…` |

## Laissés dans caypollard (non suivis par git : données lourdes ou sous licence)

- `results/iconclass-externe/gel2/candidats_feats.npz` (62.2 Mo) `347babaa95f7ca11…`
