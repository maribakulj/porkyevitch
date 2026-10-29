# Banc des systèmes Haiku (amendement 4 du pilote graphes, 29/10/2026)

Demande de Marcel (29/10) : avant d'annoter beaucoup d'images avec Haiku, tester plusieurs systèmes jusqu'à valider le meilleur ;
ensuite, deux Haiku de plus (déjà créés : annotateurs wA:pE, wA:pF, wA:pG, modèle claude-haiku-5-5). Règle de décision écrite ici,
avant tout graphe de ce banc.

## Données (apprentissage ICAI seulement, images du pilote)

Tirage `default_rng(40)` parmi les 180 images du pilote hors test20 (`~/porkyevitch-donnees/graphes-haiku/systemes/ensembles.json`) :
3 images d'**exemples** (p055, p098, p162 ; graphes rédigés par wA:p1, `exemples.json`), 30 de **réglage**, 30 d'**évaluation**.
Les annotateurs ne voient que les images de leur dossier ; jamais `verite.json`, ni les graphes d'un autre système.

## Systèmes (briques nommées)

- **S0** : consigne v1 du pilote (`../consigne.md`), une passe.
- **S1** : consigne v2 (`consigne_v2.md`) : vocabulaire d'objets, relations d'action dirigées d'abord, spatial en résidu, pas de
  relations inverses, regard par quarts ; plus, d'après le schéma de Grok p7 (`porkyevitch-schema-relations-grok.md`), la relation
  **« has attribute »** distincte de « holds » (le contact n'est pas exigé).
- **S2** : S1 + les 3 exemples.
- **S3** : S2 + une seconde passe de vérification : l'annotateur relit son graphe sur l'image, retire ce qu'il ne voit pas, ajoute un
  objet saillant oublié.
- **S4** : S2 + quatre quarts agrandis de l'image fournis avec l'image entière.
- **S5** : S2 exécuté trois fois ; on garde les objets (même nom, rectangles IoU ≥ 0,5) et relations présents au moins deux fois.

- **S1b / S2b** (briques ajoutées le 29/10 après le premier regard sur S0/S1, réglage seulement) : consigne v2b = v2 + exigence
  d'exhaustivité (5-20 objets, 3-15 relations, contenu de chaque image d'une page, sculpture nommée comme telle) ; S2b = v2b + exemples.
  Motif : S1 a produit 4,6 objets et 1,6 relation par image contre 6,5 et 5,5 pour S0, en perdant des objets et actions visibles.

- **Regard de réglage du 29/10 (10 premières images)** : S0 6,5 objets / 5,5 relations, S1 4,6 / 1,6, S2 5,1 / 2,3, S1b 12,3 /
  9,2, S2b 10,3 / 8,7 par image (30 images). Au regard, S1b et S2b dominent nettement S0-S2 en objets justes ; S1b invente un peu plus
  (« airship », « horn », bateaux) et multiplie les objets « text » ; S2b donne plus d'actions et nomme les sculptures comme telles,
  mais sort du vocabulaire (« worn by », « on », « held by »). Les deux ratent encore les petites gravures d'une page (Nativité de p031).
  Les briques suivantes sont donc construites sur **S2b** (et non S2) : **S3b** = S2b + passe de vérification et de normalisation
  des prédicats au vocabulaire ; **S5b** = vote sur trois passes S2b indépendantes ; **S4b** = S2b + quarts agrandis.

- **Fin du réglage (29/10, avant toute image d'évaluation)** : vote S5b/S5c écarté (4,8-6,5 objets et 1,1-1,9 relations par image :
  les trois passes S2b divergent trop, 6,6 à 13,8 objets en moyenne selon la passe). Vocabulaire et actions sur 30 images : S0 26
  prédicats hors vocabulaire, 0,5 action/contact par image ; S1b 0 hors vocabulaire, 4,1 actions ; S2b 51 hors vocabulaire, 1,1 ;
  S3b 0, 3,0 (S3b retrouve la Nativité de p031 mais garde « airship »). **Retenus pour l'évaluation : S1b et S3b**, sans modification.
  S4b (quarts) non testé, reporté.

## Procédure

1. **Réglage** : S0, S1, S2 en parallèle sur les 30 images de réglage (un annotateur par système), puis S3, S4, S5. Mesure de wA:p1
   sur les **10 premières** images de réglage (ordre du fichier), pour chaque système. Les consignes peuvent être corrigées pendant
   le réglage : chaque correction devient une brique nommée (S1b, …), jamais une réécriture silencieuse.
2. **Évaluation** : les deux meilleurs systèmes du réglage sur les 30 images d'évaluation, sans aucune modification ; regard de
   wA:p1 sur les 30, puis contre-regard indépendant de Grok wA:p3.

Mesures par image (regard, rectangles dessinés) : objets principaux manqués ; objets inventés ou mal nommés ; rectangles faux ;
relations fausses ; **actions justes** (relations d'action vraies) et **actions importantes manquées** ; temps par image.

## Règle de décision (évaluation)

Score par image = actions justes − 2 × (objets inventés ou mal nommés + relations fausses) − objets principaux manqués. Le meilleur
système est celui au score moyen le plus haut, **à condition** de rester dans la règle de validation du test20 aux deux regards
(≥ 29/30 graphes valides, au plus 1 objet faux et 2 relations fausses par image en moyenne, sujet principal présent sur ≥ 27/30).
Égalité à 0,25 point près : le plus rapide. Le système validé devient la consigne de l'annotation à l'échelle.
