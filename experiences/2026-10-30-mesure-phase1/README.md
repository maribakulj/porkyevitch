# Phase 1 : mesure et verdicts sur les prédictions gelées

30 octobre 2026. Claude wA:pH, à la demande de wA:p1 (jalon : prédictions gelées, sceau `3c468faa…`). Ce dossier contient le code seulement. **Rien n'est lancé.** Il est à relire par Grok p2 puis à faire auditer par Codex p4 avant chaque étape.

## Ce que le code applique, et d'où vient chaque règle

Toutes les règles viennent de la préinscription de l'architecture (`~/porkyevitch/experiences/2026-10-25-iconclass-architecture/PREINSCRIPTION.md`, sha `5115c3a5…`, amendement 4). Aucune n'est choisie ici.

| Règle | Où dans le code |
|---|---|
| **Famille de sept comparaisons** : T*−T0 (E0), puis TK, T-niv, TK-niv, T-H, T-Z, T-D, chacune contre T* | `mesure_metrics.FAMILY` ; contrôlée contre le manifeste du sceau |
| **Bonferroni** : borne unilatérale au niveau 1 − 0,05/7 ≈ 99,29 % | `LEVEL` ; borne = quantile 0,05/7 des tirages |
| **Retenue** si borne(Δ_Rijks) > 0 **et** borne(Δ_ICAI) > −0,01, sur la borne et non sur l'estimation | `retained` |
| **Bootstrap** : 10 000 tirages, graine 0, mêmes tirages pour tous les systèmes d'un banc. Rijksmuseum par composantes entières, moyenne par image recalculée sur les images tirées ; ICAI par images. IC95 bilatéraux publiés à côté | `unit_draws`, `bootstrap_delta`, `summarise` |
| **Projection sans 86** sur la vérité et les prédictions. ICAI : une image à vérité projetée vide est exclue, il en reste **787**. Rijksmuseum : aucune image vide, ce qui est vérifié. Contrôle : T0 = 0,5459 sur ICAI | `stage_test` |
| **TK-niv** n'est exécutée que si TK et T-niv sont retenues. Sinon elle garde sa place et ses prédictions de test ne sont pas ouvertes | `tk_niv_active` |
| **Planches** : pour chaque comparaison, les 12 images du dev où \|H-F1 brique − H-F1 référence\| est le plus grand (égalités : identifiant). Vérité et deux prédictions en clair, avec la description Iconclass officielle. Pour E0, la référence est T0. La planche de TK-niv est faite aussi et marquée conditionnelle | `planche`, `plate_html` |
| **Mesures secondaires** : H-F1, F1 exact (fonction `exact` de T, micro), F1 par profondeur (1-2, 3-4, 5+), rappel des codes rares (5–20 images d'apprentissage, rappel sur les ancêtres de la prédiction), couverture | `diagnostic` |
| **Diagnostic D** : (1) rappel des ancêtres par profondeur ; (2) F1 par fréquence (5-20, 21-100, >100) ; (3) couverture hors vocabulaire par image, par paire et par code ; (4) codes prédits par profondeur contre la vérité ; (6) par support | `diagnostic` |

**Deux mesures ne sont pas calculables depuis le sceau.** Elles sont déclarées comme telles :
- **D(5)**, le rang et la probabilité des codes profonds sous le seuil : le sceau ne contient que des ensembles prédits, aucune probabilité.
- **La latence T4** : le sceau ne contient aucun chronométrage.

Le D sur la validation ICAI n'est **pas mesuré** ici pour les briques. Le sceau ne contient aucune prédiction de validation, et le diagnostic de la tête ne couvre que T* et T-Z. Ce manque reste ouvert : il demande à wA:p1 de décider s'il faut produire ces prédictions, ce qui n'ouvre aucun test. Ce paquet ne prétend donc pas couvrir toutes les mesures secondaires.

## Deux étapes séparées, chacune relue avant d'être lancée

1. **`--stage dev`** : le dev du Rijksmuseum seulement.
   - Il vérifie le SHA du sceau et celui de ses 24 fichiers. Les fichiers de **prédictions** de test sont **hachés, jamais analysés** : un test synthétique le prouve, l'étape dev passe même quand ils sont illisibles.
   - En revanche, `frozen.json` est un seul fichier qui contient aussi les vérités du test Rijksmuseum. Il est entièrement analysé (`json.loads`) pour vérifier son SHA, puis seul le dev est gardé et la référence au reste est détruite. Aucun score, diagnostic ni sortie ne consulte un élément du test. Les vérités du test passent donc en mémoire sans être lues. Si l'on exige qu'elles n'y passent même pas, il faut une projection dev séparée et épinglée, qui n'existe pas encore. Le test des prédictions illisibles ne prouve rien sur ce fichier.
   - Il n'ouvre aucune vérité ICAI de test.
   - Il écrit `dev.json` (D sur le dev pour les huit systèmes), `planches/<comparaison>.html` avec ses images IIIF (SHA vérifié) et `MANIFEST_DEV.json`. Ce manifeste contient les identités du sceau, du banc, de la préinscription et des scripts, les versions, les sept planches (HTML, 12 identifiants, fichiers d'image) et le SHA de chaque fichier.
2. **Regard des planches** par wA:p1 puis Grok. Le reçu `recu_planches.json` porte :
   - `"stage": "planches_dev_regardees"` ;
   - `"dev_manifest_sha256"` : le SHA de `MANIFEST_DEV.json` ;
   - `"regards"` : `[{"viewer": "wA:p1", "viewed_at": …}, {"viewer": "Grok …", "viewed_at": …}]` ;
   - `"plates_html_sha256"` : le SHA de chaque planche, pour les sept comparaisons.
3. **`--stage test`** : **avant toute vérité de test**, il valide le dev et le reçu. Il refuse si l'une de ces conditions n'est pas remplie :
   - le manifeste vient de ce sceau, de ce banc, de cette préinscription et de ces scripts ;
   - chaque fichier listé est présent et inchangé, `dev.json` compris ;
   - les sept comparaisons sont là, chacune avec 12 images distinctes et ses fichiers ;
   - les deux regards sont présents ;
   - les SHA des planches dans le reçu égalent ceux du manifeste.

   L'**ordre d'ouverture** est le suivant :
   1. vérités ICAI de test ;
   2. vérités du test Rijksmuseum ;
   3. les six comparaisons sans condition, dans l'ordre de la famille, avec le contrôle T0 ;
   4. TK-niv, seulement si la condition est remplie ;
   5. écriture de `verdicts.json` ;
   6. **ensuite seulement**, les mesures descriptives et D sur les tests (`mesures_test.json`), puis `MANIFEST_TEST.json`.

Aucune image des tests n'est regardée par ce code.

## Entrées sur Kaggle (CPU)

- Le dossier du sceau : `MANIFEST.json` et ses 24 fichiers.
- `frozen.json` du banc (`2424b778…`) et `ENTREES_GELEES.json` du gel (`6bde8229…`).
- La sortie complète `caypollard-encode-cradio` v3 : les étiquettes d'apprentissage pour les fréquences et V, puis, à l'étape test seulement, les étiquettes du test ICAI (SHA de l'inventaire).
- Les textes Iconclass (`txt/en/`, blobs épinglés), pour les planches.
- Internet, pour les images du dev.

Le pilote est `scripts/kaggle_mesure_run.py`. Entre les deux passages, seule la ligne `STAGE` change.

## Tests

`python3 -I tests/test_mesure.py` lance les tests synthétiques :
- parité du parseur et du H-F1 avec le gel et E3 ;
- F1 exact micro ;
- bootstrap par composantes, comparé à un calcul direct ;
- niveau de Bonferroni et règle de retenue (inégalités strictes) ;
- activation de TK-niv ;
- ordre et égalités des planches ;
- profondeur, codes rares, fréquence et couverture ;
- des essais de bout en bout sur un faux sceau au **schéma réel du gel** : lignes Rijks `{index, id, image_sha256, codes}`, lignes ICAI `{index, shard, row, md5, codes}`, empreintes d'ordre du manifeste. Les constantes sont remplacées. Ils vérifient que :
  - le dev n'analyse pas les prédictions de test ;
  - un ordre Rijks faux est refusé ;
  - le test est refusé, avant les vérités, pour un manifeste dev vide, un autre sceau, un fichier manquant ou modifié, une comparaison absente, un regard manquant ou un reçu d'un autre dev ;
  - les verdicts sont écrits, il reste 787 images ICAI, et TK-niv est ouverte ou fermée selon la condition.
