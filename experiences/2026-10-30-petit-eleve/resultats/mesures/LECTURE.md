# Lecture des mesures du petit élève v1 (porte D2) : « pas de signal »

Sorties CONFORMES (sous-agent Sonnet, porkyevitch-pe-mesures-sorties-sonnet.md ; contre-vérification Codex : CONFORME, porkyevitch-petit-eleve-codex.md).
Juge : 26 graphes Gemini d'évaluation (fidélité à Gemini, pas vérité de localisation).
- Loc− : rappel@30 de l'élève contre l'a priori (rectangles fixes, 0,258) : −0,033 / −0,029 / −0,012 selon la graine,
  intervalles contenant 0, bornes hautes +0,016 / +0,023 / +0,043. L'élève ne bat pas l'a priori.
- AP? : AP50 élève − OWLv2 (moyenne de 7 catégories) −0,043 à −0,062. Loin d'OWLv2 (AP50 sans classe 0,048–0,086 selon le bras et la graine contre 0,20).
- D+ : 24,9 img/s (élève complet, b32) contre 10,9 pour OWLv2 (× 2,3, forwards seulement).
- ~21 objets par image contre ~9 chez Gemini (doublons, pas de NMS), cohérent avec les deux regards des planches.
Conséquence préinscrite (D2) : ce prototype ne justifie pas la campagne d'annotation à l'échelle ; il ne réfute ni Haiku ni
la distillation. Le test tranche 300 (brouillon) reste suspendu. Suite : décision à prendre (challenger Grok p7, contre-expertise
Codex), sans relâcher la règle.
