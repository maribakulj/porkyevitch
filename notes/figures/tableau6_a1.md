### Tableau 6 — A1 sur la validation, puis sa règle figée sur le dev Rijksmuseum

Sources : `2026-10-29-a1/resultats/diagnostic/diagnostic.json` (`6adb2404`), `2026-10-30-a1-dev-rijks/resultats/dev.json` (`3cc297f4`).

| Banque | Système | H-F1 |
|---|---|---|
| V-diagnostic ICAI | A1 (décodeur, q avec η = 0) | 0,6076 |
|  | seuil, même q qu'A1 (η = 0) | 0,6017 |
|  | seuil, q propre réglé à part (η = 1, secondaire) | 0,6102 |
|  | B (T-Z) | 0,5860 |
| dev Rijksmuseum | règle figée (seuil, q propre, η = 1) | 0,4146 |
|  | B (T-Z) | 0,4191 |
|  | T* | 0,4205 |

Dev : règle − B −0,0044 [−0,0341 ; 0,0205] ; règle − T* −0,0059 [−0,0323 ; 0,0194] (composantes, 10 000 tirages, graine 20261034) : transfert non établi.
