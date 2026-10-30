# Étape 0 : disponibilité (métadonnées seules), 25/10/2026

Les 300 premiers objets de la recherche du musée par type (portée : ces premiers résultats, pas tout le catalogue). 900/900 notices
obtenues, aucune résolution échouée, trois recherches complètes. Aucun objet, code ni image regardé ; seuls des comptes.

- Passage 1 (script `8e577da2…`, relu) : 0 éligible, parce que les droits ne sont pas où le script les cherchait (CC0 et PDM lus sur
  l'objet et l'objet numérique). Chemins localisés par comptes agrégés des chemins JSON des URI de licence dans le cache.
- Passage 2 (script `82b078b5…`, relu ; même cache, 0 requête : 5 416 entrées avant et après) : CC0 lu sur la notice
  (`subject_of[]`), PDM lu sur l'objet numérique IIIF ou sur le visual item qu'il montre. Codex : le PDM du visual item lié à son
  numérique IIIF est retenu en combinaison avec la politique du musée (§1.1, photos des œuvres du domaine public), pas par héritage
  automatique ; le collecteur final tracera déclaration, chaîne et politique, et respectera toute restriction particulière.
  Note : l'en-tête du script dit « dans les 900 notices » ; le PDM est observé sur 897 visual items, pas garanti sur 900.

| type | vérité Iconclass lisible, non vide sans 86 | CC0 notice | PDM visual item + IIIF | créateur identifié | éligibles vérifiés |
|---|---|---|---|---|---|
| peinture | 291 | 300 | 299 | 203 | 291 |
| estampe | 298 | 300 | 297 | 248 | 295 |
| dessin | 256 | 300 | 300 | 184 | 256 |

Suite : amendements B1-B4 (groupes au-delà du créateur — 30 % d'objets sans créateur identifié —, audit des filtres, tirage, contrat
de collecte) et synchronisation de l'amendement 4, relus avant le script de collecte.
