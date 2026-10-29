# P9-A — champs de preuve hiérarchiques pour Iconclass

Version 1, 29 octobre 2026 — Codex wA:p6, pour relecture Grok wA:p2 puis audit Codex wA:p4. Document écrit avant tout essai de cette méthode.

**Statut : préinscription à relire ; aucun lancement autorisé par ce document seul.** Marcel a autorisé sa rédaction. wA:p1 la copiera dans `porkyevitch` après relecture. Aucun script, entraînement, préparation de tenseurs, calcul de scores ou essai à blanc lancé ici.

## 1. Décision de Marcel, portée et revendications

Décisions du 29/10 reçues de wA:p1 :

- Priorité : **Iconclass et le graphe de scène**. R1 et P9-B sont mis de côté ; R3 n'est plus un essai séparé et son objectif « régions pour Iconclass » est absorbé dans A.
- **H-F1 reste le juge principal.** Seules les méthodes déclarées avant essai « pour les rares » peuvent avoir un second juge : **F1 moyen par code sur les codes ayant 5–20 exemples d'apprentissage**, sous tolérance H-F1 de **−0,005**. F1 par tranche de fréquence toujours publié.
- Ici : **P9-A est déclarée comme méthode visant aussi les codes rares**, dès cette version. Deux verdicts distincts, général et spécifique aux rares, sont définis en section 9 ; aucun changement de juge après résultats.

On teste une tête sur **traits gelés**, avec annotations **multiétiquettes d'image**, sans annotation de zone. Question : imposer la hiérarchie **dans les cellules avant agrégation** aide-t-il davantage que le même calcul hiérarchique **après agrégation** ? Le partage sémantique et le rétrécissement des résidus visent la longue traîne.

Cette série ne teste ni détection de copies, ni apprentissage contrastif sur reprises/miroirs, ni graphe de scène, ni kNN de régions ajouté à A. Les cartes restent des champs latents ; un gain de codes ne prouve pas une localisation correcte. Les notices, Emblematica, ICARUS, les pixels réencodés, LoRA et tout changement d'encodeur sont hors série.

**Première expérience bornée :** tous les **81 951 exemples d'apprentissage**, dix époques, quatre bras et une graine initiale. Ce choix remplace le sous-échantillon de 16 384 évoqué dans le cadrage : les tranches « 5–20 exemples » correspondent ainsi au véritable apprentissage de la tête. Dix époques bornent le premier régime ; un échec ne réfute pas une convergence plus longue. Passer à trente époques demanderait une nouvelle brique préinscrite, sans prolonger silencieusement la présente.

## 2. Données autorisées et référence gelée

### 2.1 Entrées

- `davanstrien/iconclass-vlm-brillfull`, révision **8045366ff092a06e8e1c4e47f1eb43cb2a54d732**, CC0 déclaré.
- Onze fragments **`train-00000-of-00011` à `train-00010-of-00011`** de `mabaku/caypollard-encode-cradio`, **version 3**. 86 216 lignes au total : 81 951 apprentissage, 4 265 validation ; 4 241 vérités non vides après projection sans 86.
- Grilles `(n,64,1024)` fp16 et sidecars associés ; fichiers `feats/train-*.npz` pour les identités md5. La recette C-RADIO est celle de l'encodage v3 : modèle **nvidia/C-RADIOv3-L@9d0413465e8a91e67bbf2c1ad342815478d1b906**, carré gris 128, 448 px, bicubique, jetons 28×28 réduits par moyenne adaptative en 8×8.
- Vocabulaire historique **V = 7 907 codes**, reconstruit sur les 81 951 seules images d'apprentissage et vérifié égal à celui de phase 1.

Liste positive de fichiers exacte ; pas de découverte récursive des entrées. **Interdits :** fragment test ICAI, fichiers `test-*`, autres sorties mixtes de l'encodage, `emb*`, prédictions ou journaux d'évaluation des tests, et **tout le banc Rijksmuseum**, dev compris dans cette série. Monter une source contenant ces fichiers ne donne pas le droit de les ouvrir. Les 94 324 images de l'encodage ne constituent pas le train de cette expérience.

Chaque ensemble est contrôlé à distance contre les sidecars v3 : SHA, forme, dtype, finitude, nombre et alignement des lignes/codes/md5. Aucun rehash de gros tenseur sur le Mac. Échec d'entrée ou d'alignement : arrêt technique, sans recalculer les données ni exclure discrètement des lignes.

**Pixels pour le regard seulement :** le préparateur de planches peut lire les seules lignes correspondantes des fichiers `data/train-*.parquet` à la révision Brillfull gelée, ou un petit cache préparé par l'orchestrateur avec la même provenance. Vérifier le md5 des octets contre le manifeste de features ; aucune donnée test ni image d'un autre corpus. Ces pixels ne sont pas réencodés et ne sont jamais des entrées supplémentaires de la tête. Préparer les vignettes à distance, sans rapatrier de gros parquet sur le Mac. Si les images de contrôle ne sont pas disponibles avec leur provenance, différer l'essai plutôt que supprimer le regard du protocole.

### 2.2 Référence B, immuable pour cette expérience

**B = T-Z de phase 1**, meilleure H-F1 de validation publiée au moment de cette préinscription :

| Champ | Valeur gelée |
|---|---|
| Checkpoint | `t_z.pt`, E3 complet, époque **29** sur 0–29 |
| SHA-256 du checkpoint | `06e3de0fa7c2871f6ff132791aa7594ce22614a13dc5609cebf2c2a33019bcd6` |
| Seuil global | **0,65** |
| H-F1 de validation sans 86 | **0,5890847528448202**, sur 4 241 images |
| Architecture | requête sur 64 cellules 1 024, puis MLP 1 024→2 048→7 907 |
| Script E3 de référence | SHA `b20b98f16613e3df7c81677b65780b500b8ac292f4b1ca8016c3d449c700c031` |

Source : `essais/e3-complet/full/e3.json` et `run.json`, contenant de la validation seulement. `run.json` atteste **Tesla T4**, torch **2.11.0+cu128**, numpy **2.1.3**. Les poids ne sont pas présents dans le petit dossier local lu : l'orchestrateur lie leur artefact distant à cette empreinte dans le manifeste d'entrée, avant le blanc. Aucune autre tête n'est choisie en fonction d'un résultat de la série.

La tête officiellement retenue au verdict de phase 1 pourra différer. La série présente compare à B sans anticiper ce verdict ni le consulter. Changer la référence exige un amendement avant calcul, avec ses conséquences explicites, jamais un remplacement après examen des résultats.

B est gelée, en évaluation, sans dropout ; calcul de référence en float32 sur grilles brutes, lots de validation 256 comme E3. Vérifier SHA, vocabulaire, seuil et reproduction de H-F1 à **10⁻⁶** près. Les prédictions recalculées de B sont ensuite gelées par empreinte. Aucun calibrage nouveau de B : notamment, **le candidat de mélange nul n'a que son seuil 0,65**, pas une recherche de seuils déguisée en progrès de A.

## 3. Partages et identité des exemples

Reproduire le partage E3, sans nouveau tirage : concaténer les onze fragments dans leur ordre numérique ; `groups=sorted(set(md5))` ; sélectionner les groupes de validation avec `numpy.random.default_rng(0).random(len(groups)) < 0.05`. Exiger les comptes 81 951 / 4 265 et l'absence de md5 commun. Archiver les listes de lignes sous `(fragment, indice à partir de 0, md5)` et leurs empreintes.

Tous les bras utilisent **toutes les 81 951 lignes d'apprentissage**. Compter une occurrence de code au plus une fois par image, comme E3. Des reproductions non identiques peuvent échapper aux groupes md5 ; cela limite l'indépendance, sans autoriser un nouveau calcul de copies dans cette série.

Au sein des 4 265 lignes de validation, former deux sous-ensembles entiers par md5 :

`k(m)=SHA256(UTF8("p9-a/v1/validation/" + m)).digest()`.

**V-réglage** si le premier octet de k est <128 ; **V-diagnostic** sinon. Les effectifs exacts sont produits par la préparation, avant modèle ; aucun rééquilibrage selon les codes ou scores. Si un sous-ensemble contient moins de 1 000 images évaluables, arrêter pour amendement, sans essayer une autre graine. Les vérités projetées vides restent disponibles pour les mesures par code.

V-réglage choisit époque, mélange et seuil. V-diagnostic n'est ouvert en mesures qu'après gel des choix des quatre bras de la graine. La **règle G et le juge rare portent sur l'ensemble de la validation**, conformément à la décision reçue ; V-diagnostic sert à examiner la stabilité du mécanisme. Cette validation a déjà servi à la phase 1 et à concevoir les hypothèses : la série est **exploratoire**, sans revendication confirmatoire.

Cette réserve s'applique aux **nouveaux bras**. Exception explicite : le contrôle d'intégrité de B peut reproduire son ancien H-F1 sur toute la validation avant entraînement ; sa valeur est déjà connue. Ce contrôle ne fournit aucune métrique d'un nouveau modèle, aucun choix de seuil et aucune sélection de cas V-diagnostic.

## 4. Cibles, hiérarchie, fréquences et texte public

### 4.1 Fonctions et vocabulaire

Reprendre exactement `ancestors`, `most_specific`, `drop86` du script E3 épinglé. Pas de nouvel interpréteur de codes pendant la série.

Pour la perte, cible `y_ic=1` si c appartient à l'union des ancêtres des codes bruts Y_i, en restant dans V. Les codes 86 restent appris comme dans E3. V est l'ensemble des ancêtres des codes bruts apparaissant sur au moins cinq images du seul apprentissage ; égalité stricte avec la liste historique. Aucune vérité hors V n'est retirée des métriques.

Construire la relation stricte `a ≺ c` si a appartient à `ancestors(c)\{c}`. Vérifier antisymétrie, acyclicité et transitivité sur V. Pa(c) est la réduction transitive, c'est-à-dire les ancêtres propres sans nœud intermédiaire. Une racine artificielle 0 est le parent des nœuds sans ancêtre propre. Les parents sont construits depuis V et le parseur, **pas depuis des annotations d'images de validation**. Une notation isolée non décomposable reste un nœud relié à 0 ; elle n'est pas supprimée.

Si le parseur ne définit pas une relation partiellement ordonnée sur V, arrêt avant entraînement ; aucune « réparation » de hiérarchie choisie après métriques. La hiérarchie officielle sert au texte public, pas à remplacer celle de la mesure.

### 4.2 Deux fréquences, deux usages

- `n_brut(c)=somme_(i apprentissage) 1[c dans set(Y_i)]`, **avant expansion**, sans réécriture des chaînes. C'est la fréquence des tranches et du juge rare.
- `n_ferme(c)=somme_(i apprentissage) y_ic`, **après expansion**. C'est la fréquence des priors et du rétrécissement du modèle.

Archiver les deux tables et leurs SHA. Aucun compte de validation ne sert à apprendre ces quantités. La préparation doit signaler les éventuelles collisions entre chaînes brutes et chaînes dépouillées d'espaces ; si elles modifient V ou la définition des rares, arrêt pour amendement plutôt que normalisation silencieuse.

### 4.3 Prototypes textuels, identiques dans les quatre bras

- Données officielles `iconclass/data`, révision **737ce365e3e6ab5302bafc22428ee37e57becee1**, licence **CC0** vérifiée dans le fichier LICENSE. Ne lire que les fichiers de classification et de descriptions, jamais de notices d'œuvres.
- Encodeur **sentence-transformers/all-MiniLM-L6-v2**, révision **1110a243fdf4706b3f48f1d95db1a4f5529b4d41**, licence déclarée **Apache-2.0**. Pas de `trust_remote_code`, d'API payante, d'envoi d'e-mail ou de jeton dans Kaggle.
- Description anglaise exacte si la notation c existe dans le dictionnaire épinglé. Sinon, texte déterministe : `Iconclass notation: {c}. Broader concepts: {descriptions anglaises disponibles des ancêtres propres de c}`. Ancêtres triés par nombre de leurs ancêtres puis ordre Unicode ; séparateur ` ; `. Si aucun ancêtre n'a de description, ne garder que `Iconclass notation: {c}.`.
- UTF-8, Unicode NFC pour ce texte seulement ; aucun changement des codes/cibles. Tokenisation épinglée, au plus 256 wordpieces, troncature à droite ; mean pooling du dernier état sur le masque d'attention, comme la carte du modèle, puis normalisation L2 ; e_c ∈ R³⁸⁴. e_0=0.
- Résidu `d_c=e_c−moyenne_(p dans Pa(c)) e_p`. Fichier de prototypes et tableau exact/fallback/tronqué, avec SHA. Tous les textes viennent de V d'apprentissage et du dictionnaire ; aucun code nouveau n'est récolté dans la validation.

Cette règle fixe aussi le traitement des qualificatifs et codes composés : pas d'appel dynamique à une notice de musée pour expliquer un code introuvable. La qualité de ces prototypes n'est pas garantie. Les contrôles les partagent afin que l'effet local ne soit pas confondu avec l'ajout du texte.

## 5. Quatre bras et calcul mathématique

Poids fixes des cellules `omega_u=1/64`. Avant les nouvelles têtes seulement, normaliser chaque z brut par moyenne/variance sur ses 1 024 canaux, sans paramètres affines, epsilon=10⁻⁵. B garde ses entrées brutes. Cette normalisation est identique pour les quatre bras.

Projection partagée de forme, non de poids entre bras : `v_u=W z_u`, W∈R¹²⁸×¹⁰²⁴. Score de code :

`s_uc = <v_u, U d_c + delta_c>/sqrt(128) + b_c`.

U∈R¹²⁸×³⁸⁴ ; delta_c∈R¹²⁸ ; biais b_c. Pour les trois bras de champs, racine `r_u=softplus(w0^T z_u+b0)+10⁻⁸`, et `mu=somme_u omega_u r_u`.

### F — contrôle non imbriqué

`lambda^F_uc = r_u sigmoid(s_uc)`,

`L^F_c=somme_u omega_u lambda^F_uc`, `p^F_c=−expm1(−L^F_c)`.

Même agrégation, mêmes prototypes et rétrécissement ; aucun lien parent–enfant dans le calcul appris.

### G — contrôle hiérarchique après agrégation

`g_c = [somme_u omega_u r_u sigmoid(s_uc)] / mu`.

Racine `L^G_0=mu`, puis, dans l'ordre topologique :

`L^G_c = min_(p dans Pa(c)) L^G_p × g_c`, `p^G_c=−expm1(−L^G_c)`.

La hiérarchie intervient dans le **calcul appris et sa perte**, après mise en commun. Ce contrôle n'est pas une simple remontée de maxima après seuil, qui pourrait laisser les prédictions inchangées. Il n'est pas présenté comme une reproduction de C-HMCNN.

### A — P9-A, hiérarchie dans chaque cellule

`lambda^A_u0=r_u`, puis :

`lambda^A_uc = min_(p dans Pa(c)) lambda^A_up × sigmoid(s_uc)`.

`L^A_c=somme_u omega_u lambda^A_uc`, `p^A_c=−expm1(−L^A_c)`.

**Comparaison mécaniste primaire A−G :** mêmes paramètres, données, perte et portes ; seule la position de l'imbrication par rapport à l'agrégation change. Sur une hiérarchie à un seul niveau sous la racine, A et G sont identiques : ce sera un contrôle logiciel, pas un résultat de gain scientifique.

### C — CSRA adaptée, contrôle externe apparié en capacité

Avec les mêmes scores linéaires s_uc, une tête, température **T=1**, coefficient résiduel **eta=0,1** :

`a_uc=softmax_u(s_uc)`,

`l^C_c=moyenne_u s_uc + 0,1 somme_u a_uc s_uc`, `p^C_c=sigmoid(l^C_c)`.

C'est l'opérateur CSRA de Zhu et Wu, adapté à notre projection de rang 128, nos prototypes, notre perte et nos entrées gelées. Pas de multi-head ou de réglage de température/coefficient dans cette série. Réécriture d'après l'article, sans copie du code des auteurs ou d'une réimplémentation à licence différente. Ce contrôle ne prétend pas couvrir toutes les variantes CSRA.

La racine de champs n'est pas utilisée par C : **1 025 paramètres actifs de moins**, à publier. F/G/A ont chacun **1 201 252 paramètres**, C **1 200 227**, hors B et prototypes gelés. Les comparaisons de mécanisme sont A−G ; C indique si le modèle proposé apporte quelque chose au-delà d'une attention par classe simple.

### Cohérence et conservation : contrôles, non preuves de localisation

Dans A et G, tout enfant a une intensité agrégée au plus égale à celle de ses parents, donc `p_enfant≤p_parent`. A conserve également sa sortie si une cellule est remplacée par deux cellules **aux mêmes caractéristiques**, chacune de poids omega/2. Il s'agit d'une conservation de masse, pas d'une garantie lorsqu'on réencode les pixels ou qu'on modifie réellement leur contenu.

Les champs ne sont ni des probabilités calibrées d'objet local ni des boîtes. Aucun IoU, aucune « localisation réussie » et aucune relation de scène ne sont inférés de H-F1 ou de cartes d'attention.

## 6. Initialisation, perte et entraînement apparié

### 6.1 Initialisation sans données de validation

Pour chaque graine, générer W avec coefficients N(0,1/1024), identique bit à bit dans les quatre initialisations. U=0, delta=0 ; aucune tête ne reçoit une préinitialisation supplémentaire. Les biais sont déterministes à partir des **mêmes priors marginaux** :

`pi_c=(n_ferme(c)+0,5)/(81951+1)`, `L0_c=−log1p(−pi_c)` ;

`L0_root=max(1, max_c L0_c)/0,99`.

F/G/A : w0=0, b0 choisi pour que r_u=L0_root. Dans F, `b_c=logit(clip(L0_c/L0_root,10⁻⁶,1−10⁻⁶))`. Dans A et G, `b_c=logit(clip(L0_c/min_(p dans Pa(c)) L0_p,10⁻⁶,1−10⁻⁶))`, L0_0=L0_root. C : `b_c=logit(pi_c)/1,1`.

A et G commencent avec les mêmes paramètres et les mêmes sorties, à tolérance numérique près. Les biais de F/C diffèrent par la paramétrisation, pour initialiser approximativement le même prior marginal plutôt que leur donner des sorties arbitrairement saturées. Publier les écarts initiaux aux priors et vérifier A=G ; aucun réglage de biais à partir d'un score de validation.

### 6.2 Perte commune

Pour chaque bras, ASL sur **ses probabilités propres avant mélange avec B**, cibles fermées par ancêtres : gamma positif=0, gamma négatif=4, marge négative=0,05, somme sur les codes et moyenne sur les images, comme E3. Appliquer ASL directement à p, pas une seconde sigmoid. Logarithmes protégés à 10⁻⁸.

Ajouter dans les quatre bras :

`R=10⁻⁴ somme_(c dans V) [55/(n_ferme(c)+5)] ||delta_c||²`.

Même coefficient, pas de recherche de régularisation. Cette série évalue la recette avec ce partage sémantique ; elle ne prétend pas isoler le rétrécissement lui-même. Le contrôle F et surtout G empêchent de créditer l'imbrication locale d'un gain dû aux seuls prototypes.

### 6.3 Paramètres fixes

| Paramètre | Valeur |
|---|---|
| Données avec gradients | les 81 951 lignes, une fois par époque, aucun rééchantillonnage rare |
| Horizon | **10 époques**, ni arrêt anticipé adaptatif ni prolongation |
| Graines | **0** d'abord ; **1 et 2** pour répétition préinscrite, conditions section 9 |
| Lot effectif | **64**, dernier lot conservé |
| Optimiseur | AdamW, lr **10⁻³**, betas (0,9 ; 0,999), epsilon 10⁻⁸, pas de scheduler |
| Weight decay | 10⁻⁴ sur W/U/w0 ; zéro sur biais et delta (delta déjà pénalisé par R) |
| Gradient | clipping de norme globale **5** |
| Dropout/augmentation | aucun dans les nouvelles têtes ; B gelée en eval |
| Calcul | produits linéaires fp16 autorisés ; portes, minima, intensités, sommes, exp/log et ASL **float32** |
| Déterminisme | RNG Python/numpy/torch enregistrés ; opérations déterministes activées, configuration CUDA figée dans le script relu |

Préparer la permutation des 81 951 indices par époque depuis `numpy.random.default_rng(seed)` neuf, et réutiliser le **même fichier de permutations** dans les quatre bras. Les bras ne partagent pas un optimiseur ni un état modifié par le précédent. L'ordre initial est F,G,A,C ; pour les graines 1 et 2, rotations G,A,C,F et A,C,F,G pour documenter l'effet de chauffe sur le temps.

Repli de mémoire prédéfini : micro-lot 32 avec accumulation ×2, puis 16 ×4, lot effectif toujours 64. Normaliser les gradients par le nombre effectif d'images, y compris le dernier lot ; les additions de R ne sont pas multipliées par le nombre de micro-lots. Si un bras requiert ce repli au blanc, les quatre utilisent le même micro-lot pour le calcul scientifique. Ne changer ni dimension, ni vocabulaire, ni horizon pour faire tenir un seul bras après résultats.

Pas de tenseur lot × zones × codes × codes. Ordre topologique et index de parents précompilés ; aucun label d'image dans le graphe d'inférence. La version numpy/PyTorch de référence E3 peut être réutilisée ; toute différence d'environnement est figée et auditée avant le blanc, avec contrôle de reproduction de B, jamais choisie sur un meilleur score.

## 7. Mélange avec B et choix d'un seul candidat par bras

B est commune et fixe. Former son enveloppe cohérente `b_c=max_(d descendant de c, c compris) p_B,d`, puis `L^B_c=−log1p(−b_c)` ; protéger b à [10⁻⁷,1−10⁻⁷] pour la conversion numérique. Pour un modèle h∈{F,G,A,C}, convertir ses probabilités en intensité L^h (directement disponible pour F/G/A ; `−log1p(−p^C)` pour C), puis :

`p^mix_c = −expm1(−[(1−alpha)L^B_c+alpha L^h_c])`.

Les sorties de A et G restent cohérentes ; cela n'est pas imposé au contrôle F/C. À alpha=0, l'enveloppe ne fait qu'ajouter des ancêtres de B ; seuil global puis `most_specific` reproduisent B. Vérifier l'identité **des ensembles prédits**, y compris avec le clipping, sur les images autorisées.

En implémentation, **alpha=0 retourne directement les prédictions gelées de B**, sans aller-retour logarithme/exponentielle susceptible de déplacer un score exactement au seuil. La formule de mélange et le clipping servent aux seuls alpha>0. Aucun gain obtenu par arrondi ou recalibrage du candidat nul n'est recevable.

**Grille unique :**

- Référence : alpha=0, **seuil de B=0,65 seulement**, sans recherche ni époque.
- Pour chaque époque 1 à 10 : alpha∈{0,25 ; 0,5 ; 1} et seuil theta∈{0,05 ; 0,10 ; … ; 0,95}.

Prédiction : seuil `p≥theta`, puis `most_specific`, puis `drop86`, dans **cet ordre E3**. Vérité : `drop86` sur les codes bruts, sans enlever les codes hors V ni réordonner cette projection dans la mesure.

Sur V-réglage seulement, choisir le meilleur **H-F1**, sans consulter macro-F1 rare, exact-F1 ou un sous-groupe. Égalité à 10⁻¹² près : alpha le plus faible (B prioritaire), puis époque la plus ancienne, puis seuil le plus faible. Archiver la grille et un seul choix final par bras/graine.

Si alpha=0 est choisi, verdict « référence conservée », aucun gain de méthode revendiqué. Les autres critères ne servent **pas à repêcher un deuxième checkpoint** : si le candidat H-F1 retenu échoue à une garde, on publie l'échec. Aucun candidat séparé choisi sur les rares n'est créé dans cette série.

Après gel des quatre choix, geler poids/prototypes/configuration et prédictions sur toute la validation avec SHA. Préparer les planches, puis ouvrir V-diagnostic et les agrégats complets. Les mesures de V-réglage restent accessibles pour la sélection ; tous les autres tableaux sont différés jusqu'à ce gel de la graine.

## 8. Mesures exactes et publication par fréquence

### 8.1 H-F1 et F1 exact par image

Sur les 4 241 lignes dont la vérité projetée est non vide :

`H_i=2 |A(Y_i) ∩ A(P_i)| / (|A(Y_i)|+|A(P_i)|)` ; prédiction vide ⇒0.

`E_i=2 |Y_i ∩ P_i| / (|Y_i|+|P_i|)` sur les **codes bruts projetés**, sans fermeture ; prédiction vide ⇒0.

H et E sont les moyennes par image, mêmes lignes et fonctions pour tous les systèmes. Les vérités illisibles/hors V restent dans la mesure comme E3. Les exclusions projetées vides sont comptées, pas remplacées.

### 8.2 Second juge, F1 moyen par code rare

Liste fixe avant tout modèle :

`R={c : 5≤n_brut(c)≤20 et c ne relève pas de drop86}`.

Elle est calculée sur l'apprentissage complet, **jamais** sur V-réglage/V-diagnostic. Tous ces codes doivent appartenir à V par la règle historique ; sinon arrêt pour incohérence des données/vocabulaire. Ne pas remplacer n_brut par la fréquence des ancêtres.

Sur **les 4 265 lignes de validation**, y compris les 24 vérités projetées vides comme négatifs, compter TP_c, FP_c, FN_c à partir des ensembles **bruts projetés** Y_i et P_i :

`F_c=2 TP_c/(2 TP_c+FP_c+FN_c)` ; si le dénominateur est nul, **F_c=0**.

`F_R=(1/|R|) somme_(c dans R) F_c`.

La liste R, donc le dénominateur macro, ne change pas selon les prédictions, la graine ou la présence du code en validation. **Les codes absents de la vérité de validation ne sont pas retirés.** Publier |R|, nombre de codes R avec au moins un positif de validation et leurs occurrences ; publier en plus la macro-F1 sur ces codes représentés, uniquement descriptive et sans substituer ce sous-ensemble au juge. Si R est vide, la voie rare est indisponible, sans changement de définition.

Le F1 exact par image E et la macro-F1 par code F_R sont deux mesures différentes. Le rappel rare du document de recherche antérieur devient un diagnostic ; il n'est plus le second juge après la décision de Marcel.

### 8.3 Tranches obligatoires

Publier **F1 moyen par code** pour les fréquences brutes **0 ; 1–4 ; 5–20 ; 21–100 ; >100**, mêmes conventions de zéro et même population de validation. Univers descriptif commun : union des codes bruts d'apprentissage, de V et des vérités de validation, sans 86 ; les prédictions restent nécessairement dans V. Cet univers est fixé par empreinte avant scores et identique pour toutes les graines ; il ne sert ni au vocabulaire appris ni aux prototypes. Fréquence zéro signifie absente de l'apprentissage, pas absente de l'ontologie ; cette liste ne crée aucune nouvelle sortie du modèle.

Pour chaque tranche : nombre de codes, nombre représenté en vérité de validation, occurrences positives, TP/FP/FN agrégés, macro-F1 et micro-F1 ; tranche vide = « non applicable ». Rapporter aussi H-F1/E par image, nombre de codes prédits, part hors vocabulaire des vérités, n_brut/n_ferme, couverture des descriptions, temps et mémoire. Les métriques hiérarchiques restreintes aux rares, si ajoutées pour décrire, sont nommées et ne remplacent jamais F_R.

## 9. Décisions écrites avant l'essai

Toutes les différences ci-dessous sont calculées sur **l'ensemble de la validation**, à candidat gelé, contre **B gelée**, et ne servent pas à sélectionner une autre époque.

### 9.1 Règle G — progrès général

Un bras obtient le verdict provisoire **G** si :

1. alpha>0 ;
2. `H_h−H_B ≥ 0,005` ;
3. `E_h−E_B ≥ −0,01`.

H-F1 est le juge principal ; F_R et tous les découpages sont publiés même si G passe. Ce verdict vaut pour la recette, pas automatiquement pour notre mécanisme.

### 9.2 Voie R — progrès spécifique aux rares, déclaré à l'avance

P9-A et les contrôles de cette famille sont déclarés comme visant les rares pour permettre une comparaison symétrique, **avant résultats**. Si un candidat ne passe pas G, il peut obtenir le verdict distinct **R, pour les rares seulement**, si :

1. alpha>0 ;
2. `F_R,h−F_R,B > 0` (**strictement positif**, sans inventer après coup une autre tranche) ;
3. `H_h−H_B ≥ −0,005` (**tolérance validée par Marcel**) ;
4. `E_h−E_B ≥ −0,01`, garde exacte conservée de G.

Le seuil de gain rare est strictement positif dans cette version ; aucune marge supplémentaire n'a été donnée par Marcel. L'estimation, l'intervalle et les dénominateurs restent nécessaires pour interpréter un petit gain. **R n'est pas une victoire générale H-F1.** Les deux verdicts sont présentés séparément et dans l'ordre G puis R ; aucune combinaison des scores en une note unique.

Si G et R échouent, méthode non retenue dans ce régime, même si un autre découpage semble favorable. Les copies, performances sur autres musées et graphes de scène ne constituent pas des voies de rattrapage.

### 9.3 Effet de l'imbrication et comparaison CSRA

Comparer A−G, A−F et A−C avec les mêmes prédictions et tirages. L'hypothèse d'**imbrication locale** est soutenue provisoirement si :

- voie générale : A obtient G contre B et `H_A−H_G ≥ 0,003` sur V-diagnostic ;
- voie spécifique aux rares : A obtient R (ou G) contre B, `F_R,A−F_R,G > 0` sur V-diagnostic et `H_A−H_G ≥ −0,005` sur V-diagnostic. Garder la même liste R complète dans ce sous-ensemble, pas les seuls codes qui y apparaissent.

Si les dénominateurs rares de V-diagnostic sont insuffisants — moins de **100 occurrences positives de codes R** — la conclusion mécaniste rare est **indécidable**, même si le verdict R sur l'ensemble de la validation reste calculable. Si A gagne sur F mais pas sur G, attribuer le résultat à une recette hiérarchique, sans démonstration de l'avantage local. Si CSRA est meilleure au juge principal, le dire ; ne pas recommander A comme meilleure recette en masquant C.

Ces seuils de mécanisme sont des propositions de cette préinscription, distinctes des règles de Marcel. On ne renomme pas G, le bras de contrôle, en « règle G » dans les sorties : utiliser `controle_global` pour éviter l'ambiguïté.

### 9.4 Répétitions et limites de conclusion

Graine 0 d'abord. Si A ou au moins un contrôle obtient G/R, les graines **1 et 2 des quatre bras** sont prévues pour établir la stabilité, après vérification des sorties et nouveau créneau accordé par wA:p1 ; aucune méthode ne reçoit plus de répétitions parce que son résultat plaît. Sinon arrêt au premier régime, sans chercher une autre graine gagnante. Toutes les graines lancées sont publiées.

Avant recommandation forte : les trois graines doivent être disponibles ; appliquer la même règle G/R à la **moyenne des mesures des trois graines**, et exiger qu'au moins deux graines sur trois passent individuellement la même voie. Pour R, aucune graine ne doit dépasser la tolérance H-F1 de −0,005 ; garde E≥−0,01 pour chaque graine dans les deux voies. Il s'agit de moyennes de scores, **pas d'un ensemble de prédictions** ajouté après coup.

Rapporter intervalles descriptifs appariés par groupes md5, **10 000 bootstrap**, graine 20261029, mêmes tirages pour tous les bras/B ; recalculer TP/FP/FN par code avec multiplicités de groupes, garder R et les conventions de zéro fixes. Publier le nombre de groupes, les distributions et les différences, pas seulement une borne.

Ni les deux voies ni les intervalles ne sont un test confirmatoire : sélection d'époque/seuil, validation déjà consultée et choix des hypothèses l'interdisent. Pas de p-value de découverte choisie entre deux juges. Une borne supérieure descriptive A−G inférieure au gain utile annoncé réfute au plus cet avantage **dans ce régime de dix époques** ; une incertitude large donne indécidable. Un échec logiciel ou budgétaire ne réfute pas l'idée.

## 10. Budget, essai à blanc et arrêts

### 10.1 Enveloppes avant mesure

Un T4, jamais un second GPU implicite ; compte partagé limité à deux GPU au total. Le coût de tous les bras est compté, pas seulement A.

| Étape | Enveloppe prévue |
|---|---|
| Préparation des textes/prototypes, listes et contrôles d'entrée | ≤0,5 h T4 si nécessaire pour le texte ; CPU distant ≤1 h ; pas de nouvel encodage image |
| Blanc technique, quatre bras | **≤0,5 h T4** cible, plafond **1 h** |
| Dix époques × quatre bras × une graine, 81 951 images | **4–12 h T4**, estimation à réviser avant lancement d'après blanc |
| Trois graines prévues si poursuite | **12–36 h T4**, hors préparation/blanc communs ; créneaux successifs |
| Bootstrap/tableaux, sans nouvelle inférence | CPU Kaggle **≤2 h** visées, calcul par groupes/blocs |
| VRAM | cible **4–10 Gio**, plafond de réservation **12 Gio alloués** ; réserve CUDA et total publiés |
| RAM processus | cible ≤**14 Gio** ; arrêt si >**15 Gio** ou mémoire système insuffisante |
| Sorties durables supplémentaires | cible **≤3 Go**, plafond **5 Go**, hors source v3 montée |

Les têtes E3 ont été mesurées sur T4 : T-Z ~0,61 h/30 époques, T-D ~2,53 h/30 époques. Le nouveau calcul cellule×code et le mélange/grille de seuils rendent une extrapolation directe fragile ; les enveloppes ci-dessus ne sont pas des consommations déjà mesurées.

Repères de stockage : grilles train **11,30 Go** fp16, montées en lecture seule ; probabilités de validation `4265×7907×4` ≈**135 Mo par bras** ; matrice de champs lot64×64×7907 fp32 ≈**123,55 Mio** avant autres activations. Réutiliser les buffers et libérer un bras avant le suivant ; ne pas conserver probabilités de toutes les époques en double ni les cartes complètes de toutes les images.

### 10.2 Blanc : réel, court, sans choix scientifique

Le script, le préparateur de données/textes et le blanc sont relus **Grok p2 puis Codex p4 avant exécution**. Créneau accordé par wA:p1. Pour les nouvelles têtes, le blanc utilise les **128 premières lignes d'apprentissage** dans l'ordre canonique et les **64 premières lignes V-réglage**, sans V-diagnostic. Le seul calcul sur validation entière est la reproduction de B déjà connue, exception définie en section 3. Ce sont des données réelles autorisées ; pas de faux corpus ni cibles synthétiques pour annoncer un succès.

Avant le premier score d'une nouvelle tête, faire regarder une **planche initiale de 12 images V-réglage évaluables**, les premières dans l'ordre canonique, avec leurs codes et provenance, sans sélectionner de cas selon une prédiction. Elle vérifie le matériau réel et ne sert pas à régler un hyperparamètre. La planche des écarts de section 11 est un second regard, après gel des choix.

Exécuter deux mises à jour de lot effectif par bras, un passage de validation technique, et les contrôles suivants :

- entrées autorisées, formes/dtype/finitude, alignement labels/md5/grilles, graphe sans cycle et vocabulaire exact ;
- SHA/architecture B ; contrôle alpha=0 donnant **exactement les mêmes ensembles** que B au seuil 0,65 ; la reproduction complète H=0,5890847528448202 est un contrôle d'intégrité sur validation autorisée, pas un réglage ;
- mêmes poids aléatoires partagés, mêmes listes d'indices, mêmes cibles et gradients finis ; A=G à l'initialisation ;
- sur champs issus d'images réelles : inégalité enfant≤parent pour A/G (tolérance **10⁻⁶**), sortie inchangée à duplication pondérée de cellules (tolérance **10⁻⁶**) ; la vérification à un seul niveau utilise les mêmes caractéristiques, uniquement comme contrôle logiciel ;
- métriques : F_R calculable sans retirer les codes sans support de validation ; n_brut distinct de n_ferme ; aucune recherche de seuil à alpha=0 ;
- temps froid/chaud, modèle exact du GPU, RAM, VRAM allouée/réservée et pic par phase, disque maximal, taille des sorties ;
- checkpoint de reprise : enregistrer modèle/optimiseur/scaler/RNG/permutation/position ; comparer une courte continuation reprise à la continuation sans interruption, tolérance de probabilités **10⁻⁶**, ensembles identiques.

La reproduction complète de B porte uniquement sur les onze fragments train autorisés ; le blanc n'ouvre aucun test pour vérifier la référence. Ses sorties scientifiques sur 64 images sont étiquetées **techniques seulement**, sans règle G/R ni choix d'architecture, horizon, coefficient ou prototype.

Après blanc, relecture des sorties et extrapolation temps/mémoire **avant** toute graine scientifique. Si le plafond d'une graine dépasse 12 h estimées, ou si les replis de micro-lots ne suffisent pas, arrêt pour amendement du budget/protocole ; ne pas sous-échantillonner les rares pour sauver la session. Aucun lancement automatique à la fin du blanc.

### 10.3 Arrêts et reprises

NaN/Inf, violation de hiérarchie, changement de vocabulaire, SHA incorrect, accès à un fichier hors liste, incohérence de métrique ou dépassement de plafond : arrêt technique, rapport et relecture. Une correction logicielle est versionnée ; un réglage motivé par un résultat de modèle devient une nouvelle brique, pas une correction silencieuse.

Checkpoints atomiques en fin d'époque, avec états nécessaires à la reprise, poids retenus et configuration. La survie de `/tmp` n'est pas présumée. Pas de jeton HF dans Kaggle ; persistance des sorties par les moyens existants de l'orchestrateur. Si l'optimiseur ou les RNG sont perdus, ne pas prétendre reprendre la même trajectoire : documenter l'interruption et relancer depuis l'initialisation de la graine, dans le budget autorisé.

## 11. Livrables, regard et chronologie de publication

1. Préinscription relue, versions approuvées, manifeste des entrées/prototypes/partages/rares, script et budget du blanc.
2. Blanc et rapport technique, puis relecture ; aucun score de modèle nouveau encore utilisé pour décider d'une variante.
3. Graine 0, quatre bras, sélection V-réglage, gel des checkpoints/choix/prédictions. Répétitions selon section 9 et autorisations de créneau.
4. Pour chaque bras, planche de **12 images de validation** où `|H_i(bras)−H_i(B)|` est maximal ; égalités : `(numéro de fragment, indice de ligne)` croissants. Montrer vérité brute projetée, prédictions, différences et champs de preuve lorsque disponibles. Les planches sont générées après gel et regardées **avant les tableaux agrégés V-diagnostic/complets** ; leur examen ne change rien dans la série. Marcel n'a aucune annotation à fournir.
5. Tableaux complets : H/E/F_R, cinq tranches de fréquence, dénominateurs, scores de chaque graine et moyennes, différences appariées, verdicts G/R/mécanisme, valeurs non retenues, paramètres et budget effectivement mesuré. Une belle carte n'est pas un juge supplémentaire.

Sorties : `manifestes/*.json`, `entrees.json` (révisions/SHA), `reference_validation.json`, configurations et historiques V-réglage, états de reprise, checkpoints retenus, prédictions **validation seulement**, planches cliquables, `budget.json`, `RESULTAT.md`, vérifications Grok/Codex. Aucune image ni corpus dans Git, aucun artefact de test.

Écritures wA:p6 : textes et futur code dans **`~/porkyevitch-maths`**, sorties locales compactes dans **`~/porkyevitch-donnees/maths/p9-a/`** ; `df` avant écritures/copies, rien de lourd sur le Mac. Seul wA:p1 copie vers `~/porkyevitch`. Pas de modification de `~/lermolieff`, d'E0–E3 ou des filtres du banc. Dépôt Git local sans remote.

## 12. Sources et différences avec le cadrage

- [Recherche P9, commit f7ffddf](/Users/marcel/porkyevitch-maths/docs/phase2-recherche.md) et [antériorités Grok](/Users/marcel/Documents/reviews/porkyevitch-phase2-recherche-anteriorites-grok.md). La présente version remplace, pour A seulement, le sous-échantillon de 16 384, le rappel rare et les seuils de décision du cadrage par le protocole ici écrit et la décision ultérieure de Marcel.
- [PHASE2.md](/Users/marcel/porkyevitch/PHASE2.md), [préinscription E0–E3](/Users/marcel/porkyevitch/experiences/2026-10-25-iconclass-architecture/PREINSCRIPTION.md), [script E3 épinglé](/Users/marcel/porkyevitch/experiences/2026-10-25-iconclass-architecture/scripts/e3_spatial.py).
- [Résultat de validation E3](/Users/marcel/porkyevitch/experiences/2026-10-25-iconclass-architecture/essais/e3-complet/full/e3.json), SHA `c954947c098621f053966e3023264fb6b716c169e5b5b653db68556976bb7f3a` ; [environnement E3](/Users/marcel/porkyevitch/experiences/2026-10-25-iconclass-architecture/essais/e3-complet/full/run.json), SHA `8ad8479a9a24831ac78fb1ca0ba2bb32b4c989c82cba8f0e82cc4c1adb6046ec` ; [budget E3](/Users/marcel/porkyevitch/experiences/2026-10-25-iconclass-architecture/essais/e3-complet/full/budget.json).
- [Données publiques Iconclass à la révision gelée](https://github.com/iconclass/data/tree/737ce365e3e6ab5302bafc22428ee37e57becee1), fichiers de classification et descriptions ; LICENSE CC0 lu. [MiniLM, révision gelée](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41), carte Apache-2.0 et sortie 384.
- Zhu et Wu, *Residual Attention: A Simple but Effective Method for Multi-Label Recognition*, ICCV 2021, [article primaire, équations 2–8 et tête T=1](https://openaccess.thecvf.com/content/ICCV2021/papers/Zhu_Residual_Attention_A_Simple_but_Effective_Method_for_Multi-Label_Recognition_ICCV_2021_paper.pdf). CSRA est adaptée ici et réécrite d'après les équations, sans attribution de licence aux réimplémentations trouvées sur le web.

Les équations de A ne sont pas une invention démontrée et leurs ingrédients ont des antériorités. Cette série demande si **cette imbrication locale**, avec **ces données et ce budget**, mérite d'être construite plus loin. Toute correction de cette préinscription après relecture est versionnée **avant** le premier calcul concerné.
