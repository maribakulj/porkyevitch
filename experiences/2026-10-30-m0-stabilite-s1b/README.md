# M0 : stabilité de S1b au niveau des cibles apprises, DESCRIPTIF SEUL (script seulement, rien lancé)

30 octobre 2026. Claude wA:pH. Ce dossier est ajusté au devis v2 (`notes/2026-10-30-tranche300-devis-v2.md`, section 1) : **aucune porte, aucune décision, aucun bras ne dépend de M0**. **Rien n'a tourné sur les données réelles.** La version à porte (commit `4f31d9c`) est remplacée.

**Ce que M0 compare.** Les 60 images de validation interne de la tranche de 300 (rôle `validation_interne` de `tirage.json`, sha `5be1c117…`), entre la passe S1b et la seconde passe S1b-r2. La comparaison porte sur ce que l'élève apprend : ses règles de noms et de relations v0 (`pe_common.py`, sha `20034ce4…`, inchangé).

**Appariement**, IoU ≥ 0,5, selon deux règles :
- *conjointe* : même super-catégorie, en plus de l'IoU ;
- *IoU seul*.

L'apparieur principal est glouton par IoU décroissant (égalités : ordre de la passe 1, puis de la passe 2). C'est la mesure usuelle d'accord entre deux annotations, puisque M0 mesure la stabilité du professeur, pas le mécanisme de l'élève. **Sensibilité** : l'appariement hongrois, qui maximise l'IoU total sur les paires admissibles (scipy), est publié à côté. Les rectangles dégénérés sont retirés et comptés.

**Mesures publiées** (devis v2) :
- pour chaque règle : le rappel de la passe 1, le rappel de la passe 2, le Dice 2m/(n₁+n₂) et le Jaccard m/(n₁+n₂−m), **en micro et en moyenne par image** ;
- l'accord des super-catégories parmi les objets appariés par l'IoU seul ;
- le Jaccard des triplets v0 (13 relations + `autre_relation`) entre paires appariées conjointement, en micro et par image ;
- le nombre moyen d'objets par image pour chaque passe ;
- tout cela pour le glouton et pour le hongrois ;
- les intervalles par bootstrap d'image (2 000 tirages, `default_rng(3061)`, percentile), descriptifs ;
- le Jaccard brut des noms et des triplets nommés, recalculé, à côté du 0,52 / 0,34 du journal.

`PARAMETRES.json` ne contient que le seuil d'IoU (0,5, fixe) et les réglages du bootstrap. Le script **refuse** un fichier qui contient une porte.

**Usage** (CPU, quelques secondes, avec scipy) :

```
python -I scripts/m0.py --pass1 …/tranche300/S1b --pass2 …/tranche300/S1b-r2 --tirage …/tirage.json --params PARAMETRES.json --out m0.json
```

**Tests** : `python -I tests/test_m0.py`. Les 10 tests, sur graphes fictifs seulement, vérifient les cas suivants :
- passes identiques ;
- rappels, Dice et Jaccard ;
- un cas où le hongrois trouve deux paires et le glouton une seule ;
- nom différent mais même catégorie ;
- catégorie différente au même endroit ;
- boîte déplacée et prédicat changé ;
- rectangle dégénéré ;
- départage ;
- refus d'une porte ;
- passage complet sur 60 paires fictives, sans clé de décision.
