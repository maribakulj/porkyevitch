# Têtes Iconclass : essais d'architecture, règles écrites avant calcul

Date : 25/10/2026, avant tout calcul. Accord de Marcel le 25/10 (« les essais c'est ok pour la préinscription »). Amendée le 25/10
après la relecture de Codex (`~/Documents/reviews/porkyevitch-architecture-preinscription-codex.md`), toujours avant tout calcul ; feu vert de Codex le 25/10 (contre-vérification en fin du même rapport).
Amendement 2 (25/10 au soir, toujours avant tout calcul), à la suite d'une seconde analyse transmise par Marcel : contrôle de la
référence (E0), diagnostic des erreurs (D), contrôle spatial simple (T-Z), même projection sans 86 sur les deux bancs, famille de
sept comparaisons. À relire par Codex avant tout script.
Amendement 4 (25/10, avant tout calcul d'essai), à la demande de Marcel : **le juge extérieur devient le banc du Rijksmuseum**
(`../2026-10-25-banc-rijksmuseum/PREINSCRIPTION.md` : test de 1 200 objets, bootstrap par créateurs entiers, dev de 300 pour les
planches), à la place d'Emblematica, mis de côté (doublon avec le projet sur les emblèmes, licence introuvable, banc déjà consulté).
Partout où ce texte dit « Emblematica » pour le verdict, lire « Rijksmuseum » ; la règle de verdict et la famille sont inchangées.
Emblematica ne sert plus qu'au contrôle de reproduction de T0 à l'encodage, et ses chiffres restent internes.
**Chaque script, essai à blanc compris, est relu par Codex avant d'être lancé** (demande de Marcel).

## Portée

Série **exploratoire**. Elle demande : une recette choisie sur ICAI transfère-t-elle mieux vers Emblematica, sans adaptation à ce
corpus ? Le test Emblematica gel2 a déjà été consulté (tête T, VLM, règle PE) : ce n'est plus un test vierge pour l'ensemble de la
démarche. Une graine unique par brique : un essai de recette, pas une preuve de stabilité ; une répétition à graines fixées précédera
toute recommandation forte. Une conclusion confirmatoire demandera de nouveaux livres jamais consultés, à protocole fixé.
Deux décisions distinctes : choisir la tête à publier (permis avec ces résultats exploratoires) et affirmer
un progrès scientifique hors corpus (non permis sans nouveau banc). Un gain de F1 est un gain d'accord avec le catalogue : une prédiction juste mais non cataloguée reste pénalisée, et la série ne mesure
pas la lecture des relations entre figures.

## Point de départ

- **Encodeur** : celui que la règle PE-Spatial désigne comme version recommandée (`caypollard/results/iconclass-tete-pe/PREINSCRIPTION.md` :
  PE-Spatial si la borne basse de T-PE − T est ≥ −2 points sur les deux bancs, sinon C-RADIO). Règle inchangée.
- **T0** : la tête de cet encodeur, telle que calculée (MLP 2 048, perte asymétrique, codes vus ≥ 5 fois et leurs ancêtres,
  15 époques, seuil global choisi sur la validation ; `caypollard/scripts/remote_iconclass_head.py`). Dans ce texte, « T »
  sans autre précision désigne T0.
  Les chiffres 54,8 % / 26,1 % ci-dessous sont ceux de T-C-RADIO ; si PE est désignée, les chiffres de T-PE deviennent la référence.
- **E0, contrôle de la référence, avant E1** (motif : pour T-C-RADIO, l'époque retenue est la dernière, 14 sur 0-14, la validation
  montait encore, et le seuil retenu, 0,60, est la borne haute de la grille) :
  - **T-seuil** : mêmes poids que T, seuil global choisi sur la validation dans une grille étendue de 0,05 à 0,95 par pas de 0,05 ;
  - **T-long** : même tête réentraînée jusqu'à 30 époques, époque et seuil (grille étendue) choisis sur la validation.
  La **référence T\*** des essais E1-E3 est celle des trois (T0, T-seuil, T-long) qui a le meilleur F1 hiérarchique de validation
  (mesure de validation sans chapitre 86, voir plus bas ; égalités : la plus simple, dans cet ordre). Cette sélection sur la
  validation compte une fois dans la famille (comparaison T\* − T0) et ne donne lieu à aucune autre revendication sur les tests.
  **Après E0 et avant E1**, on fige dans `reference.json` : l'encodeur, T\* (ses poids, son époque, son seuil, son horizon
  d'entraînement de 15 ou 30 époques), ses caractéristiques et leurs empreintes, et ses chiffres sur les deux bancs.
- **Ce que les essais reprennent de T\*** : TK et T-niv utilisent les probabilités de T\* (les poids de T0 si T\* = T-seuil) ;
  T-niv part du seuil de T\* ; TK à α = 1 et au seuil de T\* reproduit T\* exactement (contrôle exigé). T-H, T-Z et T-D sont
  entraînés sur l'horizon de T\* (15 époques, ou 30 si T\* = T-long), époque et seuil choisis sur la validation dans la grille
  étendue. Tous utilisent la grille étendue, pour que la référence et les essais aient accès aux mêmes seuils.
- Limites mesurées qui motivent les essais (T-C-RADIO) : 54,8 % (ICAI 788) contre 26,1 % (Emblematica 762) en F1 hiérarchique ; F1 des
  codes exacts d'environ 0,04 hors corpus ; sur ICAI, les voisins K trouvent plus de codes exacts que T (0,356 contre 0,275) ; la tête
  moyenne les jetons de l'image ; tout code absent de l'annotation compte comme négatif.

## Règle générale

- **Un seul changement par brique** (sauf E2 et E3, déclarés comme recettes ci-dessous), toujours comparé à T\* (E0 : à T0), mêmes données, même
  partage de validation (5 % groupés par md5, graine 0), même vocabulaire calculé sur le seul sous-ensemble d'entraînement.
- **Tout réglage se choisit sur la validation ICAI seule.** Le test ICAI (788) et le test Emblematica (gel2 : 800 images, 59 livres ;
  762 évaluables sans chapitre 86, 58 livres) ne servent qu'à mesurer, une fois par brique.
- **Famille fixe de sept comparaisons** : T\* − T0 (E0), TK, T-niv, TK-niv, T-H, T-Z, T-D (chacune garde sa place même si elle
  n'est pas exécutée). Correction de Bonferroni au niveau familial de 5 % unilatéral : niveau de chaque borne 1 − 0,05/7 ≈ 99,29 %.
  Écarts en F1 absolu, sur les deux bancs **avec la même projection sans chapitre 86**, appliquée à la vérité et aux prédictions ;
  une image dont la vérité projetée est vide est exclue, et le dénominateur est le nombre d'images restantes : ICAI 787 images
  (une seule exclue ; T0 = 0,5459), Emblematica 762. La même projection sert à la mesure de validation dans toute la série (choix
  d'époque, de seuil et de T\*) ; les cibles d'entraînement ne changent pas (les codes du chapitre 86 restent appris).
  Δ_ext sur Emblematica, Δ_ICAI sur ICAI :
  Δ_ext sur Emblematica, Δ_ICAI sur ICAI. Une brique est **retenue** si la borne inférieure unilatérale à 99,29 % de Δ_ext est
  **> 0** **et** celle de Δ_ICAI est **> −0,01** (non-infériorité jugée sur la borne, pas sur l'estimation) ; les deux conditions
  sont exigées ensemble. Sinon, non retenue, publiée telle quelle, sans nouveau réglage.
- Bootstrap : **10 000 tirages**, graine 0, **mêmes tirages appariés pour tous les systèmes** ; Emblematica par **livres entiers**
  (moyenne par image recalculée sur les images des livres effectivement tirés, projection sans 86 commune) ; ICAI par images. Les
  IC95 bilatéraux ordinaires sont publiés à côté, pour la description. L'amplitude est donnée sans qualificatif automatique.
- **Regarder avant les chiffres** : pour chaque brique, une planche des 12 images du dev Emblematica (202) où |F1 hiérarchique de la
  brique − celui de T| est le plus grand (égalités : ordre des noms de fichier), avec la vérité et les deux prédictions en clair,
  regardée avant d'ouvrir les mesures du test. Aucune image des deux tests n'est regardée avant que les prédictions et les verdicts
  de **toute la série** soient gelés ; elles sont examinées ensuite. **Aucun changement** de seuil, d'architecture, de prétraitement ou de vocabulaire ne
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

## Diagnostic des erreurs (D), descriptif, avant E3

Sur T, puis sur chaque brique, les deux bancs, sans test de sélection : (1) profondeur : rappel des ancêtres de la vérité par tranche,
pour voir si les bons ancêtres sont trouvés sans les descendants ; (2) fréquence : F1 selon le nombre d'images d'entraînement du code
(5-20, 21-100, plus de 100) ; (3) couverture : part des codes de vérité Emblematica hors vocabulaire, par image et par code ;
(4) nombre de codes prédits par tranche de profondeur, contre la vérité ; (5) avec les probabilités (après l'encodage) : rang et
probabilité des codes de vérité profonds sous le seuil. Le banc Emblematica est fait de picturae, mais nos archives montrent que certaines
images ne sont pas recadrées et qu'aucun audit image par image n'a été fait ; ICAI n'indique pas le type d'image : la distinction
recadrage / page entière n'est donc pas mesurée dans cette série, et c'est écrit tel quel.
Le diagnostic ne change aucun essai de cette série ; il sert à interpréter les verdicts et à choisir la série suivante.

## Briques, dans l'ordre

### E1. Mieux décider avec ce qu'on a (aucun réentraînement)

- **TK** : pour chaque code c du vocabulaire de T, s_c = α · p_c + (1 − α) · v_c, où p_c est la probabilité de la tête T et v_c le vote
  des 20 plus proches voisins d'entraînement selon la pondération de K historique (cosinus, poids négatifs ramenés à 0, normalisés par
  leur somme), **étendu aux ancêtres** : v_c = somme des poids des voisins dont un code a c pour ancêtre (c compris). Les codes hors
  vocabulaire sont ignorés (TK garde le vocabulaire de T ; ce n'est pas K historique, qui vote sur les codes bruts). Puis seuil, et
  `most_specific` comme T. α ∈ {0 ; 0,25 ; 0,5 ; 0,75 ; 1} et seuil sur la grille étendue (E0), choisis ensemble sur la validation ;
  égalités : le plus grand α, puis le plus petit seuil. À α = 1 et au seuil figé de T, TK reproduit T exactement (contrôle exigé).
- **T-niv** : un seuil par tranche de profondeur du code prédit (1-2, 3-4, 5 et plus ; profondeur calculée sur le code lui-même, sans
  la vérité). Départ : les trois seuils égaux au seuil de T ; recherche coordonnée sur la grille étendue (E0), tranches dans l'ordre 1-2, 3-4,
  5+, trois passes ; à chaque pas, la valeur qui maximise le F1 hiérarchique moyen de validation ; égalités : on garde la valeur
  courante, sinon la plus petite.
- **TK-niv** : TK avec son α choisi, puis T-niv refait sur s_c avec la même procédure. Exécutée seulement si TK et T-niv sont retenues.
- Calcul : voisins validation × entraînement, test × entraînement et Emblematica × entraînement par lots, sur Kaggle, mis en cache
  avec empreintes ; durée mesurée à l'essai à blanc.

### E2. Cohérence parent-enfant (recette C-HMCNN, réentraînement de la tête seule)

- **T-H** : même architecture, vocabulaire, cibles (fermées par ancêtres) que T0, horizon de T\*, choix sur la validation ; deux changements
  liés, comme dans la méthode publiée (Giunchiglia et Lukasiewicz, NeurIPS 2020, éq. 4) — la comparaison est celle de la recette
  complète contre T\*, sans attribuer le gain à l'un ou l'autre :
  - **module de contrainte** : avec D(a) les descendants de a dans le vocabulaire (a compris, selon `ancestors()`), la sortie est
    m_a = max_{b ∈ D(a)} p_b ;
  - **MCLoss** : m⁺_a = max_{b ∈ D(a)} (y_b · p_b) ; L_a = − y_a · log(m⁺_a) − (1 − y_a) · log(1 − m_a) ; **somme sur les codes, moyenne
    sur les images** (la réduction de T).
- Prédiction : seuil sur m_a, puis `most_specific`, comme T.
- **Pas de variante « cohérence après coup » (T-H0)** : avec un seuil global puis `most_specific`, remonter à chaque ancêtre le
  maximum de ses descendants n'ajoute que des ancêtres de codes déjà au-dessus du seuil, que `most_specific` retire : les prédictions
  sont identiques à celles de T (preuve vérifiée par Codex sur 6 561 cas jouets ; un test sur les probabilités de validation sera
  exécuté et publié avec les résultats). Le gain éventuel de T-H ne peut donc
  venir que de l'apprentissage.
- Hiérarchie : celle de la notation (`ancestors()`), la même que la mesure. Une comparaison descriptive avec l'arbre officiel
  (iconclass/data, CC0) sur les 7 907 codes du vocabulaire est publiée (codes dont les ancêtres diffèrent), sans changer la contrainte.
- Mise en œuvre : réécrite par nous d'après l'article (le code des auteurs est sous GPL-3.0, non copié) ; maxima calculés sur la liste
  des paires (ancêtre, descendant) du vocabulaire, **jamais** par un tenseur lot × codes × codes (128 Go pour 512 × 7 907²) ; un test
  jouet obligatoire où un parent positif a un enfant négatif au score le plus haut (m⁺ ne doit pas prendre ce score).

### E3. Regarder les zones de l'image (recette spatiale)

- **T-D** : un décodeur ML-Decoder (Ridnik et al., WACV 2023 ; code Alibaba-MIIL/ML_Decoder, licence MIT, révision épinglée dans le
  script, attribution gardée) sur les jetons spatiaux de l'encodeur gelé, au lieu du MLP sur le vecteur. Réglages de référence du code
  officiel : une couche, dimension 768, FFN 2 048, dropout 0,1, requêtes gelées ; **100 groupes** (valeur de l'article pour les jeux à
  nombreuses classes, non réglée), classes réparties au hasard (graine 0), permutation et inverse sauvegardés, sorties en trop
  retirées. Même vocabulaire, même perte asymétrique, horizon de T\*, même choix sur la validation.
- Entrées : jetons de patch seuls (jetons de préfixe retirés avant la remise en grille), ramenés à **8 × 8 = 64 zones** par moyenne
  adaptative (`adaptive_avg_pool2d` : C-RADIO 28 × 28, non divisible par 8 ; PE-Spatial 32 × 32). Pour C-RADIO, le jeton de synthèse
  qu'utilise T n'entre pas : T-D est une recette spatiale alternative, pas la seule localisation ajoutée à T. Sans encodage de position
  ajouté, l'attention ne garantit ni boîtes ni relations spatiales.
- **T-Z, contrôle spatial simple** (mêmes 64 zones, mêmes entrées que T-D) : une mise en commun apprise (une requête apprise, poids
  softmax sur les 64 zones, un vecteur de 1 024) suivie d'un MLP de même forme que T (entrée 1 024 au lieu de 4 096). Comme T-D,
  T-Z retire le jeton de synthèse de C-RADIO et change la dimension d'entrée : T-Z − T\* compare une **recette spatiale
  alternative**, pas la seule mise en commun. T-D contre T-Z (descriptif, à entrées égales) mesure l'apport du décodeur à
  attention. Mêmes perte, horizon, choix sur la validation.
- Volume : 86 216 × 64 × 1 024 × 2 octets ≈ 11,3 Go en fp16. Stockage en fichiers `.npy` par morceaux, lisibles sans tout charger ;
  conversion en float32 lot par lot ; l'encodeur libéré avant l'entraînement ; jamais toute la grille en mémoire GPU.
- Budget mesuré à l'essai à blanc, séparément : poids, gradients, états de l'optimiseur, activations et attention en VRAM ; RAM ;
  disque ; débit ; durée ; reprise. Persistance (amendement 3, 25/10, avant tout calcul) : pas d'envoi progressif vers Hugging Face depuis
  Kaggle, faute d'y avoir un jeton (on n'y en met pas) ; les sorties sont gardées par Kaggle à la fin de la session, rapatriées puis
  sauvegardées vers le dépôt privé Ma-Ri-Ba-Ku/porkyevitch-sauvegardes ; une session perdue en cours de route se relance depuis zéro
  (gratuit, ~2-3 h), avec des ensembles publiés atomiquement et une reprise vérifiée si le dossier de sortie survit. Les durées annoncées (~1,5 h d'encodage, ~1-2 h
  d'entraînement) sont des estimations. Jamais sur le Mac.

## Hors de cette série

- **ICARUS n'est pas utilisé dans E1-E3.** Il contient Emblematica Online parmi ses 19 sources (Zenodo 10.5281/zenodo.18980670,
  CC BY 4.0, ~118 Go). Avant tout usage futur : exclure **toute la source Emblematica Online** de l'entraînement, exclure par
  identifiants et provenance les livres de nos dev et test (pages, recadrages, éditions liées), puis rechercher les doublons entre
  sources par hachage et voisins visuels ; même audit pour les 788 images ICAI et la validation ; annotations et métadonnées comprises. Première étape, sans les
  images : le fichier de métadonnées (`data.jsonl`, 629 Mo, sur une machine distante) pour mesurer recouvrements, collections,
  distribution des codes et couverture ajoutée, et vérifier la licence déclarée pour chaque source et chaque image.
- Plus tard, préinscrits à part, après E1-E3 : descriptions textuelles des codes (iconclass/data, CC0) pour les codes rares ou
  jamais vus ; décodeur hiérarchique de type CAT (Springstein et al., WACV 2024 ; mAP par concept, non comparables à nos F1).
- Écartés : la perte « régions » (pas d'annotations de zones, et Marcel ne veut pas annoter) ; une perte à quatre termes d'un coup ;
  l'adaptation de l'encodeur (LoRA), sauf si E3 montre que la limite vient de l'encodeur.

## Où

Dépôt `porkyevitch`, `experiences/iconclass-architecture/` ; scripts copiés depuis caypollard avec leur provenance, puis modifiés.
Résultat, retenu ou non, dans `RESULTAT.md` à côté de ce fichier ; une brique retenue est ensuite proposée à lermolieff.
