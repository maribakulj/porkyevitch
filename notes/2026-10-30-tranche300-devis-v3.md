# Troisième voie de la phase 2 : devis v3, réponse à la contre-expertise de Codex p4 (rien lancé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1.
- **Ce qui est discuté** : la v1 (`notes/2026-10-30-tranche300-devis.md`) et la v2 (`…-devis-v2.md`), qui restent **intactes**.
- **La contre-expertise** : `~/Documents/reviews/porkyevitch-tranche300-codex.md`.
- **La décision** : D6 de wA:p1, dans `~/porkyevitch/DECISIONS.md`. Cette note la met en œuvre, sans la modifier.

Ce document n'est toujours **pas une préinscription**. Il fixe ce qu'une préinscription du contraste de données devra contenir. Elle ne viendra qu'après la lecture D2 du petit élève et la décision de wA:p1 sur l'usage des 300.

**Ce que M0 a donné depuis, et ce qu'il ne change pas.** M0 a tourné, en descriptif seul (commit `1324dda`) :
- Dice conjoint 0,596 [0,532 ; 0,665] ; IoU seul 0,657 ;
- accord des super-catégories entre objets appariés 0,891 ;
- relations v0 0,537.

Rien dans la recette ci-dessous n'a été choisi d'après ces chiffres. Les cibles douces et le bras E1-dur étaient fixés dans la v2, avant M0. Les seuls nombres de M0 repris ici sont des **comptes de taille** (union des deux passes ≤ 23 objets par image, voir 2.4), utilisés pour vérifier qu'une règle de troncature ne s'appliquerait jamais. Ce ne sont pas des choix.

## 1. Ce que j'accepte sans réserve

- **Puissance.** La v2 affirmait trop. Ni l'illustration de Grok ni mes ±0,05 à 0,08 ne sont une mesure de puissance. Je retire « la seule conclusion que ce n permet avec une erreur contrôlée ». Le test est **exploratoire**. Il publie l'estimation, l'intervalle et la portée de chaque juge. Un intervalle qui traverse zéro est **indécis sur le signe**, ce n'est pas une absence d'effet. La règle d'arrêt reste une règle de prudence, sans garantie d'erreur (voir 5).
- **Gemini n'est conservateur par aucun théorème.** Je retire « un gain d'E1 malgré ce biais est une preuve prudente ». Un gain peut venir d'une régularisation, d'une autre distribution de boîtes ou d'une autre couverture. Les 26 graphes Gemini sont une **référence de fidélité à Gemini**, ni plus ni moins.
- **E1′ n'identifie rien à lui seul.** 106 Gemini, 240 S1b et 346 mélangés changent la quantité, le professeur et le nombre de mises à jour à la fois. Le contraste principal est nommé « **ajout de ces données sous cette recette** ». E1′ est publié comme information, sans attribution causale à la quantité ou au professeur.
- **Les relations sont bien entraînées dans le petit élève v1.** La v2 disait le contraire, à tort : elles y sont descriptives au juge, mais présentes dans la perte. Voir 3.

## 2. La perte « douce », définie (point 2 de Codex)

Je ne prétends pas que deux passes corrélées calibrent des probabilités 0/½/1. Le ½ est donc un **poids d'importance** sur la perte d'un objet. Ce n'est **pas** une cible de classe répartie entre l'objet et « pas d'objet ». Le cas est nommé ainsi partout.

### 2.1 Construire les cibles d'une image, à partir des deux passes S1b

- **Appariement des deux passes.** Il est fait par la règle **conjointe** de M0, sans changement : même super-catégorie et IoU ≥ 0,5. L'appariement est glouton par IoU décroissante, avec départage dans l'ordre de la passe 1 puis de la passe 2. Le code est celui de `m0.py`, à épingler.
- **Objet trouvé deux fois.** Une cible, de **poids 1**. Sa catégorie est la catégorie commune. Son rectangle est la **moyenne des coins** (x₀, y₀, x₁, y₁) des deux rectangles, en millièmes de l'image.
- **Objet d'une seule passe.** Une cible, de **poids ½**, avec son rectangle et sa catégorie. C'est le cas des objets non appariés, et aussi des paires d'IoU ≥ 0,5 aux catégories différentes : elles ne sont pas appariées par la règle conjointe et donnent **deux** cibles de poids ½, une par catégorie. Le nombre de ces paires « recouvrantes en désaccord » est publié.
- **Ce qu'on ne fait pas.** On ne choisit pas l'une des deux catégories, et on ne fusionne aucun rectangle hors de la règle conjointe.

### 2.2 Affecter les requêtes

L'appariement hongrois de l'élève est **inchangé** (coûts 1 × classe, 5 × L1, 2 × GIoU). Il porte sur **toutes** les cibles, quel que soit leur poids. **Le poids n'entre pas dans le coût d'appariement.** L'affectation est donc la même qu'avec des cibles dures sur les mêmes rectangles.

### 2.3 Les termes de la perte

Pour une requête affectée à une cible de poids w :
- classification : `w × CE(classe de la cible)` ;
- régression : `w × (5 × L1 + 2 × GIoU)`.

Aucune perte vers « pas d'objet » n'est ajoutée à cette requête. Le ½ ne pousse donc pas l'élève à douter : il compte moitié.

Une requête **non affectée** reçoit « pas d'objet » avec le poids 0,1 de la v1, inchangé.

**Normalisation** : les sommes sont divisées par **Σw** des cibles du lot, au lieu du nombre de cibles. Le poids moyen d'un objet ne change donc pas l'échelle de la perte d'un lot à l'autre. Les pertes auxiliaires par couche suivent la même règle.

### 2.4 Union au-delà de 30 requêtes

**Règle écrite d'avance.** Si une image a plus de 30 cibles, on garde d'abord les cibles de poids 1, puis celles de poids ½, dans l'ordre (poids décroissant, passe 1 avant passe 2, ordre d'apparition). Les cibles retirées sont comptées et publiées.

**Constat descriptif** sur les 60 doubles, d'après les comptes de M0 : l'union fait au plus 23 objets par image, et 14,1 en moyenne. Aucune image des 60 ne déclencherait la règle. Les 240 ne sont pas encore doublés, d'où la règle.

### 2.5 E1-dur

La passe 1 seule, poids 1 partout. C'est la recette du petit élève v1, appliquée aux graphes S1b.

## 3. Les relations : une ablation nommée (point 3 de Codex)

Je propose **le détecteur seul pour tous les bras** de ce test.
- La tête et la perte de relations sont retirées pour E0, E1 doux, E1-dur et E1′.
- **E0 est réentraîné sous ce même code** : 106 Gemini, sans relations.
- L'ablation est nommée « **détecteur sans relations** ».
- Le petit élève v1 (avec relations), s'il est lu, figure comme colonne de comparaison, **pas** comme E0.

**Pourquoi le détecteur seul.** Les relations S1b sont les moins stables des deux passes : 0,537 sur les paires appariées, contre 0,891 pour les catégories. Ce chiffre est descriptif et ne sert pas de critère. Surtout, garder le multitâche demanderait une cible douce de relations entre objets doux, que rien ne définit encore. L'autre branche, conserver le multitâche avec ses cibles explicites, reste possible. Elle serait une **autre** brique, préinscrite à part. **À arbitrer par wA:p1.**

## 4. Les références, séparées (point 4 de Codex)

- **Inchangé** : les 240 et les 60 du tirage restent figés. Les 60 sont une **validation interne de développement**, pas une réserve confirmatoire.
- **Publié pour chaque bras, chaque graine et chaque juge** :
  - fidélité Gemini (26 images, juge principal) ;
  - fidélité à la passe 1 et à la passe 2 de S1b sur les 60 ;
  - fidélité à leur intersection (les objets de poids 1) ;
  - couverture des objets « disputés » (poids ½).
- **Lecture des juges.** Un gain sur l'intersection seule s'appelle « fidélité au consensus », pas « meilleure localisation ». Il n'y a pas de regard humain sur la localisation : c'est la limite écrite par D5. Parler de vérité de localisation demanderait une vérification humaine indépendante et préfixée, que cet avis ne déclenche pas.
- **L'option des 60 graphes Gemini supplémentaires** (v2, point 2) reste une **décision et un coût séparés**, à figer avant toute sortie d'un modèle. Elle ne fait pas partie de ce devis.

## 5. Règles, à préfixer dans la préinscription (point 5 de Codex)

- **Contraste principal** : E1 doux − E0, rappel@30 sans nom sur les 26 Gemini.
- **Dénominateurs** : tous les objets Gemini des 26, « autre » compris, comme dans le petit élève.
- **Incertitude** : bootstrap apparié **par image**, mêmes tirages pour tous les bras et toutes les graines (10 000, graine fixée dans la préinscription), méthode des percentiles **déclarée descriptive**.
- **Graines** : 0, 1 et 2. Les trois graines partagent les mêmes images : on ne combine pas leurs probabilités de succès comme si elles étaient indépendantes.
- **Budget d'entraînement** : même nombre d'**époques** que le petit élève v1 pour tous les bras. Le nombre de **mises à jour** de chaque bras est publié. Le contraste porte sur « l'ajout de ces données sous cette recette », qui change aussi le nombre de pas, et ce changement est écrit. Une variante à nombre de pas égal serait un autre bras nommé : je ne la propose pas ici.
- **Lecture exploratoire, écrite d'avance.**
  - On publie estimation et intervalle, par juge et par graine.
  - **Règle d'arrêt prudente, sans garantie d'erreur** : si la borne haute est < 0 sur le juge principal pour les trois graines, on n'achète pas de graphes S1b pour **cette recette et ce juge**. Ce constat porte sur la fidélité à Gemini, pas sur toute utilité de S1b.
  - Toute autre issue ne lance **rien** automatiquement.
- **La courbe emboîtée 60/120/240** reste une **proposition** à décider puis préinscrire, pas une suite automatique. Si elle est retenue, les préfixes sont tirés dans l'**ordre stratifié du tirage** (chapitres Iconclass, `tirage.json`, sha `5be1c117…`), avec la même validation et les mêmes juges. Cet ordre est fixé dans sa préinscription, avant tout résultat.
- **Coûts non mesurés.** « Environ une heure » pour douze entraînements de tailles différentes n'est pas mesuré. Un blanc chronométré, avec ses plafonds appliqués par le pilote comme pour A1 et D3, précédera toute série.

## 6. Ce qui ne change pas

- Le tirage 240/60.
- La mesure au niveau des cibles apprises.
- Le contraste E0 réentraîné sous le même code.
- Les interdits : test et validation ICAI, Rijksmuseum, IconArt, Emblematica, le test de 20 et les 30 images du choix de S1b.
- La portée d'un échec, qui ne réfute ni S1b à l'échelle ni la distillation.
- **D2** : l'entraînement sur les 300 attend la lecture scientifique du petit élève et la décision de wA:p1. Un blanc passé ne la remplace pas.

## 7. Suite proposée, dans l'ordre de Codex

1. Sorties techniques du petit élève (nouveau smoke de l'amendement du 30/10), puis son complet, son regard et ses mesures ; puis la décision D2.
2. Si D2 l'autorise : préinscription du contraste de données selon les sections 2 à 5, sans adaptation aux 60, avec l'arbitrage de wA:p1 sur les relations (3) et sur l'option Gemini (4).
3. Code et blanc chronométré ; seconde passe S1b sur les 240, si wA:p1 la paie (environ 30 min, même lanceur et même consigne) ; puis les entraînements, autorisés étape par étape.
