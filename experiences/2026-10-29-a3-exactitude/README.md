# A3 — exactitude de la borne L1 sur les 178 graphes du pilote

29/10/2026, Claude wA:pH (remplaçant de Codex p6). Script écrit pour relecture, **non lancé**. Ce contrôle répond au challenge de Grok p7 (`~/Documents/reviews/porkyevitch-algos-production-grok.md`, section A3) : on vérifie l'exactitude maintenant, on mesure la vitesse après le jalon 4.

## Ce qui est vérifié

Pour deux graphes G et G′, la proposition du rapport (`docs/algos-production.md`, section 4.2) est la suivante :

`LB(G,G′) = (1−α) · ½‖n_G − n_G′‖₁ + α · ½‖h_G − h_G′‖₁ ≤ E(T)` pour **tout** couplage T ∈ Π(a,b).

Ici, n est l'histogramme des noms, h l'histogramme des types de paires `(nom_u, nom_v, relations u→v)`, diagonale comprise (« self »), et E le FGW étiqueté à coûts 0/1 (α = 0,5, masses uniformes). Une seule paire où la borne dépasse l'énergie réfute l'implémentation ou la preuve.

**Certificat visé** (correction de Grok) : le top-k obtenu en filtrant puis en raffinant est le même que le parcours exhaustif du **marcheur gelé** S. S n'est pas le FGW exact. Le marcheur gelé est une descente miroir déterministe : départ du couplage produit, 10 pas, ε = 0,05, 100 itérations de Sinkhorn, puis arrondi exact d'Altschuler, Weed et Rigollet (2017). Comme S = E(T) pour un T réalisable, LB ≤ S découle de la proposition.

## Données

Seulement `~/porkyevitch-donnees/graphes-gemini/pilote/graphes/p*/g.json` : les 178 graphes acceptés, issus des images d'apprentissage ICAI. Le script refuse de continuer s'il n'en trouve pas exactement 178. Il ne lit **ni** `verite.json`, ni les images, ni les appels, ni aucun code Iconclass. Λ v1, fixé avant usage : noms et relations en minuscules, espaces réduits, aucune table de synonymes, métrique 0/1 sur les noms (arbre en étoile, arêtes de ½).

## Règle, écrite avant le passage

1. **Échec technique**, qui donne un arrêt sans verdict sur la borne :
   - nombre de graphes différent de 178 ;
   - marginales d'un couplage à plus de 10⁻¹² ;
   - deux calculs de LB (direct, et par intersection sur listes inversées) en désaccord à plus de 10⁻¹² ;
   - énergie factorisée contre énergie à quatre indices (graphes ≤ 8 nœuds, jusqu'à 2 000 vérifications) en désaccord à plus de 10⁻¹² ;
   - valeur non finie.
2. **Exactitude** : pour les 15 753 paires et quatre couplages chacune (produit, marcheur gelé, deux couplages aléatoires arrondis), **zéro** cas `LB > E(T) + 10⁻⁹`. Zéro : borne conforme sur ce corpus. Au moins un : **réfutée** (implémentation ou preuve), A3 s'arrête, et on examine la paire publiée.
3. **Top-10** en laisser-un-dehors sur les 178 requêtes : identique au parcours exhaustif de S pour **178/178** requêtes. Un écart signale une erreur de code, puisqu'il ne peut pas venir d'une borne conforme.
4. **Descriptif, sans verdict** (Grok : ne se projette ni à 5 000 ni à 10 millions) : quantiles de LB/S, corrélation de rang LB–S, part des raffinements évités par requête. Lecture déclarée d'avance : si la médiane des raffinements évités est < 20 %, on note « borne lâche à cette échelle ». Rien n'est décidé sur la vitesse avant le jalon 4.

La pertinence iconographique (H-F1 des codes retrouvés) n'est **pas** mesurée ici.

## Exécution prévue, après relecture

```
python3 -I scripts/a3_exactitude.py --pilot ~/porkyevitch-donnees/graphes-gemini/pilote --out ~/porkyevitch-donnees/maths/a3-exactitude
```

Coût : CPU local léger. Environ 6 ms par paire en médiane, 18 ms pour deux graphes de 28 nœuds, chronométré sur des graphes synthétiques de même taille : environ 2 à 3 minutes en tout, moins de 200 Mo de mémoire, un seul fichier `exactitude.json` (empreintes des entrées et du script, versions). numpy seul ; ni scipy ni POT, qui ne sont pas installés sur le Mac. Le dossier de sortie doit être vide, et il ne peut pas être dans `~/porkyevitch` ni `~/lermolieff`.

Tests synthétiques : `python3 -I tests/test_a3.py`, 10 tests, sans données du pilote. Ils couvrent : graphes identiques (LB = 0, énergie nulle au couplage identité) ; cas serré à un nœud ; normalisation des noms ; sens des relations ; 300 paires aléatoires avec LB ≤ E pour trois couplages ; énergie factorisée contre énergie à quatre indices ; gradient contre différences finies ; arrondi exact ; top-k par filtrage et raffinement égal à l'exhaustif, y compris avec égalités ; sortie refusée dans les dépôts interdits.
