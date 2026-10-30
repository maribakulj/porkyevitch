# Test tranche 300 : les graphes S1b aident-ils la détection du petit élève ? (BROUILLON de préinscription)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1.

**Statut : brouillon.** Il ne sera soumis à Grok p2 puis Codex p4 qu'**après la porte D2**, c'est-à-dire la lecture scientifique du complet du petit élève et la décision de wA:p1 sur l'usage des 300. Rien n'est écrit en code et rien n'est lancé. Les chiffres et empreintes marqués « à figer » le seront dans la version soumise.

**Sources.** La note tranche 300 v3 (`notes/2026-10-30-tranche300-devis-v3.md`, sha `7c51483c…`) et les décisions D6 et D9 de wA:p1 (`~/porkyevitch/DECISIONS.md`). Le petit élève v1 et son amendement (`experiences/2026-10-30-petit-eleve/`) fixent la recette commune. M0 (commit `1324dda`) est descriptif : **aucun choix ci-dessous n'en dépend**.

## 0. Question et portée

- **Question.** Sous la recette du petit élève, réduite au détecteur, l'**ajout** des graphes S1b de la tranche 300 aux 106 graphes Gemini change-t-il la fidélité de détection au professeur Gemini ?
- **Nature.** Le test est **exploratoire**. Il ne donne aucune garantie d'erreur confirmatoire et n'a aucune porte d'achat sur un gain. Une seule issue est décisive, et c'est un arrêt prudent (section 6).
- **Ce que le test ne dit pas.**
  - Il ne parle pas de vérité de localisation : les juges sont des modèles (D5), et il n'y a pas de regard humain.
  - Il ne dit rien de l'apport des relations, qui sont retirées par ablation (section 2).
  - Il ne sépare pas la quantité du professeur : E1′ est informatif, pas factoriel.
  - Un échec ne réfute ni S1b à l'échelle, ni la distillation.
- **Le contraste se nomme « ajout de ces données sous cette recette ».** Il change aussi le nombre de pas d'optimisation, ce qui est écrit (section 5).

## 1. Données (aucune autre)

| Rôle | Images | Professeur | Source |
|---|---|---|---|
| Apprentissage Gemini | les 106 du petit élève v1 | Gemini | `listes.json` du petit élève (`87e45b41…`) |
| Apprentissage S1b | les **240** `apprentissage` du tirage 300 | S1b, **deux passes** (section 3) | `tirage.json` (`5be1c117…`) |
| Réglage (choix d'époque) | les 26 du réglage du petit élève, avec graphe Gemini | Gemini | idem petit élève |
| **Juge principal** | **79 images** : les 26 de l'évaluation du petit élève, plus les **53** des 60 `validation_interne` que Gemini a acceptées | Gemini | `listes.json` ; `~/porkyevitch-donnees/graphes-gemini/val60` (`run.json` `acd3c610…`, `correspondance.json` `3ad5291b…`) |
| Références de fidélité S1b | les 60 `validation_interne` | S1b passes 1 et 2 | `graphes-haiku/tranche300/S1b`, `S1b-r2` |

- **Les 7 images refusées par Gemini** (`p055`, `p070`, `p077`, `p119`, `p123`, `p161`, `p177` dans `val60`, après 3 appels chacune) n'ont **pas** de graphe Gemini. Elles sont **hors du juge principal** : on n'invente pas de graphe. Elles restent dans les références S1b des 60. Leur nombre est publié, comme le rappel des bras sur elles contre S1b, pour signaler un éventuel biais de sélection (images plus difficiles pour Gemini). D9 prévoyait 86 images ; l'écart à 79 vient de ces refus, constatés **avant** toute sortie d'entraînement.
- **La passe Gemini des 60 est figée** (D9) : même modèle, même consigne (`2f20589b…`), même schéma (`cb3f0d87…`), script `graphes_agy.py` `35c21df5…`. Elle a été faite avant tout entraînement de ce test, et aucune n'est refaite.
- **Disjonction** (à vérifier par le code, par nom **et** md5) entre :
  - les 106 + 240 d'apprentissage ;
  - les 26 du réglage ;
  - les 79 du juge et les 60 de référence.
- **Interdits** :
  - les tests ICAI et Rijksmuseum (dev compris), IconArt, Emblematica, ICARUS ;
  - le test de 20 et les exemples du petit élève ;
  - les 30 images du choix de S1b.

## 2. Bras : détecteur sans relations pour tous (D9)

La recette commune est celle du petit élève v1 : encodeur C-RADIO v3 gelé, jetons 28×28, 30 requêtes, 3 couches de décodeur, 8 super-catégories plus « autre » plus « pas d'objet », appariement hongrois (1 × classe, 5 × L1, 2 × GIoU), pertes auxiliaires, poids 0,1 pour « pas d'objet ». **On retire la tête et la perte de relations dans tous les bras**. C'est une ablation nommée « détecteur sans relations ».

| Bras | Apprentissage | Cibles |
|---|---|---|
| **E0** | 106 Gemini | dures, **réentraîné sous ce code** |
| **E1 doux** (principal) | 106 Gemini + 240 S1b | Gemini dures ; S1b douces (section 3) |
| **E1-dur** (variante nommée) | 106 Gemini + 240 S1b | S1b passe 1 seule, poids 1 |
| **E1′** (informatif) | 240 S1b | douces |

- Le **petit élève v1** (avec relations, sur les 106 Gemini), s'il est lu, figure comme **colonne de comparaison**, jamais comme E0.
- **Graines** : 0, 1, 2 pour chaque bras.

## 3. Cibles douces, définies d'avance (note v3, section 2)

1. **Appariement des deux passes S1b** par la règle conjointe de M0 : même super-catégorie et IoU ≥ 0,5. L'appariement est glouton par IoU décroissante, avec départage dans l'ordre de la passe 1 puis de la passe 2. On réutilise le code de `m0.py` (`0e1aa12d…`).
2. **Objet trouvé deux fois** : poids **1**, catégorie commune, rectangle égal à la **moyenne des coins** (millièmes de l'image).
3. **Objet d'une seule passe** : poids **½**, avec son rectangle et sa catégorie. Une paire d'IoU ≥ 0,5 aux catégories différentes donne **deux** cibles de poids ½ ; leur nombre est publié.
4. **Appariement hongrois de l'élève inchangé**, sur toutes les cibles. Le poids **n'entre pas** dans le coût.
5. **Perte** d'une requête affectée à une cible de poids w : `w × CE(classe)` et `w × (5 L1 + 2 GIoU)`. Aucune perte vers « pas d'objet » n'est ajoutée pour cette requête. Une requête non affectée reçoit « pas d'objet » avec le poids 0,1. Les sommes sont normalisées par **Σw** des cibles du lot, et les pertes auxiliaires suivent la même règle. Le ½ est un **poids d'importance**, pas une probabilité calibrée.
6. **Union au-delà de 30 cibles** : on garde d'abord les cibles de poids 1, puis les autres dans l'ordre (poids décroissant, passe 1 avant passe 2, ordre d'apparition). Les retraits sont comptés. Sur les 60 doubles, l'union fait au plus 23 objets par image (compte de M0).
7. Un **rectangle dégénéré** est retiré et compté, comme dans le petit élève.

**Préalable** : la **seconde passe S1b sur les 240** (même lanceur, même consigne que la passe 1), payée et figée avant tout entraînement. Elle n'existe pas encore : `S1b-r2` ne couvre que les 60. Si elle manque ou échoue pour une image, cette image n'a que des cibles de poids ½. Le nombre de ces images est publié.

## 4. Mesures

- **Contraste principal** : **E1 doux − E0**, rappel@30 sans nom (rectangles à IoU ≥ 0,5, appariement glouton du petit élève), sur les 79 images Gemini. Dénominateur : **tous** les objets Gemini des 79, « autre » compris.
- **Publiés à côté**, pour chaque bras et chaque graine :
  - rappel@10 et @20, AP50 sans nom, AP50 par catégorie jugée (≥ 10 objets) ;
  - objets par image à score ≥ 0,5 ;
  - les mêmes mesures sur les **26** et sur les **53** séparément, puisque les deux juges ne viennent pas du même tirage.
- **Références séparées, sur les 60** : fidélité à la passe 1 S1b, à la passe 2, à leur **intersection** (objets de poids 1) et couverture des objets **disputés** (poids ½). Un gain sur la seule intersection s'appelle « fidélité au consensus », pas « meilleure localisation ».
- **E1-dur − E0** et **E1′ − E0**, avec les mêmes mesures. E1′ n'a pas de lecture causale.

## 5. Règles préfixées

- **Budget d'entraînement** : **300 époques** pour tous les bras, comme le petit élève v1 (lot 8, lr 1e-4). L'époque est choisie sur la perte de réglage (26 Gemini du réglage, perte du détecteur seul), évaluée toutes les 5 époques, avec la règle de départage du petit élève. Le **nombre de mises à jour** de chaque bras est publié. Une variante à pas égaux serait un autre bras, non proposé ici.
- **Incertitude** : bootstrap apparié **par image**, avec les **mêmes tirages** pour tous les bras et toutes les graines. Il y a 10 000 tirages, avec une graine à figer (proposée : 20261101). Le jeu des 79, celui des 26 et celui des 53 ont chacun leurs tirages. L'intervalle est un percentile 2,5 / 97,5 %, `numpy.quantile` méthode linéaire. Les tirages indéfinis sont comptés. Ces intervalles sont **descriptifs**.
- Les trois graines partagent les images : on ne combine pas leurs probabilités comme si elles étaient indépendantes.

## 6. Lecture écrite d'avance

- On publie l'estimation et l'intervalle de E1 doux − E0 (et des autres contrastes), par juge et par graine.
- **Arrêt prudent, sans garantie d'erreur.** Si la **borne haute** de E1 doux − E0 sur le juge principal (79) est **< 0 pour les trois graines**, on n'achète pas de graphes S1b pour **cette recette et ce juge**. Ce constat porte sur la fidélité à Gemini, pas sur toute utilité de S1b.
- **Toute autre issue ne lance rien.** Un intervalle qui traverse zéro est indécis sur le signe. Un gain ne décide aucun achat à lui seul.
- **Courbe emboîtée 60 / 120 / 240** : c'est une **proposition**, à décider par wA:p1 puis préinscrire à part. Les préfixes viendraient de l'ordre stratifié du tirage (`5be1c117…`), avec le même réglage et les mêmes juges.

## 7. Calcul (à chiffrer par un blanc avant la série)

- Kaggle T4. Il faut réencoder en 28×28 les 300 images de la tranche (C-RADIO v3, recette du petit élève, identité de grille 8×8 ≥ 0,999 contre l'encodage stocké).
- Chaque bras compte 3 graines, soit 4 bras × 3 = 12 entraînements de tailles différentes. **Le coût n'est pas mesuré** : un **blanc chronométré** le mesurera (quelques pas par bras, contrôle de surapprentissage, cibles douces sur fixture et sur 2 images réelles d'apprentissage). Le pilote applique un plafond de session, comme A1, D3 et D10.
- L'environnement est celui du complet du petit élève (`TESTED_ENV`), sans OWLv2, Florence ni YOLOE, qui ne sont pas des bras de ce test.
- **Planche avant chiffres** : 12 images du juge (6 des 26, 6 des 53, tirage fixé), avec E0, E1 doux, Gemini et S1b. Elle est scellée, puis regardée par wA:p1 et Grok, avec un reçu avant les mesures, comme le petit élève.

## 8. À figer dans la version soumise

- Les SHA des graphes S1b de la seconde passe sur les 240.
- La liste exacte des 79 avec leurs SHA de graphe.
- La graine du bootstrap et celle de la planche.
- Le code (perte douce, appariement des passes) et ses tests.
- Le manifeste.
