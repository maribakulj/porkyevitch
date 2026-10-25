# Banc extérieur Iconclass du Rijksmuseum : règles écrites avant toute collecte

Date : 25/10/2026, avant toute collecte d'images ou de codes. Demande de Marcel (25/10) : mettre Emblematica de côté (doublon avec le
projet sur les emblèmes, licence des métadonnées introuvable, banc déjà consulté) et prendre un banc plus pertinent. Relecture de Codex
avant chaque script et avant le gel.

**Amendement 1 (25/10, après l'étape 0 et avant toute collecte d'images ou de codes de la population)**, en réponse aux blocages
B1-B4 de Codex (`~/Documents/reviews/porkyevitch-banc-rijksmuseum-codex.md`) : groupes de dépendance par composantes (B1), audit des
filtres sur une réserve séparée et chronologie unique (B2), cadre de sondage, éligibilité, tirage et seuil de faisabilité (B3),
contrat de collecte (B4). La version d'origine est le commit `eac2997`. Faits connus au moment de l'amendement, tous issus de comptes
agrégés du cache de l'étape 0 (aucun objet, code, nom ni image regardé) : la recherche renvoie les objets **par identifiant
croissant** (le jeton de page encode le dernier identifiant), avec des totaux de 4 920 peintures, 48 619 dessins et 387 333 estampes
« avec image » ; un acteur générique « anonyme » figure sur 292 des 900 notices ; un même acteur peut couvrir plus de 100 des 900
premiers objets. D'où le tirage au hasard dans la liste complète (B3) et l'exclusion des acteurs génériques des liens (B1).

## Pourquoi ce banc

- Données ouvertes : métadonnées du Rijksmuseum en CC0 (déclaration portée par la notice descriptive, `subject_of[].subject_to`) ;
  reproductions en « Public Domain Mark » (déclaration du contenu visuel ou de l'objet numérique IIIF, avec la politique du musée,
  §1.1 et §3.7) ; seules celles-là sont prises. Le banc peut être publié en entier (identifiants, codes, prédictions ; les images
  restent au musée, référencées par leur adresse IIIF).
- Plusieurs supports (peintures, estampes, dessins) au lieu des seuls livres d'emblèmes : mesure du transfert vers d'autres supports.
- Jamais consulté pour nos modèles : aucune prédiction n'a été faite sur ce banc. Qui regarde quoi et quand est fixé plus bas
  (« Chronologie unique ») : la réserve d'audit est regardée avant le tirage, le dev pendant la série, **le test jamais avant la fin de
  la série** (prédictions et verdicts des sept bras gelés).

## Collecte (scripts relus avant exécution)

Source : l'API ouverte du musée, sans clé (data.rijksmuseum.nl, Linked Art, profil fixé `la-framed`). Au plus une requête par seconde
pour l'ensemble du script, agent « caypollard/0.1 (research prototype) », cache de réponses brutes et reprise (contrat en B4).

0. **Disponibilité, métadonnées seules** — faite le 25/10 (`etape0/RESULTAT.md`) : sur les 300 premiers objets de chaque type, 842/900
   éligibles vérifiés. Portée : ces premiers résultats seulement ; elle a servi à dimensionner, pas à estimer une proportion du musée.
1. **Cadre de sondage** : la liste **complète** des identifiants renvoyés par chacune des trois recherches
   `search/collection?type={painting|print|drawing}&imageAvailable=true`, parcourue page par page (`next`) jusqu'au bout, pages
   brutes archivées avec leur date ; garde contre une page déjà vue ; la liste obtenue par type est comparée à `totalItems` : une
   recherche interrompue (page en échec, page déjà vue) arrête le script et n'est jamais prise pour une population ; une pagination
   menée proprement à son terme dont le nombre d'identifiants s'écarte de `totalItems` de **plus de 1 %** arrête aussi le script ; un
   écart d'au plus 1 % (objets ajoutés ou retirés pendant le parcours) est publié et la liste collectée sert de cadre.
2. **Échantillon** : par type, **3 000 identifiants tirés au hasard sans remise** : liste du type triée par points de code Unicode
   (`sorted` de Python), `Generator.choice(n, 3000, replace=False)` sur les indices 0 … n−1 de cette liste, avec un seul générateur
   `numpy.random.default_rng(0)` (numpy 2.5.4, épinglé et vérifié par le script) appelé pour painting, puis print, puis drawing ; si
   un type a moins de 3 000 identifiants, tous sont pris et c'est publié. Union, dédoublonnée par identifiant ; un objet présent dans plusieurs listes est gardé une fois ; ses types
   sont ceux des **listes complètes** du cadre auxquelles il appartient (ordre painting, print, drawing), la provenance du tirage
   (`sampled_from`) est gardée à part ; les deux comptes sont publiés. Le nombre 3 000 (au lieu des « 6 000 premiers » de la version d'origine) tient la collecte des
   notices dans une session d'environ 9 h (3 requêtes par objet à 1/s) ; il est fixé avant toute collecte.
   **Estimand** : la moyenne par image du F1 hiérarchique sur le banc constitué par **cet** algorithme : cadre à allocation égale
   des identifiants entre les trois types (3 000 chacun, pas proportionnel au musée, où les estampes dominent), puis éligibilité,
   filtres, plafond de 20 par composante et préfixe de la permutation des composantes (plus bas). Les proportions de supports du
   test sont celles que produit ce tirage, sans quota, et ne sont **jamais** rééquilibrées après coup ; elles sont publiées. La
   moyenne par composante est publiée à titre descriptif.
3. **Notices** : pour chaque identifiant de l'échantillon, l'objet, ses contenus visuels et leurs objets numériques (contrat B4).
4. **Éligibilité, avant tout tirage** (les cibles 1 200 / 300 sont donc des images **évaluables**) : `eligible_verified` de l'étape 0
   (CC0 sur la notice ; un objet numérique avec point d'accès IIIF et PDM sur lui ou sur son contenu visuel ; aucune résolution
   échouée), aucune autre déclaration de droits restrictive sur ces nœuds, image alignable avec les codes (B4), et **vérité projetée
   sans le chapitre 86 non vide avec au moins un code lisible**. Les comptes de passage par type sont publiés à chaque étape.
5. **Images** : téléchargées à distance (Kaggle), jamais sur le Mac, pour les seuls objets éligibles ; `full/!800,800/0/default.jpg`
   (côté maximal 800 px, rapport d'aspect gardé, aucun recadrage) ; URL exacte, dimensions et SHA-256 des octets retenus. Un
   téléchargement qui échoue après les reprises, un corps qui ne se décode pas comme image, ou des octets dont l'empreinte diverge à
   la reprise : l'objet est **exclu, compté, jamais remplacé**, avant tout calcul de composantes ; la faisabilité s'applique au banc
   restant.

## Groupes de dépendance (B1)

Un **groupe** est une composante connexe du graphe dont les sommets sont les objets éligibles et dont les arêtes relient deux objets
qui partagent :

- un **acteur pertinent à l'image**, identifié par son URI du musée : acteur de `produced_by.part[].carried_out_by` dont le rôle
  (`technique`) est l'un de *painter, printmaker, draftsman, maker, photographer, knipkunstenaar* ; acteur d'une attribution
  qualifiée (`part[].assigned_by[].assigned`, quel que soit le qualificatif : attribué à, atelier, entourage, suiveur…), groupes
  d'atelier compris ; acteur source d'une influence (`formed_by.influenced_by`) ; acteur des rôles *after painting / design / drawing /
  print by* (la composition source) ;
- un **objet parent** (`part_of`, objet dont l'objet fait partie : album, série, livre) ;
- une **copie interne** entre deux objets de la population, définie **une fois pour toutes aux valeurs larges de repli** :
  dHash < 64 bits ou cosinus C-RADIO ≥ 0,92. Ces valeurs contiennent les deux réglages possibles du filtre de référence (50 / 0,95
  ou le repli 64 / 0,92, plus bas) : les composantes sont donc calculées **une seule fois, avant l'audit**, et ne sont jamais
  recalculées après la planche, quel que soit le seuil final du filtre de référence. (Cela réunit plus d'objets qu'il ne faut au
  seuil d'origine : prudence pour l'indépendance, coût en composantes seulement.)

Ne créent **pas** d'arête : les rôles d'édition et de diffusion (*publisher, vendor, printer, compiler, clichémaker, writer*), les
lieux, les ensembles de collection (`member_of`, ensembles de conservation du musée), et les **acteurs génériques** (« anonyme »,
« inconnu » : un acteur est générique si l'expression `anoni|anonym|onbekend|unknown|unidentified` est trouvée, **sans distinction
de casse, comme sous-chaîne** (`re.search`, `re.I`), dans l'une des valeurs `notation[].@value` ou dans `_label` du nœud de l'acteur
tel qu'il figure dans la notice de l'objet ; aucune retouche manuelle ; la liste des URI ainsi écartées est publiée, sans être
modifiée). Le filtre de rôle vaut pour les acteurs nommés directement comme pour les attributions qualifiées ; une partie de
production dont le rôle n'est dans aucune des deux listes (ou absent) **crée une arête** par prudence, et ces cas sont comptés ; une
source d'influence crée une arête quel que soit le rôle de la partie. Script : `scripts/collecte_notices.py` (extraction des clés) ;
les composantes sont calculées après les images, avec les copies internes. Un objet sans aucun lien reste un groupe à lui seul ; la part de ces singletons, et celle des objets dont le seul
acteur est générique, sont publiées comme limite (deux anonymes d'une même main non identifiée restent comptés comme indépendants).
Les clés et les motifs de chaque réunion sont gardés (`groupes.json` : pour chaque arête, son type et sa clé).

Les mêmes composantes servent **à la fois** au retrait après détection de copie (une composante touchée est retirée en entier), à la
séparation réserve d'audit / dev / test, et au bootstrap apparié (tirages de composantes entières). Une composante n'est **jamais
scindée** ; une très grande composante reste entière (elle ne fournit au plus que 20 images, voir le plafond) et sa taille est publiée.

Le retrait d'une composante après une copie détectée est conservateur ; il sélectionne des groupes **sans copie détectée parmi les
candidats examinés**, il ne prouve pas que l'artiste est absent des 87 004 images d'apprentissage.

## Filtres contre les copies des données d'entraînement (B2)

Référence : les 87 004 images de `davanstrien/iconclass-vlm-brillfull` (révision complète `8045366ff092a06e8e1c4e47f1eb43cb2a54d732`,
entraînement et test), telles que fournies aux systèmes. Le manifeste du gel atteste la révision, les 87 004 identités et leurs
empreintes, et la recette et la révision C-RADIO exactes (celles de l'encodage complet, kernel `caypollard-encode-cradio` v3).

- **Filtre 1** : hachage de différence 256 bits (même fonction que `build_external_iconclass_bench.py`) ; une image candidate à
  **moins de 50 bits** d'une image de la référence retire sa composante entière.
- **Filtre 2** : cosinus C-RADIO (vecteur de la tête) **≥ 0,95** avec une image de la référence retire sa composante entière.

Ces deux valeurs viennent d'Emblematica (étalonnage à l'œil du 25/10) ; leur transfert à d'autres supports n'est pas acquis : **audit
sans prédiction** sur une réserve séparée avant tout tirage du test.

- **Réserve d'audit** : 10 % des composantes (arrondi au supérieur), tirées en premier (algorithme plus bas), jamais dans le test ni le
  dev.
- **Paires** : pour chaque objet de la réserve et chaque filtre, une seule paire, avec son plus proche voisin dans la référence
  (dHash : distance minimale ; cosinus : maximal ; égalité : plus petit indice de la référence dans l'ordre des fragments de
  l'encodage). Le **support** d'un objet de plusieurs types est le premier de ses types dans l'ordre peinture, estampe, dessin.
  Ordre de toute sélection : distance au seuil, puis identifiant du candidat (points de code Unicode).
- **Planche** : pour chaque support et chaque filtre, (a) les 6 paires **juste sous** le seuil (rejetées, les plus proches du seuil)
  et (b) les 6 **juste au-dessus** (gardées, les plus proches du seuil) ; (c) **plus loin** : 4 paires gardées tirées au hasard
  (`default_rng(2)`, `Generator.choice` sans remise, supports puis filtres dans l'ordre ci-dessus) parmi les paires gardées hors de
  (b) situées dans la bande dHash 50-79 bits, ou cosinus 0,85-0,95 ; soit au plus 96 paires. Un côté ou une bande qui a moins de
  paires que prévu est montré en entier, le manque noté. Une paire retenue par les deux filtres est montrée une fois et compte pour
  les deux. **Les deux membres** de chaque paire sont montrés (candidat et image de la référence), avec la distance, sans code ni
  prédiction.
- **Décision par paire**, écrite dans `audit.json` : *copie* (même image, même composition, recadrage, variante de reproduction,
  état d'une même planche), *non-copie*, ou *incertain*. Regard par l'orchestrateur, puis contre-regard de la planche par un
  vérificateur (Grok wA:p3) ; un désaccord vaut *incertain*.
- **Règle d'amendement ou d'arrêt, fixée maintenant** : pour un filtre et un support, si **au moins 2 paires gardées** de (b) ou (c) sont des
  *copies* (ou 1 *copie* + 2 *incertains*), le seuil de ce filtre est durci à la valeur de repli prévue — **dHash < 64 bits**,
  **cosinus ≥ 0,92** — pour tous les supports, puis la planche est refaite une fois sur la réserve avec les nouvelles valeurs (mêmes
  règles de sélection, bande (c) décalée : dHash 64-93 bits, cosinus 0,82-0,92) ; si elle contredit encore, arrêt et nouvelle
  préinscription. Les composantes ne changent pas (copies internes déjà aux valeurs larges). Les faux rejets (paires rejetées qui sont des *non-copies*) ne relâchent
  **jamais** un seuil : ils coûtent des données, pas une fuite ; leur part est publiée. Aucune autre recherche de seuil.

## Chronologie unique (B2)

1. cadre, échantillon, notices, éligibilité (métadonnées) ;
2. images, empreintes, dHash et vecteurs C-RADIO à distance ; distances aux 87 004 images de référence et entre candidats ;
3. composantes (arêtes de métadonnées + copies internes) ;
4. tirage de la réserve d'audit ; planche d'audit ; décisions ; règle d'amendement ou d'arrêt ;
5. retrait des composantes touchées par le filtre de référence (seuil final de l'étape 4 : 50 / 0,95 ou 64 / 0,92) dans toute la
   population hors réserve ; les composantes elles-mêmes restent celles de l'étape 3 ;
6. contrôle de faisabilité ; tirage du test puis du dev ;
7. gel : `frozen.json` puis `vu.json` (empreinte du gel après la planche d'audit). Aucune évaluation sans gel signé.

Pendant la série d'essais, les planches de différences entre modèles se font sur le **dev** et ne règlent rien. Les images du **test**
ne sont regardées par personne avant que les prédictions et les verdicts de toute la série soient gelés. Avant le gel, les scripts ne
montrent que des comptes et des distances agrégées sur le test.

## Tirage et gel (B3)

- **Plafond** : par composante, au plus 20 objets, choisis par un générateur propre à la composante
  (`default_rng([1, i])`, i = rang **à partir de 0** de la composante dans l'ordre canonique ; `Generator.permutation` des membres
  triés par identifiant, les 20
  premiers gardés).
- **Ordre canonique** des composantes : par identifiant minimal de leurs membres (tri de chaînes). Permutation des composantes par
  `default_rng(0).permutation(k)` (k composantes ; un générateur neuf, distinct de celui de l'échantillon ; une seule permutation,
  faite avant l'audit).
- **Réserve d'audit** : les ⌈10 %⌉ premières composantes de la permutation.
- **Test puis dev** : en parcourant la suite de la permutation, après retrait des composantes touchées par les filtres, chaque
  composante (plafonnée) est ajoutée **entière** au test tant que le test a moins de 1 200 images, puis au dev tant que le dev a moins
  de 300. Le test fait donc entre 1 200 et 1 219 images, le dev entre 300 et 319 ; une composante multi-supports est ajoutée avec tous
  ses supports. **Pas de quota par support** : les proportions sont celles des composantes tirées, publiées. Aucun remplacement après
  prédiction ; une image dont la prédiction échoue reste au dénominateur avec un F1 nul, et le compte est publié.
- **Faisabilité, fixée avant tout score** : test ≥ 1 200 images et **≥ 150 composantes** ; dev ≥ 300 images et ≥ 40 composantes. Si
  la population filtrée ne le permet pas, **arrêt** et nouvelle préinscription (aucun agrandissement du test pour atteindre une
  signification ; aucun changement de règle de groupe pour gagner des composantes). Le gel publie : nombre de composantes, tailles,
  part de singletons, part d'objets à acteur seulement générique, supports, et la plus grande composante.
- 1 200 / 300 est une cible raisonnable, pas une garantie de puissance : la précision dépend du nombre de composantes et de la
  dispersion des différences appariées.
- **Projection** commune avec la série d'essais : chapitre 86 retiré de la vérité et des prédictions (déjà fait à l'éligibilité, donc
  aucune image du test n'a une vérité projetée vide).
- **Gel** : `frozen.json` (identifiants, types, composantes et motifs de réunion, vérité brute et projetée, URL IIIF, dimensions,
  empreintes des images et des réponses brutes, versions et SHA des scripts, manifeste de la référence) puis `vu.json`.

## Contrat de collecte (B4)

- **Vérité** : toutes les notations trouvées sous `shows[] → represents_instance_of_type[] → equivalent[]` dont l'URI est sur l'hôte
  exact `iconclass.org` (comparaison d'hôte, pas de sous-chaîne), décodées une fois sans transformer `+` en espace ; avec, pour chacune,
  l'URI d'origine et le contenu visuel qui la porte ; la vérité est l'ensemble dédoublonné des notations, le journal garde toutes
  les URI (y compris deux URI donnant la même notation). **Rien n'est retiré** : les codes illisibles par `readable()` et
  les codes hors vocabulaire de la tête restent dans la vérité (un code illisible compte comme un élément que nul système ne peut
  prédire, comme sur ICAI) ; leurs parts sont publiées. Les formes d'URI non prises en charge sont comptées. Absence d'annotation et
  échec de résolution sont deux comptes distincts ; un objet dont une résolution a échoué n'est jamais classé « sans code ».
- **Image** : l'objet numérique retenu est, dans l'ordre de la notice, le premier objet numérique à point d'accès IIIF (hôte exact
  `iiif.micr.io`) et PDM, **porté par le contenu visuel qui porte les codes**. L'alignement se décide **avant** tout examen des droits ou de l'IIIF, sur toutes les vues codées et tous les objets
  numériques qu'elles résolvent : s'il y a plus d'un objet numérique distinct pour l'ensemble des vues codées (recto/verso, vues
  multiples), ou une vue codée sans objet numérique, l'objet est exclu comme non alignable et compté ; sinon, cet unique objet
  numérique doit avoir l'IIIF et le PDM, faute de quoi l'objet est exclu (aucun repli sur l'image d'une autre vue, aucun code
  retiré).
  Gardés : identifiant canonique de l'objet, identifiant du contenu visuel et de l'objet numérique, URL IIIF exacte, dimensions,
  SHA-256 des octets.
- **Droits** : CC0 relevé sur la notice (`subject_of[].subject_to`), PDM relevé sur l'objet numérique ou sur son contenu visuel, chacun
  avec son URI et son chemin ; la politique du musée (§1.1, §3.7) est citée dans le gel. Toute autre déclaration (CC BY, restriction,
  « in copyright ») sur l'un de ces nœuds exclut l'objet, compté. Le droit de la photographie n'est jamais inféré du seul statut de
  l'œuvre.
- **Reprise** : cache de réponses brutes avec sidecar (URL, date UTC, profil, Accept, statut, type, SHA-256 vérifié avant décodage ;
  profil et Accept dans la clé) ; une requête par seconde au plus (horloge monotone) ; délai d'attente, reprises sur 429/5xx/erreurs
  réseau en respectant `Retry-After` ; garde contre une page de recherche répétée ; rapport écrit atomiquement avec SHA du script,
  configuration et empreinte des clés de cache utilisées ; seuls des comptes sont affichés. Les notices (≈ 9 000 objets,
  ≈ 27 000 requêtes, < 1 Go de cache) sont collectées sur le Mac en arrière-plan (réseau seulement), `df` lu avant ; les images et les
  calculs de filtres, à distance.

## Rôle dans la série d'essais d'architecture

Amendement 4 de `../2026-10-25-iconclass-architecture/PREINSCRIPTION.md`, écrit avant tout calcul d'essai, synchronisé avec cet
amendement 1 : le juge extérieur devient ce banc (test de 1 200 à 1 219 images, bootstrap par composantes entières), à la place
d'Emblematica ; la règle (famille de 7, Bonferroni 99,29 % unilatéral, Δ_Rijks > 0 et Δ_ICAI > −0,01) est inchangée. Les planches de
regard se font sur le dev. Emblematica n'est plus utilisé pour décider ; ses chiffres restent internes (porkyevitch) et ne sont pas
publiés dans lermolieff.

## Ce que ce banc ne mesure pas

- Un seul musée, néerlandais, avec ses propres habitudes de catalogage Iconclass : un gain ici reste un gain d'accord avec ce
  catalogue, parmi ses œuvres numérisées, ouvertes, annotées et retenues par les filtres. Un bootstrap de composantes ne mesure pas une
  variance entre musées.
- L'allocation égale entre types et le plafond de 20 par composante font que les proportions du banc ne sont pas celles du musée.
- Les filtres contre brillfull ne garantissent pas l'absence de ces œuvres du préentraînement des encodeurs : on dira « extérieur à
  l'ajustement supervisé, après filtres de copies », jamais « jamais vu par le modèle ».
- La part d'objets codés, la fréquence et la profondeur des codes, la part hors vocabulaire sont descriptives ; ni le banc ni les seuils
  ne sont choisis pour favoriser les codes déjà appris.
