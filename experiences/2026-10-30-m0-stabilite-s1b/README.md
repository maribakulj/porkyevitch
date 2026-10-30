# M0 : stabilité de S1b au niveau des cibles apprises (script seulement, rien lancé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1. Ce dossier est la mesure M0 de `notes/2026-10-30-tranche300-devis.md`, section 2. **Rien n'a tourné sur les données réelles.**

**Ce que M0 mesure.** Sur les 60 images de validation interne de la tranche de 300 (rôle `validation_interne` de `tirage.json`, sha `5be1c117…`), on compare la passe S1b (`tranche300/S1b`) et la seconde passe (`tranche300/S1b-r2`). La comparaison porte sur ce que le petit élève apprend : ses règles de noms et ses relations v0 (`pe_common.py`, sha `20034ce4…`, inchangé).

- **Appariement**, figé : même super-catégorie et IoU ≥ 0,5, glouton par IoU décroissant (égalités : ordre de la passe 1, puis de la passe 2). Les rectangles dégénérés sont retirés et comptés.
- **Mesures**, regroupées sur les 60 images :
  - part des objets appariés, 2m/(n₁+n₂), avec aussi la part par passe ;
  - accord des super-catégories parmi les objets appariés par l'IoU seul ;
  - Jaccard des triplets v0 (13 relations + `autre_relation`) entre paires appariées.
- **Intervalles** : bootstrap par image, 2 000 tirages, `default_rng(3061)`, percentile ; descriptifs.
- **Publié à côté** : le Jaccard brut des noms et des triplets nommés, recalculé ici. Il peut différer du 0,52 / 0,34 du journal, dont la méthode exacte n'est pas transcrite. Les deux sont publiés.

**Portes.** Elles sont lues dans `PARAMETRES.json` et valent **null** : elles seront fixées après le challenge de Grok p7 et la contre-expertise de Codex p4. Tant qu'une porte vaut null, le script mesure mais **ne décide rien**. Une fois fixées, la règle de la note s'applique :
- **Objets** : si la part appariée est ≥ la porte, on garde les cibles dures de la passe 1 ; sinon on passe aux cibles douces, avec une seconde passe sur les 240.
- **Relations** : si leur Jaccard v0 est sous la porte, elles ne servent pas de cible dure.

**Usage** (CPU, quelques secondes) :

```
python3 -I scripts/m0.py --pass1 …/tranche300/S1b --pass2 …/tranche300/S1b-r2 --tirage …/tirage.json --params PARAMETRES.json --out m0.json
```

Le script vérifie les SHA du tirage et des règles du petit élève. Un graphe manquant est tenu à l'écart et compté.

**Tests** : `python3 -I tests/test_m0.py`. Les 8 tests, sur graphes fictifs seulement, vérifient les cas suivants :
- passes identiques ;
- nom différent mais même catégorie, donc apparié ;
- catégorie différente au même endroit ;
- boîte déplacée et prédicat changé ;
- rectangle dégénéré ;
- départage ;
- portes nulles, ou fixées, avec les deux issues ;
- passage complet sur 60 paires fictives.
