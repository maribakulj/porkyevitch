# Lecture du diagnostic de non-transfert (D10), descriptive

Sorties CONFORMES (sous-agent Sonnet, porkyevitch-non-transfert-sorties-sonnet.md ; contre-vérification Codex : CONFORME, porkyevitch-non-transfert-codex.md).
Cible G (codes fréquents > 100, profondeur ≥ 3), dev Rijksmuseum (211 paires) contre validation ICAI (11 176 paires) :
R_tête (fermeture de T*) 0,355 / 0,517 ; tête exact 0,294 / 0,474 ; disponibilité chez les voisins 0,687 / 0,851 ;
vote seul au seuil 0,185 / 0,305 ; contrôle aléatoire 0,199 / 0,350. Codes communs (128, macro) : tête 0,330 / 0,375,
disponibilité 0,661 / 0,767.

Lectures permises :
- L'hypothèse « ces codes sont absents des notices du Rijksmuseum » n'est pas soutenue en bloc : sur le dev, les voisins
  d'apprentissage portent ces codes pour ~7 paires sur 10, très au-dessus du hasard (+0,49).
- La tête laisse le même écart à la disponibilité dans les deux banques (+0,33) : elle sous-exploite ce que les voisins portent.
- Sur les mêmes codes, l'écart de tête entre banques passe de 0,16 à 0,045 : compatible avec un effet de COMPOSITION des
  codes, sans le prouver ; un résidu demeure.
Interdits : « notices omises », « l'encodeur ne les contient pas », « le seuil est la cause », toute promesse d'amélioration
sur le musée, tout choix de brique ou de seuil tiré de ces chiffres. Réserves : dev petit (76 des 128 codes communs n'ont
qu'une paire) ; comparaison sur codes communs sans intervalle et à poids changés.
Réserve de Codex : « disponible chez les voisins » ne veut pas dire « gain récupérable » par une tête.
