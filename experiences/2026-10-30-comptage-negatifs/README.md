# Comptage des négatifs Gemini que S1b affirme (descriptif, sans porte, rien lancé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1. C'est le test minimal de Grok p7 (`~/Documents/reviews/porkyevitch-etiquettes-manquantes-grok.md`, section 2.3).

**Question.** Les négatifs que la perte du petit élève tire du professeur Gemini sont-ils souvent affirmés par l'autre professeur, S1b ? Si oui, beaucoup de ces « négatifs » sont peut-être des oublis de Gemini. Ce comptage ne décide rien, et **ne contient aucune porte**. Le choix éventuel, garder la perte, ignorer ces paires ou y mettre une entropie, appartient à une préinscription ultérieure.

**Données.** Les 26 images d'évaluation du petit élève qui ont à la fois un graphe Gemini et un graphe S1b. On les lit dans `listes.json` (sha `87e45b41…`), avec le SHA de chaque graphe vérifié. Règles de noms et de relations : `pe_common.py` (sha `20034ce4…`), inchangé.

**Négatifs comptés**, tels que la perte du petit élève les voit (préinscription v1, sections 2 et 3) :
- **Paires** : paires ordonnées d'objets Gemini distincts **sans aucune relation** Gemini. La tête relations en tire à 3 pour 1. Ici toutes sont comptées, si bien que la part mesurée est l'espérance du tirage.
- **Prédicats** : couples (paire, classe v0) dont la classe manque chez Gemini pour cette paire, que la paire ait une autre relation ou non. Comme la sortie est une sigmoïde multi-étiquette, chaque classe absente est un négatif.
- **Objets** : objets S1b **sans correspondant** Gemini à IoU ≥ 0,5. L'élève les apprendrait comme « pas d'objet ».

**Appariement S1b ↔ Gemini.** Glouton par IoU décroissant, à IoU ≥ 0,5. Les égalités suivent l'ordre de Gemini, puis celui de S1b. La règle est « conjointe » (même super-catégorie). Pour les objets, on publie aussi l'appariement par l'IoU seul.

Un négatif est **comparable** quand ses deux objets Gemini ont un correspondant S1b. Il est **affirmé** quand S1b énonce la relation, ou la classe, entre ces deux correspondants.

**Sorties.** Totaux et détail par image :
- négatifs, comparables, affirmés ;
- part affirmée parmi les comparables, et parmi tous les négatifs ;
- détail par classe v0 ;
- objets S1b sans correspondant, avec les deux règles.

Lecture : un négatif affirmé par S1b **n'est ni certainement faux chez Gemini, ni certainement vrai chez S1b**.

**Limite.** La perte réelle ne voit que les paires d'objets du professeur **appariées à des requêtes** de l'élève. Le comptage prend toutes les paires d'objets Gemini, et approche donc ce que voit un élève bien entraîné.

**Usage** (CPU, une seconde) :

```
python3 -I scripts/comptage.py --listes …/2026-10-30-petit-eleve/listes.json --gemini ~/porkyevitch-donnees/graphes-gemini/pilote/graphes --s1b ~/porkyevitch-donnees/graphes-haiku/systemes/evaluation/S1b --out comptage.json
```

**Tests** : `python3 -I tests/test_comptage.py`. Les 7 tests, sur graphes fictifs, couvrent :
- graphes identiques ;
- une paire négative affirmée ;
- une classe négative sur une paire déjà reliée ;
- des objets sans correspondant, donc non comparables ;
- la règle conjointe contre l'IoU seul ;
- les totaux et les parts ;
- la vérification des SHA et du compte de 26.
