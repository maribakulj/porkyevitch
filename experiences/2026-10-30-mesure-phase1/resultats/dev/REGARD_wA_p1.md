# Regard des 7 planches du dev Rijksmuseum (wA:p1, 30/10/2026), avant toute ouverture des tests

Planches lues : T*−T0, TK−T*, T-niv−T*, TK-niv−T*, T-H−T*, T-Z−T*, T-D−T* (12 images chacune, |Δ H-F1| décroissant).
Descriptif, aucune décision.

- **Changement de domaine visible.** Les vérités du Rijksmuseum sont souvent très précises (61B2 personnes historiques, noms
  propres, objets de métier) alors que toutes les têtes se replient sur des codes larges (4 Société, 3, 2 Nature, 25) dans les
  dessins et les pages de livre ; d'où un H-F1 de dev autour de 0,42 contre 0,58 sur la validation ICAI.
- **T-D et T-Z rendent parfois un ensemble vide** (portraits dessinés, photographie dans un album, page de livre) là où T* donne au
  moins des codes larges ; cela pèse sur leur score de dev (T-D 0,388, T-Z 0,419 contre T* 0,4205). Les cas où T-Z gagne sont
  nets (chevaliers en armure, scène d'hiver sur la glace, drapeau).
- **TK gagne surtout par les voisins** : saint Paul et saint Pierre, théologien au livre, figure debout ; quelques pertes sur des
  portraits où les voisins tirent vers des codes génériques.
- **T-niv est presque identique à T*** (seuils égaux à 0,60) ; ses écarts viennent d'un petit nombre d'images (série de paysages
  brésiliens de Frans Post, nus dessinés).
- **T-H** gagne sur quelques sujets bibliques (saint Paul à 1,0) et perd par des ensembles vides ou génériques (ravin, rideaux).
- Pas d'anomalie technique visible : images conformes aux identifiants, vérités et prédictions lisibles, descriptions Iconclass
  cohérentes.
