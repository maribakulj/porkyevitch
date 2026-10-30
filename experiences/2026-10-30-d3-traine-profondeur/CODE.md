# D3 : code, blanc et notes qui le lient

30 octobre 2026. Claude wA:pH. Ce code applique la préinscription D3 (sha `4a4c0c63…`, feu vert de Grok p2, audit de Codex p4 en file). **Rien n'est lancé.** Le cache de B se lit sur Kaggle, dans la sortie montée de `mabaku/porky-diag-run` v3.

## Fichiers

- **`scripts/d3_core.py`** (numpy) :
  - fonctions E3 transcrites ;
  - S0 ;
  - cible R ;
  - vote et poids de TK ;
  - mélange sur R ;
  - parent direct et familles ;
  - porte et décision routée ;
  - comptes des enfants ;
  - choix de t ;
  - règle G et voie R ;
  - bootstrap par groupes.
- **`scripts/d3_run.py`** : étapes `blanc` et `complet`. Les voisins sont calculés en numpy float32 **sur CPU** (dérogation déclarée, voir « Correctifs du 30/10 »), la tête des enfants en torch sur **un T4 exigé**.
- **`scripts/kaggle_d3_run.py`** : pilote T4, SHA des scripts et des entrées vérifiés ; T4 et torch exigés et journalisés ; moniteur global.
- **`tests/test_d3_pilot.py`** (5 tests) : moniteur du pilote sur processus et horloges fictifs.
- **`tests/test_d3.py`** (13 tests, torch CPU, sous le drapeau de test local) :
  - parité E3 ;
  - profondeur et parent ;
  - familles par supports ;
  - remplacement routé et porte fermée ;
  - identité couverture × conditionnel ;
  - choix de t ;
  - juges et seuil de 100 ;
  - poids nul ;
  - poids négatifs du vote ;
  - bootstrap apparié ;
  - `blanc` puis `complet` de bout en bout sur données factices.

## Correctifs du 30/10 (audit de Codex p4)

**Blanc (B1).**
- **Plafond de session.** Le pilote appelait `subprocess.run` sans délai, et `WITHIN_2H` n'était qu'une extrapolation. Il surveille maintenant l'enfant, sur le modèle de `kaggle_gel_run.py` : 7 200 s par étape (§5 : une session T4 de 2 h au plus), comptées depuis le départ du pilote ; sorties sous `/kaggle/working` < 200 Mo ; RAM disponible ≥ 512 Mio et disque libre ≥ 256 Mio. Aucun plafond de RAM n'est préinscrit : c'est une garde de machine, et le pic est publié. Au premier dépassement, le groupe de processus est arrêté et `driver.json` vaut `failed`. Un `blanc.json` écrit par un passage échoué est renommé `blanc.REFUSED.json`. Une fin normale mais tardive est aussi un échec. L'époque et les supports ne sont pas modifiés.
- **Dispositif.** Plus de repli silencieux sur CPU. Le pilote exige un T4 avant de lancer l'enfant et journalise torch, CUDA et le nom du GPU. `d3_run.device()` refuse aussi tout autre dispositif. Le seul CPU possible passe par le drapeau explicite des tests locaux, `D3_CPU_FOR_LOCAL_TESTS`, que le pilote retire de l'environnement de l'enfant. `blanc.json` publie `environment` (dispositif, GPU, python, numpy, scipy, torch, CUDA, voisins). Le complet refuse un blanc relu dont l'environnement diffère.
- **Voisins sur CPU, dérogation déclarée.** La préinscription (§5) annonçait les voisins en float32 sur GPU. Le code les calcule en numpy float32 sur CPU, par blocs de 256 lignes. Le temps du blanc se rapporte donc à ce calcul, ce qui est écrit dans `blanc.json`. Une version GPU serait de nouveaux octets à relire.

**Avant le complet.**
- **B sans enfant émis.** La précision de B vaut `None`. `choose_t` comparait alors un nombre à `None` (TypeError reproduite par Codex). Il n'y a pas de précision à atteindre, donc la règle préinscrite « aucun t n'atteint la précision de B » s'applique : t = 0,95, signalé, avec la raison `B_emits_no_child_precision_undefined`.
- **Porte toujours fermée.** Couverture 0, rappel conditionnel `None` : le contrôle total = couverture × conditionnel échouait (TypeError). `check_identity` vérifie maintenant l'identité là où le conditionnel est défini. Ailleurs, il exige couverture = succès = rappel total = 0, et le conditionnel est publié comme non applicable, jamais comme un support. Le contrôle couvre aussi B lui-même (V-réglage, V-lecture) et chaque courbe de t. La descente améliorée n'est jamais établie quand une des grandeurs vaut `None`.
- **Comptes de descente, déclarés.** Ils portent sur les **codes bruts exacts** après `most_specific` et `drop86`, et non sur la reconnaissance du concept par fermeture. Par exemple, avec la vérité `11H` et la sortie `11H1`, ce diagnostic compte zéro succès exact pour `11H`, alors que H-F1 crédite le concept. Ce texte est écrit dans `bras2.json` (`counting`). Un résultat de cette sonde n'est pas une preuve causale générale sur l'information profonde des traits, et H-F1 reste le juge du pipeline.

## Les notes de Grok p2 (section 6), reprises dans le code

| Note | Où |
|---|---|
| H et E sur les 4 241 lignes non vides ; F_R et TP/FP/FN sur les 4 265 | `measures` (éligibles pour H/E, toutes les lignes pour `code_f1`) |
| Profondeur d'un code simple = nombre de ses nœuds préfixes ; composés à part ; parité avec `PART`/`TOKEN` ; « hors 86 » = `strip()` puis préfixe 86 | `depth_case`, `ancestors`, `drop86`, `is86` |
| Les 100 occurrences sont des couples (image, code) de la vérité de validation ; le plancher rend R indécidable sans suspendre G | `positives`, `route_r` |
| Bootstrap figé : `default_rng(20261030)`, percentile, descriptif. Les 64 lignes du blanc suivent l'ordre de `identites_validation.json` | `BOOT_SEED`, `bootstrap_groups`, `boot_fr`, `stage_blanc` |
| Précision du seuil t, rappel total, faux positifs et lecture « descente améliorée » comptés après `most_specific` et `drop86`, sur toutes les images du lot ; un seul t pour toutes les familles | `child_counts`, `choose_t`, `arm2_outputs` |
| Perte = moyenne sur les couples (ligne, enfant) actifs ; lots de 1 024 tirés parmi les lignes qui ont au moins un enfant actif | `train_head` |
| La mémoire permutée garde les poids visuels et déplace les étiquettes : son espérance est un a priori sur R, pas un second juge | `arm1(permuted=True)`, `witness_reading` |
| Vecteurs `feats/<fragment>.npz` (n, 4096) float16, recette `summary+meanspatial\|l2-each-then-l2`, passés en float32 ; les grilles ne sont pas une entrée | `Data` (forme, type et recette vérifiés) |
| Le cache du manifeste du diagnostic : `decisions_sha256`, vocabulaire et identités comparés | `Data` |

## Autres fixations faites par le script, pas des choix sur résultat

- **Projection de B** : au seuil converti en `float32`, comme le diagnostic, pour retrouver `ea2502e1…` exactement. Le mélange garde le type `float32`, si bien qu'un poids nul rend B à l'identique (contrôle sur 4 265/4 265).
- **Décision routée** : on part des codes de B au-dessus du seuil, on en retire tous les enfants de famille, puis on ajoute les enfants dont le parent est dans la fermeture de l'ensemble projeté de B et dont le score atteint t. Viennent ensuite `most_specific` et `drop86`.
- **Garde-fous** : si aucune famille n'atteint les supports, ou si aucune ligne n'a d'enfant actif, le script s'arrête pour amendement, sans relâcher les seuils. Une R vide rend la voie R indisponible, comme le prévoit P9-A 8.2.
- **Doublons de la mémoire** : le nombre de listes de 20 voisins qui contiennent un md5 répété est publié.

## Étapes

1. **`blanc`** : vérification des entrées, reproduction de B, S0 complet, identité du poids nul, voisins de 64 lignes, familles, une époque de la graine 0, puis extrapolation au statut `WITHIN_2H` ou `AMENDMENT_REQUIRED`. Aucun score.
2. **`complet`** : il refuse sans le blanc relu. Il écrit :
   - `s0.json` ;
   - `bras1.json` : bras, témoin, juges G puis R, bootstrap, V-lecture à part, strate de proximité, doublons ;
   - `bras2.json` : familles, t réglé sur V-réglage, puis, sur V-lecture, la couverture, les exclus, le rappel conditionnel et total, la précision, les faux positifs, l'identité, la fréquence × profondeur, le pipeline H/E, la règle G pour les trois graines et la lecture descriptive de la descente.

**Non couvert localement** : les vrais fichiers et le passage à l'échelle sur GPU. Le blanc les exerce.
