# Lecture du diagnostic d'A1 (V-diagnostic, 2 100 images éligibles), exploratoire

Sorties jugées CONFORMES (sous-agent Sonnet, porkyevitch-a1-diagnostic-sorties-sonnet.md ; contre-vérification Codex à faire).
- A1 bat B : H-F1 0,6076 contre 0,5860 (+0,022), F1 exact +0,034 ; la règle préinscrite le déclare candidat et « recommended ».
- Le gain vient surtout du q tiré des voisins : à q égal, le décodeur ne gagne que +0,006 sur un seuil ; un seuil sur un q
  mieux réglé (eta = 1, analyse secondaire) fait légèrement mieux qu'A1 (0,6102). « Recommended » = « bat B », pas
  « le décodeur est nécessaire ».
- Non affirmable : que le décodeur apporte le gain ; que le gain n'est pas lié à la proximité (48 % du gain pour 30 % des images
  à cos ≥ 0,95 ; proximité ≠ copie) ; une recommandation de production ; latences et F1 par tranche sans IC.
