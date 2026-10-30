# D10 : correctif B1 de Codex p4 (code seul ; préinscription `4dca2435…` inchangée)

30 octobre 2026. Claude wA:pH.

**Défaut.** `vote_alone_at_tk_threshold` comparait au seuil 0,5 une reconstruction du vote en float64, alors que TK décide sur sa matrice float32 (`gel_predictions.votes`). Avec 10 voisins sur 20 de poids égaux, la reconstruction donne 0,49999999999999994 (faux) et la matrice de TK 0,5000000596 (vrai). La garde `gap ≤ 10⁻⁵` passait quand même. Codex l'a reproduit.

**Correction, sans changer ni le seuil ni la tolérance.**
- Les événements au seuil, et la valeur `vote` publiée (moyenne, déciles, table par code), utilisent le **vote effectif** de la banque (`bank["vote"]`, la matrice de TK). Il est comparé au seuil converti dans son type.
- La reconstruction indépendante à partir des 20 poids est gardée comme **oracle** (`vote_reconstructed`). Son écart à la matrice reste contrôlé à 10⁻⁵ par `nt_run.py`. Le résumé publie aussi le nombre de décisions au seuil qui diffèrent entre l'oracle et la matrice (`vote_oracle`), sans s'en servir.
- La recette de TK et les contrôles d'identité du dev ne changent pas.

**Notes non bloquantes, reprises.**
- `tk_above_threshold` est maintenant dans les événements publiés, et dans la chaîne seuil → émission exacte pour TK.
- Bootstrap : un tirage sans paire cible a un rapport indéfini. Il est **compté** (`defined_draws` / `undefined_draws` par grandeur) et laissé de côté. Sans tirage défini, l'intervalle vaut `null`. Les quantiles sont ceux de numpy, méthode **linéaire**, déclarée.

**Tests** (`tests/test_nt.py`, 12) :
- le cas équilibré 10 sur 20 : la reconstruction est < 0,5, l'événement suit la matrice (vrai), et le désaccord avec l'oracle est compté ;
- les cas 9, 11, 0 et 20 sur 20, de part et d'autre du seuil ;
- le compte des tirages indéfinis du bootstrap ;
- la matrice des tests est accumulée comme `votes()` : float32, poids écrêtés, total en flottant Python.
