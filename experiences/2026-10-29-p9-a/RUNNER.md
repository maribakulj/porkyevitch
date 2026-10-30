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
- **Étape `mesures`** (CPU) : elle refuse de démarrer sans le reçu `{"stage": "planches_p9a_regardees", viewer, viewed_at, manifest_sha256}` des planches.
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
