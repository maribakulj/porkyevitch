# Tirage de la tranche de 300 images S1b : préinscription

Version 1, 30 octobre 2026. Claude wA:pH. Demande de wA:p1 après la décision D2 (`~/porkyevitch/DECISIONS.md`, point 3 et 4) et l'avis de Codex p4 (`~/Documents/reviews/porkyevitch-d2-codex.md`, « Première tranche »). Écrite **avant** tout tirage. À relire par Grok p2 puis à faire auditer par Codex p4. Rien n'est lancé.

Ce document ne fixe que **le tirage**. L'annotation par Haiku S1b (lanceur `claude -p`, audit à part), son coût et l'usage des 300 graphes pour l'entraînement sont hors de ce texte. Cet usage reste conditionné à la porte du petit élève (lecture D2 de sa préinscription).

## Base

Le script reprend le tirage relu du pilote Gemini, `~/porkyevitch/experiences/2026-10-29-graphes-gemini/scripts/tirage_pilote.py` (sha `42e6efc4…`), avec ses lectures, ses contrôles et son format de sortie. Il y ajoute l'exclusion du pilote, les strates, la validation interne et des noms neutres.

## Population

- **Apprentissage ICAI seulement** : `davanstrien/iconclass-vlm-brillfull` à la révision `8045366…`, les onze fragments `train-*` (86 216 lignes).
- On retire, dans cet ordre :
  1. les groupes md5 de la **validation de la série**, `default_rng(0).random(len(groups)) < 0,05` sur les md5 triés ;
  2. les **copies exactes d'une image du test**, en lisant le seul champ md5 du fragment test (3 connues) ;
  3. les **200 groupes du pilote Gemini**, lus dans son `tirage/tirage.json` (sha `6f618135…`, vérifié).
- Les exemples, le réglage, l'évaluation du professeur et le test de 20 sont tous des images `pNNN` de ce pilote (vérifié sur `ensembles.json` et `test20/selection.json`). Ils sont donc tous exclus.
- On garde une image par groupe : sa première ligne dans l'ordre des fragments.
- La disjonction md5 est un minimum, pas une preuve d'indépendance des œuvres (Codex p4).

## Strates : le chapitre Iconclass

- Le **chapitre d'un code** est son premier caractère, un chiffre de 0 à 9. On le lit sur les étiquettes d'apprentissage, après retrait des codes 86 (`drop86`, comme la série) et des espaces.
- Le **chapitre d'une image** est celui qui porte le plus de ses codes distincts.
  - En cas d'égalité, on prend le chapitre présent dans le moins de groupes de la population (cela favorise le plus rare), puis le plus petit chiffre.
  - Une image sans aucun chapitre est écartée, et son nombre est publié.
- Ces codes ne servent qu'au tirage. Ils ne sont **jamais transmis à l'annotateur**.

## Répartition, graines écrites d'avance

- **N = 300**. Chaque chapitre reçoit d'abord min(10, N_h), où N_h est son effectif dans la population. Le reste est réparti en proportion de N_h par la méthode des plus forts restes (égalité : plus petit chiffre), sans dépasser N_h.
- Dans le chapitre h, on tire `default_rng([31, h]).choice(groupes triés de h, n_h, replace=False)`.
- **Validation interne de 60**, figée avant toute annotation (Codex p4 : 240 pour l'apprentissage, 60 pour la validation interne).
  - Le chapitre h en reçoit v_h, soit 60·n_h/300 aux plus forts restes.
  - Ce sont les v_h premiers de `default_rng([32, h]).permutation(n_h)` dans l'ordre du tirage.
  - Ces 60 sont aussi, si wA:p1 le retient, les 60 images de la seconde réponse S1b et du contrôle humain proposé par Codex. La première réponse reste la cible.
- **Noms neutres** : les fichiers sont nommés `t000` à `t299` dans l'ordre de `default_rng(33).permutation(300)`. Un nom ne dit rien du chapitre ni du rôle.
- Le tirage avec minimum **n'est pas représentatif** du corpus. Les probabilités d'inclusion n_h/N_h sont publiées par chapitre, et tout résultat sur la tranche se donne par strate ou pondéré par ces probabilités.

## Sorties, séparées

- `tirage.json` : population et exclusions comptées, table des chapitres (N_h, groupes ayant un code du chapitre, n_h, probabilité d'inclusion, v_h), règle et graines, puis pour chaque image son nom, md5, fragment, ligne, chapitre et rôle. Ce fichier n'est jamais donné à l'annotateur.
- `images/tNNN.<ext>` : les octets d'origine, avec md5 contrôlé (au complet seulement).
- `verite.json` : les codes de chaque image, **à part**, jamais montré à l'annotateur (au complet seulement).
- `run.json` : étape, sha du script et du tirage du pilote, versions.
- L'annotateur ne reçoit qu'une copie de l'image, dans un dossier qui ne contient rien d'autre (comme le pilote).

## Exécution prévue

Kaggle CPU, quelques minutes. Le pilote `scripts/kaggle_tirage_300.py` vérifie le sha du script relu et celui du tirage du pilote. Entrées : un jeu de données contenant `tirage_300.py` et le `tirage.json` du pilote, plus la sortie complète de `caypollard-encode-cradio` v3.

- **Blanc** (`STAGE = "plan"`) : il écrit `tirage.json` et `run.json`, sans lire aucune image. La table des chapitres et la liste sont relues avant le complet. Le tirage est déterministe : le complet doit redonner exactement ce `tirage.json`, hors les noms de fichiers ajoutés.
- **Complet** (`STAGE = "full"`, seule modification permise du pilote) : il récupère les images (≈ 75 Mo) et écrit `verite.json`.
- Les sorties vont dans `~/porkyevitch-donnees/graphes-haiku/tranche300/`, hors git, après un `df`. Dans git : `tirage.json` et `run.json`.

Tests locaux : `python3 -I tests/test_tirage_300.py`, 8 tests synthétiques. Ils couvrent la règle des chapitres et ses égalités, `drop86`, la répartition (minimum, plafonds, proportion, plus forts restes), les exclusions, la première ligne par groupe, les 60 de validation, les noms neutres et le déterminisme. Ils ne couvrent ni la lecture des fragments ni le téléchargement : le blanc le fait.
