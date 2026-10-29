# Petit élève du jalon 5 : préinscription, BROUILLON v0

30 octobre 2026. Claude wA:pH (remplaçant de Codex maths p6), pour la décision D2. Sources : BOUCLE.md (jalon 5), D1 (DECISIONS.md, points 1 à 4 : élève avant 5 000 graphes, OWLv2 base comme référence, mesures sur apprentissage et dev seulement) et l'avis D2 de Grok p7 (`~/Documents/reviews/porkyevitch-d2-grok.md`). **Brouillon : rien n'est lancé.** D2 attend la contre-expertise de Codex p4. Viendront ensuite la version 1, la relecture Grok p2 et l'audit Codex p4.

## 0. Réponse franche : ~100 graphes suffisent-ils à dire quelque chose ?

Comptage fait sur les fichiers, avant tout entraînement. Sur 178 graphes Gemini acceptés, les ensembles réservés en contiennent 72 : 2 des 3 exemples, 26 des 30 du réglage, 26 des 30 de l'évaluation et 18 des 20 du test de 20 (les autres n'ont pas de graphe accepté). Il reste **106 graphes pour l'entraînement** : 1 029 objets, 1 306 relations, environ 8 objets par image.

- **Noms** : 364 noms distincts, dont 222 vus une seule fois. Seuls 18 noms ont au moins 10 occurrences, 2 en ont au moins 30 (« man » 202, « woman » 91).
- **Relations** : celles qui ont au moins 20 occurrences sont presque toutes spatiales (left of 173, above 137, inside 122, behind 120, right of 99, on 94, stands on 78, wears 73, below 63, in front of 48). Les relations d'action sont rares : holds 66, looks at 48, sits on 30, mais **kneels before 6, points at 6, touches 7, carries 3, rides 2**. Ces graphes sont faits avec l'ancienne consigne Gemini, pas avec le schéma à neuf actions de Grok (`porkyevitch-schema-relations-grok.md`).
- **Taille des objets** : le plus petit côté vaut 149 millièmes en médiane. **40 %** des rectangles ont un côté inférieur à une cellule de la grille 8×8 (125 millièmes), mais seulement 2,5 % sous une cellule 28×28.

**Ce que 106 graphes peuvent dire** :
1. si la chaîne apprend et à quel **débit**. Le débit ne dépend pas de la taille des données ;
2. si la tête **localise les objets à la manière du professeur**, sans tenir compte du nom : rappel et AP à IoU 0,5 sur les **244** objets (310 relations) des 26 graphes d'évaluation, plus 163 objets dans les 18 du test de 20. La demi-largeur d'un intervalle à 95 % sur une proportion est alors d'environ ±0,06. C'est assez pour voir un écart de 0,15 avec un témoin ;
3. une **classification grossière** en environ 8 super-catégories (section 2) ;
4. un premier signal **descriptif** sur 3 à 5 relations fréquentes (spatiales, plus holds et wears).

**Ce qu'ils ne peuvent pas dire** : les noms ouverts, les relations d'action du schéma, l'utilité iconographique, une différence entre les trois régimes de Marcel (elle serait sous le bruit), et toute comparaison fine avec OWLv2 au-delà des super-catégories. Les présenter autrement serait surinterpréter.

**Minimum pour la question qui compte** (actions et objets nommés), en extrapolant linéairement les fréquences du pilote, ce qui n'est pas une mesure :
- environ **50 exemples d'entraînement et 30 tenus à part** par classe ou relation jugée ;
- « kneels before » apparaît environ 0,06 fois par image, donc il faut **≈ 900 images** pour 50 exemples ; « carries », environ 0,03 par image, demande **≈ 1 800 images** ;
- pour les noms : 49 noms ont aujourd'hui au moins 5 occurrences, donc environ 50 classes nommées auraient 50 exemples vers **1 000 images**.

Le minimum utile est donc **de l'ordre de 1 000 à 2 000 graphes, faits avec la nouvelle consigne d'actions**. Les 106 graphes servent de **porte** : si la tête ne localise même pas les objets mieux que les témoins, ou si elle est plus lente qu'OWLv2 sans faire mieux, payer ce lot n'est pas justifié. Cela va dans le sens de Grok : une tranche de quelques centaines d'images d'abord, puis l'échelle selon la courbe d'apprentissage.

## 1. Données et partages, figés

- Entraînement : les **106** graphes Gemini acceptés hors exemples, réglage, évaluation et test de 20 (`ensembles.json`, `test20/selection.json`). La liste et son empreinte sont publiées avant l'entraînement.
- Choix de l'époque : les **26** graphes Gemini du **réglage**.
- **Mesure principale** : les **26** graphes Gemini de l'**évaluation**, regardés deux fois par des humains (sur S1b). Mesure secondaire, rapportée à part : les 18 du test de 20.
- Toutes ces images viennent de l'**apprentissage ICAI** du pilote. Interdits : test ICAI, validation ICAI pour ce travail, banc Rijksmuseum, test IconArt (D1 et Grok D2 : pas même un contrôle descriptif), Emblematica.
- **Rectangles** : la règle préinscrite du pilote s'applique (Gemini si l'IoU médian Gemini/SAM 3 est ≥ 0,7, sinon SAM 3 pour les objets retrouvés). Si l'étape SAM 3 n'a pas été faite, on prend les rectangles Gemini, et on le note.
- Le professeur ne voit jamais de code (BOUCLE.md). Les codes Iconclass de ces images ne servent qu'au régime « assemblé » (section 6), qui n'est pas dans ce lot.

## 2. Vocabulaire fermé v0

Table de correspondance **figée avant l'entraînement**, construite sur les seuls noms des 106 graphes, par mots-clés écrits à la main (aucun modèle). Elle mène à **8 super-catégories + « autre »** :

1. personne (man, woman, child, people, saint…) ;
2. être surnaturel ou ailé (angel, winged child, winged figure, putto…) ;
3. animal ;
4. vêtement ou parure ;
5. objet porté ou tenu (staff, book, sword, cross, key…) ;
6. architecture ou mobilier ;
7. paysage, végétal, ciel ;
8. texte, inscription, armoiries.

La part d'« autre » est publiée. Une table refaite après résultat devient une nouvelle brique.

**Relations v0** : celles qui ont au moins 20 occurrences d'entraînement (13 aujourd'hui), plus « aucune ». Les autres sont regroupées et non jugées. On renomme `left of`/`right of` selon le sens des rectangles, sans les inverser.

## 3. Élève

- **Encodeur** C-RADIOv3-L figé, la même révision et le même prétraitement que l'encodage v3 (448, carré gris 128). **Grille native 28×28** (784 jetons de 1 024 dimensions), obtenue en **réencodant** les environ 178 images du pilote, quelques minutes de T4. La grille 8×8 stockée est trop grossière pour 40 % des rectangles. On l'entraîne quand même comme **bras témoin nommé** (« 8×8 »), parce qu'elle seule permettrait le régime assemblé sur ICAI sans réencodage (section 6).
- **Tête objets** de type DETR :
  - N = 30 requêtes apprises (au plus 28 objets par graphe dans le pilote) ;
  - 3 couches de décodeur (attention croisée vers les jetons, avec position 2D sinusoïdale), d = 256 ;
  - sorties : rectangle (cx, cy, w, h en sigmoïde) et 9 classes + « pas d'objet » ;
  - **appariement hongrois** avec les coûts de DETR (1 × classe, 5 × L1, 2 × GIoU), pertes auxiliaires par couche, poids 0,1 pour « pas d'objet ».
- **Tête relations** : pour chaque paire ordonnée de requêtes appariées, on concatène les deux plongements et la géométrie (Δcx, Δcy, log des rapports de taille, IoU), puis un MLP à 2 couches donne une sortie multi-étiquette sur les relations v0. Les paires sont prises **sur l'appariement hongrois des objets**. Les paires sans relation chez le professeur servent de négatifs, sous-échantillonnés à 3 pour 1.
- **Entraînement** : AdamW 10⁻⁴, lot 8, au plus 300 époques, époque choisie sur la perte du réglage. Pas d'augmentation en v0 : un retournement inverserait gauche et droite, et les traits devraient être réencodés. **Trois graines** (0, 1, 2) : le coût est de quelques minutes, et la variance entre graines est l'information principale à cette taille. Chaque graine est publiée.

## 4. Mesures, toutes contre le professeur sur les 26 images d'évaluation, toutes descriptives

- **Objets sans nom** : rappel à IoU 0,5 pour 10, 20 et 30 prédictions, AP50 indépendante de la classe, nombre d'objets par image comparé au professeur.
- **Objets par super-catégorie** : AP50 des catégories qui ont au moins 10 instances tenues à part ; les autres sont dites « non jugées ».
- **Relations** : (a) prédicat à objets appariés connus, du type PredCls, en rappel@1 par relation à au moins 10 instances tenues à part ; (b) rappel@20 des triplets du professeur, avec sujet et objet à IoU ≥ 0,5. Rien sur les actions rares.
- **Témoins**, sans lesquels la mesure ne veut rien dire avec si peu de données :
  - (i) **a priori** : rectangles moyens par super-catégorie, appris sur l'entraînement, et relations les plus fréquentes par paire de catégories ;
  - (ii) **OWLv2 base** (`google/owlv2-base-patch16-ensemble`, Apache-2.0, notée), sans apprentissage, interrogé avec les 8 noms de super-catégories, sur les mêmes images, avec le même appariement et le même seuil fixé d'avance (0,1).
  - Florence-2, nommée en D1, est reportée à la version 1 si Codex p4 la juge nécessaire dès ce palier.
- **Débit**, mesuré sur T4 (lot 1 et lot 32) et sur CPU 8 vCPU (Kaggle). On sépare l'encodeur et les têtes, et on mesure OWLv2 base sur le même matériel. Les cibles de D1 (2 img/s sur T4, 0,2 img/s sur CPU) sont **indicatives**.
- **Accord avec un autre professeur** (descriptif) : sur les 30 images d'évaluation, accord de l'élève avec S1b, Haiku dans sa version retenue. Ce n'est pas une vérité. Les deux regards humains comptent 47 et 98 actions justes sur les mêmes graphes (Grok D2).
- **Planche avant les chiffres** : 12 images d'évaluation, avec les rectangles et relations de l'élève et du professeur. Regard de wA:p1 puis de Grok, sans retouche de la recette.
- Incertitude : bootstrap par images (2 000 tirages) et écart entre les 3 graines.

## 5. Lecture déclarée d'avance, pour la décision D2

Ce n'est pas une règle d'adoption de modèle. Ce palier dit seulement s'il faut payer la première tranche d'annotation.

- **Signal** si les deux conditions sont réunies :
  - le **rappel@30 sans nom** de l'élève 28×28 dépasse l'a priori d'au moins **+0,15**, avec une borne basse à 95 % > 0, pour les 3 graines ;
  - son **AP50 par super-catégorie** n'est pas inférieure à celle d'OWLv2 base de plus de **0,05**, avec un débit au moins égal sur T4.
  
  Dans ce cas, la première tranche S1b de quelques centaines d'images, stratifiée, avec une seconde passe sur un sous-ensemble (Grok D2), est justifiée.
- **Pas de signal** si l'élève ne dépasse pas l'a priori, ou s'il est battu par OWLv2 base à la fois en AP et en débit. On ne paie pas de lot : on réexamine l'encodeur figé, ou on prend OWLv2 comme fournisseur de rectangles.
- **Indécidable** si la variance entre graines dépasse l'écart mesuré. On le dit, sans le transformer en signal.
- **Relations** : description seulement, à ce palier.

## 6. Les trois régimes de Marcel, seulement esquissés (hors de ce lot)

- **Séparé** : les têtes objets et relations, et la tête Iconclass T-Z, vivent sur le même encodeur figé, sans échange. C'est ce lot.
- **Séparé puis assemblé** : la tête Iconclass reçoit, en plus des jetons, les plongements des requêtes objets (et relations) de l'élève figé. On apprend une correction sur l'apprentissage ICAI, mesurée sur la validation ICAI avec la règle G. Cela suppose d'exécuter l'élève sur les 81 951 images. Avec la grille 28×28, il faut réencoder (environ 138 Go de cache, devis de p6) ; avec la grille 8×8, ce n'est pas nécessaire, d'où le bras témoin 8×8.
- **Commun** : une **partie partagée entraînable** (adaptateur léger sur les jetons, ou LoRA des derniers blocs) sous les deux familles de têtes. Pertes masquées : la perte Iconclass sur les images ICAI, les pertes de graphe sur les images à graphe. D1 rappelle que des têtes disjointes sur un encodeur figé ne transfèrent rien. Ce régime n'a de sens qu'avec un nombre de graphes du même ordre que le minimum de la section 0.

## 7. Coût prévu, non mesuré

- Réencodage 28×28 d'environ 180 images : moins de 10 min de T4.
- Têtes : 3 graines × 2 grilles, environ 30 min de T4.
- OWLv2 base sur les 26 + 18 images et les chronométrages : environ 15 min de T4 et 30 min de CPU.

Total ≤ 1,5 h de T4 et 1 h de CPU, sur un seul créneau Kaggle de wA:p1. Sorties ≤ 2 Go dans `~/porkyevitch-donnees/maths/petit-eleve/`. Rien de lourd sur le Mac.

## 8. Ce qui reste à écrire pour la version 1

La table de correspondance des noms, publiée avec son empreinte. Le script (préparation, réencodage, têtes, OWLv2, chronométrage) avec son blanc. La liste des 106, 26 et 18 identifiants avec leurs empreintes. La vérification de l'étape SAM 3 du pilote. La position de Codex p4 sur Florence-2 et sur ce minimum.
