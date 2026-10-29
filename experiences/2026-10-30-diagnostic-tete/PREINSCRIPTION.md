# Diagnostic « où la tête perd des points » : préinscription

Version 1, 30 octobre 2026. Claude wA:pH, remplaçant de Codex maths wA:p6. Demande de wA:p1 : palier 0 du cours, chapitre 13, et PHASE2.md. Écrite **avant** tout calcul. À relire par Grok p2 puis à faire auditer par Codex p4. Rien n'est lancé.

**Nature : purement descriptive.** Ce diagnostic ne choisit ni modèle, ni seuil, ni recette. Aucun de ses chiffres ne modifie B, la série phase 1 ou P9-A. Les bornes hautes calculées ici sont **optimistes par construction** : elles sont choisies sur l'ensemble même qui est mesuré. Ce ne sont pas des résultats atteignables. Une piste qu'il suggère devient une brique préinscrite, avec ses propres partages.

## Données

- **Validation ICAI seule** : partage E3 historique (groupes md5, `default_rng(0) < 0,05`), 4 265 lignes, dont 4 241 évaluables (vérité non vide après `drop86`). L'apprentissage (81 951 lignes) ne sert qu'aux fréquences `n_brut` et au vocabulaire V (7 907 codes, reconstruit et contrôlé).
- **Sorties existantes seulement**, empreintes vérifiées (`ENTREES.json`, sous-ensemble de l'inventaire relu du gel phase 1, `6bde8229…`, **sans le fragment test**) :
  - `porky-e0-run/full` : `t_long.pt` (`5a1b3041…`), `e0.json`, `journal_t_long.jsonl` ;
  - `porky-e3-run/full` : `t_z.pt` (`06e3de0f…`), `e3.json`, `journal_t_z.jsonl` ;
  - `caypollard-encode-cradio` v3 : les onze fragments `train-*` (vecteurs, grilles, étiquettes).
- **Systèmes** : B = T-Z (époque 29, seuil 0,65, H-F1 historique 0,5890847528448202) et T* = T-long (époque 27, seuil 0,6, 0,5780389782560774).
- Interdits : fragment `test-*`, banc Rijksmuseum (dev compris), Emblematica, test IconArt, sorties PE-Spatial (celles qui existent portent sur le test ICAI fermé). Le script refuse tout chemin de ce type.

## Condition d'arrêt

Les sorties des têtes sont recalculées sur CPU en float32. Si le H-F1 de validation de T* ou de B diffère de sa valeur historique de **plus de 10⁻⁴**, le script s'arrête avant toute mesure. La tolérance couvre l'écart CPU/T4 (seuil ≥ sur des probabilités recalculées) ; l'écart observé est publié. S'y ajoutent les empreintes des entrées, le partage 81 951 / 4 265, V = 7 907 codes et 4 241 lignes évaluables.

## Mesures, pour chacun des deux systèmes

Conventions de la préinscription P9-A, section 8.

1. **Tranches de fréquence d'apprentissage** : n_brut = nombre d'images d'apprentissage dont l'étiquette brute contient le code. Tranches **0 ; 1–4 ; 5–20 ; 21–100 ; 101–1 000 ; > 1 000**. Les quatre de la demande sont 5–20, 20–100, 100–1 000 et > 1 000 ; 0 et 1–4 sont gardées comme dans P9-A. Univers fixé avant les scores : codes bruts d'apprentissage, V et vérités de validation, sans 86. Sur les 4 265 lignes et sur les codes bruts projetés : par tranche, nombre de codes, codes représentés, positifs, TP/FP/FN, macro-F1 (F_c = 0 si 2TP+FP+FN = 0 ; codes absents gardés au dénominateur), micro-F1, et macro-F1 sur les seuls codes représentés (descriptive).
2. **Profondeur** : profondeur d'un code simple = nombre de ses nœuds préfixes ; les composés `A:B` forment une case à part. Précision, rappel et F1 des nœuds des fermetures, par profondeur.
3. **Profondeur d'arrêt des codes manqués** : pour chaque code vrai non prédit exactement, on croise sa profondeur avec celle de son ancêtre simple le plus profond présent dans la fermeture de la prédiction (0 si aucun).
4. **Prédictions sûres absentes de la vérité** : couples (image, code) avec p ≥ 0,9, code le plus spécifique parmi ceux ≥ 0,9, hors 86, **absent de la fermeture de la vérité**. Échantillon de **100**, `default_rng(1030)`, au plus 2 par image. **Identifiants seulement** (fragment, ligne, md5, code, p), sans aucune vérité. Le regard est fait par wA:p1 et Grok, pas par ce script. On publie aussi le nombre total de candidats.
5. **Borne haute par tranche** : un seuil par tranche de fréquence, choisi **sur la validation mesurée** par montée coordonnée (ordre des tranches fixé, grille 0,05…0,95, deux passes, une égalité garde la valeur courante), en partant du seuil historique. On publie aussi la courbe du H-F1 au seuil global. C'est une borne optimiste du gain qu'apporteraient des seuils par tranche, **pas** une recette.
6. **Graines : non disponibles.** La phase 1 a entraîné une seule graine (0) par tête. À la place, on publie l'écart du H-F1 de validation sur les **5 dernières époques** des journaux, sous ce nom, jamais comme un écart entre graines.
7. **Corrélation des erreurs C-RADIO / PE-Spatial : non disponible.** Aucune prédiction de validation PE n'a été conservée, et les seules prédictions PE portent sur le test fermé, qu'on n'ouvre pas. À la place, on publie la corrélation des erreurs **T* contre B**, les deux sur C-RADIO : Pearson du H-F1 par image, Jaccard des codes manqués et des codes faux, et images sous 0,3 pour l'un, pour l'autre ou pour les deux.
8. **Résumé** : H-F1, F1 exact, codes par image, prédictions vides, intervalles bootstrap appariés par groupes md5 (1 000 tirages, descriptifs) de H-F1, F1 exact et B − T*, part des vérités hors vocabulaire.

Les probabilités de validation des deux têtes sont gardées en fp16 (`probabilites_validation.npz`, avec `identites_validation.json`) pour un usage ultérieur relu : A1 en a besoin. Elles ne servent ici à rien d'autre que ces mesures.

## Exécution prévue

Kaggle **CPU** (≤ 2 h, créneau de wA:p1), GPU 0, RAM estimée ≤ 4 Go. Sortie dans `/kaggle/working/diagnostic/`, à rapatrier dans `~/porkyevitch-donnees/maths/diagnostic-tete/`.

- **Blanc** : `kaggle_diagnostic.py --stage smoke --binding … --out …`. Il fait les contrôles, la reproduction des deux H-F1 historiques et écrit `blanc.json`, **sans aucune mesure**. Il est relu avant le passage complet.
- **Complet** : `--stage full`. Il écrit `diagnostic.json`, les probabilités et les identités.

Fichier de liaison : `{"e0_root": ".../porky-e0-run/full", "e3_root": ".../porky-e3-run/full", "encoder_root": ".../caypollard-encode-cradio-v3/full"}`.

Tests locaux : `python3 -I tests/test_diag_metrics.py`, 10 tests synthétiques, dont la parité exacte avec `ancestors`, `hier_f1`, `most_specific` et `drop86` d'E3. Ils ne couvrent ni le chargement ni l'inférence : torch n'est pas sur le Mac. Le blanc les remplace pour ces parties.
