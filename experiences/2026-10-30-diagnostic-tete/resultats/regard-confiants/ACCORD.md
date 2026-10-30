# Regard des 100 « confiants absents » (T-Z, validation ICAI) : deux regards indépendants

| | wA:p1 | Grok wA:p3 |
|---|---|---|
| O : vrai et précis (oubli du catalogueur) | 61 | 29 |
| A : vrai mais générique (4, 25, 31D1…) | 27 | 45 |
| E : vraie erreur | 12 | 26 |

Accord sur 53 / 100. Désaccords principaux : 27 cas O chez wA:p1 → A chez Grok (codes de portrait et de posture jugés génériques),
7 cas O → E et 9 cas A → E (Grok plus strict, notamment sur « tête tournée à droite » lu comme le nez vers la droite de l'image).
Les deux regards s'accordent sur l'essentiel : **74 à 88 % de ces prédictions sûres sont vraies** (O + A), les vraies erreurs sont
de 12 à 26 %. Le F1 brut pénalise donc à tort la majorité de ces prédictions ; la part d'oublis *précis* va de 29 à 61 % selon le
juge. Ce n'est pas un score ; une mesure corrigée exigerait une règle de catégorie écrite d'avance et un troisième regard sur les
désaccords.

## Troisième regard (Gemini wA:p8, 30/10), sur les 47 désaccords, à l'aveugle

Règle écrite d'avance par Grok wA:p3 (`~/Documents/reviews/porkyevitch-regle-OAE-grok.md`), sans accès aux deux regards.
Sur les 47 : O 2, A 30, E 15 ; d'accord avec Grok sur 39, avec wA:p1 sur 5, avec aucun sur 3.
**Comptes arbitrés (accord des deux premiers regards, sinon troisième regard) : O 29, A 46, E 25 → 75 % de prédictions vraies.**
Réserves : la règle est celle du juge le plus strict, ce qui pousse l'arbitre vers lui ; les justifications de Gemini citent
surtout les clauses de la règle ; la lecture effective des 47 images est contrôlée dans ses journaux agy (Grok wA:p3, porkyevitch-troisieme-regard-controle-grok.md : 47/47 ouvertes).
Lecture pour l'article : un quart des prédictions sûres « fausses » sont de vraies erreurs ; trois quarts sont vraies, dont
environ 30 % d'oublis précis du catalogueur.
