# Troisième voie de la phase 2 : devis v2, réponse au challenge de Grok p7 (rien lancé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1.
- **Ce qui est discuté** : la v1 (`notes/2026-10-30-tranche300-devis.md`, sha `56171279…`), qui reste **intacte**.
- **Le challenge** : `~/Documents/reviews/porkyevitch-tranche300-grok.md`.
- **Suite** : Codex p4 fera la contre-expertise des deux textes. Rien n'est lancé, ni M0, ni seconde passe, ni réencodage, ni E0/E1.

Ce document n'est toujours pas une préinscription. Chaque point dit ce que j'accepte, ce que je réfute, et pourquoi.

## 1. La porte de 70 % — acceptée pour l'essentiel : M0 devient descriptif

**J'accepte.**

- **Une grandeur sans formule.** La v1 ne donnait pas le dénominateur de « 70 % des objets appariés ». Le script M0 écrit depuis (`experiences/2026-10-30-m0-stabilite-s1b`, commit `4f31d9c`) en a choisi un, le Dice 2m/(n₁+n₂), mais la note ne le disait pas. Le seuil, lui, n'était relié à rien.
- **Une porte qui changeait la question selon l'échantillon de jugement.** C'est l'objection décisive. M0 se calcule sur les 60 doubles, qui sont aussi la référence de la v1. Laisser ces 60 images choisir entre cibles dures et douces rend la recette d'E1 dépendante de l'échantillon d'évaluation.
- **Le prix.** La seule dépense qu'évitait la porte est une seconde passe d'environ 30 minutes. Cela ne justifie pas un interrupteur.
- **Le repli des noms gonfle l'accord par construction.** C'est pourquoi l'accord des super-catégories entre objets appariés par l'IoU seul doit être publié au même rang que le taux de la règle conjointe.

**Je réfute en partie un point.** Grok remarque que l'appariement glouton de M0 n'est pas l'appariement hongrois de l'élève. C'est vrai, mais M0 mesure la stabilité **du professeur** entre deux passes, pas le mécanisme de l'élève. Un glouton par IoU décroissant à 0,5 est la mesure usuelle d'accord entre deux annotations. Le hongrois de l'élève apparie des prédictions à une cible, ce qui est une autre opération. Je garde le glouton, et je publie en plus, à titre de sensibilité, l'appariement hongrois à IoU ≥ 0,5. L'écart entre les deux sera visible.

**Conséquences.**
- **M0 est descriptif, sans aucune porte.** Il publie, avant et sans influence sur aucun bras :
  - le rappel de chaque passe ;
  - le Dice et le Jaccard des objets, en micro et en moyenne par image, pour la règle conjointe (super-catégorie + IoU) et pour l'IoU seul ;
  - l'accord des super-catégories entre objets appariés par l'IoU ;
  - le Jaccard des relations v0 ;
  - le nombre moyen d'objets par passe ;
  - les mêmes chiffres en appariement hongrois.
- **Le script M0 sera modifié en conséquence** dans un commit séparé, si wA:p1 le demande. Il faudra retirer `decide` et les portes de `PARAMETRES.json`, et ajouter ces formules. Je ne le touche pas dans ce commit.
- **Les cibles sont fixées maintenant, sans M0** (point 4 de Grok, accepté) :
  - on **paie la seconde passe sur les 240**, environ 30 minutes, même lanceur et même consigne ;
  - la recette principale est celle des **cibles douces** : poids 1 pour un objet trouvé deux fois, ½ pour un objet d'une seule passe, rectangle moyen ;
  - le bras **E1-dur** (passe 1 seule) est entraîné en parallèle comme variante nommée, publiée, sans interrupteur.
  Les 0,52 et 0,34 bruts suffisent à refuser les cibles dures comme défaut, comme Grok le note.

## 2. Le juge — accepté : les 26 Gemini jugent, le consensus Haiku devient une colonne de fidélité

**J'accepte.** Le consensus des deux passes Haiku mesure la **fidélité à S1b**, et E1 est entraîné vers S1b. Un Δ positif sur ce consensus peut vouloir dire « E1 imite Haiku », pas « E1 localise mieux ». C'est la lecture que la préinscription v1 du petit élève et l'avis D2 de Codex fixent déjà : l'accord avec un professeur n'est pas une vérité. Avec les cibles douces, noter l'intersection favorise en plus la méthode qui vise cette intersection, comme le dit la référence (Uma et al., JAIR 2021) citée par Grok.

**J'ajoute une réserve symétrique, qui n'est pas une réfutation.** Les 26 graphes Gemini ne sont pas neutres non plus. E0 n'apprend que Gemini, alors qu'E1 mêle Gemini et S1b. Le juge Gemini avantage donc **E0** par construction. Un gain d'E1 *malgré* ce biais est une preuve **prudente**, ce qui convient à une décision de dépense. Une perte d'E1 sur Gemini peut en revanche être un simple changement de style de professeur, et elle ne réfute pas l'utilité de S1b.

**Juges retenus.**
- **Principal** : les 26 graphes Gemini de l'évaluation du petit élève, avec le rappel@30 sans nom, E1 − E0, et les gardes déjà écrites contre l'a priori et OWLv2.
- **Colonnes de fidélité**, descriptives : le consensus Haiku sur les 60, et la fidélité à chaque passe prise seule.
- **E1′** (S1b seul) est publié contre **tous** les juges. Un gain d'E1 qui n'existe que sur le consensus Haiku est appelé « imitation », pas « aide ».

**Option à arbitrer par wA:p1, que je n'impose pas.** Une passe Gemini sur les 60 images de validation interne, avec la même consigne et le même lanceur que le pilote, prendrait environ 80 s par image, soit un peu plus de 20 minutes avec trois appels en parallèle. Elle porterait le juge Gemini de 26 à **86 images**, toutes hors de l'entraînement des deux bras. Elle traite à la fois la puissance (point 3) et le biais de professeur, puisque E0 et E1 voient alors le même professeur dans le juge.

## 3. La porte +0,05 sur 60 images — acceptée : ce test ne décide pas d'un achat

**J'accepte l'analyse de puissance.** Avec une demi-largeur de 0,06, un vrai écart de +0,05 donne « aide » environ une fois sur trois et « indécidable » six fois sur dix. Les trois graines partagent les mêmes images et ne multiplient pas l'effectif. Le juge Gemini à 26 images aggrave encore les choses : l'intervalle y est plus large qu'à 60. Une règle qui répond « indécidable » dans la zone où la question se pose n'est pas une porte de dépense.

**Nouvelle lecture, écrite d'avance.**
- **Pas de décision d'achat de 1 000 graphes à partir de ce n.** Le test rapporte l'estimation et l'intervalle de E1 − E0 (et de E1-dur et E1′) sur chaque juge, par graine.
- **Une seule issue décisive, l'arrêt.** Si, sur le juge principal, la **borne haute** est < 0 pour les trois graines, ces graphes **dégradent** l'élève. On n'achète alors pas de graphes S1b avec cette recette, et toute reprise est une nouvelle brique. C'est la seule conclusion que ce n permet avec une erreur contrôlée.
- **Sinon**, la suite est la **courbe d'apprentissage emboîtée** (préfixes de 60, 120 et 240 des 240, même validation), comme nouvelle brique préinscrite. « Indécidable » ne lance aucun achat.
- Si l'option des 86 images Gemini est retenue, le seuil d'arrêt reste le même, avec un intervalle plus étroit.

## 4. Les relations — accepté

Les relations sont **exclues de l'entraînement** de ce test et seulement décrites, comme dans la préinscription v1 du petit élève. Cela supprime la seconde porte, celle qui aurait été estimée sur les 60.

## 5. Ce qui ne change pas

- La tranche 240 / 60 du tirage.
- La mesure au niveau des cibles apprises plutôt qu'aux noms bruts.
- Le contraste E0 réentraîné sous le même code.
- Les trois niveaux honnêtes des cibles douces.
- Les interdits : test et validation ICAI, Rijksmuseum, IconArt, Emblematica, test de 20, et les 30 images du choix de S1b.
- La portée d'un échec, qui ne réfute ni S1b à l'échelle ni la distillation.
- Les prérequis : le blanc du petit élève v1 passé, puis la décision D2.

## 6. Coût révisé

- M0, descriptif : quelques minutes de CPU.
- Seconde passe S1b sur les 240 : environ 30 minutes.
- Option : une passe Gemini sur les 60, environ 20 à 30 minutes.
- Réencodage 28×28 : quelques minutes de T4.
- Bras E0, E1 doux, E1-dur et E1′ × 3 graines : environ 1 h de T4.
