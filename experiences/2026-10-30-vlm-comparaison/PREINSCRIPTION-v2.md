# Comparaison avec des VLM — préinscription v2

30 octobre 2026. Claude wA:pH, à la demande de wA:p1, après l'accord de Marcel (**D18**). La v2 reprend la v1 (`PREINSCRIPTION-v1.md`, intacte) avec **trois systèmes**, une famille ajustée, des plafonds recalculés, et les choix d'implémentation imposés par le code (`scripts/`). Rien n'est lancé. Avant tout lancement, cette version passe par un sous-agent Sonnet puis par l'audit de Codex. Les points ouverts sont marqués **[à trancher]**, les faits que S0 doit établir **[à vérifier en S0]**.

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
| **G** | Gemini 3.8 Flash, `gemini-3.8-flash-medium` dans `agy` **[à vérifier en S0 : nom exact donné par `agy models`]** | `agy -p` (§2.2) | famille principale |
| **O** | Claude Opus 5.5, `claude-opus-5-5` | `claude -p` (§2.1) | **repère de plafond**, sur une petite tranche ; **descriptif**, hors famille ; pas un candidat de production (D18) |
| B | T-Z | décisions de validation (cache du diagnostic) et prédictions scellées du dev | référence interne |
| T\* | T-long | idem | référence publiée |

**Une image par appel, une session neuve par appel.** Les identifiants des modèles, la version des outils et la date de chaque appel sont journalisés.

### 2.1 Claude (H et O) : `claude -p`

- **Commande** : `claude -p <consigne> --model <id> --system-prompt <consigne système gelée> --tools Read --allowedTools Read --output-format stream-json --verbose --no-session-persistence`.
- **Dossier** : la commande est lancée dans un dossier temporaire qui ne contient que l'image.
- **Image réellement lue** : la consigne demande d'ouvrir l'image avec l'outil de lecture. Le flux `stream-json` doit contenir un appel `Read` sur ce chemin exact ; sinon, l'appel est classé **image non lue** et compté (§3.4).
- **Coût** : `total_cost_usd`, `usage` et `duration_ms` de l'événement `result`, journalisés tels quels. **Aucun prix tiré de mémoire.**
- **[à vérifier en S0]** :
  - que la mémoire et les réglages de l'utilisateur ne s'ajoutent pas au contexte ; sinon, `--bare` ou `--setting-sources ""`, au choix fixé avant S1 ;
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
- **VLM-libre** reste hors de cette v2 (désactivée) **[à trancher]**.

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
- **Famille principale** : **H − T\* et G − T\* sur le dev**, deux contrastes, correction de Bonferroni sur 2. La borne unilatérale est au niveau 1 − 0,05/2, c'est-à-dire le 2,5e centile du bootstrap pour la borne basse et le 97,5e pour la borne haute. Bootstrap apparié de 10 000 tirages par composantes, graine `20261035`.
- **Lecture écrite d'avance** (inchangée) :
  - borne basse > 0 : « dépasse T\* sur le dev, en accord de catalogue » ;
  - borne haute < 0 : « sous T\* sur le dev » ;
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
| temps réel par appel | mesuré par le script, de l'envoi à la fin du processus ; médiane, P90 et parallélisme déclarés | étape T4-chrono **[à trancher : ici ou préinscription séparée ; le code de cette v2 ne la contient pas]** |
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
5. **S1**.
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

**Budget** : **[à trancher par Marcel]** un plafond en dollars pour Claude (cumul de `total_cost_usd`) et un temps réel maximal par système. Au plafond, on arrête et on publie ce qui est fait comme **incomplet** ; jamais un sous-ensemble choisi après coup. Gemini n'a pas de coût rapporté : son plafond est le nombre d'appels et le temps.

**Parallélisme** : au plus 3 appels simultanés par système (pratique d'`agy`) **[à trancher]**, déclaré.

## 7. Ce que la comparaison ne permettra pas de dire (inchangé, avec O)

- Rien sur le test ICAI ni sur le test du Rijksmuseum.
- Pas de justesse visuelle.
- Pas de rapport coût–qualité unique.
- Pas de fidélité indépendante de G contre un juge Gemini.
- Pas de généralisation à d'autres consignes, versions ou dates.
- **Opus** : un repère sur au moins 50 images. Ce n'est ni une estimation de production ni un membre de la famille.

## 8. Questions restantes

1. Le budget en dollars (Claude) et le temps maximal par système.
2. La place de T4-chrono.
3. Le parallélisme (3 proposé).
4. VLM-libre : non par défaut.
