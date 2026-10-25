# Provenance — 2026-10-17-graphe-de-scene

Décision « graphe de scène » : LoRA Qwen 7B, tête maison, Qwen sans entraînement, revues de sources. `colab_train_scene.sh` est gardé comme archive, pas comme lanceur (le lanceur actif est porky/colab.py).

- Source : `https://github.com/maribakulj/caypollard.git`, commit `c0bfe6c587452aba77cc552b9f43799839c81fc8` (branche pilote-figures), copie du 25/10/2026 par `tools/migrer.py`.
- Copie à l'identique (empreintes vérifiées) des fichiers suivis par git et de quelques fichiers non suivis légers (scripts, journaux d'entraînement) ; rien n'a été modifié.
- Les scripts copiés sont une archive : ils s'exécutent depuis un clone de caypollard à ce commit.
- Arbre de travail au moment de la copie : fichiers non suivis ou modifiés présents :
  - `?? results/xanto-parties/kaggle/caypollard-xanto-parts-run.log`

## Ce qui a réellement tourné

- Aucun `run.json` avec empreinte de script dans cette expérience.

## Dépendances restées dans caypollard

- `scripts/remote_train_scene_lora.py` : importe `caypollard.atelier.bricks`, lit des fichiers relatifs à la racine du dépôt (ROOT)
- `scripts/remote_scene_qwen.py` : importe `caypollard.atelier.bricks`, lit des fichiers relatifs à la racine du dépôt (ROOT)
- `scripts/remote_head_scene.py` : importe `caypollard.atelier.bricks`, lit des fichiers relatifs à la racine du dépôt (ROOT)

## Fichiers copiés (ancien chemin → nouveau chemin, sha256)

| caypollard | porkyevitch | sha256 |
|---|---|---|
| `scripts/build_scene_train_set.py` | `scripts/build_scene_train_set.py` | `f9e550262d81d47c…` |
| `scripts/remote_train_scene_lora.py` | `scripts/remote_train_scene_lora.py` | `5fbd021643f1f54e…` |
| `scripts/remote_scene_qwen.py` | `scripts/remote_scene_qwen.py` | `9fa13cc77fb20030…` |
| `scripts/remote_head_scene.py` | `scripts/remote_head_scene.py` | `19f5f34ac93b8820…` |
| `scripts/colab_train_scene.sh` | `scripts/colab_train_scene.sh` | `7472560b8334059d…` |
| `results/decision-graphe/.gitignore` | `resultats/.gitignore` | `039d8697cb0ebf2e…` |
| `results/decision-graphe/archive-entrainement.md` | `resultats/archive-entrainement.md` | `8d12731f959ac4fd…` |
| `results/decision-graphe/couts.md` | `resultats/couts.md` | `1c1c2ecf3cf37210…` |
| `results/decision-graphe/modeles-sgg.md` | `resultats/modeles-sgg.md` | `0dd111fa40ebf925…` |
| `results/decision-graphe/qwen-sous-ensemble-160.md` | `resultats/qwen-sous-ensemble-160.md` | `0e3bd643a6ae53c0…` |
| `results/decision-graphe/revue-sources/banc-exterieur-iconclass.md` | `resultats/revue-sources/banc-exterieur-iconclass.md` | `b5bdb8803c9ed608…` |
| `results/decision-graphe/revue-sources/graphes-deux-temps.md` | `resultats/revue-sources/graphes-deux-temps.md` | `49496e962058f013…` |
| `results/decision-graphe/revue-sources/iconclass-vlm-reproduction.md` | `resultats/revue-sources/iconclass-vlm-reproduction.md` | `a3781383a9676e1a…` |
| `results/decision-graphe/revue-sources/iconclass.md` | `resultats/revue-sources/iconclass.md` | `22e4a618189fc215…` |
| `results/decision-graphe/revue-sources/motifs-copies.md` | `resultats/revue-sources/motifs-copies.md` | `56b4b7d78e914a75…` |
| `results/decision-graphe/revue/reports/Graphes de scène et art.md` | `resultats/revue/reports/Graphes de scène et art.md` | `d1223e4cb16e4a1e…` |
| `results/decision-graphe/revue/research_notes/Graphes de scène et art/iconographie_vlm.md` | `resultats/revue/research_notes/Graphes de scène et art/iconographie_vlm.md` | `4106e00eaaf30301…` |
| `results/decision-graphe/revue/research_notes/Graphes de scène et art/methodes_peu_de_donnees.md` | `resultats/revue/research_notes/Graphes de scène et art/methodes_peu_de_donnees.md` | `a7f361bf07801112…` |
| `results/decision-graphe/revue/research_notes/Graphes de scène et art/precedents_complements.md` | `resultats/revue/research_notes/Graphes de scène et art/precedents_complements.md` | `cdb6df2a46c2b25f…` |
| `results/decision-graphe/revue/research_notes/Graphes de scène et art/precedents_directs.md` | `resultats/revue/research_notes/Graphes de scène et art/precedents_directs.md` | `eb1bd966696b5bdc…` |
| `results/decision-graphe/revue/research_notes/Graphes de scène et art/structure_composition.md` | `resultats/revue/research_notes/Graphes de scène et art/structure_composition.md` | `62538411ce5a2eef…` |
| `results/decision-graphe/richart.md` | `resultats/richart.md` | `775688695dd3af1d…` |
| `results/decision-graphe/verifications.md` | `resultats/verifications.md` | `465176f5bbd16ccc…` |
| `results/decision-graphe/classify.py` | `resultats/classify.py` | `d264531c33afa3b2…` |
| `results/decision-graphe/stats.py` | `resultats/stats.py` | `968b493f4e4c404e…` |
| `results/decision-graphe/verbs.py` | `resultats/verbs.py` | `715f0f880df80019…` |
| `results/decision-graphe/qwen7b-lora/log.json` | `resultats/qwen7b-lora/log.json` | `8feda3290b3d7ff6…` |
| `results/decision-graphe/tete-maison/log.json` | `resultats/tete-maison/log.json` | `2fec425756f69bee…` |

## Laissés dans caypollard (non suivis par git : données lourdes ou sous licence)

- `results/decision-graphe/auto.json` (0.0 Mo) `b3c04797e354296c…`
- `results/decision-graphe/raw/README.md` (0.0 Mo) `5b4956c7a8aa4633…`
- `results/decision-graphe/raw/test.json` (2.3 Mo) `64262477bce3d68a…`
- `results/decision-graphe/raw/train.json` (18.6 Mo) `62344d13a96c0037…`
- `results/decision-graphe/raw/val.json` (2.3 Mo) `5439339c2f02b5ae…`
- `results/decision-graphe/rel_others.json` (0.0 Mo) `93f563d4a8d1c0a8…`
- `results/decision-graphe/sample300.json` (0.1 Mo) `5887290e588d6e06…`
- `results/decision-graphe/src/aub-semart-hoi.pdf` (21.4 Mo) `6f7cbe0a5c29346b…`
- `results/decision-graphe/src/aub-semart-hoi.txt` (0.3 Mo) `8ca370145eed5f47…`
- `results/decision-graphe/src/couts/lf.txt` (0.1 Mo) `89f6eb1d42f995bd…`
- `results/decision-graphe/src/couts/location-free.pdf` (8.3 Mo) `eb1e635b08b8ca40…`
- `results/decision-graphe/src/couts/reltr.pdf` (10.3 Mo) `72578ecbf66a7a47…`
- `results/decision-graphe/src/couts/reltr.txt` (0.1 Mo) `b8508ef5101349ee…`
- `results/decision-graphe/src/couts/vg.pdf` (8.1 Mo) `e5a0c3cb0b240c2a…`
- `results/decision-graphe/src/couts/vg.txt` (0.2 Mo) `c22fdfb306929c9b…`
