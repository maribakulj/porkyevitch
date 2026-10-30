# A1 v2 : code, blanc et notes qui le lient

30 octobre 2026. Claude wA:pH. Le code applique la préinscription v2 (sha `ed452dc3…`, feu vert de Grok p2, audit de Codex p4 en file). **Rien n'est lancé.** Le cache `c7df9d3d…` n'est lu que sur Kaggle, dans la sortie montée de `mabaku/porky-diag-run` v3, et seulement après la relecture de ce code.

## Fichiers

- **`scripts/a1_core.py`** (numpy et scipy) :
  - fonctions E3 transcrites ;
  - modèle q (atomes, masses, fusion exacte, atomes de masse nulle gardés) ;
  - tri GFM, certificat, PLNE contraint exact avec départage, égalités résiduelles comptées ;
  - contrôle « même q, seuil ».
- **`scripts/a1_run.py`** : les étapes `blanc`, `reglage` et `diagnostic`.
- **`scripts/kaggle_a1_run.py`** : pilote CPU, un seul fil, SHA des scripts et des entrées vérifiés.
- Tests :
  - `tests/test_a1_core.py` (8) : parité E3, tri fermé et optimal pour chaque k (exhaustif), décodeur égal à l'exhaustif avec émission (branche du solveur exercée), PLNE de fermeture seule égal au tri, cas à maximal interdit, π₀ = 1, contrôle par seuil, projection `float32` ;
  - `tests/test_a1_run.py` (4) : E0 et E1 sur données factices, non-régression HiGHS, départages, et étapes `reglage` puis `diagnostic` de bout en bout, avec refus d'un reçu sans le regard de Grok.

## Deux défauts de HiGHS trouvés par E1 avant tout calcul réel

1. **Le prétraitement (presolve) de HiGHS, avec scipy 1.18.1, rend un faux optimum.** Sur un problème factice de fermeture seule, il a déclaré une valeur de 0,45380 avec un écart nul. Or l'ensemble fermé du tri vaut 0,45532, et il est faisable pour ce même PLNE (vérifié contrainte par contrainte). Sans prétraitement, la valeur juste est retrouvée. Le PLNE tourne donc **sans prétraitement**, et ce cas est un test de non-régression.
2. **HiGHS s'arrête à un écart absolu de 10⁻⁶**, réglage que scipy ne laisse pas modifier. Avec des poids de l'ordre de 10⁻⁸ à 10⁻¹, cela donnait 110 écarts entre 10⁻⁹ et 10⁻⁶ sur 9 366 problèmes. L'objectif et la ligne de valeur du départage sont donc mis à l'échelle, le plus grand poids valant 10⁶. Résultat : **0 écart sur 9 366 problèmes**, pire différence 4·10⁻¹⁶.

Sans E1, ces deux défauts auraient pu passer pour un « mécanisme » ou une erreur du tri. Ils sont consignés pour l'audit.

## Les notes de Grok p2 (section 7.3), reprises dans le code

| Note | Où |
|---|---|
| `PART` et `TOKEN` transcrits avec les quatre fonctions ; N teste comme `drop86` (`strip()` puis préfixe 86) | `a1_core.py`, en tête ; `non_emissible` |
| L'ensemble vide est réalisable avec utilité 0 : il est émis si un PLNE est irréalisable ou si la meilleure valeur certifiée est ≤ 0 | `decode` : `best_val = 0`, chemins `empty` et `solver_empty` |
| Graine et méthode du bootstrap figées : `default_rng(20261029)`, percentile (numpy linéaire), 10 000 tirages par groupes md5. Les « 64 premières » sont l'ordre de `identites_validation.json` restreint à V-réglage, et les 8 du blanc sont les premières de ces 64 | `a1_run.py` : `BOOT_SEED`, `common`, `stage_blanc` |
| `reglage.json` scelle les 108 scores, plus la configuration q et le seuil t de l'analyse secondaire | `stage_reglage` |
| Version de scipy (donc de HiGHS) et un seul fil : `OMP_NUM_THREADS=1` dans le pilote, versions inscrites. Le complet exige les versions du blanc relu. Les égalités résiduelles HiGHS sont comptées par un PLNE de vérification avec coupe | `versions()`, `kaggle_a1_run.py`, `residual_tie` |
| Une image non certifiée entre dans la part publiée ; le résultat y est le décodeur exécuté, pas un optimum certifié | `diagnostic.json`, champ `certification` |
| E1-(i) compare des valeurs à 10⁻⁹ ; l'égalité des ensembles relève d'E1-(ii) et E1-(iii) ; le second PLNE de départage fait partie du logiciel | `e1_identity`, `e1_pi0_one`, `decode_checked` |
| Le seuil « même q » retire N avant `most_specific` ; c'est le bras de comparaison, pas le décodeur | `threshold_control` |

Autres fixations faites dans le script, qui ne sont pas des choix sur résultat :
- **B** est projeté au seuil converti dans le type des probabilités (`float32`), comme le diagnostic, pour retrouver exactement le SHA des décisions `ea2502e1…`.
- **Seuil du contrôle** : en cas d'égalité, le plus petit t.
- **Planche E2** : 12 groupes md5 de V-réglage tirés par `default_rng(1029)`, la première ligne de chaque groupe. Elle montre les codes et les utilités sous q, sans vérité ni score.
- **Voisins** : vecteurs re-normalisés en float32, égalités départagées dans l'ordre canonique d'apprentissage. La part des 20 premiers voisins identiques à ceux du produit scalaire brut de TK est publiée.

## Étapes, chacune relue avant la suivante

1. **`blanc`** (CPU, au plus 20 min visées). Il fait :
   - E0 complet ;
   - B depuis le cache (SHA, décisions, H-F1) ;
   - E1-(i) sur les 8 premières images de V-réglage à K = 4 ;
   - E1-(ii) sur 64 images ;
   - les chronométrages : 16 images de V-réglage par K et 2 configurations, une identité à K = 64, et le contrôle par seuil ;
   - l'extrapolation, avec le statut `WITHIN_2H` ou `AMENDMENT_REQUIRED`.

   Aucun score n'est publié.
2. **`reglage`** : il refuse sans le blanc relu ni avec un autre environnement. Il fait ensuite :
   - E0 ;
   - E1 complet, soit 64 images à K = 4, 16 à K = 64, puis π₀ = 1 sur 4 241/4 241 ;
   - la grille des 108 configurations sur V-réglage ;
   - le contrôle par seuil au même q, et l'analyse secondaire ;
   - le sceau `reglage.json` ;
   - la planche E2 et `MANIFEST_REGLAGE.json`.

   V-diagnostic n'est jamais décodé à cette étape.
3. **Regard de la planche** par wA:p1 puis Grok. Le reçu `recu_planche_a1.json` porte `{"stage": "planche_a1_regardee", "reglage_manifest_sha256": …, "regards": [wA:p1, Grok…]}`.
4. **`diagnostic`** : la seule ouverture de V-diagnostic (E3). Elle calcule :
   - le contraste du mécanisme, avec l'ordre des cas ;
   - la règle G ;
   - la strate de forte proximité, avec les contributions des deux strates ;
   - le témoin du tri ;
   - la certification ;
   - les tranches, la latence P50/P95/P99 sur un fil, et ce qui est toujours publié.

**Non couvert localement** : le chargement des vrais fichiers et le passage à l'échelle. Le blanc les exerce.
