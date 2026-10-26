# Notebooks et exécutions

Deux formes, gardées ensemble. Les scripts `.py` restent les sources qui ont tourné. Un notebook n'est inscrit ici que s'il a été récupéré tel quel.

Aucun notebook reconstruit n'a été ajouté : un fichier écrit après coup ne serait pas l'exécution archivée.

Les noyaux Kaggle retrouvés sont de type `script`, pas `notebook`. Ceux dont les octets sont déjà un script du dépôt sont signalés. Les autres noyaux sont privés et ne sont pas copiés ici.

## Récupérés

| notebook | origine | statut |
|---|---|---|
| `experiences/2026-10-25-notebooks-caypollard/notebooks/` (9 fichiers et leur README) | caypollard `c0bfe6c587452aba77cc552b9f43799839c81fc8`, branche `pilote-figures` | historique, aucune exécution enregistrée |
| `experiences/2026-10-17-graphe-de-scene/notebooks/qwen_relations.ipynb` | `Mon Drive/caypollard/colab/qwen_relations.ipynb` | historique, aucune sortie enregistrée |

`porky/colab.py` envoie une chaîne Python à `colab exec`. Il n'écrit pas de `.ipynb`.

## Chaque expérience

| expérience | ce qui a tourné | empreinte ou commit | environnement | résultats | notebook |
|---|---|---|---|---|---|
| `2026-10-17-graphe-de-scene` | `scripts/remote_train_scene_lora.py` via `scripts/colab_train_scene.sh` ; aussi `remote_scene_qwen.py`, `remote_head_scene.py` | pas de `run.json` à empreinte de script | Colab. Noyaux Kaggle privés, non copiés : `mabaku/caypollard-relations-qwen`, `mabaku/caypollard-relations-pose`, `mabaku/caypollard-qwen-cpu-0` à `3` | `resultats/` | `notebooks/qwen_relations.ipynb` (lecture Qwen, pas le LoRA) |
| `2026-10-25-iconclass-tete` | `scripts/executes/remote_iconclass_head@210d1c4079.py` ; `scripts/remote_iconclass_vlm_bench.py` | `22c674d47821…` ; `6d3697f5b84b…` identique au script copié | Colab pour le banc VLM (`resultats/colab/`). Noyau Kaggle privé non copié : `mabaku/caypollard-iconclass-head-smoke` | `resultats/full/run.json`, `resultats/colab/vlm_bench.json` | aucun |
| `2026-10-25-iconclass-externe` | `scripts/executes/remote_external_iconclass@210d1c4079.py`, `@a798259166.py` ; `scripts/remote_external_vlm.py` | `5e73cfd2d98e…`, `bc95b3598319…`, `77bdcfa50d41…` | scripts distants, voir `PROVENANCE.md` | `resultats/gel/`, `resultats/gel2/` | aucun |
| `2026-10-25-iconclass-tete-pe` | `scripts/remote_iconclass_head.py` pour `resultats/full/run.json` | `ad7cb459336d…` identique au script copié. `7a0e5ad8627f…` de `resultats/externe/reference.json` introuvable | Noyau Kaggle privé non copié : `mabaku/caypollard-iconclass-pe-run` | `resultats/full/run.json` | aucun |
| `2026-10-25-xanto-parties` | `scripts/remote_xanto_parts.py` | `4fe64ea7699e…` identique au script copié | Kaggle. Noyau privé non copié : `mabaku/caypollard-xanto-parts-run` | `resultats/kaggle/out/run.json` | aucun |
| `2026-10-25-iconclass-architecture` | `scripts/kaggle_encode_run.py`, qui vérifie `scripts/encode_cradio.py` | le pilote Kaggle `mabaku/caypollard-encode-cradio` a les mêmes octets que `kaggle_encode_run.py`. `encode_cradio.py` : `c3f12bb71deda0b96bf3b8d015d9a79f4db666c234ad8edb0ff04633bd2bf1ca` | Kaggle, GPU, internet | `essais/encodage-full/`, `essais/encodage-smoke/` | aucun |
| `2026-10-25-lermolieff-publication` | `kaggle_smoke.py` | mêmes octets que le noyau `mabaku/lermolieff-smoke-run` | Kaggle | `essai-distant/` | aucun |
| `2026-10-25-banc-rijksmuseum` | scripts du banc, dont `scripts/kaggle_filtres_run.py` | mêmes octets que le noyau `mabaku/rijks-filtres-run` | Kaggle pour l'essai des filtres | `filtres/essai-blanc/` | aucun |
| `2026-10-25-notebooks-caypollard` | aucun entraînement porkyevitch | caypollard `c0bfe6c` | notebooks sur fixtures | aucun résultat d'entraînement | les neuf fichiers du dossier |
