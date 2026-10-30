# Bras Haiku, test de 20 images : résultat (amendement 3)

29/10/2026. Annotateur : Claude Haiku 5.5 (`claude-haiku-5-5`, onglet wA:pE), consigne et schéma du pilote, à l'aveugle. Vérification :
wA:p1, image par image, rectangles dessinés (`~/porkyevitch-donnees/graphes-haiku/test20/planche/`), avant tout chiffre agrégé.
Incident : première consigne trop stricte (liste des images non fournie) ; p012 faite avant, 19 autres après reprise.

**Débit** : 19 graphes en 2 min 01 s (22:50:02 → 22:52:03), soit ≈ 6 s par image (Gemini dans le pilote : ≈ 80 s par appel).

## Regard image par image

| image | contenu | objets principaux | inventés / mal nommés | relations fausses | remarques |
|---|---|---|---|---|---|
| p012 | gravure, saint auréolé à la bêche, femme agenouillée, arbre, page | oui | 0 | 0 | rapport « s'agenouille devant » absent |
| p014 | homme levant la main, femme assise, bol, oiseau, cage | oui | 0 | 0 | plante à droite oubliée |
| p017 | dos de carton manuscrit | oui (rien d'autre) | 0 | 0 | |
| p019 | arbres en fleurs, rangée d'arbres, pré | oui | 0 | 0 | |
| p038 | Vierge à l'Enfant allaitant, rideau | oui | 0 | 0 | allaitement non dit (seulement « holds ») ; rectangles larges |
| p044 | portrait d'homme âgé, chapeau, fraise, main | oui | 0 | 0 | « hat above man » faible ; armoiries oubliées |
| p047 | portrait de femme, bonnet, main à la joue, rideau, drapé, lorgnon | oui | 0 | 0 | |
| p077 | portrait de femme, étole, collier, broche, main | oui | 0 | 0 | |
| p082 | damas : arbre, écu central, armoiries, inscription | oui | 1 (« date » incertaine) | 0 | animaux et fleurs du décor oubliés |
| p095 | cortège : cavaliers en armure, chevaux, cinq lances | oui | 0 | 0 | |
| p097 | page imprimée, gravure coloriée : deux figures, tour, collines, texte | oui | 0 | 0 | |
| p106 | nature morte : coupe et raisins, asperges, langouste, poisson, coquillages | oui | 0 | 0 | cornichons et olives oubliés |
| p112 | paon, chrysanthèmes | oui | 0 | 1 (« faces flowers ») | |
| p116 | village : église, arbre, grange, personnages, puits à balancier, barque | oui | 0 | 0 | |
| p124 | page imprimée, rangée de médaillons | oui | 1 (cinq « boîtes » au lieu de six médaillons, rectangle mal placé) | 0 | |
| p134 | femme debout, chaise, rideau | oui | 0 | 0 | |
| p144 | gravure « Virgo potens » : femme dans un ovale, trophées, deux femmes, figure couchée | oui | 0 | 0 | |
| p154 | page à gravures : femme en niche, scène, figures, foule, texte | oui | 1 (« flower » tenue, douteuse) | 1 (« holds flower ») | |
| p173 | silhouette d'homme au chapeau, bêche | oui | 1 (bêche nommée « staff ») | 0 | |
| p176 | oiseau aux ailes ouvertes sur une branche, herbe | oui | 0 | 0 | |

## Règle préinscrite

| critère | seuil | observé |
|---|---|---|
| graphes valides | ≥ 19 / 20 | 20 / 20 |
| objets inventés ou mal nommés, moyenne par image | ≤ 1 | 4 / 20 = 0,2 |
| relations fausses, moyenne par image | ≤ 2 | 2 / 20 = 0,1 |
| objets principaux présents | ≥ 18 images | 20 |

**Haiku est validé** selon la règle écrite avant le regard.

## Limites, à garder pour la suite

- Un seul regard (wA:p1) ; la règle de l'amendement 3 n'exigeait pas de contre-regard, mais il serait utile avant l'échelle.
- Relations surtout **spatiales** (gauche, droite, au-dessus), souvent dédoublées (A gauche de B et B droite de A) ; peu d'actions
  (allaitement, agenouillement devant, geste) alors que ce sont elles qui portent l'iconographie. La consigne devra le demander.
- Rectangles **approximatifs** (larges ou décalés) : SAM 3 reste utile pour les préciser.
- Objets secondaires souvent oubliés (décors, petits objets).
- Comparaison avec Gemini sur les 12 images communes : à faire quand la passe Gemini sera finie.
