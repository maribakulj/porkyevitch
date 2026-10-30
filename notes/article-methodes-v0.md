# Méthodes (premier jet v0, privé)

30 octobre 2026. Claude wA:pH, pour wA:p1. Ce premier jet est rédigé à partir des préinscriptions et des résultats déjà rendus. **Aucun chiffre des tests**, qui ne sont pas encore ouverts. Les chiffres cités sont tous de validation, ou sont des effectifs. Les points à vérifier ou à trancher sont marqués [à vérifier].

## 1. Données

**ICAI.** Nous utilisons le jeu `iconclass-vlm-brillfull` (révision `8045366`, CC0 déclaré) : des images de reproductions d'œuvres, chacune annotée par des notations Iconclass venant de son catalogue.
- **Apprentissage et validation.** L'apprentissage compte 86 216 images. 5 % de groupes d'images identiques à l'octet (même md5) en sont tirés pour la validation, avec une graine fixe. On obtient 81 951 images d'apprentissage et 4 265 de validation, dont 4 241 gardent une vérité non vide après la projection décrite en section 3.
- **Test.** Le test ICAI compte 788 images. Il est resté fermé pendant toute la phase de choix.

**Banc du Rijksmuseum.** C'est un banc extérieur construit pour cette série, et jamais consulté avant le gel des prédictions.
- **Notices.** Les métadonnées sont publiées sous CC0, et les reproductions relèvent du domaine public.
- **Tirage.** 3 000 identifiants ont été tirés par type de support (peinture, estampe, dessin). On n'a gardé que les objets éligibles : droits vérifiés, image alignable avec ses codes, et vérité non vide après projection.
- **Composantes de dépendance.** Les objets liés sont réunis en composantes connexes. Les liens viennent des métadonnées : même série, même attribution, même source, etc. Ils viennent aussi des copies internes. Une composante n'est jamais scindée, et elle compte au plus 20 objets.
- **Filtrage contre les données d'apprentissage.** Toute composante qui contient une image proche d'une image de référence est retirée en entier. Une image est proche si sa distance de hachage perceptuel est inférieure à 50 bits, ou si son cosinus C-RADIO est ≥ 0,95. Ces seuils ont été audités sur une réserve tirée à part avant le tirage. Cela retire 84 composantes, soit 5 912 objets.
- **Répartition.** Une réserve d'audit prend 10 % des composantes. Le reste est permuté par une graine fixe et versé, composante par composante, d'abord au test, puis au dev.
- **Effectifs.** Le test compte **1 201 images** en **908 composantes** (402 peintures, 462 estampes, 337 dessins). Le dev compte **301 images** en **239 composantes**. Le dev sert uniquement aux planches et au diagnostic.

**Vérité du Rijksmuseum.** Ce sont les notations Iconclass des notices, dédoublonnées. Un code absent de la notice compte comme négatif, alors qu'il peut être vrai. C'est une limite commune aux deux bancs, discutée en section 5.

## 2. Représentation et têtes

Toutes les têtes reposent sur un même encodeur figé, **C-RADIOv3-L** (révision épinglée). Le prétraitement est le suivant : image remise dans un carré gris, 448 px, interpolation bicubique, calcul en fp16. On en tire deux sorties :
- un **vecteur** de 4 096 dimensions (jeton de synthèse et moyenne spatiale, chacun normalisé) ;
- une **grille** de 8 × 8 zones de 1 024 dimensions (moyenne adaptative des 28 × 28 jetons).

Le vocabulaire **V** compte 7 907 codes : les codes vus au moins 5 fois en apprentissage, avec tous leurs ancêtres.

La référence initiale **T0** est un perceptron à deux couches sur le vecteur, entraîné avec une perte asymétrique. Les essais de la phase 1 sont cinq :
- un vote des 20 voisins d'apprentissage (TK) ;
- des seuils par profondeur (T-niv) ;
- leur combinaison (TK-niv) ;
- la cohérence parent–enfant de C-HMCNN, réentraînée (T-H) ;
- deux recettes spatiales sur la grille : une mise en commun apprise (T-Z) et ML-Decoder (T-D).

Tous les réglages (époque, seuil, poids du vote) sont choisis sur la validation ICAI seule.

## 3. Mesure

**Hiérarchie.** Elle est lue directement dans la notation : les ancêtres d'un code sont ses préfixes de jetons (chiffres, lettres, parenthèses), partie par partie pour un code composé. Ce n'est pas l'arbre officiel d'Iconclass. Une comparaison descriptive avec cet arbre est publiée.

**Projection.** Le chapitre 86 (proverbes et locutions) est retiré de la vérité comme des prédictions. Une image dont la vérité projetée est vide est exclue du dénominateur. Il en reste 787 sur 788 au test ICAI, 4 241 sur 4 265 en validation, et toutes au test du Rijksmuseum, où c'est un critère d'éligibilité.

**Mesure principale : le F1 hiérarchique (H-F1).** Pour une image, c'est le F1 entre la fermeture par ancêtres de la vérité et celle de la prédiction. Le H-F1 rapporté est la moyenne de ce F1 sur les images. La prédiction s'obtient par un seuil, puis par la suppression des ancêtres déjà impliqués, puis par la projection.

**Mesures secondaires**, toutes descriptives :
- le F1 des codes exacts ;
- le F1 par tranche de profondeur (1–2, 3–4, 5 et plus) ;
- le F1 par fréquence d'apprentissage du code (5–20, 21–100, plus de 100) ;
- le rappel des codes rares ;
- la part des vérités hors du vocabulaire, que toute tête à vocabulaire fixe ne peut pas prédire.

## 4. Protocole de la phase 1

**Préinscription.** Les règles ont été écrites et relues avant tout calcul, puis amendées avant le premier calcul concerné, chaque fois avec date et motif :
- la famille de comparaisons ;
- le juge extérieur ;
- la projection ;
- les seuils de décision ;
- l'ordre d'ouverture.

Chaque script, essai à blanc compris, a été relu avant d'être lancé. [à vérifier : formulation sur les relecteurs, qui sont des modèles et non des pairs humains.]

**Référence.** T\* est choisie sur la validation seule, parmi T0, T0 au seuil élargi et T0 entraînée plus longtemps (30 époques). Ce choix compte comme l'une des comparaisons de la famille.

**Famille de sept comparaisons**, fixée d'avance : T\* − T0, TK, T-niv, TK-niv, T-H, T-Z et T-D, ces six dernières contre T\*. TK-niv n'est exécutée que si TK et T-niv sont toutes deux retenues, mais elle garde sa place dans la famille.

**Règle de retenue.** Une brique est retenue si deux conditions sont réunies :
- la borne inférieure unilatérale de Δ_Rijks est > 0 ;
- celle de Δ_ICAI est > −0,01 (non-infériorité).

Les deux bornes sont prises au niveau 1 − 0,05/7 ≈ 99,29 % (correction de Bonferroni sur la famille). Elles viennent d'un bootstrap de 10 000 tirages, apparié entre systèmes. Au Rijksmuseum, on tire des composantes entières, et la moyenne est recalculée sur les images des composantes tirées ; à ICAI, on tire des images. Les intervalles bilatéraux à 95 % sont publiés à titre descriptif.

**Gel avant mesure.**
- Les prédictions des huit systèmes sur les trois bancs (test ICAI, dev et test du Rijksmuseum) ont été produites puis **scellées**. Ce sont 24 fichiers, avec un manifeste et leurs empreintes.
- Pour chaque comparaison, une **planche de 12 images du dev** montre la vérité et les deux prédictions. Ce sont les images où l'écart de H-F1 est le plus grand.
- Ces planches ont été regardées par **deux regards** (l'orchestrateur et un second modèle relecteur, puis un reçu) **avant** l'ouverture d'un seul score de test. Le code de mesure refuse d'ouvrir les tests sans ce reçu, lié aux planches par empreinte.

L'ordre d'ouverture est écrit : vérités ICAI, vérités du Rijksmuseum, comparaisons dans l'ordre de la famille, TK-niv seulement si sa condition est remplie, puis les verdicts, et enfin les mesures descriptives.

**Statut.** La série est **exploratoire** :
- une seule graine par brique ;
- le test ICAI avait déjà été consulté au moment de la préinscription, ce qui le rend non confirmatoire ;
- le choix est fait sur une validation consultée plusieurs fois.

Une conclusion confirmatoire demanderait un nouveau banc jamais consulté.

## 5. Diagnostic sur la validation

Le diagnostic est purement descriptif. Il a été préinscrit, et il porte sur la seule validation ICAI, pour la meilleure référence de validation B (T-Z) et pour T\*.

- **Longue traîne.** Le macro-F1 des 4 073 codes vus 5 à 20 fois à l'apprentissage vaut 0,07 pour B. Il monte à 0,20 sur les seuls codes présents en validation. Sous 5 exemples, le F1 est pratiquement nul.
- **Profondeur.** Le rappel des nœuds de la vérité passe de 0,86 en profondeur 1 à 0,38 en profondeur 6, pendant que la précision baisse moins, de 0,74 à 0,64. Fréquence et profondeur restent confondues tant qu'elles ne sont pas croisées.
- **Seuils par tranche.** Un seuil par tranche de fréquence, ajusté sur la validation elle-même par montée coordonnée, ne gagne que +0,0013. C'est un score ajusté, optimiste : ce n'est ni une borne supérieure, ni une recette.
- **Erreurs corrélées.** Les erreurs de T\* et de B sont fortement corrélées (Pearson du H-F1 par image : 0,82). Cela ne mesure pas l'information absente des traits.
- **Audit des « confiants absents ».** On a tiré au hasard, avec une graine fixe, 100 couples (image, code) que B prédit avec une probabilité ≥ 0,9 et que la vérité fermée ne contient pas, au plus deux par image. Ils ont été classés en trois catégories :
  - **O**, vrai et précis : un oubli du catalogueur ;
  - **A**, vrai mais générique ;
  - **E**, vraie erreur.

  Deux regards indépendants ont été faits, par l'orchestrateur et par un second modèle. Ils s'accordent sur 53 couples sur 100. Les 47 désaccords ont été arbitrés à l'aveugle par un troisième modèle, avec une règle écrite d'avance par le juge le plus strict ; un contrôle a confirmé que les 47 images avaient bien été ouvertes. Comptes arbitrés : **O 29, A 46, E 25**. Environ trois quarts de ces prédictions sûres, comptées fausses par le F1, sont donc vraies. L'audit n'est pas un score : la règle penche vers le juge le plus strict, et une mesure corrigée demanderait une règle et un taux d'oubli établis d'avance.
- **Conséquence pour la lecture des scores.** Les F1 mesurent un accord avec le catalogue, pas la justesse visuelle. Un oubli du catalogueur est compté comme un faux positif.

## 6. Méthodes en cours (préinscrites, pas encore mesurées)

**P9-A, champs de preuve hiérarchiques.**
- *Question* : imposer la hiérarchie dans chaque zone **avant** l'agrégation aide-t-il plus que le même calcul **après** l'agrégation ?
- *Dispositif* : quatre bras appariés, sur les mêmes traits gelés :
  - un contrôle non imbriqué ;
  - la hiérarchie après agrégation ;
  - la hiérarchie par zone ;
  - CSRA adaptée, en contrôle externe.

  Chaque bras a dix époques et une graine d'abord. Il est mélangé à B dans l'espace des intensités. Un seul candidat est choisi parmi 571, sur une moitié de la validation.
- *Juges* : le H-F1 (règle G), puis le F1 moyen des codes rares sous une tolérance de H-F1 (voie R). Le mécanisme est jugé sur l'autre moitié de la validation.
- *État* : l'essai à blanc technique est passé, le programme scientifique est écrit. L'essai à blanc a fait ressortir une sensibilité des produits fp16 à la forme des lots. Elle est documentée, et le contrôle algébrique se fait désormais en float64.

**A1, décision par maximisation du F1 sous une loi de voisins.**
- *Méthode* : c'est le *General F-measure Maximizer* (Waegeman et al.) appliqué à une loi q construite à partir des étiquettes des voisins d'apprentissage et des sorties de B. GFM utilisait déjà les voisins d'apprentissage ; notre apport est la restriction aux ensembles fermés et émissibles.
- *Décodeur* : sous des atomes fermés, le tri de GFM, départagé par la profondeur, donne déjà l'ensemble fermé optimal. Un programme linéaire en nombres entiers n'est nécessaire que pour les maximaux non émissibles (chapitre 86).
- *Validation du logiciel* : le décodeur a été validé contre une énumération exhaustive. Les contrôles d'identité ont révélé deux défauts du solveur HiGHS dans la version utilisée : un prétraitement qui rendait un faux optimum certifié, et un écart d'arrêt absolu de 10⁻⁶. Ils sont contournés et reproduits.
- *Mesure* : sur la validation, en deux moitiés, réglage puis diagnostic.

**D3, deux sondes ciblées sur traits gelés.**
1. **Vote de voisins limité aux codes rares** (5–20 exemples), mélangé à B. Il est jugé par la règle G puis par la voie R, avec un témoin à mémoire permutée.
2. **Tête des seuls enfants**, routée par le parent prédit par B. On publie :
   - la couverture du parent ;
   - le rappel conditionnel ;
   - le rappel total ;
   - les faux positifs.

   Le seuil est réglé à une précision au moins égale à celle de B.

**Petit élève (graphes de scène).**
- *Question* : peut-on distiller des graphes de scène produits par un modèle multimodal professeur (Gemini) en une tête légère sur l'encodeur figé ? La tête prédit des objets (type DETR, appariement hongrois) et des relations.
- *Données* : 106 graphes d'apprentissage, et 26 graphes pour le réglage comme pour l'évaluation.
- *Références* : un a priori, OWLv2 et Florence-2.
- *Mesure* : une mesure de fidélité au professeur, explicitement distincte d'une vérité humaine, avec un contrôle préalable de surapprentissage et une lecture fixée d'avance pour décider d'une campagne d'annotation.
- *Seconde source de graphes* : un second annotateur (Claude Haiku, consigne S1b) a annoté 300 images. Sa stabilité entre deux passes est faible sur les noms et les relations brutes (Jaccard 0,52 et 0,34). Elle sera mesurée au niveau des cibles apprises, à titre descriptif seulement.

## 7. Ce que ces méthodes ne permettent pas de dire

- Un gain de F1 est un gain d'accord avec le catalogue, pas une preuve de justesse visuelle.
- Les verdicts de la phase 1 sont exploratoires (graine unique, tests déjà consultés pour ICAI).
- Les relectures et les regards ont été faits par des modèles. [à vérifier : comment le présenter, et s'il faut un regard humain sur un sous-ensemble.]
- Les graphes de scène sont jugés par fidélité à un professeur, pas par une vérité de localisation.
- Aucune des méthodes en cours n'a encore de résultat.
