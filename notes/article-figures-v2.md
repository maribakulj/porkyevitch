# Tableaux et figures de l'article (v2, privé)

v1 : la figure 5 montre aussi les bras 8×8, dans un panneau à part (demande de wA:p1). v2 : corrections de l'audit factuel de Codex (B3, B4, B5, B6, N9, N10, N11), sans nouveau calcul. Les v0 et v1 restent intactes.

30 octobre 2026. Claude wA:pH, à la demande de wA:p1.

**Production.** Un seul script léger, `notes/figures/make_figures.py` (matplotlib 3.10.7, CPU, quelques secondes) :

```
python -I notes/figures/make_figures.py
```

- Il écrit 9 tableaux Markdown et 5 figures PNG dans `notes/figures/` de `~/porkyevitch-maths`. Les tableaux y sont commités ; les PNG sont ignorés par le `.gitignore` du dépôt et se régénèrent par le script. La copie auditée par Codex ne contenait que le script : l'audit est statique, pas une validation du rendu.
- Il lit seulement des fichiers de résultats agrégés déjà rapatriés sous `~/porkyevitch/experiences` : verdicts, mesures et diagnostics.
- Il ne lit aucune image ni aucune prédiction ligne à ligne, et aucune donnée de test brute. Pour le test, il ne lit que les deux fichiers agrégés de la phase 1 (`verdicts.json`, `mesures_test.json`).
- Il charge le diagnostic de la tête en entier, mais n'utilise que ses clés agrégées : jamais les champs `sample`, ni pour un calcul ni pour une sortie.
- Aucune nouvelle mesure scientifique : il recopie des valeurs et fait des traitements descriptifs (arrondis, une différence déjà citée, +0,0013 du seuil par tranche ; des sommes d'effectifs de nœuds ; un pourcentage de porte ; une comparaison des bras 8×8 à l'a priori).
- Chaque tableau imprime ses sources avec leur empreinte (8 premiers caractères du SHA-256), y compris le tableau 4, qui cite `ACCORD.md` (`97af4703`). Les effectifs ICAI du tableau 1 sont recopiés de Méthodes v4 §1 ; Codex les a recoupés.

**Chiffres relus.** Toutes les valeurs ont été comparées à Résultats v3, aux mêmes arrondis, et Codex en a confronté les sources. Deux groupes de cellules **viennent des mêmes fichiers, sont vérifiés par Codex, mais ne sont pas cités par les Résultats**. Ils restent marqués ‡ dans les tableaux tant qu'ils ne sont pas cités :
- les profondeurs 2 à 5 (tableau 3) ;
- les bras 8×8 du petit élève, qui sont secondaires (tableau 9).

Les H-F1 absolus des tableaux 2 et 6 sont dans Résultats v3 (§1, §4 et §4 bis).

| Pièce | Fichier source | Ce qu'il montre | Sortie |
|---|---|---|---|
| Tableau 1 — Effectifs | Méthodes v4 §1 ; `mesure-phase1/.../verdicts.json` (`denominators`) ; `a1-dev-rijks/resultats/dev.json` (`population`) | ICAI apprentissage, validation, test (787 au dénominateur) ; Rijksmuseum test (1 201 images, 908 composantes) et dev (301, 239). Des effectifs, pas des scores. | `tableau1_effectifs.md` |
| Tableau 2 — Phase 1 | `verdicts.json`, `mesures_test.json` (`hier_f1`) | Les sept comparaisons : H-F1 des deux bancs, Δ, borne unilatérale 99,29 %, IC95, retenue. TK-niv non exécutée. Aucune brique retenue. | `tableau2_phase1.md` |
| Figure 1 — Écarts de la phase 1 | `verdicts.json` | Deux panneaux (ICAI par images, Rijksmuseum par composantes) : Δ et IC95 de chaque brique, trait à 0. T\* et TK sont entièrement positifs sur ICAI, mais leurs intervalles Rijksmuseum contiennent 0. | `figure1_phase1_ecarts.png` |
| Tableau 3 — Diagnostic de validation | `diagnostic-tete/resultats/complet/diagnostic.json` (`depth_nodes`, `tranches_exact_codes`, `tranche_threshold_coordinate_ascent`, `error_overlap_T_star_vs_B_TZ`) | Rappel et précision des nœuds par profondeur pour B, macro-F1 de la traîne, seuil par tranche (optimiste), corrélation T\*–B. Étiqueté validation. | `tableau3_diagnostic_validation.md` |
| Tableau 4 — Jugements O/A/E | `diagnostic-tete/resultats/regard-confiants/ACCORD.md` (comptes arbitrés) | O 29, A 46, E 25 : des jugements de modèles sur un échantillon conditionné (codes les plus spécifiques à p ≥ 0,9, absents de la vérité fermée) ; ni score, ni vérité, ni borne du F1. | `tableau4_audit.md` |
| Tableau 5 et figure 2 — Non-transfert | `non-transfert/resultats/diagnostic.json` (`banks.*.main.recall`) | Pour la cible G, sur le dev Rijksmuseum et la validation ICAI : ce que rend la tête (fermeture, exact), ce que portent les voisins, le vote seul au seuil de TK, le contrôle aléatoire. Descriptif. La légende dit que la disponibilité-union n'est pas un gain récupérable et rappelle les lectures interdites, dont toute cause (D10). Le titre de la figure dit : sans cause établie. | `tableau5_non_transfert.md`, `figure2_non_transfert.png` |
| Tableau 6 et figure 3 — A1 et A1-dev | `a1/resultats/diagnostic/diagnostic.json` (`H`) ; `a1-dev-rijks/resultats/dev.json` (`H`, contrastes) | Sur V-diagnostic : A1, le seuil sur la **même** loi q (η = 0, 0,6017) et le seuil sur un q **propre** réglé à part (η = 1, secondaire, 0,6102), contre B. Les deux contrôles sont nommés et séparés. Sur le dev, la règle figée contre B et contre T\*, avec l'IC95 par composantes : transfert non établi. | `tableau6_a1.md`, `figure3_a1_dev.png` |
| Tableau 7 — D3 | `d3-traine-profondeur/resultats/complet/bras1.json`, `bras2.json` | Bras 1 : F_R contre B et contre le témoin permuté sur la **validation entière** (4 241 évaluables, avec IC), puis sur **V-lecture** (2 130 évaluables, descriptif, sans IC). Bras 2, sur **V-lecture** : rappel conditionnel et F1 des enfants par graine, seuil de repli t = 0,95 (aucun seuil n'atteint la précision de B), couverture de la porte. Négatif. | `tableau7_d3.md` |
| Tableau 8 et figure 4 — P9-A | `p9-a/resultats/mesures-0/verdicts.json` | ΔH, ΔE, ΔF_R des quatre bras, graine 0, avec le seuil G. Aucun bras retenu ; graines 1 et 2 non lancées (D15). | `tableau8_p9a.md`, `figure4_p9a.png` |
| Tableau 9 et figure 5 — Petit élève | `petit-eleve/resultats/mesures/resultats.json` (`arms`, `witnesses_measures`, `timing`, `d2_reading`) | Rappel@30 et AP50 de l'élève, de l'a priori, d'OWLv2 et de YOLOE (descriptif) ; débit, en forwards seulement ; lecture D2 « pas de signal ». La figure a deux panneaux : à gauche, les bras 28×28 de la lecture D2 et les témoins ; à droite, hachurés, les bras 8×8, « descriptif, hors règle D2 », avec la phrase calculée sur le fichier : un bras 8×8 (graine 1) dépasse l'a priori. Juge : fidélité au professeur, 26 images. | `tableau9_petit_eleve.md`, `figure5_petit_eleve.png` |

**Choix de forme.**
- Les figures sont en niveaux de gris, avec un trait à 0 ou au seuil de la règle. Elles ne superposent jamais un niveau absolu à un écart.
- Chaque figure a un titre qui dit l'issue, pas un gain : aucune brique retenue (1), sans cause établie (2), transfert non établi (3), aucun bras retenu (4), les bras 28×28 ne battent pas l'a priori (5).
- Il n'y a ni figure de débit ni figure de calibration de la phase 1 (`latency_T4` et `D5_probabilities` sont des absences, suivant Grok p7).
- La figure 5 ne cache pas les bras 8×8. Ils sont dans un panneau séparé, hachuré et titré « descriptif, hors règle D2 ». Le titre général ne parle que des bras 28×28. L'un des bras 8×8 (graine 1) dépasse l'a priori, et le panneau le dit. Ces bras restent marqués ‡ dans le tableau 9 tant que les Résultats ne les citent pas.

**Ce qui n'est pas proposé.** Le croisement fréquence × profondeur du non-transfert n'a ni tableau ni figure ici. Il est dans le fichier (`cross_table`), mais Résultats v1 ne le cite pas ; il irait en annexe après relecture. Les coupes descriptives du test par support ou par fréquence (Grok p7, tableaux 3 à 6 de sa structure) ne sont pas reprises ici : Résultats v1 ne les cite pas, et elles demanderaient une relecture propre.
