# Le graphe de recherche

Un graphe Turtle des idées, hypothèses, cartes, courses, résultats, verdicts et décisions d'un projet. Il sert à
répondre sans relire tout le journal : d'où vient cette piste, a-t-elle été testée, avec quelle puissance, et que
faudrait-il pour la rouvrir. Outil **facultatif** : le reste du plugin n'a pas besoin de lui.

    pip install -r labo/graphe/requirements.txt        # rdflib et pyshacl

## Ce qui est écrit par qui

- **Les faits**, par le générateur : le tableau des idées, les notations d'un tri, les cartes de recherche (empreinte,
  date du dernier commit, puissance recalculée par `labo/puissance.py`), les cartes de calcul, les courses du guichet
  et leurs artefacts hachés.
- **Les jugements**, par les agents : hypothèses et décisions dans un fichier TOML ; les verdicts par `verdict.py`, qui
  refuse tout verdict violant les formes.

Le graphe ne contient que des métadonnées, des empreintes et des statuts, jamais de fichier de données ni de résultats.

## Commandes

    python3 labo/graphe/graphe.py --config graphe/config.toml construire   # lit les sources, écrit le Turtle
    python3 labo/graphe/graphe.py --config graphe/config.toml valider      # formes SHACL, code 1 si violation
    python3 labo/graphe/graphe.py --config graphe/config.toml rapport H-001
    python3 labo/graphe/graphe.py --config graphe/config.toml compter
    python3 labo/graphe/verdict.py --config graphe/config.toml H-001 non-concluante --auteur orchestrateur \
        --condition "jeu J, modèle M" --course R-… --artefact recu.json --valeur 0.004 --ic-bas -0.006 --ic-haut 0.014

`config.exemple.toml` et `jugements.exemple.toml` montrent le format ; les chemins y sont relatifs au fichier de
configuration. Le rapport garde ce qui est écrit sous sa dernière rubrique (« Interprétation ») quand on le régénère.

## Les six statuts

Non testée, test invalide, non concluante, réfutée dans ces conditions, soutenue, suspendue (avec sa condition de
réouverture). « Réfutée » exige une carte confirmatoire, une prémisse vérifiée, une puissance recalculée d'au moins
0,8 et un IC dont la borne haute est sous l'effet minimal d'intérêt ; sinon c'est « non concluante ».

## Les formes (`formes.ttl`)

R0 empreinte SHA-256 ; R1 idée sourcée ; R2 hypothèse issue d'une idée, avec mesure et effet minimal ; R3 course avec
clé, état et carte de calcul ; R4 résultat tiré d'un artefact haché d'une course réussie ; R5 verdict à un seul statut,
fondé, conditionné, signé ; R6 réfutation ; R7 soutien ; R8 test invalide ; R9 carte datée avant sa course ; R10
décision fondée sur un verdict ; R11 raccourcis dérivés ; R12 suspension.

## Tests

    python3 -I labo/graphe/tests/test_graphe.py

Sans rdflib ni pyshacl, les tests sont sautés.
