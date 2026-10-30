# Comparaison avec des VLM — préinscription v2.2

30 octobre 2026. Claude wA:pH, à la demande de wA:p1, après l'accord de Marcel (**D18**). La v2 reprend la v1 (`PREINSCRIPTION-v1.md`, intacte) avec **trois systèmes**, une famille ajustée, des plafonds recalculés, et les choix d'implémentation imposés par le code (`scripts/`). Rien n'est lancé. Avant tout lancement, cette version passe par un sous-agent Sonnet puis par l'audit de Codex. Les points ouverts sont marqués **[à trancher]**, les faits que S0 doit établir **[à vérifier en S0]**.

**v2.1 (décisions de wA:p1, 30/10)**, la v2 restant intacte :
- **budget dur de 30 USD au total** pour les appels Claude (H et O), mesuré par la somme des `total_cost_usd`, avec arrêt au dépassement. Gemini via `agy` n'a pas de coût monétaire rapporté : il est compté en appels et en temps ;
- **temps réel maximal de 6 h pour S1** ;
- **parallélisme : 3** appels simultanés par système ;
- **T4-chrono** fera l'objet d'une **préinscription séparée, plus tard**. Ici, la colonne du modèle rapide est **absente**, et c'est déclaré.

Toutes les mentions « [à trancher] » correspondantes ci-dessous sont remplacées par ces décisions.

**v2.2 (relecture Sonnet du code, décisions de wA:p1, 30/10)**, la v2.1 restant intacte :
- **B1** : les bornes de la famille sont **bilatérales Bonferroni sur 2**, soit les centiles **1,25 % et 98,75 %** du bootstrap. La lecture (§3.5) est écrite en conséquence ;
- **B2** : S1 s'exécute **par blocs, dans cet ordre** : dev H et G (la famille), puis la tranche Opus, puis V-diagnostic H et G, puis les graphes H et G. Une **règle d'extrapolation du coût à partir de S0** (§6) peut réduire **V-diagnostic seulement** ;
- **isolation de `claude -p`, décidée maintenant** (§2.1) ;
- **un `Read` en erreur ne compte pas comme image lue** (§2.1) ;
- **un appel Claude sans coût rapporté** (délai, échec) est imputé au budget à une **borne prudente** (§6) ;
- **au plus 3 appels Claude en vol au total**, H et O confondus (§6) ;
- **les 6 h de S1 sont cumulées entre reprises** (§6) ;
- **le nom du modèle Gemini est vérifié** : `gemini-3.8-flash-medium` figure dans `agy models` (30/10) ; « medium » est le niveau d'effort, déclaré.

## 0. Question et statut (inchangés)

Sur les **mêmes images**, avec le **même vocabulaire fermé V** (7 907 codes) et la **même métrique hiérarchique** (H-F1 de la série), que vaut un VLM généraliste appelé image par image face à la tête rapide sur encodeur gelé ? Le coût et le temps sont journalisés de la même façon des deux côtés.

- La comparaison est **exploratoire et descriptive** : aucune brique retenue, et T\* reste la référence publiée (D10).
- Toutes les images ont déjà été consultées. Le test ICAI et le test du banc Rijksmuseum **restent fermés** : le code ne lit que les fragments `train` d'ICAI et le seul membre « dev » du banc.
- **Contamination possible** : les jeux sont publics, et un VLM a pu les voir à l'entraînement. Elle est déclarée, et non mesurable.
- **Images envoyées à Google et à Anthropic** (D18) : même pratique qu'aux pilotes, déclarée. Aucune image n'est exclue.

## 1. Littérature (inchangée)

Voir v1 §1 : Spinaci, Klic et Colavizza ; Jolivet, Terriel et Vidal-Gorène ; Springstein et al. Ce sont des chiffres d'auteurs sur d'autres tâches, pas des cibles.

## 2. Systèmes

| Nom | Modèle | Accès | Rôle |
|---|---|---|---|
| **H** | Claude Haiku 5.5, `claude-haiku-5-5` | `claude -p` (§2.1) | famille principale |
| **G** | Gemini 3.8 Flash, `gemini-3.8-flash-medium` dans `agy` (vérifié par `agy models`, 30/10 ; effort « medium ») | `agy -p` (§2.2) | famille principale |
| **O** | Claude Opus 5.5, `claude-opus-5-5` | `claude -p` (§2.1) | **repère de plafond**, sur une petite tranche ; **descriptif**, hors famille ; pas un candidat de production (D18) |
| B | T-Z | décisions de validation (cache du diagnostic) et prédictions scellées du dev | référence interne |
| T\* | T-long | idem | référence publiée |

**Une image par appel, une session neuve par appel.** Les identifiants des modèles, la version des outils et la date de chaque appel sont journalisés.

### 2.1 Claude (H et O) : `claude -p`

- **Commande** : `claude -p <consigne> --model <id> --system-prompt <consigne système gelée> --tools Read --allowedTools Read --setting-sources "" --output-format stream-json --verbose --no-session-persistence`.
- **Dossier** : la commande est lancée dans un dossier temporaire neuf, sous le répertoire temporaire du système, **hors du dossier personnel**, qui ne contient que l'image.
- **Isolation (v2.2, décidée avant le sceau)** :
  - `--bare` est écarté : il n'accepte que `ANTHROPIC_API_KEY`, absente ici (l'authentification est OAuth) ;
  - `--setting-sources ""` : aucun réglage utilisateur, projet ou local (ni crochets ni permissions) ;
  - la mémoire automatique de Claude Code est rangée par dossier de travail : un dossier temporaire neuf n'en a aucune, et la mémoire du projet (rangée sous le dossier personnel) n'est pas chargée ;
  - il n'existe pas de `~/.claude/CLAUDE.md` (30/10). `vlm_call.py` **refuse de lancer** un appel Claude si ce fichier apparaît, ou si le dossier de travail est sous le dossier personnel.
- **Image réellement lue** : la consigne demande d'ouvrir l'image avec l'outil de lecture. Le flux `stream-json` doit contenir un appel `Read` sur ce chemin exact **et son résultat sans erreur** (`is_error` faux) ; sinon, l'appel est classé **image non lue** et compté (§3.4). Un refus reste un refus même sans lecture de l'image ; on publie le nombre de refus sans lecture.
- **Coût** : `total_cost_usd`, `usage` et `duration_ms` de l'événement `result`, journalisés tels quels. **Aucun prix tiré de mémoire.**
- **[à vérifier en S0]** :
  - que la température n'est pas exposée : elle reste la valeur par défaut, et c'est déclaré.

### 2.2 Gemini (G) : `agy -p`

Le danger est connu : en `agy -p`, Gemini peut répondre **sans ouvrir l'image** et inventer une réponse plausible. La garde reprend la méthode déjà utilisée pour BBVLM (`src/region_agy.py`).
- **Commande** : `agy -p <consigne avec @image> --model <id> --output-format json --print-timeout <délai>`, lancée dans un dossier qui ne contient que l'image.
- **Contenu de la consigne** :
  - « ouvre d'abord l'image ; si tu ne peux pas la voir, réponds IMAGE_ABSENTE » ;
  - « n'exécute aucune commande et n'utilise aucun outil autre que la lecture de l'image jointe » ;
  - « ne lis aucun autre fichier ».
- **Réponse acceptée seulement si** :
  - `status` vaut `SUCCESS` ;
  - la base sqlite de la conversation (`~/.gemini/antigravity-cli/conversations/<id>.db`, lue en lecture seule) montre que l'image a été ouverte ;
  - la réponse ne contient pas IMAGE_ABSENTE.
- **Sinon** : un seul nouvel essai, puis l'état « image non lue » ou « illisible ».
- **Coût** : `agy` ne rapporte pas de coût. On journalise l'objet `usage` (jetons) tel quel.
- **Réglages non contrôlables, déclarés** : température, graine et sûreté ne sont pas exposés par `agy`.
- **Asymétrie déclarée** : la consigne système de Claude est remplacée, celle d'`agy` ne l'est pas.

### 2.3 Images envoyées

- **ICAI** : les octets JPEG du fragment parquet, côté long ≤ 500 px. Leur md5 doit égaler celui des identités de validation.
- **Rijksmuseum** : les octets IIIF du gel, dont le SHA-256 doit égaler `image_sha256` du banc, téléchargés comme le gel (une requête par seconde).
- **Aucun redimensionnement par défaut.** **[à vérifier en S0]** : si un outil refuse une image trop lourde, la règle de redimensionnement (côté long, qualité JPEG) est écrite dans un amendement avant S1 et s'applique à tous les systèmes.

## 3. Tâche a : Iconclass

### 3.1 Échantillons, scellés avant tout appel (graine `20261035`)

- **V-diagnostic ICAI**, systèmes H et G :
  - V-diagnostic est l'ensemble d'A1 : la validation de la série, partagée par md5 avec le sel `A1-2026-10-29|`. On en garde les images évaluables, c'est-à-dire de vérité non vide après `drop86`. **Contrôle** : 2 100 images évaluables.
  - On tire les **groupes md5** dans une permutation fixée par la graine, et on les ajoute entiers jusqu'à atteindre au moins **200 images** (le nombre exact est publié).
- **Dev Rijksmuseum**, systèmes H et G : les **301 images** (239 composantes).
- **Tranche Opus**, système O : on tire les **composantes** du dev dans une permutation fixée par la graine, et on les ajoute entières jusqu'à atteindre au moins **50 images**.
- **Répétabilité**, systèmes H et G : de la même façon, au moins **20 images** du dev, par composantes entières, avec la graine `20261036`.
- La liste des identifiants est scellée par SHA-256. Le script vérifie `test_rows` = 0.

### 3.2 Consigne principale : VLM-V (inchangée par rapport à la v1)

- **Liste** : les 7 907 codes de V, dans l'ordre de `vocabulaire.json`, sont donnés **dans la consigne**, identique pour les trois systèmes.
- **Réponse attendue** : `{"codes": [...]}`, ou `{"refus": "<motif>"}` si le modèle refuse.
- **Pas de libellés, pas de plafond de cardinalité.**
- **Gel** : la consigne, la consigne système de Claude et la règle de nettoyage sont gelées par SHA-256 (`vlm_core.py`).
- **VLM-libre** reste hors de cette préinscription (décision v2.1).

### 3.3 Classes des chaînes (inchangées)

- **valide** : présente dans V, après nettoyage (espaces aux bords retirés) ;
- **hors V** : bien formée selon la règle syntaxique, mais absente de V ;
- **notation invalide** : mal formée.

La règle syntaxique est l'expression régulière de `vlm_core.NOTATION`. Le test vérifie qu'elle reconnaît les 7 907 codes de V, et qu'elle rejette le texte libre et les parenthèses non fermées. **Le taux d'invalidité**, (hors V + invalide) / chaînes émises, est publié par système. Seules les chaînes valides sont mesurées, après `drop86`.

### 3.4 États d'appel

- **réponse** : JSON lisible, image lue (§2.1, §2.2) ;
- **refus** :
  - pour Claude, l'objet `{"refus": ...}`, ou l'arrêt du modèle pour cause de refus (`stop_reason` « refusal ») ;
  - pour Gemini, l'objet `{"refus": ...}`, ou un statut de blocage de sûreté ;
  - aucun nouvel essai ;
- **illisible** : pas d'objet JSON exploitable. Un seul nouvel essai, puis ensemble vide ;
- **image non lue** : traitée comme illisible (un nouvel essai, puis ensemble vide), mais comptée à part ;
- **échec technique** : délai dépassé, sortie vide de l'outil. Un seul nouvel essai, puis ensemble vide.

**Toutes les images restent au dénominateur.** Les comptes des états sont publiés par système.

### 3.5 Métrique, famille et lecture

- **Mesure** : `a1_core.hier_f1` (copie à l'octet, épinglée) par image, sur la vérité projetée. Mêmes fonctions pour B et T\*.
- **B et T\* sur V-diagnostic** : les probabilités de validation du diagnostic de la tête, projetées aux seuils 0,65 (B) et 0,6 (T\*). **Contrôles** :
  - l'empreinte des décisions de chaque tête égale celle du cache ;
  - le H-F1 de B sur les 2 100 évaluables de V-diagnostic vaut 0,5860487335040372 (A1).

  Ce sont des recalculs CPU en float32, déclarés comme tels par le cache.
- **B et T\* sur le dev** : les deux fichiers du dev du sceau de la phase 1 (`3c468faa`), et seulement ceux-là. **Contrôles** : H-F1 de B et de T\* égaux aux valeurs d'A1-dev (`dev.json`, `3cc297f4`), à 10⁻⁹ près.
- **Famille principale** : **H − T\* et G − T\* sur le dev**, deux contrastes, correction de Bonferroni sur 2. Les bornes sont **bilatérales, Bonferroni sur 2** : le **1,25e centile** du bootstrap pour la borne basse et le **98,75e** pour la borne haute (risque de famille 5 %, les deux côtés de la lecture compris). L'IC95 non corrigé est publié à côté, comme description. Bootstrap apparié de 10 000 tirages par composantes, graine `20261035`.
- **Lecture écrite d'avance** (bornes de Bonferroni ci-dessus) :
  - borne basse (1,25 %) > 0 : « dépasse T\* sur le dev, en accord de catalogue » ;
  - borne haute (98,75 %) < 0 : « sous T\* sur le dev » ;
  - sinon : « pas de différence établie ».
- **Descriptif, hors famille** :
  - H − B et G − B, sur les deux banques ;
  - H − T\* et G − T\* sur V-diagnostic, par groupes md5 ;
  - **O − T\*, O − B, O − H et O − G sur la tranche Opus**, avec un IC95 par composantes, mais sans lecture de décision ;
  - accord exact, cardinalité, taux d'invalidité, états d'appel, répétabilité.

### 3.6 Répétabilité (H et G)

Les images de répétabilité sont appelées une seconde fois, après tout S1. On publie le Jaccard des ensembles valides entre les deux appels, et l'écart de H-F1. Le premier appel est celui qui compte.

## 4. Tâche b : graphes (H et G seulement, descriptive)

- **Images** : les 26 images d'évaluation qui ont un graphe Gemini (`listes.json`, rôle « evaluation »). Opus n'y entre pas.
- **Consigne** : au plus 30 objets, `{"objets": [{"nom": ..., "boite": [x0, y0, x1, y1]}]}`, boîtes en millièmes, par saillance décroissante. Le rang tient lieu de score, et c'est déclaré.
- **Mesure** : `pe_common.clean_box`, `recall_counts` et `pooled_recall` (copie épinglée), IoU ≥ 0,5, sans classe, top 30. Les références sont les boîtes de `load_graph` du petit élève, reproduites à l'identique.
  - **Contre le juge Gemini** : c'est **circulaire** pour G, et déclaré.
  - **Contre S1b**.
- **Repères** repris sans recalcul (Résultats v3 §7). Aucune règle de décision ; relations non mesurées.

## 5. Journal de coût et de temps (inchangé, avec O)

| Champ | VLM (H, G, O) | Modèle rapide (B, T\*) |
|---|---|---|
| temps réel par appel | mesuré par le script, de l'envoi à la fin du processus ; médiane, P90 et parallélisme déclarés | **absente ici** : T4-chrono fera l'objet d'une préinscription séparée, plus tard (décision du 30/10) |
| durée rapportée par l'outil | `duration_ms` pour Claude ; aucune pour `agy` | — |
| coût | `total_cost_usd` pour Claude ; `usage` pour `agy` ; aucun prix de mémoire | heures T4, sans prix inventé |
| essais | nombre d'essais, avec l'état de chacun | — |

**Lecture** : une latence d'API n'est pas un débit sur T4. Les deux journaux sont publiés côte à côte, sans rapport unique.

## 6. Ordre et plafonds

**Ordre** :
1. `vlm_prepare.py` : échantillons, images, vérités et références, avec les contrôles d'identité, puis le sceau de la préparation.
2. Gel des consignes et du code (SHA dans le sceau).
3. **S0** : 5 images du dev par système, et 2 images de la tâche b pour H et G. On publie les états, l'invalidité et le temps, **aucun score**.
4. Un amendement daté si S0 l'impose.
5. **Plan de S1** : la règle d'extrapolation ci-dessous, appliquée au journal de S0, écrit `plan_S1.json` (déterministe). Puis **S1, par blocs** : (i) dev, H et G ; (ii) tranche Opus ; (iii) V-diagnostic, H et G, dans l'ordre du tirage des groupes ; (iv) graphes, H et G. Un bloc commence quand le précédent est fini.
6. **Répétabilité**.
7. Gel des sorties brutes.
8. Planche et reçu.
9. `vlm_measure.py`, puis la `LECTURE.md`.

`vlm_call.py` **ne calcule aucun score**. `vlm_measure.py` refuse de tourner sans le reçu.

**Appels prévus, par l'arithmétique de §3.1** :

| Étape | Calcul | Appels |
|---|---|---:|
| Tâche a, H et G | 2 × (≥ 200 + 301) | ≥ 1 002 |
| Tâche a, tranche O | ≥ 50 | ≥ 50 |
| Répétabilité, H et G | 2 × ≥ 20 | ≥ 40 |
| Tâche b, H et G | 2 × 26 | 52 |
| **Total S1** | | **≈ 1 144** (le nombre exact est fixé par le sceau de préparation) |
| S0 | H et G : 5 + 2 chacun ; O : 5 | 19 |

**Plafond dur** : `vlm_call.py` refuse d'appeler au-delà de 1,15 fois le nombre prévu par le sceau, ce qui laisse la place aux nouveaux essais.

**Budget** : **30 USD au total** pour H et O ensemble (cumul des `total_cost_usd` de tous les essais, S0 compris), et **6 h** de temps réel pour S1. `vlm_call.py` vérifie le cumul **avant** chaque appel Claude et s'arrête dès qu'il atteint 30 USD ; les appels déjà en cours (au plus 3 par système Claude, parallélisme 3) peuvent faire dépasser légèrement, et ce dépassement est publié. Le budget n'arrête que H et O : G continue jusqu'à son propre plafond (appels, temps). Au plafond, on arrête et on publie ce qui est fait comme **incomplet** ; jamais un sous-ensemble choisi après coup. Gemini n'a pas de coût rapporté : son plafond est le nombre d'appels et le temps.

**Parallélisme** : 3 appels simultanés par système, au plus, et **3 appels Claude en vol au total**, H et O confondus.

**Règle d'extrapolation du coût (v2.2, B2)**, appliquée une fois, après S0 et avant S1 :
1. Coûts unitaires tirés du journal de S0, essais compris : `c_H` (moyenne des `total_cost_usd` des appels H « codes »), `c_Hb` (H « boîtes »), `c_O` (O « codes »). Un coût unitaire non observé prend la borne prudente ci-dessous.
2. Coût prévu : P(n) = 1,2 × [c_H × (n_dev + n + n_repet) + c_Hb × n_graphes + c_O × n_opus], où n est le nombre d'images de V-diagnostic retenues. Le facteur 1,2 couvre les nouveaux essais.
3. Disponible : A = 30 − dépense de S0.
4. Si P(n complet) ≤ A : plan complet. Sinon, on garde **le plus long préfixe des groupes de V-diagnostic, dans l'ordre du tirage**, tel que P(n) ≤ A ; la réduction s'applique à H **et** à G (mêmes images). Le dev, la tranche Opus, la répétabilité et les graphes ne sont jamais réduits.
5. Si P(0) > A : S1 n'est pas lancé, et la décision revient à Marcel.
6. Le plan et le calcul sont écrits dans `plan_S1.json`, publiés, et vérifiés à chaque reprise.

**Borne prudente (v2.2)** : un essai Claude sans `total_cost_usd` (délai, échec technique) est imputé au budget pour **2 fois le plus grand coût observé pour ce système**, ou **1 USD** si aucun n'est encore observé. L'imputation est écrite dans le journal (`budget_charge_usd`).

**Temps de S1 (v2.2)** : les 6 h sont **cumulées entre reprises** (fichier `wall_S1.json`, mis à jour après chaque essai).

## 7. Ce que la comparaison ne permettra pas de dire (inchangé, avec O)

- Rien sur le test ICAI ni sur le test du Rijksmuseum.
- Pas de justesse visuelle.
- Pas de rapport coût–qualité unique.
- Pas de fidélité indépendante de G contre un juge Gemini.
- Pas de généralisation à d'autres consignes, versions ou dates.
- **Opus** : un repère sur au moins 50 images. Ce n'est ni une estimation de production ni un membre de la famille.

## 8. Questions restantes

1. VLM-libre : non (hors de cette préinscription).

Budget, temps, parallélisme et T4-chrono sont tranchés (en-tête v2.1).
