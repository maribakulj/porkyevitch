# Résultats (premier jet, v0, privé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1. Ce texte est écrit **uniquement** à partir des fichiers relus et de leurs `LECTURE.md`. Chaque chiffre renvoie à son fichier source ; les chemins sont relatifs à `~/porkyevitch/experiences/`, avec les 8 premiers caractères du SHA-256.

**Ce que ces résultats sont.**
- Toutes les séries sont **exploratoires** : une seule graine, sauf mention, un encodeur gelé (C-RADIOv3), et la projection sans le chapitre 86.
- Un F1 mesure un **accord avec un catalogue**, pas une justesse visuelle.
- Toutes les relectures et tous les regards sont faits par des **modèles** : sous-agents Sonnet, Claude, Grok, Gemini, Codex. Aucun regard humain (D5).
- Les marques **[Codex]** signalent un résultat que l'audit final de Codex p4 doit encore contre-vérifier (D12, D13) avant de servir à une décision ou à une publication.

## 1. Phase 1 : sept comparaisons, aucune brique retenue

Sources : `2026-10-30-mesure-phase1/resultats/test/verdicts.json` (`5a4193cc`) et `.../mesures_test.json` (`e6ac6206`).

- **Règle préinscrite.** Une brique est retenue si la borne inférieure unilatérale à 99,29 % (1 − 0,05/7) de Δ_Rijks est > 0 et celle de Δ_ICAI > −0,01.
- **Bootstrap** : 10 000 tirages, graine 0, appariés. L'unité est l'image pour ICAI (787 images, une vérité vide exclue) et la composante pour le Rijksmuseum (1 201 images, 908 composantes).
- **Contrôle** : T0 mesure 0,5459 sur ICAI, égal à la valeur préinscrite.

| Brique | Réf. | Δ ICAI | borne 99,29 % | IC95 | Δ Rijks | borne 99,29 % | IC95 | Retenue |
|---|---|---:|---:|---|---:|---:|---|---|
| T\* | T0 | +0,0277 | +0,0188 | [+0,0206 ; +0,0352] | +0,0026 | −0,0061 | [−0,0046 ; +0,0097] | non |
| TK | T\* | +0,0075 | +0,0012 | [+0,0024 ; +0,0128] | +0,0015 | −0,0066 | [−0,0051 ; +0,0083] | non |
| T-niv | T\* | 0 | 0 | [0 ; 0] | 0 | 0 | [0 ; 0] | non |
| T-H | T\* | −0,0268 | −0,0376 | [−0,0354 ; −0,0184] | −0,0082 | −0,0193 | [−0,0173 ; +0,0006] | non |
| T-Z | T\* | −0,0052 | −0,0190 | [−0,0165 ; +0,0060] | −0,0325 | −0,0477 | [−0,0448 ; −0,0207] | non |
| T-D | T\* | +0,0035 | −0,0099 | [−0,0072 ; +0,0142] | −0,0532 | −0,0678 | [−0,0649 ; −0,0412] | non |
| TK-niv | T\* | — | — | — | — | — | — | non exécutée (TK et T-niv non retenues) |

**H-F1 absolus** (`mesures_test.json`) :
- ICAI test : T0 0,5459, T\* 0,5736, TK 0,5812, T-H 0,5469, T-Z 0,5685, T-D 0,5771 ;
- Rijksmuseum test : T0 0,4192, T\* 0,4218, TK 0,4233, T-H 0,4136, T-Z 0,3893, T-D 0,3686.

**Phrase tenable.** Aucune des sept comparaisons ne passe la porte conjointe. T\* et TK augmentent l'accord avec le catalogue ICAI. Aucun gain Rijksmuseum de ces recettes n'est démontré. Les recettes spatiales T-Z et T-D ont des écarts Rijksmuseum entièrement sous zéro.

**À ne pas dire** : que le transfert est nul au sens général, que T-D gagne sur ICAI, qu'une brique a été choisie, ou que T-Z et T-D isolent le coût du seul retrait du jeton de synthèse. Ces réserves viennent de la contre-expertise de Codex et de la lecture de Grok (`~/Documents/reviews/porkyevitch-phase1-lecture-*.md`).

## 2. Diagnostic de la tête sur la validation ICAI, et audit des « confiants absents »

Source : `2026-10-30-diagnostic-tete/resultats/complet/diagnostic.json` (`312d5a40`), descriptif, référence B = T-Z ; chiffres repris de la section 5 de Méthodes v1.1.

- **Traîne.** Le macro-F1 des 4 073 codes vus 5 à 20 fois à l'apprentissage vaut 0,07 pour B, et 0,20 sur les seuls codes présents en validation.
- **Profondeur.** Le rappel des nœuds de la vérité passe de 0,86 en profondeur 1 à 0,38 en profondeur 6. La précision passe de 0,74 à 0,64.
- **Seuils par tranche**, ajustés sur la validation elle-même : +0,0013. C'est un score optimiste, ni une borne ni une recette.
- **Erreurs de T\* et de B fortement corrélées** : Pearson du H-F1 par image 0,82.
- **Audit** : 100 couples (image, code) prédits par B avec p ≥ 0,9 et absents de la vérité fermée. Deux regards (Claude, Grok) s'accordent sur 53 couples sur 100. Les 47 désaccords sont arbitrés à l'aveugle par Gemini, selon la règle du juge le plus strict. Résultat : **O 29, A 46, E 25**, soit environ trois quarts de ces prédictions comptées fausses qui sont vraies. **Ce n'est pas un score** : la règle penche vers le juge le plus strict.

## 3. Pourquoi le gain ne passe pas au Rijksmuseum : diagnostic descriptif [Codex]

Source : `2026-10-30-non-transfert/resultats/diagnostic.json` (`1cb6fce9`), lecture `.../LECTURE.md`. Les sorties sont jugées conformes par un sous-agent Sonnet.

**Cible G** : codes vus plus de 100 fois à l'apprentissage, de profondeur ≥ 3. On compare le dev Rijksmuseum (211 paires) et la validation ICAI (11 176 paires).

| Événement | Dev Rijksmuseum | Validation ICAI |
|---|---:|---:|
| R_tête (fermeture de T\*) | 0,355 | 0,517 |
| tête, code exact | 0,294 | 0,474 |
| disponibilité chez les 20 voisins (poids > 0) | 0,687 | 0,851 |
| vote seul au seuil de TK | 0,185 | 0,305 |
| contrôle de prévalence (20 images au hasard) | 0,199 | 0,350 |

Sur les 128 codes communs aux deux banques (moyenne par code), la tête vaut 0,330 au Rijksmuseum et 0,375 sur ICAI, et la disponibilité 0,661 et 0,767.

**Lectures permises** (`LECTURE.md`) :
- L'hypothèse « ces codes sont absents des notices du Rijksmuseum » n'est pas soutenue en bloc. Les voisins portent ces codes pour environ 7 paires sur 10, bien au-dessus du hasard (+0,49).
- La tête laisse le même écart à la disponibilité dans les deux banques (environ +0,33) : elle sous-exploite ce que portent les voisins.
- Sur les codes communs, l'écart de tête entre banques passe de 0,16 à 0,045. C'est compatible avec un effet de composition des codes, sans le prouver.

**Interdits** : « notices omises », « l'encodeur ne les contient pas », « le seuil est la cause », toute promesse pour le musée, tout choix tiré de ces chiffres.

**Réserves** : le dev est petit (76 des 128 codes communs n'ont qu'une paire), et la comparaison sur codes communs n'a pas d'intervalle.

## 4. A1 : décodage optimal sous une loi de candidats tirée des voisins (validation) [Codex]

Source : `2026-10-29-a1/resultats/diagnostic/diagnostic.json` (`6adb2404`), lecture `.../LECTURE.md`, sur 2 100 images éligibles de V-diagnostic. Les sorties sont jugées conformes par un sous-agent Sonnet.

- A1 obtient un H-F1 de **0,6076** contre **0,5860** pour B (+0,022), et un F1 exact supérieur de +0,034. La règle préinscrite le déclare « recommended ».
- **Le gain vient surtout de q**, la loi tirée des voisins. À q égal, le décodeur ne gagne que +0,006 sur un simple seuil. Un seuil sur q (`threshold_own_q`, analyse secondaire) obtient 0,6102, soit légèrement mieux qu'A1. « Recommended » veut dire « bat B », pas « le décodeur est nécessaire ».
- **Non affirmable** :
  - que le décodeur apporte le gain ;
  - que le gain est indépendant de la proximité : 48 % du gain vient de 30 % des images dont le premier voisin a un cosinus ≥ 0,95, et proximité ne veut pas dire copie ;
  - une recommandation de production ;
  - les latences et les F1 par tranche, qui n'ont pas d'intervalle.
- **Portée** : validation ICAI seule, référence B = T-Z. Ce n'est pas une amélioration de T\* ni du musée (D10, Codex).

## 5. D3 : traîne et profondeur, résultat négatif (validation) [Codex]

Sources : `2026-10-30-d3-traine-profondeur/resultats/complet/bras1.json` (`90409cd5`) et `bras2.json` (`b7dd1e25`), lecture `.../LECTURE.md`. Les sorties sont jugées conformes par un sous-agent Sonnet.

- **Bras 1**, vote des 20 voisins sur les codes rares, poids fixe 0,25 : **non retenu**.
  - F_R vaut 0,048 contre 0,070 pour B (IC95 de l'écart [−0,018 ; −0,013]), et H −0,004.
  - Il réduit les faux positifs (714 contre 2 071) mais perd des vrais positifs (230 contre 357).
  - Il bat le témoin à mémoire permutée (F_R 0,039) : la mémoire porte un signal, insuffisant pour battre B.
  - Le négatif est borné à cette recette, dont le poids n'est pas réglé.
- **Bras 2**, tête linéaire des enfants, 3 graines : **non retenu**.
  - Le rappel conditionnel vaut 0,14 contre 0,61 pour B, et le F1 sur les enfants 0,11 contre 0,32. Pas de « descente améliorée ».
  - La porte issue de B ne laisse passer que 55 % des vrais enfants.
  - Cela ne dit rien d'une tête sur les grilles, ni de la séparabilité des frères.
- Les comptes de descente portent sur des **codes bruts exacts**, pas sur la reconnaissance des concepts par fermeture (préinscription D3, et `CODE.md`).

## 6. P9-A, graine 0 : prototypes textuels et imbrication locale, négatif (validation) [Codex]

Sources : `2026-10-29-p9-a/resultats/mesures-0/verdicts.json` (`6a026547`) et `mesures.json`, lecture `.../LECTURE.md`, décisions D14 et D15. Le gel est `13f75f3a`. Les verdicts sont jugés conformes par un sous-agent Sonnet.

| Bras | ΔH | ΔE | ΔF_R | verdict |
|---|---:|---:|---:|---|
| F | +0,0043 | +0,0000 | −0,0026 | non retenu |
| contrôle global | +0,0019 | −0,0079 | −0,0023 | non retenu |
| A | +0,0015 | −0,0073 | −0,0032 | non retenu |
| C | +0,0018 | −0,0054 | −0,0026 | non retenu |

- Le seuil de la règle G est ΔH ≥ 0,005. Les intervalles de ΔF_R sont entièrement négatifs (`LECTURE.md`), et la garde E est respectée.
- **Mécanisme d'imbrication locale non soutenu**, en général comme sur les codes rares. Sur V-diagnostic, A − contrôle global vaut −0,0003 en H, avec un intervalle [−0,0017 ; +0,0011] selon `LECTURE.md`, et −0,0007 en F_R.
- La phrase « reading » de `verdicts.json` est un gabarit : **ne pas la citer**.
- **Graines 1 et 2 non lancées** (D15). La règle préinscrite §9.4 a été appliquée mécaniquement : aucun bras n'obtient G ou R à la graine 0. La graine 0 est publiée comme résultat **exploratoire négatif**, sans recommandation.
- `gel.json` contient le score de référence de B (0,58908) : c'est un écart déclaré, jugé non bloquant (D14).

## 7. Petit élève v1 : porte D2, « pas de signal » [Codex]

Source : `2026-10-30-petit-eleve/resultats/mesures/resultats.json` (`5463d532`), lecture `.../LECTURE.md`. Les sorties sont jugées conformes par un sous-agent Sonnet.

**Le juge** est formé des 26 graphes Gemini d'évaluation. Il mesure la **fidélité à Gemini, pas une vérité de localisation**. La planche a été regardée avant les chiffres, par wA:p1 et Grok wA:p7.

- **Loc−.** Le rappel@30 de l'élève (28×28) vaut 0,225 / 0,230 / 0,246 selon la graine, contre **0,258** pour l'a priori de rectangles fixes. L'écart est de −0,033 / −0,029 / −0,012. Les intervalles contiennent 0 ; leurs bornes hautes valent +0,016 / +0,023 / +0,043 (la `LECTURE.md` dit « < 0,15 »). L'élève ne bat pas l'a priori.
- **AP?** L'AP50 élève − OWLv2, moyenné sur 7 catégories, vaut de −0,04 à −0,06 selon la graine. L'AP50 sans classe de l'élève va de 0,048 à 0,086 sur les six bras (28×28 et 8×8), contre **0,199** pour OWLv2.
  - Écart à signaler : la `LECTURE.md` écrit « 0,06–0,09 ». Les fichiers donnent 0,062 / 0,050 / 0,067 pour les bras 28×28 (graines 0, 1, 2) et 0,080 / 0,086 / 0,048 pour les bras 8×8 : deux bras sont sous 0,06.
- **D+.** L'élève complet traite 24,9 images/s en lot de 32, avec la tête de relations, contre 10,9 pour OWLv2, soit D = 2,29. Il s'agit de forwards seulement, et les colonnes ne couvrent pas la même portion du pipeline.
- **Témoins descriptifs.** YOLOE-v8-S texte obtient un rappel@30 de 0,152 et un AP50 sans classe de 0,116. Florence-2 retrouve 0,246 de rappel sur toutes ses boîtes, avec 3,3 boîtes par image. OWLv2 a un rappel@30 de 0,307.
- L'élève produit environ 21 objets par image au score ≥ 0,5 (de 19,8 à 23,0 selon le bras), contre environ 9 chez Gemini (doublons, pas de NMS). C'est cohérent avec les deux regards des planches.
- **Conséquence préinscrite (D2).** Ce prototype ne justifie pas la campagne d'annotation à l'échelle. Il ne réfute ni Haiku ni la distillation. Le test tranche 300 reste suspendu.

## 8. Ce que l'ensemble ne dit pas

- Aucune brique n'est retenue en phase 1. A1 « bat B » sur la validation, mais son gain tient surtout à q. D3 et P9-A sont négatifs dans leur régime. Aucun de ces résultats ne promet un gain sur le Rijksmuseum.
- La cause du non-transfert **n'est pas établie** (D10). Le diagnostic localise un défaut d'exploitation du voisinage par la tête et un effet de composition possible, sans trancher entre catalogue et vision.
- Une seule graine, sauf pour D3 bras 2 et le petit élève (3 graines).
- Les juges sont des modèles : Gemini pour le petit élève, Claude, Grok et Gemini pour l'audit O/A/E.

## 9. En attente de la contre-vérification de Codex

- §3 non-transfert, §4 A1, §5 D3, §6 P9-A (verdicts, D14, D15) et §7 petit élève : chaque `LECTURE.md` porte « contre-vérification Codex à faire ».
- La section 1 reprend les verdicts déjà contre-expertisés par Codex dans sa lecture de la phase 1.
