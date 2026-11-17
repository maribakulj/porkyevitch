# Carte de recherche — <nom du calcul>

Écrite avant le code. Quelques lignes par question ; « je ne sais pas » est une réponse admise, à condition de dire
comment on le saura.

## 1. Décision

| Issue possible | Décision qui suit |
|---|---|
| | |
| | |

Si toutes les issues mènent à la même décision : ne pas lancer.

## 2. Peut-il conclure ?

- Effet plausible : … — source : <mesure passée, citée>
- Effectif prévu : … ; erreur-type attendue : … — source : <IC déjà mesuré sur ce banc, ou pilote>
- Règle de décision : <bilatérale / « borne basse > 0 »>, famille de <K> comparaisons
- `labo/puissance.py` : puissance … %, effet minimal détectable …, verdict …

## 3. Prémisse

Ce que le calcul suppose sans l'avoir mesuré, et le diagnostic le moins cher qui le vérifierait.

## 4. Comparabilité

Ce qui diffère entre les bras, en dehors de ce qu'on veut mesurer : rien, ou la liste.

## 5. Contrôle direct

Existe-t-il une vérification directe du résultat qui rendrait ce calcul, ou une partie, inutile ?

## 6. Coût et artefacts

- Durée : … (mesurée par <course> si > 3 h) ; plateforme : … ; GPU : oui / non
- Artefacts dont la suite aura besoin (ils vont dans `artefacts_attendus`) : …
