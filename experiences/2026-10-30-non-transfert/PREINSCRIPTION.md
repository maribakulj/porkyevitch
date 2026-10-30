# Diagnostic du non-transfert : la tête T* contre le vote de ses vingt voisins (dev Rijksmuseum et validation ICAI)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1 (décision **D10**, point 3). Le protocole suit la contre-expertise de Codex p4 (`~/Documents/reviews/porkyevitch-phase1-lecture-codex.md`, section 3) et la lecture de Grok p7 (`porkyevitch-phase1-lecture-grok.md`, « Test qui départage »).

**Rien n'est lancé.** Le script est à relire par Grok p2 puis à auditer par Codex p4.

## 0. Nature et portée

- **Diagnostic descriptif et exploratoire**, motivé par les résultats de la phase 1. Il ne choisit ni tête, ni seuil, ni mélange, ni recette. Il ne retient aucune brique et n'a aucune porte.
- **Question.** Sur les codes **fréquents** de l'apprentissage ICAI (plus de 100 images) et **profonds** (profondeur ≥ 3), la chute observée sur le Rijksmuseum vient-elle de ce que la tête ne les rend plus, de ce que le voisinage d'apprentissage ne les porte pas, ou des deux ? On compare au même diagnostic sur la validation ICAI.
- **Ce qu'il ne départage pas** : catalogue contre vision. Un code absent du voisinage ne prouve pas que la notice a omis un concept visible, ni que l'encodeur ne le contient pas (voir 6). La cause du non-transfert reste **non établie** (D10). L'hypothèse de Grok, « codes fréquents profonds absents des notices », n'est qu'une hypothèse.
- **Pas de nouvelle famille confirmatoire.** Les intervalles sont descriptifs, et aucun seuil de succès n'est inventé après coup.
- **Hors de ce diagnostic** : P9-A, A1 et D3 gardent leurs règles et leurs interdits. Le dev n'entre dans aucune de ces séries par ce biais.

## 1. Données autorisées, et seulement elles

| Banque | Population | Unité de rééchantillonnage |
|---|---|---|
| **Dev Rijksmuseum** | 301 images, 239 composantes, vérités `truth_projected` du banc gelé (`frozen.json`, sha `2424b778…`) | composante |
| **Validation ICAI** | 4 265 lignes du partage historique par groupes md5, dont 4 241 à vérité projetée non vide | groupe md5 |
| **Apprentissage ICAI** | 81 951 lignes, voisins et fréquences seulement | — |

**Interdits** : test ICAI, test Rijksmuseum, IconArt, Emblematica, ICARUS. Le diagnostic n'écrit **aucune ligne de test**. Deux contenants mêlés imposent une lecture sélective :

- **Le banc** `frozen.json` contient le test **avant** le dev. Le script hache le fichier entier, puis place le décodeur directement sur la clé `"dev"` de premier niveau. Il décode **ce seul membre**, et vérifie qu'il se termine exactement à la clé suivante. Les octets du test ne sont **ni décodés en JSON, ni même décodés en UTF-8**. Un test le vérifie avec un faux membre de test qui n'est pas du JSON valide.
- **Le sceau du gel** (sortie `porky-gel-run`, `MANIFEST.json` sha `3c468faa…`) est monté en entier, puisque Kaggle monte une sortie complète. Seuls **deux** fichiers y sont ouverts, `predictions__rijks_dev__T_star.json` et `predictions__rijks_dev__TK.json`, chacun vérifié par son SHA dans le manifeste. Aucun fichier `icai_test` ni `rijks_test` n'est ouvert.

**Incident à consigner.** En préparant ce texte, j'ai affiché les 400 premiers octets de `frozen.json` pour en connaître l'ordre. J'ai ainsi vu les métadonnées d'**une** image du test : pid, adresses IIIF, support, composante. Je n'ai vu ni vérité Iconclass ni prédiction. Rien de cette ligne n'entre dans le diagnostic.

## 2. Ce qui est fixé avant tout calcul

- **Vocabulaire V** : les 7 907 codes historiques (vocabulaire du checkpoint, égal à `vocabulaire.json` du diagnostic de la tête).
- **n_brut(c)** : le nombre d'images d'apprentissage dont l'étiquette **brute** contient c (sur les 81 951 lignes seulement), comme dans les mesures de la phase 1. **Profondeur** : `len(ancestors(c))`, le parseur historique. **Projection** : sans le chapitre 86.
- **Tête T\*** : T-long, époque 27, seuil 0,6. Projection : seuil, puis `most_specific`, puis `drop86`.
  - Sur la validation : le cache float32 relu (`probabilites_validation.npz`, sha `c7df9d3d…`). Contrôle : le SHA des décisions vaut `2d7140ee…`.
  - Sur le dev : la tête est recalculée sur le dev réencodé (voir 4).
- **Vote TK** : les 20 voisins d'apprentissage par produit scalaire des vecteurs C-RADIO, poids négatifs ramenés à 0, normalisés par leur somme. Vote `v_ic` = somme des poids des voisins dont la **fermeture dans V** contient c. Le mélange TK est `α·p + (1 − α)·v`, avec α = 0,75 et seuil 0,5, lus dans E1. Ce sont exactement les opérations de `gel_predictions.votes`, que le script réutilise.
- **Cible principale G_i** : les codes distincts de la vérité projetée de l'image i qui sont **dans V**, avec **n_brut > 100** et **profondeur ≥ 3**.
- **Tranches publiées**, fixées maintenant et jamais redécoupées : la fréquence (5–20, 21–100, > 100) croisée avec la profondeur (1–2, 3–4, 5+). Ce sont les neuf cases, chacune avec son effectif.

## 3. Mesures, par paire (image, code), sur les mêmes paires pour tous

Pour chaque paire (i, c), avec c dans la vérité projetée et dans V :

| Événement | Définition |
|---|---|
| `head_closure` (**R_tête**) | c est dans la fermeture des prédictions de T\* |
| `head_exact` | c est émis exactement par T\* (raccord avec D2, qui compte en codes exacts) |
| `head_above_threshold` | p_c(T\*) ≥ 0,6, avant `most_specific` |
| `vote_available` (**R_vote, disponibilité**) | c est dans la fermeture d'au moins un des 20 voisins **de poids strictement positif** |
| `vote` | la valeur v_ic, publiée par déciles et en moyenne |
| `vote_alone_at_tk_threshold` | v_ic ≥ 0,5 : le vote seul atteindrait le seuil de TK |
| `tk_closure`, `tk_exact`, `tk_above_threshold` | les mêmes événements pour TK, à partir de son score mélangé figé |
| `random_available`, `random_vote` | le contrôle de prévalence (voir 5) |

Le **rappel** est la somme des succès divisée par la somme des |G_i|. On publie :

- R_tête, R_tête exact, R_vote (disponibilité), R_vote au seuil de TK, R_TK et R_aléatoire. Toutes ces grandeurs ont le même dénominateur.
- La **table appariée** tête × voisinage : les deux, tête seule, voisins seuls, aucun. R_vote n'est pas une borne de R_tête : la tête peut prédire un code absent des vingt voisins.
- La **chaîne seuil → `most_specific`** : paires au-dessus du seuil, paires au-dessus du seuil mais non émises exactement, paires émises exactement, paires atteintes par la seule fermeture.
- Le nombre d'images **sans cible** (sans leur inventer un rappel nul), et le nombre de paires hors de V.
- Les mêmes grandeurs dans les **neuf cases** fréquence × profondeur.
- Une table **par code** sur G, avec effectif, R_tête, R_tête exact, disponibilité et vote moyen.
- La **comparaison sur les codes communs** : moyenne par code, à poids égal (pondération fixée ici), sur les codes de G présents dans **les deux** banques. Un code absent d'une banque n'y est pas évaluable : il est laissé de côté, jamais compté comme zéro. Cette comparaison complète les rappels naturels, elle ne les remplace pas.

## 4. Contrôles d'identité, avant toute mesure (arrêt sinon)

- **Dev réencodé.** Les 301 images du dev sont réencodées sur T4 par la recette du gel (téléchargeur IIIF au SHA d'image vérifié, carré gris, 448, C-RADIO v3 à la révision épinglée), avec le code relu du gel. Ensuite :
  - T\* recalculé sur ces vecteurs doit redonner **exactement** les prédictions scellées `predictions__rijks_dev__T_star.json` (0 image différente) ;
  - TK recalculé doit redonner exactement `predictions__rijks_dev__TK.json` ;
  - l'ordre des identités doit égaler celui du sceau.

  Si une seule image diffère, le script s'arrête avant toute mesure.
- **Validation.** On vérifie :
  - le SHA des décisions T\* ;
  - l'ordre des identités du cache ;
  - l'ordre d'apprentissage, égal à celui du gel ;
  - le partage 81 951 / 4 265 et les 4 241 lignes évaluables.
- **Vote.** Pour chaque paire, v_ic recalculé à partir des 20 poids doit égaler la matrice de vote de `votes()` à 10⁻⁵ près.

## 5. Contrôle de prévalence

Pour chaque requête, on tire **20 lignes d'apprentissage distinctes uniformément** (`default_rng(20261031)`, tirage fixé ici, d'abord la validation dans son ordre, puis le dev), puis on calcule la disponibilité et le vote uniforme (1/20 par ligne). Un R_vote élevé obtenu en réunissant vingt annotations fréquentes peut venir de la prévalence, sans voisinage informatif. On publie aussi l'écart R_vote − R_aléatoire.

## 6. Incertitude et lectures écrites d'avance

- **Bootstrap**, sur la cible principale G : 10 000 tirages de groupes entiers, par composantes pour le dev (graine 20261032) et par groupes md5 pour la validation (graine 20261033). L'estimateur est un rapport (succès / paires). Les tirages sont les mêmes pour tous les événements d'une banque, donc les écarts sont appariés : R_vote − R_tête et R_vote − R_aléatoire. Les intervalles sont des percentiles à 95 %, **descriptifs**.
- **Lectures permises**, reprises de Codex. Aucune ne retient une brique ni ne rouvre un test.

| Constat sur le dev, comparé à la validation | Conclusion permise | Conclusion non permise |
|---|---|---|
| Disponibilité basse, peu au-dessus du contrôle aléatoire | Le voisinage actuel ne fournit pas ces annotations ; régler le vote seul a peu de matière | « Les notices ont omis des concepts visibles » ; « l'encodeur ne les contient pas » |
| Disponibilité haute, tête basse | Des annotations utiles sont chez les voisins ; examiner poids, rangs, calibration, projection | « Le seuil est la cause » ; « un nouveau mélange améliorera le musée » |
| Disponibilité et tête hautes, F1 D2 bas | Examiner précision, granularité, exact contre fermé | « Le transfert est résolu » |
| Disponibilité basse sur les deux banques | Les vingt voisins n'offrent pas ce rappel sous cette définition | « La traîne rare explique la chute des codes fréquents » |

- **Suite éventuelle, non autorisée ici.** Trancher l'omission des notices demanderait un regard humain sur le dev seul, échantillonné selon une règle stratifiée, préinscrit à part. Aucun regard humain n'est prévu pour l'instant (D5).

## 7. Calcul et sorties

- **Kaggle T4**, une session d'**au plus 3 600 s** comptées depuis le départ du pilote, sous un moniteur global comme pour A1 et D3 : arrêt de l'ensemble des processus, sorties ≤ 200 Mo, gardes de mémoire et de disque, refus d'une sortie déjà remplie avant le lancement. Internet est actif, pour les images IIIF du dev.
- Le pilote réinstalle `open_clip_torch==3.3.0`, comme le gel, avec torch exigé inchangé, et journalise les versions. **Les contrôles du point 4 sont la vraie garde de l'environnement** : un autre environnement qui ne reproduirait pas exactement les prédictions scellées arrêterait le passage.
- **Entrées montées** : le code relu du gel (`porky-gel-code`, manifeste `c3a538cc…`), sa liaison `porky-gel-config/sources.json` (`60639678…`), les sorties montées par cette liaison (T0, E0–E3, encodeur C-RADIO, banc `porky-banc-gel`, cache C-RADIO), le sceau `porky-gel-run`, le cache `porky-diag-run` v3 et ce dossier.
- **Sortie** : `diagnostic.json`. Il contient les rapports des deux banques, les codes communs, les contrôles d'identité, la recette, le contrôle aléatoire, les empreintes des entrées et les versions. Il ne contient ni ligne de test, ni prédiction ligne à ligne. Le cache des images du dev est effacé à la fin.
- **Lecture** par wA:p1, puis Grok, puis Codex, avant toute suite.

## 8. Code

- `scripts/nt_core.py` : partie pure (numpy). Elle contient les cases, les paires, les résumés, la table appariée, les neuf cases, la table par code, les codes communs et le bootstrap par groupes.
- `scripts/nt_run.py` : partie Kaggle. Elle contient la lecture sélective du dev, la réutilisation de `TrainingReference`, `rijks_features`, `load_checkpoint`, `probabilities` et `votes` du gel, les contrôles du point 4, puis les mesures.
- `scripts/mesure_metrics.py` : copie épinglée (`9a9d4526…`) des mesures de la phase 1, pour `ancestors`, la profondeur, les tranches, `closure` et `drop86`.
- `scripts/kaggle_nt_run.py` : le pilote.
- Tests : `tests/test_nt.py` (9 tests sur données fictives, dont la lecture sélective avec un faux test non décodable) et `tests/test_nt_pilot.py` (3 tests : moniteur, refus d'une sortie remplie, empreintes).
- **Non couvert localement** : le chargement réel, le réencodage et les contrôles d'identité, qui demandent un T4. Ce sont précisément les contrôles du point 4.
