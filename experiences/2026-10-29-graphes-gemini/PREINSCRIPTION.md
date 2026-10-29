# Pilote : graphes de scène produits par Gemini (préinscription, 29/10/2026)

Demande de Marcel (29/10) : produire des graphes de scène (objets, cadres, relations) avec un VLM plutôt qu'avec un modèle entraîné
sur des photos, pour s'en servir ensuite comme données d'entraînement (distillation) et pour la recherche par objets et relations.
Agent : Gemini, onglet herdr `wA:p8` (« gemini porkyevitch »). Orchestrateur : wA:p1. Relecture : Grok wA:p2 puis Codex wA:p4.

Ce pilote est **un essai de faisabilité et de qualité**, pas une mesure d'utilité pour Iconclass. Il répond à trois questions :
Gemini produit-il des graphes lisibles et justes à l'œil sur nos images ? Combien de temps et de quota par image ? Le format tient-il
(JSON valide, cadres dans l'image, relations entre objets déclarés) ?

## Données

- **Apprentissage ICAI seulement** : `davanstrien/iconclass-vlm-brillfull` révision 8045366, fragments `train-*`, hors validation
  (groupes md5 de la série architecture : `default_rng(0).random(len(groups)) < 0.05` sur les md5 triés, comme `e0_reference.py`).
  Ni validation, ni test ICAI, ni Emblematica, ni banc Rijksmuseum.
- **200 images**, tirées par `default_rng(29)` parmi les groupes md5 d'apprentissage (une image par groupe). Le tirage, ses md5 et
  ses identifiants sont écrits avant tout envoi à Gemini.
- Images copiées sur le Mac (≈ 50 Mo, `df` avant) dans `~/porkyevitch-donnees/graphes-gemini/pilote/images/`, renommées `p000.jpg`
  à `p199.jpg`. Les codes Iconclass sont gardés à part (`verite.json`) et **ne sont jamais montrés à Gemini**.

## Production : une seule passe, à l'aveugle

- Gemini reçoit l'image seule, sans titre, sans codes, sans nom de fichier parlant. Consigne fixe (`consigne.md`, figée avant l'envoi) :
  lister les objets visibles (personnes, animaux, objets, éléments de décor), chacun avec un identifiant, un nom libre en anglais, un
  cadre `[x0, y0, x1, y1]` en millièmes de la largeur et de la hauteur, et des attributs visibles (posture, geste, vêtement) ; puis les
  relations `[sujet, prédicat, objet]` entre identifiants déclarés. Ne nommer ni personnage ni sujet iconographique (pas « la Vierge »,
  « saint Jérôme ») : seulement ce qui se voit (« woman », « old man », « lion »). Sortie : un JSON par image, `g000.json`…
- Pas de commande système pour Gemini ; il lit les images et écrit les JSON dans le dossier de sortie, rien d'autre.
- Modèle et réglage notés (nom exact du modèle affiché par l'agent) ; temps par image noté.

## Amendement 1 (29/10, demande de Marcel, avant tout envoi à Gemini) : passe SAM 3 après Gemini

Gemini dit *quoi* et *à peu près où* ; SAM 3 place des rectangles précis à partir de ces noms et sert de contrôle indépendant.
La passe Gemini, le tirage et la règle de décision ci-dessous ne changent pas.

- **Outil** : SAM 3 (Meta), segmentation guidée par un texte, sur Kaggle T4, révision des poids épinglée. **Préalable** : licence
  et accès aux poids vérifiés par Grok wA:p7. S'ils ne conviennent pas, repli décidé d'avance : SAM 2.1 guidé par le rectangle de
  Gemini (masque et rectangle serré seulement, sans contrôle du nom), noté comme tel.
- **Entrée** : pour chaque objet d'un graphe valide, l'image et le nom donné par Gemini (texte seul, jamais les codes).
- **Appariement** : parmi les instances rendues par SAM 3 pour ce nom, celle dont le rectangle a le plus grand recouvrement (IoU)
  avec le rectangle de Gemini. Objet **retrouvé** si cet IoU ≥ 0,3 ; sinon **non retrouvé** (ni instance, ou aucune assez proche).
- **Mesures, descriptives** (elles ne décident pas du passage à l'échelle, SAM 3 pouvant lui-même rater sur des œuvres) :
  part des objets retrouvés, par type de nom ; distribution de l'IoU entre rectangles de Gemini et de SAM 3 sur les objets retrouvés.
- **Usage décidé d'avance** : si l'IoU médian des objets retrouvés est ≥ 0,7, les rectangles de Gemini sont gardés à l'échelle ;
  sinon, à l'échelle, le rectangle de SAM 3 remplace celui de Gemini pour les objets retrouvés, et les autres gardent celui de Gemini
  avec la marque « non retrouvé ».
- **Planche** : les mêmes 12 images montrent les deux rectangles (Gemini et SAM 3) ; les objets non retrouvés sont regardés en
  premier.
- Masques hors git (`~/porkyevitch-donnees/graphes-gemini/`) ; dans git : script relu, appariements, IoU, `run.json`.

## Ce qu'on regarde, dans l'ordre

1. **Planche avant tout chiffre** : 12 images tirées par `default_rng(30)` parmi les 200, avec cadres et relations dessinés.
   Regard de l'orchestrateur, puis contre-regard indépendant de Grok wA:p3. Pour chaque image : objets manquants évidents, objets
   inventés, cadres faux, relations fausses, comptés à l'œil.
2. **Validité** sur les 200 : JSON lisible, cadres dans [0, 1000] et non vides, relations entre identifiants déclarés, noms
   iconographiques interdits absents.
3. **Coût** : temps moyen par image, quota consommé, extrapolation à 5 000 images.

## Règle de décision (écrite avant l'envoi)

- **Passage à l'échelle (≈ 5 000 images d'apprentissage)** si : ≥ 95 % de graphes valides ; sur la planche, au plus 1 objet inventé
  et au plus 2 relations fausses par image en moyenne aux deux regards ; coût extrapolé compatible avec le quota (chiffré et montré à
  Marcel avant).
- **Ajout d'une passe de vérification** (oui/non sur recadrages, par un autre modèle) seulement si la planche montre plus d'erreurs
  que ce seuil.
- **Arrêt** si moins de 80 % de graphes valides après une correction de la consigne (une seule correction permise ; elle devient une
  nouvelle brique nommée, et la planche est refaite sur un nouveau tirage).
- L'utilité pour Iconclass (codes rares, recherche) n'est **pas** jugée ici : elle fera l'objet d'une série préinscrite à part, sur
  les graphes à l'échelle.

## Où

Script de tirage et de dessin de la planche : `scripts/` de ce dossier, relu avant usage. Graphes et images hors git
(`~/porkyevitch-donnees/graphes-gemini/`) ; dans git : consigne, tirage (md5), validité, planche annotée, temps, `RESULTAT.md`.
