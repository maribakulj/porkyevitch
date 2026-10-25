# Têtes Iconclass : essais d'architecture, règles écrites avant calcul

Date : 25/10/2026, avant tout calcul. Accord de Marcel le 25/10 (« les essais c'est ok pour la préinscription »). Amendée le 25/10
après la relecture de Codex (`~/Documents/reviews/porkyevitch-architecture-preinscription-codex.md`), toujours avant tout calcul ; feu vert de Codex le 25/10 (contre-vérification en fin du même rapport).
**Chaque script, essai à blanc compris, est relu par Codex avant d'être lancé** (demande de Marcel).

## Portée

Série **exploratoire**. Elle demande : une recette choisie sur ICAI transfère-t-elle mieux vers Emblematica, sans adaptation à ce
corpus ? Le test Emblematica gel2 a déjà été consulté (tête T, VLM, règle PE) : ce n'est plus un test vierge pour l'ensemble de la
démarche. Une graine unique par brique : un essai de recette, pas une preuve de stabilité ; une répétition à graines fixées précédera
toute recommandation forte. Une conclusion confirmatoire demandera de nouveaux livres jamais consultés, à protocole fixé.
Un gain de F1 est un gain d'accord avec le catalogue : une prédiction juste mais non cataloguée reste pénalisée, et la série ne mesure
pas la lecture des relations entre figures.

## Point de départ

- **Encodeur** : celui que la règle PE-Spatial désigne comme version recommandée (`caypollard/results/iconclass-tete-pe/PREINSCRIPTION.md` :
  PE-Spatial si la borne basse de T-PE − T est ≥ −2 points sur les deux bancs, sinon C-RADIO). Règle inchangée.
- Référence **T** : la tête de cet encodeur, telle que calculée (MLP 2 048, perte asymétrique, codes vus ≥ 5 fois et leurs ancêtres,
  15 époques, seuil global choisi sur la validation ; `caypollard/scripts/remote_iconclass_head.py`). **Avant E1**, on fige dans
  `reference.json` : l'encodeur désigné, le `head.pt` de T, ses caractéristiques et leurs empreintes, et ses chiffres sur les deux bancs.
  Les chiffres 54,8 % / 26,1 % ci-dessous sont ceux de T-C-RADIO ; si PE est désignée, les chiffres de T-PE deviennent la référence.
- Limites mesurées qui motivent les essais (T-C-RADIO) : 54,8 % (ICAI 788) contre 26,1 % (Emblematica 762) en F1 hiérarchique ; F1 des
  codes exacts d'environ 0,04 hors corpus ; sur ICAI, les voisins K trouvent plus de codes exacts que T (0,356 contre 0,275) ; la tête
  moyenne les jetons de l'image ; tout code absent de l'annotation compte comme négatif.

## Règle générale

- **Un seul changement par brique** (sauf E2 et E3, déclarés comme recettes ci-dessous), toujours comparé à T, mêmes données, même
  partage de validation (5 % groupés par md5, graine 0), même vocabulaire calculé sur le seul sous-ensemble d'entraînement.
- **Tout réglage se choisit sur la validation ICAI seule.** Le test ICAI (788) et le test Emblematica (gel2 : 800 images, 59 livres ;
  762 évaluables sans chapitre 86, 58 livres) ne servent qu'à mesurer, une fois par brique.
- **Famille fixe de cinq comparaisons** : TK, T-niv, TK-niv, T-H, T-D (TK-niv garde sa place même si elle n'est pas exécutée).
  Correction de Bonferroni au niveau familial de 5 %. Écarts en F1 absolu : Δ_ext = brique − T sur Emblematica, Δ_ICAI = brique − T sur
  ICAI. Une brique est **retenue** si la borne inférieure **unilatérale à 99 %** de Δ_ext est **> 0** **et** celle de Δ_ICAI est
  **≥ −0,01** ; les deux conditions sont exigées ensemble. Sinon, non retenue, publiée telle quelle, sans nouveau réglage.
- Bootstrap : **10 000 tirages**, graine 0, **mêmes tirages appariés pour tous les systèmes** ; Emblematica par **livres entiers**
  (moyenne par image recalculée sur les images des livres effectivement tirés, projection sans 86 commune) ; ICAI par images. Les
  IC95 bilatéraux ordinaires sont publiés à côté, pour la description. L'amplitude est donnée sans qualificatif automatique.
- **Regarder avant les chiffres** : pour chaque brique, une planche des 12 images du dev Emblematica (202) où |F1 hiérarchique de la
  brique − celui de T| est le plus grand (égalités : ordre des noms de fichier), avec la vérité et les deux prédictions en clair,
  regardée avant d'ouvrir les mesures du test. **Aucun changement** de seuil, d'architecture, de prétraitement ou de vocabulaire ne
  découle des planches dans cette série ; une correction de bogue avérée est documentée avec ses versions avant/après.

## Mesures secondaires (descriptives, sans test de sélection)

Pour T et chaque brique, sur les deux bancs, avec la même projection des prédictions pour tous les systèmes :
- F1 hiérarchique par la notation (la mesure de T) et F1 des codes exacts (fonctions `hier_f1` et `exact` de T, inchangées) ;
- **par profondeur** : profondeur d'un code = nombre de ses ancêtres selon `ancestors()` de T (la hiérarchie par la notation, pas
  l'arbre officiel), en trois tranches 1-2, 3-4, 5 et plus ; pour une tranche, F1 entre les ancêtres de la vérité et ceux de la
  prédiction restreints à la tranche, sur les images dont la vérité a au moins un ancêtre dans la tranche ; une image sans prédiction
  dans la tranche compte 0 ;
- **codes rares** : codes vus sur 5 à 20 images du sous-ensemble d'entraînement (comptés par image, avant expansion par ancêtres),
  même liste pour tous ; rappel = part des (image, code de vérité rare) dont le code figure parmi les ancêtres de la prédiction ;
- **couverture** : part des codes de vérité hors vocabulaire (aucune tête à vocabulaire fixe ne peut les prédire) ;
- latence de bout en bout sur T4.

## Briques, dans l'ordre

### E1. Mieux décider avec ce qu'on a (aucun réentraînement)

- **TK** : pour chaque code c du vocabulaire de T, s_c = α · p_c + (1 − α) · v_c, où p_c est la probabilité de la tête T et v_c le vote
  des 20 plus proches voisins d'entraînement selon la pondération de K historique (cosinus, poids négatifs ramenés à 0, normalisés par
  leur somme), **étendu aux ancêtres** : v_c = somme des poids des voisins dont un code a c pour ancêtre (c compris). Les codes hors
  vocabulaire sont ignorés (TK garde le vocabulaire de T ; ce n'est pas K historique, qui vote sur les codes bruts). Puis seuil, et
  `most_specific` comme T. α ∈ {0 ; 0,25 ; 0,5 ; 0,75 ; 1} et seuil sur la grille de T, choisis ensemble sur la validation ;
  égalités : le plus grand α, puis le plus petit seuil. À α = 1 et au seuil figé de T, TK reproduit T exactement (contrôle exigé).
- **T-niv** : un seuil par tranche de profondeur du code prédit (1-2, 3-4, 5 et plus ; profondeur calculée sur le code lui-même, sans
  la vérité). Départ : les trois seuils égaux au seuil de T ; recherche coordonnée sur la grille de T, tranches dans l'ordre 1-2, 3-4,
  5+, trois passes ; à chaque pas, la valeur qui maximise le F1 hiérarchique moyen de validation ; égalités : on garde la valeur
  courante, sinon la plus petite.
- **TK-niv** : TK avec son α choisi, puis T-niv refait sur s_c avec la même procédure. Exécutée seulement si TK et T-niv sont retenues.
- Calcul : voisins validation × entraînement, test × entraînement et Emblematica × entraînement par lots, sur Kaggle, mis en cache
  avec empreintes ; durée mesurée à l'essai à blanc.

### E2. Cohérence parent-enfant (recette C-HMCNN, réentraînement de la tête seule)

- **T-H** : même architecture, vocabulaire, cibles (fermées par ancêtres), époques et choix sur la validation que T ; deux changements
  liés, comme dans la méthode publiée (Giunchiglia et Lukasiewicz, NeurIPS 2020, éq. 4) — la comparaison est celle de la recette
  complète contre T, sans attribuer le gain à l'un ou l'autre :
  - **module de contrainte** : avec D(a) les descendants de a dans le vocabulaire (a compris, selon `ancestors()`), la sortie est
    m_a = max_{b ∈ D(a)} p_b ;
  - **MCLoss** : m⁺_a = max_{b ∈ D(a)} (y_b · p_b) ; L_a = − y_a · log(m⁺_a) − (1 − y_a) · log(1 − m_a) ; **somme sur les codes, moyenne
    sur les images** (la réduction de T).
- Prédiction : seuil sur m_a, puis `most_specific`, comme T.
- Mise en œuvre : réécrite par nous d'après l'article (le code des auteurs est sous GPL-3.0, non copié) ; maxima calculés sur la liste
  des paires (ancêtre, descendant) du vocabulaire, **jamais** par un tenseur lot × codes × codes (128 Go pour 512 × 7 907²) ; un test
  jouet obligatoire où un parent positif a un enfant négatif au score le plus haut (m⁺ ne doit pas prendre ce score).

### E3. Regarder les zones de l'image (recette spatiale)

- **T-D** : un décodeur ML-Decoder (Ridnik et al., WACV 2023 ; code Alibaba-MIIL/ML_Decoder, licence MIT, révision épinglée dans le
  script, attribution gardée) sur les jetons spatiaux de l'encodeur gelé, au lieu du MLP sur le vecteur. Réglages de référence du code
  officiel : une couche, dimension 768, FFN 2 048, dropout 0,1, requêtes gelées ; **100 groupes** (valeur de l'article pour les jeux à
  nombreuses classes, non réglée), classes réparties au hasard (graine 0), permutation et inverse sauvegardés, sorties en trop
  retirées. Même vocabulaire, même perte asymétrique, mêmes époques, même choix sur la validation.
- Entrées : jetons de patch seuls (jetons de préfixe retirés avant la remise en grille), ramenés à **8 × 8 = 64 zones** par moyenne
  adaptative (`adaptive_avg_pool2d` : C-RADIO 28 × 28, non divisible par 8 ; PE-Spatial 32 × 32). Pour C-RADIO, le jeton de synthèse
  qu'utilise T n'entre pas : T-D est une recette spatiale alternative, pas la seule localisation ajoutée à T. Sans encodage de position
  ajouté, l'attention ne garantit ni boîtes ni relations spatiales.
- Volume : 86 216 × 64 × 1 024 × 2 octets ≈ 11,3 Go en fp16. Stockage en fichiers `.npy` par morceaux, lisibles sans tout charger ;
  conversion en float32 lot par lot ; l'encodeur libéré avant l'entraînement ; jamais toute la grille en mémoire GPU.
- Budget (RAM, VRAM, disque, débit, durée, reprise) mesuré à l'essai à blanc sur Kaggle avant le calcul complet ; les durées
  annoncées jusqu'ici (~1,5 h d'encodage, ~1-2 h d'entraînement) sont des estimations. Jamais sur le Mac.

## Hors de cette série

- **ICARUS n'est pas utilisé dans E1-E3.** Il contient Emblematica Online parmi ses 19 sources (Zenodo 10.5281/zenodo.18980670,
  CC BY 4.0, ~118 Go). Avant tout usage futur : exclure **toute la source Emblematica Online** de l'entraînement, exclure par
  identifiants et provenance les livres de nos dev et test (pages, recadrages, éditions liées), puis rechercher les doublons entre
  sources par hachage et voisins visuels ; même audit pour les 788 images ICAI et la validation ; annotations et métadonnées comprises.
- Plus tard, préinscrits à part, après E1-E3 : descriptions textuelles des codes (iconclass/data, CC0) pour les codes rares ou
  jamais vus ; décodeur hiérarchique de type CAT (Springstein et al., WACV 2024 ; mAP par concept, non comparables à nos F1).
- Écartés : la perte « régions » (pas d'annotations de zones, et Marcel ne veut pas annoter) ; une perte à quatre termes d'un coup ;
  l'adaptation de l'encodeur (LoRA), sauf si E3 montre que la limite vient de l'encodeur.

## Où

Dépôt `porkyevitch`, `experiences/iconclass-architecture/` ; scripts copiés depuis caypollard avec leur provenance, puis modifiés.
Résultat, retenu ou non, dans `RESULTAT.md` à côté de ce fichier ; une brique retenue est ensuite proposée à lermolieff.
