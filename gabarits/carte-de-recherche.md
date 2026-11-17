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

## Bloc lu par le guichet

Requis pour une course GPU : la carte de calcul nomme ce fichier dans `carte_recherche`. Le guichet recalcule la
puissance à partir de ces nombres ; un verdict écrit ici ne compte pas.

```toml recherche
decision = "<la décision qui change selon l'issue, en une phrase>"
premisse = "verifiee"        # verifiee | sans_objet | non_verifiee (non vérifiée : accord humain)
[puissance]
ic = [0.0, 0.0]              # IC95 déjà mesuré sur le même banc ; ou se = 0.0
effet_plausible = 0.0        # tiré de la mesure citée en question 2
# n = "N0:N1"                # effectif de la mesure source : effectif prévu
# famille = 1                # nombre de comparaisons (Bonferroni)
# unilateral = false         # règle « borne basse > 0 »
```

Pour un calcul qui ne prétend rien conclure, remplacer la table `[puissance]` par
`exploratoire = "pourquoi ce calcul vaut d'être fait sans conclure"` (accord humain).
