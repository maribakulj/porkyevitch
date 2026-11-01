### Tableau 9 — Petit élève, 26 graphes Gemini (fidélité au professeur), lecture D2

Sources : `2026-10-30-petit-eleve/resultats/mesures/resultats.json` (`5463d532`).

| Système | rappel@30 | AP50 sans classe | objets/image (score ≥ 0,5) |
|---|---|---|---|
| 28×28_seed0 | 0,225 | 0,062 | 19,8 |
| 28×28_seed1 | 0,230 | 0,050 | 23,0 |
| 28×28_seed2 | 0,246 | 0,067 | 21,1 |
| 8×8_seed0 ‡ | 0,258 | 0,080 | 20,8 |
| 8×8_seed1 ‡ | 0,287 | 0,086 | 20,5 |
| 8×8_seed2 ‡ | 0,250 | 0,048 | 21,5 |
| a priori (rectangles fixes) | 0,258 | — | — |
| OWLv2 | 0,307 | 0,199 | — |
| YOLOE-v8-S texte (descriptif) | 0,152 | 0,116 | — |

Lecture D2 (bras 28×28) : Loc-, AP?, D+ → « pas de signal ». Débit, forwards seulement (lot 32) : élève complet 24,9 img/s, OWLv2 10,9 img/s (D = 2,29). Florence-2 : rappel 0,246 sur toutes ses boîtes. ‡ Bras 8×8 : secondaires, hors règle D2, vérifiés par Codex mais non cités par les Résultats (à relire avant usage).
