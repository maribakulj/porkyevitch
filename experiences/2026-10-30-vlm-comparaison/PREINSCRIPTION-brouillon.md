# Comparaison avec des VLM — préinscription, BROUILLON

30 octobre 2026. Claude wA:pH, à la demande de wA:p1. **Brouillon** : rien n'est lancé, aucun appel de modèle n'est fait, aucun échantillon n'est tiré. Ce texte attend l'accord de Marcel sur la suite, puis la relecture (sous-agent Sonnet, audit Codex) avant toute version définitive. Les points à trancher sont marqués **[à trancher]**, les faits à vérifier **[à vérifier]**.

## 0. Question et statut

**Question** (objectif initial de Marcel) : face à un grand modèle vision–langage (VLM) appelé image par image, que vaut une tête rapide sur encodeur gelé, en accord avec le catalogue, en temps et en coût ?

- **Tâche a, Iconclass.** Des VLM proposent des notations Iconclass. On les mesure avec **le même code** que B (T-Z) et T\*, sur des images déjà ouvertes : un sous-ensemble de V-diagnostic ICAI et le dev du Rijksmuseum. **Jamais le test**, ni ICAI ni Rijksmuseum.
- **Tâche b, graphes.** Les mêmes VLM localisent les objets des 26 images d'évaluation du petit élève. On mesure leur rappel sans classe contre le juge Gemini et contre S1b.

**Statut** : comparaison **exploratoire et descriptive**. Elle ne retient aucune brique et ne change pas la référence publiée (T\*, D10). Les images ont déjà été consultées : la validation et le dev plusieurs fois, les 26 images d'évaluation par la planche du petit élève. Un VLM a pu voir ces images ou leurs notices pendant son entraînement, puisque le jeu Iconclass et les collections du Rijksmuseum sont publics. Cette **contamination possible** est déclarée et n'est pas mesurable ici.

## 1. Systèmes comparés

| Nom | Modèle | Accès | Remarque |
|---|---|---|---|
| G | Gemini 3.8 Flash | `agy -p` avec l'image en pièce jointe, aucune commande permise | ~2 à 7 min par planche observés ailleurs (mémoire de session) ; temps par image à mesurer |
| C | Claude Sonnet 5.5 (`claude-sonnet-5-5`) | `claude -p --model claude-sonnet-5-5`, sortie JSON, image en pièce jointe | **[à trancher]** : Sonnet 5.5 (moins cher), Opus 5.5 (`claude-opus-5-5`), ou Fable 5.1 (`claude-fable-5-1`), qu'évoquait Marcel. Un seul modèle Claude, nommé avant le tirage. |
| B | T-Z, tête de la phase 1 | prédictions **déjà scellées** | référence interne des sondes |
| T\* | T-long, référence publiée | prédictions **déjà scellées** | référence de l'article |

Pour B et T\*, aucune nouvelle prédiction : on relit les prédictions scellées de V-diagnostic et du dev (sources de D10 et d'A1-dev, contrôles d'identité déjà passés) **[à vérifier : les fichiers exacts de T\* et de B sur V-diagnostic]**.

## 2. Tâche a : Iconclass

### 2.1 Échantillons, tirés et scellés avant tout appel

- **V-diagnostic ICAI.** 200 images tirées **par groupes md5** parmi les 2 100 évaluables, avec une graine fixe écrite ici (`20261035`) **[à trancher : 200]**. La liste des md5 est scellée par SHA-256 avant le premier appel.
- **Dev Rijksmuseum.** Les **301 images** (239 composantes) entières : c'est la population d'A1-dev. Seul le membre « dev » du banc est décodé (règle de D10).
- Aucune ligne de test n'est lue (`test_rows` = 0, vérifié par le script).

### 2.2 Deux variantes de consigne, nommées

- **VLM-libre.** La consigne demande les notations Iconclass de l'image, sans liste. Les codes rendus sont nettoyés (espaces, casse), puis passés par `drop86`. Ils sont mesurés tels quels : un code hors de V compte comme dans la vérité.
- **VLM-V.** La consigne fournit le vocabulaire V (7 907 codes, `vocabulaire.json`), et demande de choisir seulement dans cette liste. Un code rendu hors de V est retiré et compté à part.

Le texte exact des deux consignes, le format de sortie (une liste JSON de codes) et la règle de nettoyage sont **gelés par SHA-256** avant le tirage. **[à trancher]** : faut-il donner les libellés anglais des codes dans VLM-V ? Ils ne sont pas dans `vocabulaire.json`. Les ajouter demanderait une source de libellés, à citer, et allongerait fortement la consigne.

### 2.3 Mesure

- **Même code de mesure** que la série : `a1_core.ancestors`, `closure`, `drop86` et `hier_f1`, copiés à l'octet et épinglés par SHA-256 (comme pour A1-dev). On calcule le H-F1 par image (principal) et l'accord exact (descriptif).
- **Projection.** Les VLM sont mesurés sur la vérité projetée de la série (chapitre 86 retiré), comme B et T\*.
- **Contrastes appariés**, VLM − T\* et VLM − B, par banque. Bootstrap de 10 000 tirages (graine `20261035`), par groupes md5 sur V-diagnostic et par composantes sur le dev.
- **Famille principale** : les contrastes **VLM − T\* sur le dev**, soit 2 modèles × 2 variantes = 4 contrastes, au niveau unilatéral 1 − 0,05/4. Tout le reste est descriptif : VLM − B, V-diagnostic, accord exact, part hors vocabulaire.
- **Lecture écrite d'avance** :
  - si la borne basse de VLM − T\* sur le dev est > 0 : « le VLM dépasse T\* sur le dev, en accord de catalogue » ;
  - si la borne haute est < 0 : « le VLM est sous T\* sur le dev » ;
  - sinon : « pas de différence établie ».

  Aucune lecture n'est une justesse visuelle ni un choix de production. Avec 239 composantes, l'intervalle est large (A1-dev : environ ±0,03) : un écart de cet ordre ne sera pas tranché, et c'est écrit d'avance.

### 2.4 Temps et coût

- **Temps par image** : le temps réel de chaque appel, de l'envoi à la réponse complète, mesuré par le script. On publie la médiane et le 90e centile, en déclarant le parallélisme utilisé.
- **Coût** : le coût rapporté par l'outil s'il le donne (sortie JSON de `claude -p`, compteurs de jetons d'`agy`), sinon les jetons, sinon « non mesuré ». **Aucun prix n'est tiré de mémoire** ; un prix public, s'il est cité, l'est avec sa page et sa date.
- **B et T\*** : leur temps par image **n'a pas été mesuré** dans cette série (`latency_T4` : « not measured »). On ne l'invente pas. Les seuls débits mesurés sont ceux du petit élève en forwards, qui ne couvrent pas la même portion du pipeline. **[à trancher]** : ajouter une mesure du débit de l'encodeur gelé et de T\* sur T4, à préinscrire à part, ou publier la colonne B/T\* comme absente.

## 3. Tâche b : graphes

- **Images** : les 26 images d'évaluation du petit élève, déjà vues sur la planche.
- **Consigne** : lister au plus 30 objets avec leur boîte `[x0, y0, x1, y1]` en millièmes de la largeur et de la hauteur, convention de `pe_common.clean_box`, dans l'ordre de saillance décroissante. Les VLM ne rendent pas de score : **le rang tient lieu de score**, ce qui est déclaré.
- **Mesure** : `pe_common.recall_counts` et `pooled_recall`, avec IoU ≥ 0,5, sans classe, top 30 ; le code est épinglé.
  - **contre le juge Gemini** (26 graphes). Pour G, c'est **circulaire** : le juge est aussi un graphe Gemini. Le chiffre est publié, mais il ne compte pas comme une fidélité indépendante ;
  - **contre S1b**, le second annotateur Haiku, présent sur ces 26 images (plus 4 sans graphe Gemini, qui restent hors de la population principale).
- **Repères déjà mesurés** (Résultats v3 §7) : a priori 0,258, OWLv2 0,307, élève 28×28 de 0,225 à 0,246. Ils sont repris sans recalcul.
- **Lecture** : descriptive seulement. 26 images ne suffisent pas à trancher un écart de quelques points. Aucune règle D2 ne s'applique : D2 juge l'élève, pas un VLM.
- Les relations ne sont pas mesurées dans ce brouillon **[à trancher]**.

## 4. Règles d'exécution, écrites d'avance

1. **Ordre**, et chaque étape est un artefact scellé :
   - le tirage de l'échantillon ;
   - le gel des consignes et du code de mesure ;
   - **S0, essai technique** sur 5 images du dev par système et par variante : taux de sortie lisible et temps seulement, **aucun score** ;
   - les appels de S1 ;
   - le gel des sorties brutes, avec leur SHA-256 ;
   - un regard sur une planche de sorties (wA:p1 et un sous-agent), puis un reçu ;
   - enfin, l'ouverture des scores.
2. **Une seule passe** par image, système et variante. Une réponse illisible a droit à **un seul** nouvel essai, journalisé ; si elle reste illisible, elle compte comme un **ensemble vide** et entre au dénominateur. Le taux d'illisibles est publié.
3. **Pas de réglage sur les scores** : ni la consigne, ni le nettoyage, ni le modèle ne changent après S0. Un changement imposé par S0 donne un amendement daté, écrit avant S1.
4. **Température et graine** : les réglages par défaut des outils, notés tels quels. Si l'outil n'expose pas de graine, c'est déclaré.
5. **Images envoyées à des services externes.** Les images partent chez Google et Anthropic. Pour les images potentiellement sensibles (D11), la décision revient à **Marcel** **[à trancher]** : les envoyer, ou les exclure avant le tirage, avec le compte publié.
6. **Plafonds**, avant tout appel :
   - le nombre d'appels : tâche a, 2 systèmes × 2 variantes × (200 + 301) = **2 004 appels** ; tâche b, 2 × 26 = **52 appels** ; S0, 2 × 2 × 5 + 2 × 5 = 30 appels. Total : **2 086** ;
   - un temps réel maximal par système, et un budget en dollars par système, **fixés par Marcel** **[à trancher]**. Au plafond, on arrête et on publie ce qui est fait comme incomplet ; on ne mesure pas un sous-ensemble choisi après coup.
7. **Calcul local léger** : les appels sont réseau, et la mesure est du numpy sur CPU (rien de lourd sur le Mac).

## 5. Ce que la comparaison ne permettra pas de dire

- **Rien sur le test**, ni sur un musée au-delà du dev.
- **Pas de justesse visuelle** : c'est un accord avec le catalogue. Un VLM peut nommer juste un motif que le catalogue omet ; c'est l'audit O/A/E, qui n'est pas un score.
- **Pas d'avantage de vitesse ou de coût chiffré pour B ou T\*** sans mesure préinscrite de leur débit (voir §2.4).
- **Pas de fidélité indépendante** pour Gemini contre un juge Gemini.
- **Aucune généralisation** à d'autres consignes ou versions de modèle. Les modèles sont nommés par leur identifiant et leur date d'appel.

## 6. Questions ouvertes pour Marcel et wA:p1

1. Le modèle Claude : Sonnet 5.5, Opus 5.5 ou Fable 5.1 (un seul).
2. La taille de V-diagnostic (200 proposé) ; le dev entier (301) ou un sous-ensemble.
3. VLM-V avec ou sans les libellés des codes.
4. Le budget en dollars et le temps maximal par système.
5. Les images sensibles (D11) : les envoyer ou les exclure.
6. Le débit de B/T\* : le mesurer (préinscription séparée) ou le déclarer absent.
7. Les relations dans la tâche b : oui ou non.
