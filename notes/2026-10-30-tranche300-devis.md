# Troisième voie de la phase 2 : que faire des 300 graphes Haiku S1b ? (devis, rien lancé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1. Ce n'est pas une préinscription : c'est le devis d'une préinscription à écrire. **Rien n'est lancé.** D2 reste en vigueur : l'usage de ces graphes pour l'entraînement attend la porte du petit élève (lecture D2 de sa préinscription v1).

## 1. Ce qu'on a

- **La tranche.** 300 images d'apprentissage ICAI, stratifiées par chapitre (`experiences/2026-10-30-tirage-300`), hors pilote, validation et copies du test. Au tirage, elles ont été figées en **240 pour l'apprentissage** et **60 pour la validation interne**.
- **La stabilité de S1b**, mesurée sur ces 60 images avec deux passes indépendantes (`JOURNAL-BOUCLE.md`, 30/10) :
  - Jaccard des noms d'objets **0,52** ;
  - Jaccard des relations **0,34** ;
  - écart moyen de **2,4 objets** par image.

**Lecture.** Un graphe S1b n'est pas une étiquette fixe. C'est un tirage dans la distribution des réponses de Haiku. Deux passes ne s'accordent que sur environ la moitié des noms et le tiers des relations. Entraîner sur une seule passe revient donc à donner à l'élève des cibles dont une bonne part changerait si l'on reposait la question.

**Ce que ces chiffres ne disent pas encore.** Ils portent sur les **noms bruts** et les **triplets bruts**. Or l'élève n'apprend pas les noms bruts. Il apprend 8 super-catégories + « autre » (table figée `noms.json`), des rectangles appariés à IoU 0,5, et 13 relations + « autre_relation ». Deux passes qui disent « old man » et « man » sont en désaccord sur le nom, mais d'accord sur la cible apprise (personne). **L'instabilité des cibles réellement apprises est donc inconnue, et probablement plus faible.** On peut la mesurer sans nouvel appel, puisque les 60 doubles existent.

## 2. Cibles dures ou douces

**Dures (une seule passe).** Chaque objet de la passe 1 est une cible, avec l'appariement hongrois habituel.
- *Pour* : c'est simple, et c'est la recette déjà écrite du petit élève.
- *Contre* : si la cible apprise est aussi instable que les noms bruts, l'élève apprend en partie le bruit de Haiku. Pour les relations, à 0,34, c'est le cas probable.

**Douces (deux passes ou plus).** On apparie les objets des passes : même super-catégorie et IoU ≥ 0,5, par appariement glouton d'IoU décroissant.
- **Objets** : un objet trouvé dans les deux passes a un poids 1, un objet d'une seule passe un poids ½. Le poids passe dans le terme de classe et dans « pas d'objet ». Le rectangle est la moyenne des rectangles appariés.
- **Relations** : la cible d'une paire appariée est la **fréquence** de chaque prédicat entre les passes (0, ½ ou 1), avec une BCE à cible fractionnaire.
- *Pour* : la cible porte l'incertitude mesurée au lieu de la cacher.
- *Contre* : une seconde passe sur les 240 coûte environ 30 min avec trois annotateurs. L'appariement entre passes est lui-même une règle à figer. Deux passes ne donnent que trois niveaux (0, ½, 1).

**Variante intermédiaire, sans nouvel appel** : une passe, avec un lissage des étiquettes calibré sur la stabilité mesurée. Elle est moins informative, puisqu'elle lisse tout de la même façon, objets sûrs compris. Je ne la recommande pas en premier.

**Recommandation : décider par une mesure, écrite d'avance.**

1. **Mesure M0**, sur les 60 doubles, sans appel ni entraînement. On mesure l'accord entre passes **au niveau des cibles apprises** :
   - part des objets appariés (même super-catégorie, IoU ≥ 0,5) ;
   - accord des super-catégories sur les objets appariés par IoU seul ;
   - Jaccard des triplets dans le vocabulaire de relations v0, sur les paires appariées.

   On publie aussi les 0,52 / 0,34 bruts, à côté.
2. **Règle, fixée avant M0** :
   - **Objets** : si au moins 70 % des objets sont appariés entre passes, on garde les cibles dures de la passe 1 pour les objets. Sinon, on passe aux cibles douces, avec une seconde passe sur les 240.
   - **Relations** : si leur Jaccard au niveau v0 reste sous 0,5, elles ne servent **pas** de cibles dures. Elles sont soit douces avec deux passes, soit exclues de l'entraînement de ce test et seulement décrites.

   Le seuil de 70 % est une porte choisie, pas une valeur dérivée. Il reste à discuter en relecture **avant** M0.

## 3. Test minimal préinscriptible : les graphes S1b aident-ils le petit élève ?

**Question unique.** Ajouter les 240 graphes S1b aux 106 graphes Gemini améliore-t-il la localisation de l'élève, mesurée contre une référence plus stable qu'une seule passe ?

**Bras**, tous avec la recette du petit élève v1 inchangée (encodeur figé, grille 28×28, tête DETR, mêmes hyperparamètres, graines 0, 1 et 2, époque choisie sur la perte des 26 graphes Gemini du réglage) :
- **E0** : les 106 graphes Gemini seuls. C'est le petit élève v1, réentraîné sous le même code pour l'appariement.
- **E1** : 106 Gemini + 240 S1b, avec les cibles fixées par la règle de M0.
- **E1′** (contrôle descriptif) : les 240 S1b seuls. Il sépare l'effet de la quantité de celui du changement de professeur.

**Référence de mesure : le consensus des deux passes** sur les 60 images de validation interne. Seuls comptent les objets trouvés par les deux passes (même règle d'appariement que M0).
- Elle n'est pas humaine, et c'est écrit tel quel.
- Elle est **plus stable** que chacune des passes, et ces 60 images n'ont servi à rien d'autre.
- Mesure secondaire, descriptive : la fidélité aux 26 graphes Gemini de l'évaluation du petit élève.

**Grandeur et règle, à écrire d'avance :**
- **Δ_s**, pour chaque graine : rappel@30 sans nom à IoU 0,5 de E1, moins celui de E0, contre le consensus.
- **Intervalle** : bootstrap apparié **par image**, 2 000 tirages de 60 images, `default_rng(3060 + s)`.
- **Issue**, cas évalués dans cet ordre :
  1. **aide** si, pour les 3 graines, Δ_s ≥ +0,05 et la borne basse est > 0 ;
  2. sinon **n'aide pas** si, pour les 3 graines, la borne haute est < +0,05 ;
  3. sinon **indécidable**.
- **Garde** : E1 ne doit pas perdre plus de 0,05 de rappel sur les 26 Gemini par rapport à E0. Sinon l'issue « aide » est rapportée avec cette perte, sans recommandation.
- **Publié à côté** : l'AP50 par super-catégorie, les relations (descriptives), E1′, et la stabilité M0.

**Honnêteté sur la taille.** 60 images groupées donnent un intervalle large, de l'ordre de ±0,05 à ±0,08 sur un rappel. « Indécidable » sera donc fréquent. Le seuil de +0,05 est une **porte de dépense** (« vaut-il la peine d'acheter 1 000 graphes de plus ? »), pas un effet dont la puissance serait acquise.

**Portée d'un échec.** Un échec dirait : *ces* 240 graphes, avec *cette* recette, n'ont pas aidé à l'échelle de 346 images. Il ne réfuterait ni S1b à plus grande échelle, ni la distillation. La courbe d'apprentissage emboîtée suggérée par Codex (240 en préfixes de 60, 120 et 240) en serait la suite naturelle, comme nouvelle brique.

## 4. Coût, ordre et dépendances

1. **M0** : CPU, quelques minutes, aucun appel. Il est possible dès maintenant, puisqu'il ne touche pas à l'entraînement.
2. **Seconde passe S1b sur les 240**, seulement si la règle de M0 l'exige : environ 30 min avec trois annotateurs, même lanceur et même consigne que la première passe.
3. **Réencodage 28×28** des 300 images : quelques minutes de T4.
4. **Entraînements** : 3 bras × 3 graines, chacun de quelques minutes sur T4, soit **moins d'une heure de T4** au total.

**Prérequis.** La préinscription v1 du petit élève relue et son blanc passé (contrôle de surapprentissage). Puis la décision de wA:p1 selon la lecture D2 : ce test *est* l'usage pour l'entraînement que D2 conditionne.

**Interdits inchangés** : test ICAI, validation ICAI, Rijksmuseum, IconArt, Emblematica. Le test de 20 et les 30 images du choix de S1b restent fermés.
