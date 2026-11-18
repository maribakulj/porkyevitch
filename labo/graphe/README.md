# Le graphe de recherche

Un graphe Turtle des idées, hypothèses, cartes, courses, résultats, verdicts et décisions d'un projet. Il sert à
répondre sans relire tout le journal : d'où vient cette piste, a-t-elle été testée, avec quelle puissance, et que
faudrait-il pour la rouvrir. Outil **facultatif** : le reste du plugin n'a pas besoin de lui.

    pip install -r labo/graphe/requirements.txt        # rdflib et pyshacl

## Ce qui est écrit par qui

- **Les faits**, par le générateur : le tableau des idées, les notations d'un tri, les cartes de recherche (empreinte,
  date du dernier commit, puissance recalculée par `labo/puissance.py`), les cartes de calcul, les courses du guichet
  et leurs artefacts hachés.
- **Les jugements**, par les agents : hypothèses dans un fichier TOML ; les verdicts par `verdict.py` et les décisions
  par `decision.py`, qui refusent tout ajout violant les formes.

Le graphe ne contient que des métadonnées, des empreintes et des statuts, jamais de fichier de données ni de résultats.

## Commandes

    python3 labo/graphe/graphe.py --config graphe/config.toml construire   # lit les sources, écrit le Turtle
    python3 labo/graphe/graphe.py --config graphe/config.toml valider      # formes SHACL, code 1 si violation
    python3 labo/graphe/graphe.py --config graphe/config.toml rapport H-001
    python3 labo/graphe/graphe.py --config graphe/config.toml compter
    python3 labo/graphe/verdict.py --config graphe/config.toml H-001 non-concluante --auteur orchestrateur \
        --condition "jeu J, modèle M" --course R-… --artefact recu.json --valeur 0.004 --ic-bas -0.006 --ic-haut 0.014

## Les décisions (`decision.py`, `decideur.py`)

    python3 labo/graphe/decision.py --config graphe/config.toml proposer decision.toml   # code 1 si refusée, fichier inchangé
    python3 labo/graphe/decision.py --config graphe/config.toml executer D-1             # état « executee », date d'exécution
    python3 labo/graphe/decision.py --config graphe/config.toml noter D-1 --issue "…" --realisee true \
        [--changement-realise true|false] [--statut-obtenu non-concluante] [--heures-mesurees 2] [--heures-agent-mesurees 1]
    python3 labo/graphe/decision.py --config graphe/config.toml renverser D-1 --par D-2
    python3 labo/graphe/decision.py --config graphe/config.toml bilan
    python3 labo/graphe/decideur.py --config graphe/config.toml                          # file des candidats

Une décision (classe `lab:Decision`, pas de classe en plus) porte : au moins deux options avec leur valeur V, dont
« ne rien faire » ; le choix ; la règle invoquée ; deux prédictions (issue attendue parmi les six statuts avec sa
probabilité, et probabilité que l'issue change une décision suivante) ; un poids de 1 à 5 ; un chantier (`C-n`, une
`prov:Collection`) ; un effet ; des heures d'agent et de calcul estimées ; un état (proposee, en_attente_humain, relue,
executee, notee) ; un remplacement éventuel (`prov:wasRevisionOf`). Le fichier d'une décision à proposer est un TOML
dont les champs sont décrits en tête de `decision.py`.

**L'importance est calculée par `decision.py`, jamais choisie** : importante si le poids est d'au moins 4, si l'effet est
`ouvre_chantier`, `ferme_chantier`, `clot_piste` ou `production`, si la décision écrit ou propose un statut réfuté ou
suspendu, si les heures de calcul du chantier dépassent 3 h sur 24 h, ou si elle s'appuie sur un verdict exploratoire
pour une mise en production. Une décision importante exige une relecture (verdict, date, auteur différent de celui de la
décision) et l'empreinte SHA-256 du fichier de candidats dont les cinq premiers forment le dossier de relecture ;
exécutée, elle doit avoir été relue avant l'exécution.

`noter` écrit l'issue réelle, la réalisation des deux prédictions et les coûts mesurés. `bilan` donne : le score de
Brier de l'issue et celui de `p_changement`, chacun avec son score de compétence relatif au taux de base
(1 − Brier / Brier du taux de base), la part des décisions courantes et importantes, la part d'issues non concluantes,
le taux de décisions (champ `renversee_par`) et de verdicts conclusifs renversés plus tard, et la médiane du rapport
coût mesuré / estimé avec l'écart signé en heures.

`decideur.py` lit le graphe et écrit `file-candidats.json`, `file-candidats.md` et `dossier-relecture.json`. Il ne décide
rien. Candidats : cartes sans `RELECTURE-CONCEPTION.md` (et sans course), cartes confirmatoires sans `regle.py` ni `temoins/*.json`
dans leur dossier (« instrument manquant », voir `labo/regle`), courses réussies sans verdict, verdicts
conclusifs portés par une seule course, une vérification de prémisse pour chaque prémisse non vérifiée d'une hypothèse
ouverte, les réouvertures (dernier verdict non concluant, invalide ou suspendu, avec sa condition) et le portefeuille
(idées gardées par les deux notateurs, sans hypothèse, rangées par S moyen des deux). **Règle d'arrêt** : une lignée
d'hypothèses (`revision_de` dans le fichier des hypothèses, `prov:wasRevisionOf` dans le graphe) qui compte deux verdicts
non concluants sur les mêmes données (`--donnees` de `verdict.py`, une ressource `lab:donnees`) voit ses nouvelles
cartes marquées « écartée (règle d'arrêt) ». Il compte aussi les chantiers actifs et signale plus de 3.
Un verdict soutenu ou réfuté sans `recalcule_par` (artefact d'un recalcul indépendant, par exemple `labo/regle/rejouer.py`)
reste candidat « recalcul ».
Précisions : une prémisse infirmée (état `infirmee`) donne une seule réouverture « redessiner sans cette prémisse »,
même partagée par plusieurs hypothèses ; un verdict qui porte `remplace` (`verdict.py --remplace`) laisse seul son
remplaçant compter ; une idée est couverte (hors du rang, comptée à part) si une hypothèse la cite, si une idée interne
la désigne en `proche_de` ou si une hypothèse porte `couvre = ["I…"]` ; `[[course_technique]] id = "R-…" motif = "…"`
retire une course sans hypothèse des candidats « verdict » ; la source 4 lit `jugements/instruments.toml`
(`[[instrument]]` id, description, fait, poids) et liste les instruments non faits. La source 5 (suites déclarées)
n'est pas lue. R17 ne vaut que pour les courses commencées ou finies après le 18/11/2026 17 h.

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
décision fondée sur un verdict, une idée, un résultat ou une décision ; R11 raccourcis dérivés ; R12 suspension ;
R13 options (au moins deux, dont « ne rien faire », avec V ; choix parmi elles) ; R14 deux prédictions ; R15 relecture
d'une décision importante (autre auteur, empreinte du dossier, avant l'exécution) ; R16 importance forcée ; R17 pas de
course sur une carte confirmatoire à prémisse non vérifiée ; R18 lignée et données de verdict.

## Tests

    python3 -I labo/graphe/tests/test_graphe.py
    python3 -I labo/graphe/tests/test_decision.py

Sans rdflib ni pyshacl, les tests sont sautés.
