# Petit élève du jalon 5 : préinscription, version 1

30 octobre 2026. Claude wA:pH, remplaçant de Codex maths p6. Elle remplace le brouillon v0.1 (`PREINSCRIPTION-brouillon.md`, gardé tel quel pour la trace).

- **Origine** : décision D2 de wA:p1 (`~/porkyevitch/DECISIONS.md`, 30/10).
- **Réserves intégrées** : celles de la contre-expertise de Codex p4 (`~/Documents/reviews/porkyevitch-d2-codex.md`). Chacune est repérée **[C1]** à **[C6]** dans le texte.
- **Déjà corrigés en v0.1** : les deux blocages de Grok p2.
- **Suite** : relecture par Grok p2, puis audit par Codex p4. **Rien n'est lancé.**

Écrite avant tout entraînement. Ce que ce document ne fixe pas reste hors de la lecture.

## 0. Ce que ce prototype peut dire, et ce qu'il ne peut pas dire

**Les données.** Sur les 178 graphes Gemini acceptés du pilote, les ensembles réservés en contiennent 72 :
- 2 des 3 exemples ;
- 26 des 30 du réglage ;
- 26 des 30 de l'évaluation ;
- 18 des 20 du test de 20.

Restent **106 graphes d'entraînement** : 1 029 objets, 1 306 relations. Le test de 20 et les exemples sont **fermés** : ni entraînement, ni mesure, ni témoin, ni chronométrage.

**Ce qu'on peut en attendre :**
- savoir si la chaîne fonctionne ;
- détecter des échecs grossiers ;
- mesurer le débit ;
- savoir si la tête localise les objets *à la manière du professeur* mieux qu'un témoin naïf.

**Ce qu'on ne peut pas en attendre :**
- noms ouverts ;
- actions rares ;
- utilité iconographique ;
- différence entre les trois régimes de Marcel ;
- comparaison fine avec OWLv2 au-delà de quelques super-catégories.

**Taille [C2].** Les 244 objets de l'évaluation sont regroupés dans **26 images**. Ce ne sont pas 244 observations indépendantes, et l'argument « ±0,06 » du brouillon est retiré.
- La taille effective dépend des corrélations entre objets d'une même image. Le niveau minimal d'incertitude est donc le **bootstrap apparié par image**.
- Les trois graines ne multiplient pas le nombre d'images.
- Le seuil de +0,15 est une **porte de dépense** choisie, pas un effet dont la puissance serait acquise.
- Les « 1 000 à 2 000 graphes » du brouillon restent une **extrapolation des fréquences Gemini** (ancienne consigne), pas une borne de taille pour S1b. On compte séparément occurrences et images, entraînement et référence tenue à part.

**Lien avec la tranche de 300 (D2, point 3).** La tranche S1b de 300 images est tirée et annotée en parallèle (`experiences/2026-10-30-tirage-300`). Son **usage pour l'entraînement** attend l'issue de la section 5. Ce texte ne l'utilise pas.

## 1. Données et listes, figées

**Référence [C1].** Les graphes Gemini sont une **référence de fidélité** : ce que l'élève reproduit du professeur. Ce ne sont **pas** une vérité humaine de localisation.
- Les deux regards humains déjà faits (47 et 98 actions justes) portent sur les graphes S1b et S3b, pas sur une annotation exhaustive des rectangles Gemini.
- Les 30 images qui ont servi à choisir S1b sont une **validation de développement réutilisée**. Elles ne confirment pas de façon indépendante la qualité du professeur.

**Rectangles.** La règle du pilote (amendement 1) prend les rectangles de SAM 3 quand l'IoU médian Gemini/SAM 3 est < 0,7. **L'étape SAM 3 n'a pas été faite** : aucune sortie n'existe. On prend donc les rectangles Gemini, et on le note.
- Un rectangle est remis dans l'ordre et borné à [0, 1000].
- Un rectangle dégénéré est retiré avec ses relations, et compté.

**Les listes** sont dans `listes.json` (`scripts/pe_listes.py`, comptage de fichiers seulement, sans mesure). Chaque entrée porte le nom, le md5, le fragment et la ligne ICAI, le SHA-256 de l'image, celui du graphe Gemini et, pour l'évaluation, celui du graphe S1b.

| liste | images | graphes Gemini utilisés | rôle |
|---|---|---|---|
| entraînement | 106 | 106 | apprentissage des têtes, prototypes et a priori des relations |
| réglage | 30 | 26 (4 sans graphe ignorées) | choix de l'époque, sur la perte |
| évaluation | 30 | 26 | mesure principale (26) ; accord avec S1b (26 + 4) |
| planche | 12 de l'évaluation (avec graphe) | — | regard avant les chiffres, `default_rng(1230)` |
| surapprentissage | 8 de l'entraînement | 8 | contrôle de panne [C3], `default_rng(1231)` |
| chronométrage | 96 de l'entraînement | — | débit, 3 lots de 32, `default_rng(1232)` |
| exemples | 3 | fermé | — |
| test de 20 | 20 | fermé | — |

Les fichiers des ensembles fermés ne doivent pas être dans les entrées Kaggle : le script refuse de démarrer s'il en trouve un. Toutes ces images viennent de l'apprentissage ICAI du pilote. Interdits : test ICAI, validation ICAI, banc Rijksmuseum, test IconArt, Emblematica. Le professeur ne voit jamais de code.

## 2. Ontologie [C4]

**Table des noms** : `noms.json`, construite **sur les seuls noms des 106 graphes d'entraînement**.
- Les règles sont dans `scripts/pe_common.py`, écrites à la main, sans modèle. Chaque règle est une liste de mots-clés reconnus comme mots entiers, le pluriel en -s ou -es compris.
- La **première règle qui s'applique l'emporte**. L'ordre fixe les priorités :
  1. exceptions nommées (« coat of arms » → texte, « hair ornament » → parure, « clock face » → objet, « barrel vault » → construction…) ;
  2. **parties du corps → « autre »**, exprès (hand, head, beard…) : ce ne sont pas des objets de la scène ;
  3. jouets et dépouilles → objet (« hobby horse », « animal skin ») ;
  4. **surnaturel avant personne** (« winged child » est surnaturel, pas personne) ;
  5. texte, inscription, armoiries et image dans l'image (page, cadre, peinture, ornement) ;
  6. **vêtement et parure avant objet** (« bow tie » est une parure, « bow » un objet). Le nimbe est rangé en parure ;
  7. sculpture → construction (une statue n'est pas une personne) ;
  8. personne ;
  9. animal ;
  10. objet mobile, porté, tenu ou posé ;
  11. construction, mobilier et véhicule ;
  12. paysage, végétal et ciel.
- **Noms inconnus** : un nom sans règle va dans « autre ». Les mêmes règles s'appliquent **sans retouche** au réglage, à l'évaluation et à S1b. La part d'« autre » est publiée pour chaque ensemble ; elle vaut 5 objets sur 1 029 à l'entraînement.
- Super-catégories : personne (249 objets d'entraînement), construction (197), paysage (143), texte et image (132), objet (125), vêtement et parure (81), animal (65), surnaturel (32), autre (5).
- Une table refaite après lecture d'un résultat devient une nouvelle brique.

**Relations.** On garde les 13 prédicats du professeur qui ont au moins 20 occurrences à l'entraînement, sans les renommer : left of, above, inside, behind, right of, on, stands on, wears, holds, below, in front of, looks at, sits on.
- Tous les autres forment **une sortie « autre_relation »**. Ils ne sont **jamais** transformés en « aucune ».
- Une relation que le professeur ne mentionne pas n'est pas pour autant fausse. Les négatifs et le rappel des relations sont **relatifs à ce professeur incomplet**.

## 3. Élève

- **Encodeur** C-RADIOv3-L figé, recette v3 inchangée (carré gris 128, 448, bicubique, autocast fp16), grille native **28×28** réencodée pour les 162 images utilisées.
  - **Contrôle d'identité** : la moyenne adaptative 8×8 du réencodage doit redonner la grille 8×8 stockée (cosinus minimal par cellule ≥ 0,999), sinon arrêt.
  - Le bras **8×8** est entraîné comme témoin nommé. Il n'entre pas dans la lecture.
  - La taille d'une cellule n'est pas un seuil dur de détectabilité [Codex] : plusieurs cellules et le contexte peuvent coder un petit objet.
- **Tête objets** de type DETR :
  - 30 requêtes, 3 couches de décodeur (d = 256, 8 têtes, position 2D sinusoïdale sur les jetons) ;
  - classes : 8 super-catégories + autre + « pas d'objet » ;
  - **appariement hongrois** (coûts 1 × classe, 5 × L1, 2 × GIoU), pertes auxiliaires par couche, poids 0,1 pour « pas d'objet ».
  - Les rectangles sont appris dans le repère du carré que voit l'encodeur, puis ramenés à l'image.
- **Tête relations** : pour les paires ordonnées de requêtes appariées, on concatène les deux plongements et la géométrie (Δcx, Δcy, log des rapports de largeur et de hauteur, GIoU, distance), puis un MLP à 2 couches donne une sortie multi-étiquette sur 13 + 1 relations.
  - Négatifs : les paires sans relation chez le professeur, tirées à 3 pour 1 à l'entraînement, toutes prises sur le réglage.
- **Entraînement** : AdamW 10⁻⁴ (décroissance 10⁻⁴), lot 8, écrêtage 0,1, au plus 300 époques, perte du réglage tous les 5 époques, meilleure époque gardée. Pas d'augmentation. Graines 0, 1 et 2, chacune publiée.
- On n'ajuste **rien** sur l'évaluation pour faire passer une issue.

## 4. Mesures

Toutes les mesures portent sur les **26 graphes Gemini d'évaluation**, sont descriptives, et sont prises contre le professeur.

- **Objets sans nom** :
  - rappel à IoU 0,5 pour 10, 20 et 30 prédictions (appariement glouton de type COCO, par score décroissant) ;
  - AP50 indépendante de la classe (interpolation sur 101 points) ;
  - objets par image (score ≥ 0,5).
- **Par super-catégorie** : AP50 des catégories qui ont au moins 10 objets dans l'évaluation, « autre » exclu. Ce sont les « catégories jugées », **les mêmes pour tous les systèmes**.
- **Relations** :
  - (a) **prédicat sur paires appariées** : sujet et objet du professeur appariés à des requêtes. Les catégories ne sont pas données, donc **pas d'étiquette PredCls**. Rappel@1 par prédicat, jugé à partir de 10 instances ;
  - (b) rappel@20 des triplets, avec sujet et objet à IoU ≥ 0,5 ;
  - rien sur les actions rares.
- **Témoins** :
  - (i) **a priori** : 30 rectangles prototypes (k-moyennes déterministe sur les rectangles d'entraînement, `default_rng(2031)`), notés par leur fréquence, identiques pour toutes les images. Pour les relations, le prédicat le plus fréquent par paire de catégories ;
  - (ii) **OWLv2 base** (`google/owlv2-base-patch16-ensemble`, Apache-2.0) [C5]. Une requête texte figée par super-catégorie (`OWL_QUERIES`), seuil 0,1. Liste sans classe : union des 8 requêtes, NMS à 0,5. Ses boîtes sont ramenées du carré complété à l'image. Le nombre d'objets « autre », qu'OWLv2 n'interroge pas, est publié ; ils restent au dénominateur du rappel sans classe pour tous les systèmes ;
  - (iii) **Florence-2 base** (`microsoft/Florence-2-base`, MIT) [C5], tâche `<OD>` sans texte, donc sans recherche de prompt. Elle ne donne pas de score : on mesure le rappel sur toutes ses boîtes, le nombre de boîtes et le débit. **Descriptive** : elle n'entre pas dans la lecture. Si elle ne se charge pas dans l'environnement figé, c'est noté comme dérogation à D1. On ne revendique alors pas d'avoir battu toutes les références.
- **Accord avec S1b** (descriptif) : rappel@30 de l'élève (graine 0, 28×28) contre S1b, sur les 30 images d'évaluation. Les 26 avec graphe Gemini et les 4 sans graphe sont rapportées à part. Ce n'est pas une vérité.
- **Planche, avant les chiffres** : 12 images, trois panneaux séparés (élève, Gemini, S1b). Conventions : rectangles rouges, élève au score ≥ 0,5. Regard de wA:p1 puis de Grok, sans retouche ensuite.
- **Débit** [C6] :
  - Mesuré sur T4, sur le **corpus de chronométrage fixe de 96 images d'entraînement**, ce qui ne dépense aucune image tenue à part et règle la question des lots de 32 avec 26 images.
  - Images décodées avant la mesure pour tous les systèmes, prétraitement chronométré à part sur CPU.
  - autocast fp16 pour tous, `cuda.synchronize`, une passe d'échauffement puis 5 répétitions : médiane, minimum et maximum.
  - On distingue l'élève complet (encodeur et têtes), les têtes seules et le lot 1.
  - OWLv2 tourne au plus grand lot ≤ 32 qui tient en mémoire, et ce lot est noté.
  - Le débit dépend du nombre de requêtes, de classes et du contenu : on ne le déclare pas indépendant de l'échelle.

## 5. Lecture déclarée d'avance, pour D2

Ce n'est pas une règle d'adoption de modèle. Toutes les grandeurs portent sur l'élève 28×28 et les 26 images d'évaluation. Elles sont codées dans `pe_common.states` et `pe_common.issue`, et testées.

**Grandeurs, par graine s :**
- **Δ_s** : rappel@30 sans nom de l'élève, moins celui de l'a priori.
- **L_s et U_s** : quantiles 2,5 % et 97,5 % du bootstrap apparié **par image** de Δ_s (2 000 tirages de 26 images avec remise, `default_rng(2030 + s)`).
- **G_s** : AP50 moyenne de l'élève sur les catégories jugées, moins celle d'OWLv2 sur les mêmes catégories. Son intervalle bootstrap par image (`default_rng(2040 + s)`) est **publié mais n'entre pas dans la règle**. On n'annonce aucune non-infériorité démontrée.
- **D** : débit médian de l'élève complet au lot 32, divisé par celui d'OWLv2 complet (même corpus). Son minimum et son maximum sont publiés. Un D < 1 de faible marge ne démontre pas une différence de coût robuste ; l'issue reste celle de la table.

**États** (le premier qui s'applique) :
- Localisation :
  - **Loc+** : Δ_s ≥ 0,15 et L_s > 0 pour les 3 graines ;
  - **Loc−** : sinon, si U_s < 0,15 pour les 3 graines ;
  - **Loc?** : sinon.
- AP :
  - **AP+** : G_s ≥ −0,05 pour les 3 graines ;
  - **AP−** : G_s < −0,05 pour les 3 graines ;
  - **AP?** : sinon, y compris quand aucune catégorie n'est jugée.
- Débit : **D+** si D ≥ 1, **D−** sinon.

**Issue de chaque cas** (les 18 combinaisons) :

| Localisation | AP | Débit | Issue |
|---|---|---|---|
| Loc− | toute | tout | **pas de signal** |
| Loc? | toute | tout | **indécidable** |
| Loc+ | AP+ | D+ | **signal** |
| Loc+ | AP+ | D− | **pas de signal** |
| Loc+ | AP− | D− | **pas de signal** |
| Loc+ | AP− | D+ | **indécidable** |
| Loc+ | AP? | tout | **indécidable** |

**Panne technique [C3].** Le contrôle de surapprentissage tourne avant tout entraînement réel :
- graine 0, 28×28, les 8 images fixes en un seul lot, 1 000 pas.
- Il passe si les quatre conditions suivantes sont réunies :
  - rappel@30 ≥ 0,8 sur ces 8 images ;
  - perte finale ≤ la moitié de la perte initiale ;
  - gradients finis à chaque pas, et chaque tenseur de paramètres reçoit un gradient non nul au premier pas ;
  - aller-retour des conversions de rectangles avec une erreur < 10⁻⁵.
- S'il échoue, l'issue est **« panne technique »**, pas une case scientifique. Rien d'autre n'est lancé. On corrige le code, et ce n'est pas un ajustement sur l'évaluation.

**Conséquences :**
- **Signal** : les 300 graphes S1b peuvent servir à l'entraînement, selon le protocole de Codex : 240 pour l'apprentissage et 60 pour la validation interne, figés au tirage ; tailles emboîtées préfixées ; même validation. La suite reste une décision de wA:p1 selon BOUCLE.md.
- **Pas de signal** : **ce prototype ne justifie pas cette campagne**. Cela ne réfute ni Haiku ni la distillation en général : on mélange ici un professeur Gemini à l'ancienne consigne, une tête initialisée au hasard, des super-catégories et peu de données. Cela n'adopte pas non plus OWLv2 d'office. Toute alternative est une nouvelle brique décidée explicitement.
- **Indécidable** : aucune dépense automatique, aucune requalification en signal. Le cas est rapporté tel quel.
- **Relations, bras 8×8, Florence-2, accord S1b** : description seulement.

## 6. Les trois régimes de Marcel, seulement esquissés (hors de ce lot)

Ils sont inchangés depuis le brouillon v0.1, section 6 :
- **séparé** : c'est ce lot ;
- **séparé puis assemblé** : il passe par la grille 8×8 ou par un réencodage d'environ 138 Go ;
- **commun** : il suppose un nombre de graphes de l'ordre du millier.

## 7. Exécution

**Préparation, locale et légère, déjà faite.** `python3 -I scripts/pe_listes.py PILOTE HAIKU .` écrit `listes.json` et `noms.json`. Elle hache les fichiers d'évaluation sans lire leurs objets.

**Entrées Kaggle.** Un jeu de données contenant :
- `listes.json`, `noms.json` et les scripts ;
- `images/` (162 images) ;
- `graphes/` (158 graphes Gemini) ;
- `s1b/` (30 graphes S1b).

S'y ajoute la sortie `caypollard-encode-cradio` v3, pour le contrôle d'identité. Aucun fichier des ensembles fermés n'y figure. Kaggle T4, internet activé pour les poids.

**Blanc** (`--stage smoke`) :
- il hache et ouvre les fichiers d'**entraînement seulement** ;
- il réencode les 8 images de surapprentissage et fait le contrôle d'identité ;
- il fait le contrôle de surapprentissage ;
- il fait tourner OWLv2 et Florence-2 sur 2 de ces images et **relève leurs révisions** ;
- il fait un chronométrage d'une répétition et mesure le pic de RAM et de VRAM.

Il écrit `blanc.json` et ne touche ni au réglage ni à l'évaluation. Il est relu avant le complet.

**Complet** (`--stage full`). Les SHA de `listes.json` et `noms.json` sont déjà épinglés dans `pe_kaggle.py` (vérifiés au blanc comme au complet). Le complet refuse de démarrer tant que les révisions d'OWLv2 et de Florence-2 relevées au blanc ne sont pas épinglées par un commit relu ; le pilote `scripts/kaggle_pe_run.py` vérifie alors les SHA des deux scripts. Il écrit `resultats.json` et `planche/`.

**Coût prévu, non mesuré** : environ 1,5 h de T4, plafond de 4 h vérifié entre étapes. Sorties de moins de 1 Go dans `~/porkyevitch-donnees/maths/petit-eleve/`. Rien de lourd sur le Mac.

**Tests locaux** : `python3 -I tests/test_pe_common.py`. Ils couvrent les priorités de la table des noms, les rectangles, l'appariement glouton, le rappel, l'AP, le bootstrap apparié, les prototypes, les 18 cas de la lecture et la panne technique. Les parties torch sont vérifiées par `tests/test_pe_torch.py` (6 tests, torch 2.14.1 CPU) : conversions de rectangles, appariement hongrois injectif, pertes et gradients finis, boucle de surapprentissage, choix de l'époque, prédiction, mesures de relations, chargement d'un graphe (rectangle dégénéré retiré, relation rare gardée en « autre_relation »). Sur 8 images synthétiques, le contrôle de surapprentissage atteint un rappel@30 de 1,0 dès 300 pas : le critère est atteignable, sans rien dire du réel. Le chargement des modèles et l'inférence réelle sont vérifiés par le blanc.
