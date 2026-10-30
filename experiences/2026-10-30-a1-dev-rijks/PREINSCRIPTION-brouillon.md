# A1-dev : le seuil sur le q des voisins, figé, mesuré une fois sur le dev Rijksmuseum (BROUILLON de préinscription)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1, d'après la recommandation 1 de Grok p7 (`~/Documents/reviews/porkyevitch-apres-phase2-grok.md`).

**Statut : brouillon.** Rien n'est codé ni lancé. Il attend la contre-expertise de Codex sur la phase 2, puis Sonnet (D13) et l'audit de Codex. **Une seule mesure, aucune ligne de test.**

## 0. Question et portée

Sur la validation ICAI, le gain d'A1 sur B vient surtout de **q**, la loi tirée des voisins, et non du décodeur. Un seuil sur q à η = 1 (analyse secondaire) atteint **0,6102** de H-F1 sur V-diagnostic, contre 0,5860 pour B. Source : `~/porkyevitch/experiences/2026-10-29-a1/resultats/diagnostic/diagnostic.json` (`6adb2404`) et sa `LECTURE.md`.

**Question.** Cette règle **figée**, sans aucun réajustement, garde-t-elle un écart positif sur B sur le dev Rijksmuseum ?

**Portée.**
- Une mesure **exploratoire**, sur un dev **déjà ouvert** : regards de la phase 1 et diagnostic de disponibilité D10. Ce dev n'a servi à choisir ni η, ni t, ni aucun paramètre de q.
- Elle peut **réfuter** un transfert espéré. Avec 301 images, elle ne peut pas **couronner** une recette, ni rien promettre sur le test Rijksmuseum, qui n'est pas ouvert.
- Ce n'est ni une recommandation de production, ni une preuve que le décodeur est inutile ailleurs.

## 1. La règle figée (aucune liberté)

**La configuration** est celle que le réglage d'A1 a **scellée** avant toute ouverture de V-diagnostic. Source : `~/porkyevitch-donnees/a1-reglage/a1-reglage/reglage.json`, champ `secondary_threshold_control`, dans le manifeste `8f75d500` :

| K | τ | η | π₀ | t |
|---|---|---|---|---|
| 16 | 0,02 | 1 | 0,25 | 0,3 |

Le seuil `t = 0,3` a été **choisi sur V-réglage** et **vu** sur V-diagnostic (0,6102). On le dit, et on interdit de le bouger.

**La règle**, avec le code d'A1 tel quel :
1. Prendre les K = 16 voisins d'apprentissage par produit scalaire des vecteurs C-RADIO normalisés, sur les seules 81 951 lignes d'apprentissage. Les égalités sont départagées par (fragment, ligne).
2. Construire les atomes fermés dans V. Le poids est `π_j ∝ exp(cos_j/τ + η·ℓ̄_j)`, où ℓ̄_j est la moyenne des logits de B sur T_j ∩ V. On fusionne les empreintes identiques.
3. Mélanger : `q = π₀ δ_{T₀} + (1 − π₀) Σ π_j δ_{T_j}`, où T₀ est la fermeture de l'ensemble projeté de B.
4. Calculer les marginales `m_a`, puis émettre `drop86(most_specific({a ∈ U \ N : m_a ≥ 0,3}))`. C'est `a1_core.threshold_control`, inchangé.

**Comparateur** : B = T-Z, époque 29, seuil 0,65. C'est la référence d'A1, que D10 garde. Les prédictions de B sur le dev sont **les prédictions scellées** du gel de la phase 1 (`predictions__rijks_dev__T-Z.json`, sceau `3c468faa`).

**Colonne descriptive, hors règle** : T\*, la référence publiée de D10, à partir de `predictions__rijks_dev__T_star.json`.

## 2. Population et mesure

- **Le dev Rijksmuseum, et lui seul** : 301 images, 239 composantes. On utilise les vérités `truth_projected` du banc gelé (`frozen.json` `2424b778`), dont seul le membre `dev` est décodé, comme pour D10.
- **Mesure** : H-F1 moyen par image (fonctions E3 `hier_f1`, `drop86`), sur les 301 images, toutes à vérité projetée non vide. On mesure aussi le F1 exact, en descriptif.
- **Unité** : l'image et la composante. Les « 211 paires » de la recommandation de Grok sont l'unité du diagnostic D10, pas celle de ce H-F1.

## 3. Règle de lecture, écrite d'avance

- On calcule `Δ = H(règle figée) − H(B)` sur les 301 images.
- **Bootstrap** : 10 000 tirages de composantes entières, `default_rng(20261101)`, les mêmes tirages pour la règle et pour B. Intervalle percentile bilatéral à 95 %, `numpy.quantile` méthode linéaire. Les tirages indéfinis sont comptés.
- **Transfert observé** si **Δ > 0 et la borne basse de l'IC95 > 0**.
- **Sinon**, si Δ ≤ 0 ou si l'IC95 contient 0, **le gain d'A1 reste un gain de validation ICAI**, et l'article l'écrit tel quel. On ne rouvre ni le test ni le dev pour rattraper.
- **Il s'agit d'une seule comparaison** : il n'y a ni famille, ni correction, ni second essai.
- **Réfuté aussi** :
  - si η, t, K, τ ou π₀ sont changés après la lecture du dev ;
  - si le seuil s'inspire des chiffres de disponibilité de D10 ;
  - si une autre configuration de la grille est essayée sur le dev.
- **Publié dans tous les cas** :
  - Δ, l'intervalle, les nombres d'images et de composantes, et les gains et pertes par image ;
  - les mêmes chiffres par support (peinture, estampe, dessin), descriptifs et sans intervalle ;
  - la strate de forte proximité (premier voisin cos ≥ 0,95), comme dans A1, sans dire « copie » ;
  - la colonne T\*.
- **Interdits** :
  - toute recommandation de production ;
  - « le décodeur est inutile » ;
  - « le musée sera amélioré » ;
  - tout choix de brique ou de seuil tiré de ce résultat.

## 4. Contrôles d'identité, avant la mesure (arrêt sinon)

1. **Dev réencodé** par la recette du gel (IIIF au SHA d'image vérifié, C-RADIO v3 épinglé, vecteurs **et** grilles), comme D10.
2. **B recalculé** sur ces grilles (tête T-Z, `t_z.pt` de `porky-e3-run`, float32, lots de 256). Ses ensembles projetés doivent égaler **exactement** `predictions__rijks_dev__T-Z.json`, avec 0 image différente.
3. **T\*** recalculé sur les vecteurs doit égaler exactement `predictions__rijks_dev__T_star.json`. C'est le même contrôle que D10.
4. **q sur la validation** : la règle figée, recalculée sur V-diagnostic depuis le cache de B (`probabilites_validation.npz` `c7df9d3d`), doit redonner **0,6102** (à 10⁻¹² près, valeur de `diagnostic.json`). On ne lit aucun chiffre nouveau de validation.
5. **π₀ = 1 sur le dev** doit redonner exactement B : c'est le contrôle d'identité d'A1.

## 5. Ce que le code d'A1 doit gagner pour lire le dev

Le code d'A1 (`a1_core.py` `177ef542`, `a1_run.py` `78b1ed98`) ne lit que la validation ICAI depuis le cache de B. Il faut **une nouvelle étape `dev`**, dans un **nouveau script**, pour garder intacts les octets relus d'A1. Ce script réutilise les modules épinglés.

| Besoin | Source réutilisée (octets relus) | Nouveau |
|---|---|---|
| lire le seul membre `dev` de `frozen.json` | `nt_run.dev_items` (D10, `19ec006` et suivants) | — |
| télécharger et réencoder les 301 images (vecteurs + grilles) | `gel_predictions.rijks_features`, `gel_data` (gel `c3a538cc`) | — |
| B sur le dev (tête spatiale T-Z) | `gel_models.load_checkpoint(spatial=True)`, `SpatialPooling`, `probabilities(… grids, 256)` | contrôle 2 contre le sceau |
| T\* sur le dev | `gel_models.vector_head`, comme D10 | contrôle 3 |
| voisins d'apprentissage pour des requêtes du dev | `a1_run` (chargement des atomes d'apprentissage, `neighbours`), à appeler sur les vecteurs du dev | adaptateur : requêtes extérieures à la validation, même normalisation float32 |
| q et le seuil | `a1_run.Image.set_q`, `a1_core.threshold_control` | aucun |
| H-F1, bootstrap par composantes | fonctions E3 d'`a1_core`, bootstrap de `nt_core` | appariement règle / B |
| pilote T4, internet (IIIF), plafond de session, moniteur, refus B3, `CUDA_VISIBLE_DEVICES=0` | pilotes de D10 et A1 | plafond à chiffrer (environ 1 h : réencodage d'environ 5 min, puis CPU) |
| aucune ligne de test | sceau : seuls `predictions__rijks_dev__T-Z.json` et `__T_star.json` sont ouverts | — |

**Sorties** : `dev.json`, descriptif, avec la règle, Δ, l'intervalle et les colonnes. Il ne contient aucune prédiction ligne à ligne du test, puisqu'il n'y en a pas. Le cache d'images est effacé à la fin.

## 6. Coût

Pas d'entraînement : le coût est un réencodage de 301 images, deux têtes en inférence et une règle CPU, en une session T4 d'environ 30 à 60 minutes. Avant le lancement viennent la relecture et l'audit, et un blanc éventuel sur 32 images (contrôles 2 à 5 seulement).
