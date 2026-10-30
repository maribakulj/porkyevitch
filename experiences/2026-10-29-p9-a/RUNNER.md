# P9-A : runner du passage scientifique

30 octobre 2026. Claude wA:pH, à la demande de wA:p1, d'après les conditions de Codex p4 (`~/Documents/reviews/porkyevitch-p9a-codex.md`, « Ce qui manque avant l'autorisation scientifique »). Ce document décrit du code seulement. **Rien n'est lancé.** Il est à relire par Grok p2 puis à faire auditer par Codex p4. La préinscription (sha `25f1040f…`) n'est pas modifiée.

## Fichiers ajoutés, sans toucher au blanc

- **`scripts/p9a_science.py`** (numpy et scipy, sans torch ni accès aux données) : enveloppe de B, mélange, grille et sélection, mesures de la section 8, verdicts de la section 9, bootstrap par groupes md5, choix des planches.
- **`scripts/p9a_run.py`** : les quatre étapes. Il réutilise **tels quels** `TrainData`, `Head`, `optimizer`, `update`, `probability_pass`, `invariants`, `load_preparation`, `seed_all`, `rng_state` et `restore_rng` du blanc relu, ainsi que `extract` du cache d'images.
- **`scripts/kaggle_p9a_science.py`** : un pilote séparé, avec son manifeste à liste fermée `CODE_SHA256_SCIENCE.json`. Le pilote du blanc et `CODE_SHA256.json` restent inchangés. Le premier échec (smoke-1) et le blanc 2 restent distincts.
- Tests : `tests/test_science.py` (9 tests) et `tests/test_run_resume.py` (3 tests, torch CPU).

## Les six conditions de Codex, une par une

**1. Runner et pilote auditables.**
- Nouveau manifeste, configuration par étape et approbations Grok/Codex exigées ; créneau donné par wA:p1 ; versions des paquets figées.
- Le blanc 2 est lié par son SHA (`a850389e…`, `passed`, micro-lot 64). La préparation et le reçu de la planche initiale sont vérifiés par `load_preparation`, inchangé.
- Aucune recette n'est changée : même perte, même vocabulaire, mêmes données, micro-lot 64, même précision. Le contrôle float64 de duplication et les écarts GPU sont publiés à l'initialisation et à la fin de chaque bras (`invariants`).

**2. Dix époques appariées, graine 0 d'abord.**
- Permutations : `default_rng(graine)` neuf, 10 × 81 951, sauvegardées dans `permutations.npy` avec leur SHA, communes aux quatre bras.
- Ordre des bras : F, G, A, C pour la graine 0. Les rotations des graines 1 et 2 suivent la préinscription.
- Chaque bras a son modèle, son optimiseur et son scaler neufs : aucun état n'est partagé.
- Même W initial (`manual_seed(graine)`, N(0, 1/1024)). A et G sont contrôlés égaux à l'initialisation, quel que soit l'ordre.
- Lot effectif 64 et micro-lot 64, avec `ceil(81951/64)` = 1 281 mises à jour par époque, dernier lot gardé et vérifié. La mise à jour est l'`update` du blanc : AdamW, ASL, régularisation une fois par mise à jour, écrêtage à 5, fp16 seulement dans les produits.
- En fin d'époque, on écrit de façon atomique les poids de l'époque (avec leur SHA) et l'état de reprise : modèle, optimiseur, scaler, RNG, époque et identité.
- **Reprise** (`--resume`, section 10.3) : un bras ne reprend que depuis son propre état de fin d'époque, si l'identité est la même (graine, données, permutations, préparation, préinscription, micro-lot) et que la grille est complète. Les poids sont recopiés après vérification de leur SHA. Sinon le bras repart de son initialisation, sans prétendre reprendre la même trajectoire.
- Toute non-finitude ou tout dépassement arrête la course. On ne retire aucun bras et on ne raccourcit pas l'horizon.

**3. La sélection exactement préinscrite.**
- Après chaque époque, on calcule l'intensité propre du bras sur V-réglage seulement : F, G et A donnent leur intensité agrégée, C donne −log1p(−p) comme sa tête.
- Les 57 candidats de l'époque sont {0,25 ; 0,5 ; 1} × 19 seuils. Le mélange `−expm1(−[(1−α)L^B + αL^h])` se fait avec l'enveloppe de B, max sur les descendants et écrêtage [10⁻⁷, 1−10⁻⁷]. On projette ensuite par seuil, `most_specific` puis `drop86`.
- Les probabilités de toutes les époques ne sont pas stockées : seuls les 57 scores le sont.
- **571 candidats** par bras : la référence α = 0 au seul seuil 0,65 (les ensembles gelés de B, rendus directement), plus 570 points de grille. `select` exige exactement ces nombres.
- Critère : H-F1 de V-réglage. Égalités à 10⁻¹² : α le plus faible (B d'abord), puis l'époque la plus ancienne, puis le seuil le plus faible.
- `selection.json` est écrit et haché **avant** toute inférence d'une nouvelle tête sur la validation entière.
- Gel : pour chaque bras, les poids de l'époque choisie (SHA vérifié) donnent les prédictions sur les 4 265 lignes de validation, ou celles de B si α = 0. Ensuite on écrit `gel.json`, qui ne contient **aucune mesure**.
- Contrôle de la section 7 : en float64, l'enveloppe de B à α = 0 doit redonner les ensembles de B au seuil 0,65, sinon arrêt.

**4. Mesures, planches et verdicts après le gel, dans l'ordre préinscrit.**
- **Étape `planches`** (CPU, réseau) : 12 lignes de validation par bras, où |H_i(bras) − H_i(B)| est le plus grand (égalités : fragment, ligne). On montre les octets Brillfull d'origine (md5 contrôlé par `extract`), la vérité projetée, B et le bras, avec les descriptions officielles. Les champs de preuve ne sont pas montrés, parce qu'ils demanderaient une nouvelle inférence, ce qui est écrit sur la planche. Aucun agrégat n'est calculé.
- **Étape `mesures`** (CPU) : avant tout agrégat, elle vérifie les planches de **ce** gel, c'est-à-dire quatre bras de 12 lignes, chaque fichier présent et inchangé. Elle exige ensuite un reçu qui atteste **les deux regards**, wA:p1 **et** un Grok, chacun avec `viewed_at`, comme pour la mesure de la phase 1 : `{"stage": "planches_p9a_regardees", "manifest_sha256": …, "regards": [{"viewer": "wA:p1", "viewed_at": …}, {"viewer": "Grok …", "viewed_at": …}], "plates_html_sha256": {bras: sha}}`. Cette correction a été demandée par Grok p2 en blocage pour l'étape mesures (30/10). Elle est commitée à part, et ne change aucune ligne exécutée par le devis.
- Mesures de la section 8 :
  - H et E sur les 4 241 lignes éligibles ;
  - F_R sur les 4 265 lignes, avec la liste R complète (4 073 codes), ses zéros et la convention du zéro ;
  - macro-F1 sur les codes représentés, à part, en descriptif ;
  - cinq tranches de `n_brut` sur l'univers fixé, avec `n_fermé` distinct (dans `donnees.json`) et les vérités hors V gardées.
- Verdicts : la règle **G**, puis la voie **R** seulement si G échoue, chacune avec ses gardes ; α = 0 donne « référence conservée ».
- **Mécanisme** (section 9.3) sur V-diagnostic : il compare A et le contrôle global, et publie aussi A−F et A−C. Le seuil de support rare de 100 occurrences est compté sur V-diagnostic. Un gain contre F n'est jamais présenté comme une preuve de l'imbrication.

**5. Bootstrap.**
- 10 000 tirages, graine 20261029, unité = groupe md5, mêmes tirages pour B et les quatre bras (`group_draws`, par blocs de 500).
- H et E sont recalculés sur les lignes éligibles des groupes tirés. Les TP, FP et FN de chaque code rare sont recalculés avec la multiplicité des groupes, par matrices creuses. R et la convention du zéro restent fixes.
- Le bootstrap de V-diagnostic utilise les **mêmes** tirages, restreints aux groupes de V-diagnostic.
- Il n'y a aucune nouvelle inférence : le test le compare au recalcul direct.

**6. Devis complet avant la course.**
- **Étape `devis`** (T4, moins d'une heure). Sur les vraies données, et pour chaque bras, elle chronomètre :
  - la mise en place (vérification des 11,3 Go) et la reproduction de B ;
  - 20 mises à jour à chaud ;
  - un passage V-réglage et la grille complète des 57 candidats ;
  - l'écriture d'un point de reprise et sa taille ;
  - un passage sur toute la validation.
- Elle mesure aussi les pics de RAM et de VRAM, et le temps des tables et d'un bloc de 500 tirages du bootstrap. Ce dernier temps est mesuré sur les ensembles gelés de B (exception d'intégrité) ; aucune nouvelle tête n'est mesurée.
- `devis.json` donne l'estimation d'une graine (entraînement, sélection, gel), le disque et le CPU des mesures. Son statut vaut `WITHIN_12H` ou `AMENDMENT_REQUIRED`.
- **L'étape `seed` refuse de démarrer** sans un devis relu (SHA donné par la configuration) au statut `WITHIN_12H` pour la même graine.
- Aucun score du devis n'est gardé : les 20 mises à jour et la grille ne servent qu'au chronométrage.
- Les plafonds de la section 10 restent les portes : 12 h estimées par graine, RAM 15 Gio, VRAM 12 Gio, sorties 5 Go.
- Les graines 1 et 2 restent conditionnelles : le pilote exige `seeds_1_2_decision` dans l'approbation.

## Ce que les tests couvrent, et ce qu'ils ne couvrent pas

- `test_science.py`, avec numpy et scipy :
  - enveloppe égale au max sur les descendants, et B retrouvé à α = 0 ;
  - limites du mélange, et refus d'α = 0 ;
  - parité de `fast_h` avec `hier_f1` ;
  - sélection : B gagnant, départage, tolérance 10⁻¹², exactement 571 candidats ;
  - mesures de la section 8, contre `code_f1` ;
  - verdicts G, R et non retenu ;
  - mécanisme et seuil de support ;
  - bootstrap par groupes, comparé au recalcul direct, et tirages identiques ;
  - ordre des planches.
- `test_run_resume.py` : reprise valide, absence d'état, identité différente, grille incomplète, poids modifiés.
- **Non couverts ici** : l'entraînement sur GPU, les passages d'inférence et le pilote, qui demandent un T4. Ils réutilisent le code relu du blanc. L'étape `devis` est le contrôle réel de ces branches avant `seed`. Codex demande aussi un contrôle technique ciblé des branches de sélection, de reprise et de bootstrap sur fixtures : les tests ci-dessus en sont la version locale.

## Déroulé prévu, chaque étape relue avant la suivante

1. `devis` (T4) ;
2. relecture de `devis.json` ;
3. `seed` graine 0 (T4) ;
4. relecture de `gel.json` et `selection.json` ;
5. `planches` (CPU) ;
6. regard de wA:p1 puis Grok, et reçu ;
7. `mesures` (CPU) ;
8. relecture, puis décision sur les graines 1 et 2 (section 9.4).

## Amendement du 30/10 : pas sautés par GradScaler (après l'échec du devis 0)

**Constat.** Le devis 0 s'est arrêté après 184 s, sur `nonfinite gradients`. Le bras F avait fini ses 21 mises à jour. Le bras `controle_global` (G) en avait réussi 11 et a échoué à la 12e (lignes 704–767 de la permutation 0). À ce pas, les probabilités et l'ASL étaient finies, et les paramètres l'étaient au pas précédent : seuls les gradients après `unscale_` étaient non finis. C'est le cas que GradScaler sait traiter : un dépassement des produits fp16 sous une échelle de 2¹⁶, qui saute le pas et divise l'échelle par deux. Or `update()` du blanc (`p9a_smoke.py`) refusait tout gradient non fini. Le blanc 2 ne pouvait pas le voir : il ne fait que deux mises à jour par bras, depuis l'initialisation.

**Correctif, dans `p9a_run.py` seulement.** Les octets du blanc sont inchangés (`p9a_smoke.py` `7bb798b3…`, manifeste `733a3f28…`). `update_amp()` reprend la recette de `update()` avec un seul changement : si des gradients sont non finis après `unscale_`, le pas est sauté.
- Pas d'écrêtage ; `scaler.step` saute le pas et `scaler.update` divise l'échelle par deux.
- On vérifie que les poids sont inchangés à l'octet.
- Le saut est journalisé `{bras, époque, pas, échelle avant, n_inf, n_nan, paramètre le plus touché}`, dans `execution.log` (`AMP_SKIP`), dans `devis.json` (par bras) et dans `<bras>_seed.json` (par époque).

Si les gradients sont finis, le chemin relu est inchangé, écrêtage `error_if_nonfinite` compris. Un test le compare à une étape AMP écrite à la main : mêmes poids à l'octet. Les étapes `devis` et `seed` utilisent `update_amp`.

**Seuils fixés par wA:p1 avant toute relance**, jamais relâchés après coup :
- **arrêt si l'échelle tombe sous 1**. Seize sauts de suite depuis 2¹⁶ ne sont plus un dépassement fp16 : c'est une divergence ;
- **arrêt si les sauts d'un bras dépassent 1 % des mises à jour d'une époque**, soit 12,81 sur 1 281 : le 13e saut d'une époque arrête le passage, et un amendement est exigé. Pour le devis, ses 21 pas comptent comme l'époque 1.

Le blanc 2 n'a eu aucun saut : il passe aussi sous cette règle.

**Tests** (`tests/test_amp_skip.py`, 5 tests, CPU, inf injecté par un crochet sur le gradient) :
- saut légitime : poids inchangés, échelle divisée par deux, journal complet, puis reprise normale au pas suivant ;
- divergence : échelle 4 → 2 → 1 → 0,5, arrêt au 3e saut ;
- plafond de 1 % : arrêt au 13e saut d'une époque, avec l'échelle restée ≥ 1 ;
- plafond compté par bras et par époque ;
- chemin fini identique à la recette.

Ce que le correctif ne tranche pas : si le premier saut du devis corrigé est un NaN et que l'échelle s'effondre, la garde l'arrête. C'est alors une vraie divergence de G, à examiner sans changer de tolérance.
