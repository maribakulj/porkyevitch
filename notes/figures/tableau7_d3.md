### Tableau 7 — D3, résultat négatif : bras 1 sur la validation entière et sur V-lecture, bras 2 sur V-lecture

Sources : `2026-10-30-d3-traine-profondeur/resultats/complet/bras1.json` (`90409cd5`), `2026-10-30-d3-traine-profondeur/resultats/complet/bras2.json` (`b7dd1e25`).

| Sonde | Mesure | Bras | B | IC95 de l'écart | Retenue |
|---|---|---|---|---|---|
| Bras 1 (vote rares, poids 0,25), validation entière (4 241 évaluables) | F_R | 0,048 | 0,070 | [−0,018 ; −0,013] | non |
|  | témoin permuté F_R | 0,039 |  |  |  |
| Bras 1, V-lecture (2 130 évaluables), descriptif | F_R | 0,025 | 0,038 | — |  |
| Bras 2 (tête des enfants), V-lecture, graine 0, t = 0,95 (repli) | rappel conditionnel / F1 enfants | 0,14 / 0,11 | 0,61 / 0,32 |  | non |
| Bras 2 (tête des enfants), V-lecture, graine 1, t = 0,95 (repli) | rappel conditionnel / F1 enfants | 0,14 / 0,11 | 0,61 / 0,32 |  | non |
| Bras 2 (tête des enfants), V-lecture, graine 2, t = 0,95 (repli) | rappel conditionnel / F1 enfants | 0,14 / 0,11 | 0,61 / 0,32 |  | non |

Comptes en codes bruts exacts. La porte issue de B laisse passer 55 % des vrais enfants. Bras 2 : aucun seuil n'atteint sur V-réglage la précision de B ; le repli signalé (t = 0,95) a été appliqué aux trois graines, le bras n'est donc pas mesuré à précision contrôlée. L'IC du bras 1 porte sur la validation entière seulement.
