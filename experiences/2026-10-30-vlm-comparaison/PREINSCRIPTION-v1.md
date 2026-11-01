# Comparaison avec des VLM — préinscription v1 (proposition, non gelée)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1. La v1 révise le brouillon (`PREINSCRIPTION-brouillon.md`, intact) à la lumière de la note de littérature de Grok p7 (`~/Documents/reviews/porkyevitch-vlm-litterature-grok.md`).

**Statut.** Rien n'est lancé, rien n'est tiré, aucun appel n'est fait. La suite attend la décision de Marcel, puis une relecture par un sous-agent Sonnet et l'audit de Codex. Les choix ouverts sont marqués **[à trancher]**, les faits à vérifier **[à vérifier]**.

**Ce qui change par rapport au brouillon.**
1. **Le vocabulaire fermé V est la variante principale.** La variante libre devient facultative, descriptive et hors famille, désactivée par défaut.
2. **Les codes invalides sont comptés à part**, en deux classes : hors de V, et notation invalide. On publie leur taux, comme dans Jolivet et al.
3. **Les refus sont comptés à part** des réponses illisibles. Les réglages de sûreté sont journalisés.
4. **Un contrôle de répétabilité** : 20 images appelées deux fois par système.
5. **Un journal de coût et de temps identique des deux côtés.** Pour le modèle rapide, une étape de chronométrage sur T4, sans score.
6. **La cardinalité** (codes émis par image) est publiée à côté du H-F1.
7. **Une section de littérature**, avec des chiffres d'auteurs qui ne sont pas des cibles.

## 0. Question

Sur les **mêmes images**, avec le **même vocabulaire fermé V** (7 907 codes) et la **même métrique hiérarchique** (H-F1 de la série), que vaut un VLM généraliste appelé image par image face à la tête rapide sur encodeur gelé ? Et à quel coût, et en combien de temps, journalisés de la même façon des deux côtés ?

La comparaison est **exploratoire et descriptive**. Elle ne retient aucune brique et ne change pas la référence publiée T\* (D10). Toutes les images ont déjà été consultées. Le test ICAI et le test du banc Rijksmuseum **restent fermés**.

**Contamination possible, déclarée.** Le jeu Iconclass et les collections du Rijksmuseum sont publics : un VLM a pu voir ces images ou leurs notices pendant son entraînement. Ce n'est pas mesurable ici.

## 1. Littérature, chiffres d'auteurs, pas des cibles

D'après la note de Grok p7 : seules les pages qu'il a ouvertes, et les chiffres de leurs auteurs.

- **Spinaci, Klic et Colavizza** (arXiv:2509.18839). Accuracy top-1 sur dix saints, un seul choix par image parmi dix noms, dont un sous-ensemble filtré de l'ICONCLASS AI Test Set (863 images). Gemini 2.5 Pro y obtient 83,31 en test 1 (tableau 3). Ce n'est **ni le vocabulaire Iconclass ni un F1 de catalogue**. Réglages : température 0, graine fixée, sûreté de Gemini à BLOCK_NONE, parce que l'art religieux serait sinon refusé. Sur 36 paires de quasi-doublons, GPT-4o ne répète sa prédiction qu'environ 27 % du temps.
- **Jolivet, Terriel et Vidal-Gorène** (arXiv:2610.38462, sur le thésaurus TIMEL, pas Iconclass). C'est le seul voisin ouvert qui oppose un VLM génératif à une tête fermée sur encodeur gelé. L'évaluation porte sur 46 images. Le taux de sorties invalides va de **0 % à 29,2 %** selon le format de sortie, et un prec@1 élevé peut aller avec un hier-F1 faible. Gemini-3-Flash, en zéro-shot, émet 22,4 concepts par image. Aucun débit ni aucun coût n'est publié.
- **Springstein et al.** (WACV 2024) mesurent un CLIP zéro-shot en mAP, pas un VLM génératif.
- **Graphes de scène d'œuvres** : aucune page ouverte ne donne de score de VLM.

**Conséquences pour ce protocole** : mêmes images, même vocabulaire, même métrique, sorties invalides comptées à part, journal de coût identique des deux côtés. Aucun de ces chiffres n'estime l'issue de la comparaison.

## 2. Systèmes

| Nom | Modèle | Accès | Réglages journalisés |
|---|---|---|---|
| G | Gemini 3.8 Flash | `agy -p`, image en pièce jointe, aucune commande permise | température, sûreté et graine si `agy` les expose **[à vérifier]** ; sinon « défaut de l'outil », déclaré |
| C | **un seul** modèle Claude **[à trancher : Sonnet 5.5 `claude-sonnet-5-5`, Opus 5.5 `claude-opus-5-5`, Fable 5.1 `claude-fable-5-1`]** | `claude -p --model …`, sortie JSON, image en pièce jointe | modèle et version de l'outil ; température si elle est exposée **[à vérifier]** |
| B | T-Z | prédictions **scellées** de V-diagnostic et du dev | — |
| T\* | T-long, référence publiée | prédictions **scellées** de V-diagnostic et du dev | — |

- **Une image par appel**, sans lot. Spinaci et al. groupaient les images par cinq ; ici, on évite qu'une image influence la réponse sur une autre.
- **Les identifiants exacts** des modèles et la date de chaque appel sont journalisés.
- Les prédictions de B et de T\* sur V-diagnostic et sur le dev viennent des sources de D10 et d'A1-dev **[à vérifier : chemins et SHA exacts ; T\* sur V-diagnostic]**.

## 3. Tâche a : Iconclass

### 3.1 Échantillons, scellés avant tout appel

- **V-diagnostic ICAI** : 200 images tirées **par groupes md5** parmi les 2 100 évaluables, avec la graine `20261035` **[à trancher : 200]**.
- **Dev Rijksmuseum** : les **301 images** (239 composantes) entières, la population d'A1-dev. Seul le membre « dev » du banc est décodé.
- **Images sensibles** (D11) : les envoyer ou les exclure **avant le tirage** **[à trancher par Marcel]**. En cas d'exclusion, le nombre exclu est publié.
- La liste des identifiants est scellée par SHA-256. `test_rows` = 0 est vérifié par le script.

### 3.2 Consigne principale : VLM-V (vocabulaire fermé)

- La consigne donne la liste des 7 907 codes de V (`vocabulaire.json`). Elle demande les codes de cette liste qu'un catalogueur attribuerait à l'image, en JSON (`{"codes": [...]}`).
- **Aucun nombre de codes n'est imposé** : un plafond serait un réglage. La cardinalité est publiée.
- **Libellés des codes** : sans libellés par défaut. Le vocabulaire ne les contient pas, et toute source de libellés devrait être citée **[à trancher]**.
- La consigne, le format et la règle de nettoyage (espaces, casse) sont **gelés par SHA-256** avant le tirage.

### 3.3 Variante facultative : VLM-libre

Elle est désactivée par défaut **[à trancher]**. La consigne est la même, sans liste. On l'analyse de deux façons :
- **projection sur V**, puis la même mesure que ci-dessus ;
- **descriptif brut**, sur les codes tels quels.

Elle reste hors famille.

### 3.4 Codes invalides et réponses manquantes

Chaque chaîne émise reçoit une seule classe :
- **valide**, si elle est dans V ;
- **hors V**, si c'est une notation Iconclass bien formée mais absente de V ;
- **notation invalide**, si elle n'a pas la syntaxe d'une notation.

On publie le **taux d'invalidité**, (hors V + notation invalide) / chaînes émises, par système. La tête fermée a ce taux à 0 par construction. Seuls les codes valides sont mesurés, après `drop86`. **[à vérifier]** : la règle syntaxique d'une notation sera écrite dans le code et testée sur les 7 907 codes de V, qui doivent tous être reconnus valides.

Chaque appel reçoit aussi un état :
- **réponse**, si le JSON est lisible ;
- **illisible** : un seul nouvel essai, journalisé, puis ensemble vide ;
- **refus** : ensemble vide, sans nouvel essai, et le motif est journalisé s'il est donné.

Le dénominateur garde **toutes** les images. On publie les comptes des trois états.

### 3.5 Métrique et lecture

- **Le même code** que la série : `a1_core.ancestors`, `closure`, `drop86` et `hier_f1`, copiés à l'octet et épinglés par SHA-256. On mesure le H-F1 par image, sur la vérité projetée (chapitre 86 retiré).
- **Contrastes appariés** VLM − T\* et VLM − B, par banque. Bootstrap de 10 000 tirages, graine `20261035`, par groupes md5 sur V-diagnostic et par composantes sur le dev.
- **Famille principale** : **VLM-V − T\* sur le dev**, avec 2 contrastes (G et C), au niveau unilatéral 1 − 0,05/2. Tout le reste est descriptif : VLM − B, V-diagnostic, accord exact, cardinalité, taux d'invalidité, VLM-libre.
- **Lecture écrite d'avance** :
  - borne basse > 0 : « dépasse T\* sur le dev, en accord de catalogue » ;
  - borne haute < 0 : « sous T\* sur le dev » ;
  - sinon : « pas de différence établie ».

  Avec 239 composantes, l'intervalle d'A1-dev avait une largeur d'environ 0,05 : un écart de cet ordre ne sera pas tranché, et c'est écrit d'avance.
- **Répétabilité, descriptive.** 20 images du dev, tirées dans l'échantillon avec la même graine, sont appelées une seconde fois par système. On publie le Jaccard des ensembles valides entre les deux appels et l'écart de H-F1. Spinaci et al. montrent qu'une température 0 ne garantit pas la répétition. Le premier appel est celui qui compte.

## 4. Tâche b : graphes, descriptive

- **Images** : les 26 images d'évaluation du petit élève.
- **Consigne** : au plus 30 objets, boîtes en millièmes, convention de `pe_common.clean_box`, par saillance décroissante. Le rang tient lieu de score, et c'est déclaré.
- **Mesure** : `pe_common.recall_counts` et `pooled_recall` (IoU ≥ 0,5, sans classe, top 30), code épinglé, contre :
  - **le juge Gemini**, ce qui est **circulaire** pour G (déclaré, et ce n'est pas une fidélité indépendante) ;
  - **S1b**.
- **Repères repris sans recalcul** (Résultats v3 §7) : a priori 0,258, OWLv2 0,307, élève 28×28 de 0,225 à 0,246.
- **Aucune règle de décision.** D2 juge l'élève, pas un VLM. La littérature ouverte n'a aucun score de VLM sur des graphes d'œuvres. Les relations ne sont pas mesurées **[à trancher]**.

## 5. Journal de coût et de temps, identique des deux côtés

| Champ | VLM (G, C) | Modèle rapide (B, T\*) |
|---|---|---|
| temps réel par image | de l'envoi à la réponse complète, par appel ; médiane et P90 ; parallélisme déclaré | **étape T4-chrono** (ci-dessous) |
| débit | images par seconde au parallélisme utilisé | images par seconde, prétraitement, encodeur et tête |
| coût | coût rapporté par l'outil si présent (JSON de `claude -p`), sinon les jetons d'entrée et de sortie ; **aucun prix de mémoire** ; un tarif public est cité avec sa page et sa date | heures T4 utilisées ; aucun prix inventé |
| matériel et lieu | API distante, région inconnue | Kaggle T4, image Docker épinglée |

- **Étape T4-chrono** **[à trancher : l'inclure ici ou la préinscrire à part]**. Sur Kaggle T4, sans aucun score :
  - on chronomètre le prétraitement, l'encodeur gelé C-RADIOv3-L (448 px, fp16) et les têtes T\* et B, sous `no_grad`, en lot de 32 et de 1 ;
  - on prend les images du dev, déjà ouvertes, avec la même méthode de répétitions que le petit élève ;
  - le code de prédiction scellé est réutilisé tel quel, et les prédictions produites doivent égaler le sceau (contrôle d'identité).
- **Lecture** : une latence d'API n'est pas un débit sur T4. Les deux colonnes sont publiées côte à côte, sans rapport unique.

## 6. Ordre d'exécution, écrit d'avance

Chaque étape produit un artefact scellé :
1. le tirage des échantillons et des 20 images de répétabilité ;
2. le gel des consignes, de la règle de nettoyage, de la règle syntaxique et du code de mesure ;
3. **S0, essai technique** : 5 images du dev par système et par variante active, plus 2 images de la tâche b. On publie les états, le taux d'invalidité et le temps, **aucun score** ;
4. un amendement daté si S0 l'impose, écrit avant S1 ;
5. **S1** : tous les appels, chaque image une seule fois, puis les 20 répétitions ;
6. le gel des sorties brutes (SHA-256) et du journal ;
7. la **planche** des sorties, regardée par wA:p1 et un sous-agent, puis un reçu ;
8. l'ouverture des scores ;
9. la `LECTURE.md`.

**Plafonds**, fixés avant tout appel :
- **Appels de S1**, variante V seule :
  - tâche a : 2 × (200 + 301) = 1 002 ;
  - répétabilité : 2 × 20 = 40 ;
  - tâche b : 2 × 26 = 52 ;
  - soit **1 094 appels**, plus **14** pour S0 (2 × 5 en tâche a et 2 × 2 en tâche b).
- **Avec VLM-libre** : + 1 002 appels en S1 et + 10 en S0.
- **Budget en dollars et temps réel maximal par système** : fixés par Marcel **[à trancher]**. Au plafond, on arrête et on publie ce qui est fait comme **incomplet**. On ne mesure jamais un sous-ensemble choisi après coup.
- **Sur le Mac** : appels réseau et mesure numpy sur CPU seulement. T4-chrono tourne sur Kaggle.

## 7. Ce que la comparaison ne permettra pas de dire

- Rien sur le test ICAI ni sur le test du Rijksmuseum.
- Pas de justesse visuelle : un VLM peut nommer un motif que le catalogue omet. C'est le domaine de l'audit O/A/E, qui n'est pas un score.
- Pas de rapport coût–qualité unique : les deux journaux sont publiés côte à côte.
- Pas de fidélité indépendante de Gemini contre un juge Gemini.
- Pas de généralisation à d'autres consignes, versions de modèles ou dates d'appel.
- Pas de comparaison avec les chiffres de la littérature, qui portent sur d'autres tâches et métriques.

## 8. Questions pour Marcel et wA:p1

1. Le modèle Claude : Sonnet 5.5, Opus 5.5 ou Fable 5.1.
2. La taille de V-diagnostic (200 proposé).
3. La variante VLM-libre : oui ou non (+ 1 002 appels).
4. Les libellés des codes dans VLM-V : non par défaut.
5. Le budget en dollars et le temps maximal par système.
6. Les images sensibles (D11) : les envoyer à Google et Anthropic, ou les exclure.
7. L'étape T4-chrono : ici, ou dans une préinscription séparée.
8. Les relations dans la tâche b : non par défaut.
