# Lecture de D3 (complet, validation seule), résultat négatif

Sorties CONFORMES (sous-agent Sonnet, porkyevitch-d3-complet-sorties-sonnet.md ; contre-vérification Codex à faire).
- Bras 1 (vote des 20 voisins sur les codes rares, poids fixe 0,25) : NON retenu. F_R 0,048 contre B 0,070
  (IC95 de l'écart [−0,018 ; −0,013]), H −0,004. Il réduit les faux positifs (714 contre 2 071) mais perd des vrais
  (230 contre 357). Il bat le témoin permuté (F_R 0,039) : la mémoire porte un signal, mais pas assez pour battre B.
  Négatif borné à cette recette (poids non réglé).
- Bras 2 (tête linéaire des enfants, 3 graines) : NON retenu. Rappel conditionnel 0,14 contre 0,61 pour B, F1 enfants
  0,11 contre 0,32 ; « descente améliorée » : non. La porte issue de B ne laisse passer que 55 % des vrais enfants.
  Ne dit rien d'une tête sur les grilles ni de la séparabilité des frères.
