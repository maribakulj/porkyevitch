# Relectures du banc Rijksmuseum

Rapports complets dans `~/Documents/reviews/` (hors dépôt).

| date | relecteur | objet | verdict | rapport |
|---|---|---|---|---|
| 25/10 | Codex | préinscription `eac2997` + amendement 4 de la série | BLOQUANT B1-B4 (groupes, audit des filtres, tirage, contrat de collecte) ; feu vert pour le script de l'étape 0 | `porkyevitch-banc-rijksmuseum-codex.md` |
| 25/10 | Codex | script de l'étape 0 (`b9406a3`, puis `82b078b5…`) | bloquant puis feu vert ; passage 2 sur le cache : 842/900 éligibles | idem, sections suivantes |
| 25/10 | Grok wA:p2 | amendement 1 `aab2458` | BLOQUANT : copie interne contre repli des seuils, motif générique, planche « plus loin », estimand, tirage non épinglé, `totalItems`, échec d'image | `porkyevitch-banc-amendement1-grok.md` |
| 25/10 | Grok wA:p2 | `fc077b3` + `collecte_notices.py` (`eb7a7483…`) | texte levé ; script BLOQUANT : échec classé comme absence, lieux et influences | idem |
| 25/10 | Grok wA:p2 | `fd50d85` (`d086b37d…`) | les deux défauts levés | idem |
| 25/10 | Codex wA:p4 | `fd50d85` | B1, B2, amendement 4 levés ; BLOQUANT N1 (vérité multi-vues pour une image), N2 (types du cadre perdus) | `porkyevitch-banc-amendement1-codex.md` |
| 25/10 | Codex wA:p4 | `99080db` (`365f45ee…`) | **FEU VERT** pour la collecte complète des notices (métadonnées seules) ; pas pour les images, les composantes ni le gel | idem |
| 25/10 | Codex wA:p4 | correctif réseau `57ec980` (`ede3bb97…`) | feu vert étendu (connexion coupée reprise) | `porkyevitch-banc-amendement1-codex.md` |
| 25/10 | Grok wA:p2 | étape 2 `7720e73` (filtres, pilote, liste) | FEU VERT essai à blanc | `porkyevitch-banc-filtres-grok.md` |
| 25/10 | Codex wA:p4 | étape 2 `a0dff53` (`e0fb13ff…`, pilote `5c969c36…`) | FEU VERT essai à blanc (pas l'exécution complète) | `porkyevitch-banc-filtres-codex.md` |
| 25/10 | Grok wA:p3 | résultats de l'essai à blanc Kaggle | CONFORME | `porkyevitch-banc-filtres-essai-verif-grok.md` |
| 25-26/10 | Grok wA:p2 | `composantes_reserve.py` | BLOQUANT (appel du générateur à 4 paires) → corrigé `b7ef65f` | `porkyevitch-banc-composantes-grok.md` |
| 26/10 | Grok wA:p2 | `planche_images.py`, `tirage_gel.py` | BLOQUANT (empreintes repli et réponses brutes) → FEU VERT après `c68b58b` | `porkyevitch-banc-planche-gel-grok.md` |
| 26/10 | Codex wA:p4 | étapes 3-7 `f1d863b` | FEU VERT par script (pilote de la planche à relire à part) | `porkyevitch-banc-suite-codex.md` |
