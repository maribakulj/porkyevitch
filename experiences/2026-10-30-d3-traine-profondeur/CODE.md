# D3 : code, blanc et notes qui le lient

30 octobre 2026. Claude wA:pH. Ce code applique la préinscription D3 (sha `4a4c0c63…`, feu vert de Grok p2, audit de Codex p4 en file). **Rien n'est lancé.** Le cache de B se lit sur Kaggle, dans la sortie montée de `mabaku/porky-diag-run` v3.

## Fichiers

- **`scripts/d3_core.py`** (numpy) :
  - fonctions E3 transcrites ;
  - S0 ;
  - cible R ;
  - vote et poids de TK ;
  - mélange sur R ;
  - parent direct et familles ;
  - porte et décision routée ;
  - comptes des enfants ;
  - choix de t ;
  - règle G et voie R ;
  - bootstrap par groupes.
- **`scripts/d3_run.py`** : étapes `blanc` et `complet`. Les voisins sont calculés en numpy, la tête des enfants en torch, sur GPU si présent.
- **`scripts/kaggle_d3_run.py`** : pilote T4, SHA des scripts et des entrées vérifiés.
- **`tests/test_d3.py`** (11 tests, torch CPU) :
  - parité E3 ;
  - profondeur et parent ;
  - familles par supports ;
  - remplacement routé et porte fermée ;
  - identité couverture × conditionnel ;
  - choix de t ;
  - juges et seuil de 100 ;
  - poids nul ;
  - poids négatifs du vote ;
  - bootstrap apparié ;
  - `blanc` puis `complet` de bout en bout sur données factices.

## Les notes de Grok p2 (section 6), reprises dans le code

| Note | Où |
|---|---|
| H et E sur les 4 241 lignes non vides ; F_R et TP/FP/FN sur les 4 265 | `measures` (éligibles pour H/E, toutes les lignes pour `code_f1`) |
| Profondeur d'un code simple = nombre de ses nœuds préfixes ; composés à part ; parité avec `PART`/`TOKEN` ; « hors 86 » = `strip()` puis préfixe 86 | `depth_case`, `ancestors`, `drop86`, `is86` |
| Les 100 occurrences sont des couples (image, code) de la vérité de validation ; le plancher rend R indécidable sans suspendre G | `positives`, `route_r` |
| Bootstrap figé : `default_rng(20261030)`, percentile, descriptif. Les 64 lignes du blanc suivent l'ordre de `identites_validation.json` | `BOOT_SEED`, `bootstrap_groups`, `boot_fr`, `stage_blanc` |
| Précision du seuil t, rappel total, faux positifs et lecture « descente améliorée » comptés après `most_specific` et `drop86`, sur toutes les images du lot ; un seul t pour toutes les familles | `child_counts`, `choose_t`, `arm2_outputs` |
| Perte = moyenne sur les couples (ligne, enfant) actifs ; lots de 1 024 tirés parmi les lignes qui ont au moins un enfant actif | `train_head` |
| La mémoire permutée garde les poids visuels et déplace les étiquettes : son espérance est un a priori sur R, pas un second juge | `arm1(permuted=True)`, `witness_reading` |
| Vecteurs `feats/<fragment>.npz` (n, 4096) float16, recette `summary+meanspatial\|l2-each-then-l2`, passés en float32 ; les grilles ne sont pas une entrée | `Data` (forme, type et recette vérifiés) |
| Le cache du manifeste du diagnostic : `decisions_sha256`, vocabulaire et identités comparés | `Data` |

## Autres fixations faites par le script, pas des choix sur résultat

- **Projection de B** : au seuil converti en `float32`, comme le diagnostic, pour retrouver `ea2502e1…` exactement. Le mélange garde le type `float32`, si bien qu'un poids nul rend B à l'identique (contrôle sur 4 265/4 265).
- **Décision routée** : on part des codes de B au-dessus du seuil, on en retire tous les enfants de famille, puis on ajoute les enfants dont le parent est dans la fermeture de l'ensemble projeté de B et dont le score atteint t. Viennent ensuite `most_specific` et `drop86`.
- **Garde-fous** : si aucune famille n'atteint les supports, ou si aucune ligne n'a d'enfant actif, le script s'arrête pour amendement, sans relâcher les seuils. Une R vide rend la voie R indisponible, comme le prévoit P9-A 8.2.
- **Doublons de la mémoire** : le nombre de listes de 20 voisins qui contiennent un md5 répété est publié.

## Étapes

1. **`blanc`** : vérification des entrées, reproduction de B, S0 complet, identité du poids nul, voisins de 64 lignes, familles, une époque de la graine 0, puis extrapolation au statut `WITHIN_2H` ou `AMENDMENT_REQUIRED`. Aucun score.
2. **`complet`** : il refuse sans le blanc relu. Il écrit :
   - `s0.json` ;
   - `bras1.json` : bras, témoin, juges G puis R, bootstrap, V-lecture à part, strate de proximité, doublons ;
   - `bras2.json` : familles, t réglé sur V-réglage, puis, sur V-lecture, la couverture, les exclus, le rappel conditionnel et total, la précision, les faux positifs, l'identité, la fréquence × profondeur, le pipeline H/E, la règle G pour les trois graines et la lecture descriptive de la descente.

**Non couvert localement** : les vrais fichiers et le passage à l'échelle sur GPU. Le blanc les exerce.
