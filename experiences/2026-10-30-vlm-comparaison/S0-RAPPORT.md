# Rapport S0, comparaison VLM (31/10/2026)

Claude wA:pH. Code scellé `SCEAU-CODE.json` 4c45fd38, préinscription v2.5. **Aucun score calculé** : ni H-F1, ni rappel, ni comparaison à B ou T\*. Les données (journal, sorties brutes, images) sont dans `~/porkyevitch-donnees/vlm-comparaison/prep/` ; elles ne sont pas versionnées.

## Préparation

- **Sceau** : `prep.json` `186ba1b4`, code égal au sceau 4c45fd38 (7 fichiers), archive ICAI `937173dc` (récupérée sur Kaggle : 200 images, 11 fragments TRAIN, sans jeton).
- **Contrôles passés** :
  - 2 100 évaluables en V-diagnostic ;
  - H de B en V-diagnostic : 0,5860487335040372 ;
  - H de B et de T\* sur le dev : égaux à A1-dev ;
  - empreintes des décisions égales au cache ;
  - `test_rows` = 0 (déclaration fondée sur le code).
- **Échantillons** : 200 images de V-diagnostic (200 groupes), 301 images du dev (239 composantes), tranche Opus de 50, répétabilité de 20, 26 images de graphes. Images : 35 Mo en tout.
- **Incidents de préparation**, tous journalisés (`prepare-essai*.log`) :
  - réseau Hugging Face local trop lent pour la colonne d'images, d'où l'amendement v2.5 ;
  - copie locale du sceau de phase 1 partielle : un dossier `sceau-dev` a été assemblé avec le manifeste et les deux seuls fichiers du dev, aux SHA conformes, sans aucun fichier de test ;
  - deux défauts de mon code révélés par les vraies données (identités du dev, clés URI), corrigés et contre-vérifiés par Codex ;
  - un téléchargement Rijks tronqué, refusé par le contrôle SHA, puis réussi à la relance ;
  - une coupure SSL.

## S0 : 19 appels, 19 essais, complet

`status_S0.json` : complet sur H, G et O ; 19 essais pour 19 appels prévus (plafond 22, non atteint) ; aucun arrêt ; journal `5a270dcc`. Versions : Claude Code 2.1.314, `agy` 1.4.7.

| Système, tâche | Appels | États | Image lue (preuve) | Refus | Temps médian / max | Coût unitaire moyen |
|---|---:|---|---:|---:|---|---|
| H (Haiku 5.5), codes | 5 | 5 réponses | 5/5 (Read sans erreur) | 0 | 13,7 / 19,1 s | 0,0175 USD |
| H, boîtes | 2 | 2 réponses | 2/2 | 0 | 10,0 / 10,8 s | 0,0031 USD |
| G (Gemini 3.8 Flash), codes | 5 | 5 réponses | 5/5 (étape 132, statut 3, octets image) | 0 | 69,4 / 170,0 s | coût non rapporté ; environ 71 k jetons d'entrée par appel |
| G, boîtes | 2 | 2 réponses | 2/2 | 0 | 31,7 / 37,1 s | non rapporté |
| O (Opus 5.5), codes | 5 | 5 réponses | 5/5 | 0 | 10,1 / 15,2 s | **0,899 USD** |

Constats :
- **Statuts `agy`** : tous `SUCCESS`. **Aucune commande exécutée** (0 appel `run_command` ou `send_command_input`). Aucun statut de blocage de sûreté rencontré : les valeurs supposées de `SAFETY_STATUSES` restent non observées.
- **Taille d'images acceptée** : aucun refus pour les 5 images du dev (≤ 800 px) ni pour les 2 images du petit élève. Les images ICAI (≤ 500 px) ne figurent pas dans S0.
- **Chaînes émises (codes)** : H 23 valides sur 23, G 19 sur 19, O 21 sur 21. Taux d'invalidité de 0 % pour les trois. Codes valides par image : H 3 à 6, G 2 à 8, O 3 à 6.
- **Boîtes** : H 15 et 15, G 25 et 17.
- **Coût Claude imputé en S0** : 4,59 USD sur 30.

## Extrapolation du coût de S1 : la règle préinscrite dit NE PAS LANCER

La règle §6 a été appliquée **en mémoire seulement**, sans écrire `plan_S1.json` :
- coûts unitaires : H codes 0,0175, H boîtes 0,0031, O codes 0,899 USD ;
- disponible : 30 − 4,59 = **25,41 USD** ;
- coût prévu, plan complet : **65,0 USD**. Sans aucune image de V-diagnostic, il reste **60,8 USD**, dont environ 54 USD pour les 50 appels Opus (50 × 0,899 × 1,2) ;
- conclusion de la règle : P(0) > disponible, donc **S1 n'est pas lancé, et la décision revient à Marcel.**

**Cause du coût.** Chaque consigne contient les 7 907 codes de V, soit environ 110 000 jetons. Le journal montre que ces jetons sont **réécrits en cache à chaque appel** (`cache_creation_input_tokens` ≈ 111 000) au lieu d'être relus. La raison : la consigne commence par le chemin de l'image, différent à chaque appel, si bien que la liste du vocabulaire n'est jamais un préfixe commun. Les trois premiers appels H, partis ensemble, ont relu environ 61 000 jetons en cache (0,0136 USD), contre 0,0229 USD pour ceux qui ont tout réécrit.

## Options pour Marcel et wA:p1 (aucune n'est engagée)

1. **Réordonner la consigne** : le vocabulaire en tête, l'image à la fin, pour que le préfixe soit relu en cache d'un appel à l'autre. Il faut un amendement : nouveau texte gelé, nouveau `prep.json`, puis un **nouveau S0** pour mesurer l'économie. Le gain n'est pas chiffré ici. Les tarifs ne sont pas connus de façon fiable, et la mesure se fera en S0.
2. **Réduire la tranche Opus**, par exemple vers 15 images : environ 16,2 USD prévus pour Opus (15 × 0,899 × 1,2) et environ 11 USD pour H sur tout le plan (0,0175 × 521 × 1,2), soit environ 27 USD. C'est au-dessus de 25,4 USD : la règle réduirait alors V-diagnostic à une centaine d'images, le dev restant entier. Amendement de la préinscription.
3. **Relever le budget** à environ 70 USD.
4. **Retirer Opus** : H et G seuls, environ 11 USD prévus, plan complet.

Les options 1 et 2 peuvent se combiner.

## Fichiers

- Journal `journal/S0.jsonl` (`5a270dcc`), statut `status_S0.json`, sorties brutes `raw/S0_*`, et `prep.json` (`186ba1b4`), sous `~/porkyevitch-donnees/vlm-comparaison/prep/`.
- Préparation : `prepare-relance1.log` (succès) et les journaux des essais échoués.
