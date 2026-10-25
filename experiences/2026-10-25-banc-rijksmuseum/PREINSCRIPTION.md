# Banc extérieur Iconclass du Rijksmuseum : règles écrites avant toute collecte

Date : 25/10/2026, avant toute collecte d'images ou de codes. Demande de Marcel (25/10) : mettre Emblematica de côté (doublon avec le
projet sur les emblèmes, licence des métadonnées introuvable, banc déjà consulté) et prendre un banc plus pertinent. Relecture de Codex
avant chaque script et avant le gel.

## Pourquoi ce banc

- Données ouvertes : métadonnées du Rijksmuseum en CC0 (champ `subject_to` des notices) ; images marquées « Public Domain Mark » objet
  par objet (seules celles-là sont prises). Le banc peut être publié en entier (identifiants, codes, prédictions ; les images restent
  au musée, référencées par leur adresse IIIF).
- Plusieurs supports (peintures, estampes, dessins) au lieu des seuls livres d'emblèmes : mesure du transfert vers d'autres supports.
- Jamais consulté : aucune prédiction, aucune image, aucun code de ce banc n'a été regardé par nous avant le gel.

## Collecte (scripts relus avant exécution)

Source : l'API ouverte du musée, sans clé (data.rijksmuseum.nl, Linked Art) : recherche par type avec image disponible, puis notice
de l'objet et de sa représentation (`shows` → `represents_instance_of_type` → `equivalent` iconclass.org). Au plus une requête par
seconde, agent « caypollard/0.1 (research prototype) », reprise sur journal.

0. **Disponibilité, métadonnées seules** : pour chacun des trois types (peinture, estampe, dessin), les 300 premiers objets de la
   recherche (ordre de l'API) : part qui porte au moins un code Iconclass et une image en domaine public. Publiée ; ne sert qu'à
   dimensionner la collecte. Aucune image n'est téléchargée à cette étape.
1. **Population** : objets de ces trois types, avec image en domaine public et au moins un code Iconclass lisible (`readable()` de la
   tête). Codes = notations décodées des adresses iconclass.org. Groupe de dépendance = le créateur principal de l'objet (ou
   « anonyme » + l'identifiant de l'objet si aucun) : les œuvres d'un même artiste ou d'une même série ne sont pas indépendantes.
2. **Liste brute** : jusqu'à 6 000 objets par type, dans l'ordre de l'API ; métadonnées et image IIIF à 800 px de côté max.

## Filtres contre les copies des données d'entraînement (mêmes règles qu'Emblematica, références à jour)

- **Filtre 1** : hachage de différence 256 bits (même fonction que `build_external_iconclass_bench.py`) de chaque image contre les
  87 004 images de `davanstrien/iconclass-vlm-brillfull` (révision 8045366, entraînement et test) ; un créateur dont une œuvre est à
  moins de 50 bits d'une image du jeu est retiré en entier (pour Emblematica, la référence était l'ensemble ICAI brut ; ici ce sont les
  images d'apprentissage elles-mêmes, ce qui est la question posée).
- **Filtre 2** : cosinus C-RADIO (vecteur de la tête) ≥ 0,95 avec une image du jeu → créateur retiré en entier (seuil d'Emblematica,
  étalonné à l'œil le 25/10).
- **Regard** : planche des 12 paires restantes les plus proches (cosinus), regardée avant le gel, côté images d'entraînement ; une
  copie manifeste arrête le gel et conduit à un amendement avant tout tirage (pas de nouveau seuil choisi après avoir vu le test).

## Tirage et gel

- Après les filtres, tirage par créateurs (graine 0) : un **test de 1 200 objets** et un **dev de 300 objets**, créateurs disjoints ;
  au plus 20 objets par créateur dans chacun ; proportions des trois types gardées telles que la population filtrée les donne.
- Projection commune avec la série d'essais : chapitre 86 retiré de la vérité et des prédictions ; une image dont la vérité projetée
  est vide est exclue ; le dénominateur est publié.
- Gel : `frozen.json` (listes, groupes, empreintes des images et des métadonnées, versions des scripts) puis `vu.json` (empreinte du gel
  après le regard de la planche). Aucune évaluation sans gel signé.

## Rôle dans la série d'essais d'architecture

Amendement 4 de `../2026-10-25-iconclass-architecture/PREINSCRIPTION.md`, écrit avant tout calcul d'essai : le juge extérieur devient
ce banc (test de 1 200, bootstrap par créateurs entiers), à la place d'Emblematica ; la règle (famille de 7, Bonferroni 99,29 %
unilatéral, Δ_ext > 0 et Δ_ICAI > −0,01) est inchangée. Les planches de regard se font sur le dev de 300. Emblematica n'est plus
utilisé pour décider ; ses chiffres restent internes (porkyevitch) et ne sont pas publiés dans lermolieff.

## Ce que ce banc ne mesure pas

- Un seul musée, néerlandais, avec ses propres habitudes de catalogage Iconclass : un gain ici reste un gain d'accord avec ce catalogue.
- La part d'objets avec codes Iconclass peut être faible et biaisée vers certains types : publiée à l'étape 0, et la composition finale
  (types, branches, nombre de créateurs) est publiée avec le gel.
