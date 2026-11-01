# Rapport S0 v2.6, comparaison VLM (31/10/2026)

Claude wA:pH. Code scellé 2749206e, préinscription v2.6, `prep.json` `2d25187e` (dossier `prep-v26`). **Aucun score calculé.**

## Contrôles avant les appels

- `prior_spend` = **4,589728 USD**, statut `fe3d7907…`, journal `5a270dcc…` : conforme à la consigne de wA:p1.
- Code de `prep.json` = sceau 2749206e.
- Échantillons, images (SHA revérifiés) et plan d'appels identiques à la v2.5.
- Contrôles d'identité passés (2 100 évaluables ; dev B et T\* = A1-dev).
- Pas de `~/.claude/CLAUDE.md`.

## S0 v2.6 : 19 appels, 20 essais, complet

`status_S0.json` : complet sur H, G et O, 20 essais (plafond 22), aucun arrêt, journal `0fbcab13`. Dépense Claude cumulée (v2.5 + v2.6) : **9,153942 USD sur 30**. Versions : Claude Code 2.1.314, `agy` 1.4.7.

| Système, tâche | Essais | États | Image lue | Temps médian / max | Coût par appel | Cache écrit / lu, en jetons |
|---|---:|---|---:|---|---|---|
| H, codes | 5 | 5 réponses | 5/5 | 11,5 / 17,6 s | 0,0115 à 0,0228 USD (moyenne 0,0161) | 3 appels simultanés : 51 k écrits, 72 k lus ; 2 appels suivants : 111 k écrits, 2 k lus |
| H, boîtes | 2 | 2 réponses | 2/2 | 10,1 / 11,1 s | 0,0036 USD | 14 k / 2 k |
| G, codes | 6 | 5 réponses, 1 échec technique (statut `ERROR`), relancé avec succès | 6/6 | 89,9 / 141 s | non rapporté | ≈ 71 k jetons d'entrée, dont ≈ 65,6 k **lus en cache** |
| G, boîtes | 2 | 2 réponses | 2/2 | 31,8 / 32,5 s | non rapporté | 15,6 k d'entrée, 0 lu |
| O, codes | 5 | 5 réponses | 5/5 | 8,3 / 13,9 s | **0,893 à 0,898 USD** (moyenne 0,8953) | **≈ 110,7 k écrits, 2,2 k lus, à chaque appel** |

- 0 refus, 0 commande `agy`, 0 erreur de lecture côté Claude.
- Chaînes émises : H 25, G 22 et O 27, toutes valides. Invalidité : 0 %.

## Constat : l'amendement v2.6 n'a pas produit l'économie attendue

Pour Opus, et pour les appels H qui ne partent pas en même temps, **les quelque 110 000 jetons du vocabulaire sont toujours réécrits en cache à chaque appel**. Mettre l'image en dernier n'a pas suffi.

**Hypothèse, non vérifiée :** le cache ne se relit qu'à des frontières de blocs du message. Le vocabulaire et la référence d'image forment ici un seul bloc de texte, donc aucun point de coupure ne sépare la partie commune de la partie variable. Une piste serait de placer le vocabulaire dans un bloc séparé, par exemple la consigne système (`--system-prompt`), qui est la même à chaque appel. Ce serait un nouvel amendement, avec un nouveau S0 d'environ 4,5 USD. Rien n'est engagé.

**Gemini, lui, relit déjà environ 65 600 jetons sur 71 000 en cache.**

## Extrapolation de S1 selon la règle (§6), sans écrire `plan_S1.json`

Disponible = 30 − 4,589728 − 4,564214 = **20,85 USD**. Coûts unitaires mesurés en v2.6 : H codes 0,0161, H boîtes 0,0036, O codes 0,8953 USD. Marge de 1,2.

| Scénario | Coût prévu, plan complet | Coût prévu sans V-diagnostic | Images de V-diagnostic gardées | Règle |
|---|---:|---:|---:|---|
| Opus 50 images (préinscrit) | 63,91 USD | 60,04 USD | 0 | **ne pas lancer** |
| Opus 15 images | 26,31 USD | 22,44 USD | 0 | **ne pas lancer** (même sans V-diagnostic) |
| Sans Opus | 10,20 USD | — | 200 (plan complet) | lancer |

Repères calculés avec la même formule :
- avec V-diagnostic complet, au plus environ **9 images Opus** tiennent dans 20,85 USD ;
- sans V-diagnostic, au plus environ 13.

## Décision à Marcel (rien n'est lancé)

1. **Sans Opus** : S1 tient, à environ 10,2 USD prévus.
2. **Opus réduit à environ 9 images** avec V-diagnostic complet, ou environ 13 sans V-diagnostic : il faut un amendement.
3. **Relever le budget** pour garder 50 images Opus : environ 64 USD prévus pour S1, en plus des 9,15 déjà dépensés.
4. **Nouvel amendement de cache** (vocabulaire dans la consigne système), puis nouveau S0 d'environ 4,5 USD, avant de trancher.

## Fichiers

Sous `~/porkyevitch-donnees/vlm-comparaison/prep-v26/` : `prep.json` (`2d25187e`), `journal/S0.jsonl` (`0fbcab13`), `status_S0.json`, sorties brutes `raw/S0_*`. Préparation : `prepare-v26-1.log`.
