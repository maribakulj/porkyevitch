### Tableau 3 — Diagnostic de la tête B (T-Z) sur la validation ICAI, par profondeur

Sources : `2026-10-30-diagnostic-tete/resultats/complet/diagnostic.json` (`312d5a40`).

| Profondeur | Rappel des nœuds | Précision | Nœuds vrais |
|---|---|---|---|
| 1 | 0,86 | 0,74 | 8 555 |
| 2 ‡ | 0,69 | 0,68 | 10 599 |
| 3 ‡ | 0,58 | 0,67 | 13 457 |
| 4 ‡ | 0,49 | 0,66 | 13 933 |
| 5 ‡ | 0,43 | 0,65 | 12 981 |
| 6 | 0,38 | 0,64 | 9 454 |

Codes vus 5–20 fois : macro-F1 0,07 sur 4 073 codes, 0,20 sur les codes présents en validation. Seuils par tranche ajustés sur la validation elle-même : +0,0013 de H-F1 (score optimiste, ni borne ni recette). Pearson du H-F1 par image, T* contre B : 0,82. ‡ Profondeurs 2 à 5 : lues dans le même fichier et vérifiées par Codex, mais non citées par les Résultats (à relire avant usage).
