# D3 — Codes rares et profondeur sur traits gelés : préinscription (deux bras)

Version 1, 30 octobre 2026. Claude wA:pH. Elle découle de la décision D3 de wA:p1 (`~/porkyevitch/DECISIONS.md`) et s'appuie sur deux avis :
- Grok p7 (`~/Documents/reviews/porkyevitch-traine-profondeur-grok.md`, sha `39c604b1…`) ;
- Codex p4 (`~/Documents/reviews/porkyevitch-traine-profondeur-codex.md`), dont toutes les corrections sont reprises et marquées **[P4]**.

Écrite **avant tout code**. Elle est à relire par Grok p2, puis à faire auditer par Codex p4 avec le script. **Rien n'est lancé.**

Statut : **exploratoire**. La validation ICAI a déjà servi à choisir les têtes et au diagnostic. La coupure réglage/lecture du bras 2 limite les nouveaux ajustements, mais elle ne rend pas la série confirmatoire [P4]. On n'ajoute rien à P9-A ni à A1 à partir de cette série.

## 0. Ce que la série cherche, et ce qu'elle ne dit pas

Le diagnostic complet (`diagnostic.json`, sha `312d5a40…`) a mesuré deux défauts de B :
- **codes rares** : macro-F1 de 0,0705 sur les 4 073 codes bruts à 5–20 exemples, et 0,1998 sur les seuls 1 437 représentés en validation ;
- **profondeur** : le rappel des nœuds passe de 0,859 (profondeur 1) à 0,375 (profondeur 6), pendant que la précision passe de 0,742 à 0,640.

Ce que ces chiffres ne disent pas [P4] :
- La rareté et la profondeur sont liées. Une partie de la baisse du rappel peut venir de la fréquence, pas d'une descente défectueuse.
- Un Jaccard élevé des erreurs entre T* et B compare des sorties. Il ne mesure pas l'information absente des traits.
- Le score ajusté de +0,0013 n'est pas une borne, et il ne rend pas un autre ajustement impossible.

Les deux bras sont donc des **sondes ciblées**, pas des tests d'hypothèses causales.
- **Bras 1 — vote de voisins rares** : une variante ciblée de TK. Ce n'est pas une transposition démontrée de RAC ([Long et al.](https://arxiv.org/abs/2202.11233)).
- **Bras 2 — tête des seuls enfants** : une sonde locale de la descente.

Hors de ce lot : CAT, CHiLS, RAC complet, perte distribution-balanced, décalage de logits (contrôle peu coûteux mais distinct), ICARUS.

## 1. Données, références, interdits

- **Traits gelés.** Les vecteurs C-RADIO de 4 096 dimensions de l'encodage v3 (`caypollard-encode-cradio` v3, onze fragments `train-*`), sans rien réencoder. Partage E3 inchangé : 81 951 lignes d'apprentissage, 4 265 de validation, dont 4 241 évaluables.
- **Référence B = T-Z** : époque 29, seuil 0,65.
  - Ses probabilités viennent du **cache float32** du diagnostic. Le script le lit directement sur Kaggle, dans la sortie du noyau `mabaku/porky-diag-run` v3 montée comme `kernel_source` : `probabilites_validation.npz`, sha `c7df9d3d…`, tableau `B_TZ`, colonnes dans l'ordre de `vocabulaire.json`, lignes dans l'ordre de `identites_validation.json`.
  - Avant toute mesure, le script vérifie : les SHA du cache et du vocabulaire, le SHA des décisions projetées de B (`ea2502e1…`), et le H-F1 de B, 0,5890847528448202, à 10⁻⁶ près. Un écart arrête le script.
- **Fonctions** : `ancestors`, `most_specific`, `drop86` et `hier_f1` sont la transcription exacte d'E3, avec un test de parité.
- **Fréquences, toujours distinguées** [P4] :
  - `n_brut(c)` = nombre d'images d'apprentissage dont l'étiquette **brute** contient c ;
  - `n_fermé(c)` = nombre d'images d'apprentissage dont la **fermeture** de l'étiquette contient c. C'est la fréquence des cibles réellement apprises.
- **Interdits** : test ICAI, banc Rijksmuseum, test IconArt, Emblematica, ICARUS. Aucun voisin pris en validation ou en test, et aucune inspection de copies du test.
- **Partage du bras 2**, par groupes md5 : un groupe va en **V-réglage** si le premier octet de `sha256("D3-2026-10-30|" + md5)` est < 128, sinon en **V-lecture**. Les effectifs sont publiés avant toute mesure. Le bras 1 n'a aucun réglage : il est jugé sur toute la validation, et V-lecture est publiée à part.

## 2. Étape S0 — supports et émissibilité, avant tout score [P4]

À partir de l'apprentissage, de V et des vérités de validation (sans aucune sortie de modèle), le script publie un tableau par tranche de `n_brut` (0 ; 1–4 ; 5–20 ; 21–100 ; 101–1 000 ; > 1 000) croisée avec la profondeur (1 à 6, 7 et plus, composés à part). Pour chaque case :
- les codes dans V et hors V ;
- les médianes de `n_brut` et de `n_fermé` ;
- les supports de validation bruts (le code est une étiquette) et fermés (le code est dans la fermeture).

Contrôles :
- tout code à `n_brut` ≥ 5 est dans V (construction historique) ; un échec arrête la série ;
- l'univers descriptif reste celui du diagnostic. Les prédictions restent dans V, et aucun code hors V ne devient émissible [P4].

## 3. Bras 1 — vote de voisins limité aux codes rares

**Cible.** `R = {c ∈ V : c ne commence pas par 86, 5 ≤ n_brut(c) ≤ 20}`, liste fixée par empreinte avant tout score. |R| est publié. Les tranches 0, 1–4 et 5–20 sont publiées à part ; seule R est la cible. On ne promet rien sur les codes hors V [P4].

**Mémoire et voisins**, recette TK de la phase 1 sauf la cible :
- mémoire : les 81 951 lignes d'apprentissage, **par lignes**, comme TK ;
- K = **20** voisins par cosinus des vecteurs normalisés, égalités départagées par (fragment, ligne) ;
- poids : cosinus ramené à 0 s'il est négatif, puis normalisé par la somme. Une somme nulle donne un vote nul ;
- vote : `v_c = Σ` des poids des voisins dont la **fermeture** de l'étiquette brute contient c ;
- doublons : les lignes de même md5 votent chacune, comme dans TK. Le nombre de listes de voisins qui contiennent un md5 répété est publié, rien n'est retiré en silence [P4] ;
- validation et apprentissage n'ont aucun groupe md5 commun (partage E3) ; le script le vérifie.

**Mélange**, sur la seule cible R :
- `s_c = 0,75 · p_c^B + 0,25 · v_c` pour c ∈ R, et `s_c = p_c^B` ailleurs.
- Puis seuil 0,65 (celui de B), `most_specific` et `drop86`.
- K = 20 et le poids 0,25 sont un **choix initial explicite repris du contrôle historique, sans grille**. Ce ne sont pas des valeurs validées pour B [P4].
- Une sortie peut changer hors de R par `most_specific`, puisqu'un enfant rare émis retire son ancêtre. Ce n'est pas une garantie d'identité hors R [P4].
- **Contrôle d'identité** : avec un poids de vote nul, les décisions doivent égaler celles de B (SHA `ea2502e1…`) sur 4 265/4 265 lignes. Sinon le script s'arrête.

**Témoin de proximité** (descriptif) : la même recette avec une **mémoire permutée**. Les étiquettes des voisins sont prises sur la ligne `σ(j)`, avec σ = `default_rng(3030).permutation(81 951)`. Il isole l'apport de la proximité visuelle de celui d'un simple a priori sur R [P4].

**Juges**, sur toute la validation, contre B gelée, dans l'ordre :
- **Règle G** (P9-A §9.1) : `H − H_B ≥ +0,005` et `E − E_B ≥ −0,01`, où H est le H-F1 et E le F1 exact par image.
- **Voie R** (P9-A §9.2, déclarée ici avant essai), si G échoue :
  - `F_R − F_R,B > 0`, strictement ;
  - `H − H_B ≥ −0,005` (tolérance validée par Marcel) ;
  - `E − E_B ≥ −0,01`.
- **Calcul de F_R.** F_R est la macro-F1 par code sur **tous** les codes de R, en codes exacts après projection, conventions de P9-A §8. Un code absent de la vérité de validation reste au dénominateur avec F = 0 si 2TP + FP + FN = 0. La macro-F1 sur les seuls codes représentés est publiée à part, à titre descriptif.
- **Seuil de support.** Si la validation compte moins de **100 occurrences positives** de codes R, la lecture rare est **indécidable**.
- R n'est **pas** une victoire générale. Si G et R échouent, la variante n'est pas retenue.

**Toujours publié** : gain, intervalle bootstrap apparié par groupes md5 (10 000 tirages, descriptif), effectifs, les six tranches de fréquence, le témoin de mémoire permutée et une strate de forte proximité (cosinus du premier voisin ≥ 0,95). Cette strate est décrite sans affirmer de recopie [P4].

**Portée d'un échec** [P4] : ce vote, cette mémoire et ce poids n'ont pas apporté le gain cherché. Cela ne réfute ni RAC complet, ni l'information des traits, ni l'usage d'un texte aligné. Un score ponctuel inchangé n'établit pas l'équivalence.

## 4. Bras 2 — tête des seuls enfants, routée par le parent

**Familles**, choisies par des règles de support d'apprentissage écrites, jamais d'après la validation [P4] :
- **Parent direct** d'un code simple c (sans `:`) : l'ancêtre propre de c dont |ancestors| est le plus grand. Pour un code simple, les ancêtres sont des préfixes, donc une chaîne, et ce parent est unique.
- **Composés exclus** du bras : ils ont plusieurs parents, ce qui demanderait un masque, une règle de déclenchement et des contraintes d'émission propres. Leurs décisions restent celles de B [P4].
- **Une famille** = un parent p ∈ V avec `n_fermé(p) ≥ 100` et au moins deux enfants directs simples, dans V, hors `86`, avec `n_fermé ≥ 5`. Seuls ces enfants entrent dans la famille ; les autres restent à B.
- On publie le nombre de familles, d'enfants, leurs profondeurs et leurs tranches de fréquence.

**Tête.**
- Une couche linéaire du vecteur gelé (4 096) vers les N enfants retenus, avec des **sorties binaires sigmoïdes**. Plusieurs enfants d'un parent peuvent être vrais ensemble ; pas de softmax exclusif [P4].
- Pour la famille de p, on n'apprend que sur les lignes dont la **fermeture** de l'étiquette contient p. La cible d'un enfant c est `c ∈ fermeture` [P4]. La BCE est masquée, moyennée sur les couples (ligne, enfant) actifs.
- AdamW, lr 10⁻³, décroissance 10⁻⁴, lots de 1 024 lignes, **20 époques fixes**, sans choix d'époque. La perte masquée sur V-réglage est publiée pour la convergence.
- Graines 0, 1 et 2, toutes publiées.
- L'entrée est le vecteur global, pas les grilles de B. Un échec ne démontrerait pas l'absence du signal dans les grilles [P4].

**Porte du parent, gelée, issue de B.** `E(p) = 1` si p est dans la **fermeture de l'ensemble projeté de B** pour l'image, et jamais dans les seuls codes maximaux, que `most_specific` retire [P4]. Elle n'utilise aucune vérité. La même porte et la même population éligible servent à B et à la tête [P4].

**Décision.**
- Pour un enfant c d'une famille : c est retenu si `E(p) = 1` et `s_c ≥ t`. Cela **remplace** la décision de B pour cet enfant.
- Les autres codes gardent la décision de B.
- Puis `most_specific` et `drop86`.

**Seuil t**, sur V-réglage seulement, grille 0,05…0,95. Parmi les t dont la précision micro sur les enfants de famille est ≥ celle de B sur les mêmes enfants, on prend celui qui maximise leur rappel total. Égalités : le plus grand t. Si aucun t n'atteint la précision de B, t = 0,95 et le cas est signalé. Ce contrôle du budget de faux positifs empêche de gagner du rappel conditionnel en prédisant tous les frères [P4].

**Mesures sur V-lecture**, pour la tête et pour B, sur les mêmes vrais enfants de famille [P4] :
- **couverture de la porte** : P(E(p) = 1 | enfant vrai), et nombre d'enfants vrais exclus parce que la porte a échoué ;
- **rappel conditionnel** : P(émis | enfant vrai, E(p) = 1) ;
- **rappel total** sur tous les vrais enfants, précision, F1 et **faux positifs** sur toutes les images ;
- **identité de contrôle** : `rappel_total = couverture × rappel_conditionnel`. Elle vaut pour la tête et pour B, puisqu'un enfant émis par B implique son parent dans la fermeture. Le script la vérifie à 10⁻¹².
- le croisement fréquence × profondeur, pour séparer rareté et profondeur ;
- le H-F1 et le F1 exact du pipeline complet.

**Lecture du mécanisme**, descriptive : ce n'est pas un juge [P4].
- « **Descente améliorée** » si, pour les 3 graines, le rappel conditionnel de la tête dépasse celui de B d'au moins +0,02 **et** la précision de la tête est ≥ celle de B − 0,01.
- Sinon « **pas d'amélioration de la descente dans ce régime** ».
- Un rappel conditionnel en hausse avec un rappel total plat est rapporté tel quel.

**Juge** : la **règle G** sur V-lecture, contre B gelée, pour **chacune** des trois graines. Le verdict G n'est retenu que si les trois graines l'obtiennent. Il n'y a pas de voie R pour ce bras (décision D3). Un gain de H-F1 sans hausse du rappel conditionnel est rapporté comme tel, et il n'est pas attribué à la descente.

**Portée d'un échec** [P4] : cette sonde linéaire de 20 époques sur le vecteur global n'a pas amélioré la descente. Cela ne réfute ni la séparabilité des frères dans la représentation, ni une perte hiérarchique en général, ni une tête locale sur les grilles.

## 5. Exécution

- **Calcul.** Kaggle T4, une session de 2 h au plus, créneau de wA:p1. Entrées : `caypollard-encode-cradio` v3 (vecteurs et étiquettes d'apprentissage et de validation) et `mabaku/porky-diag-run` v3 (cache de B), plus les SHA épinglés. Voisins en float32 sur GPU, par blocs. Sorties de moins de 200 Mo dans `~/porkyevitch-donnees/maths/d3/`.
- **Blanc** :
  - contrôles d'entrées et reproduction de B ;
  - tableau S0 complet ;
  - identité du poids nul sur 4 265/4 265 lignes ;
  - voisins de 64 lignes de validation, avec leur temps ;
  - familles du bras 2 et une époque de la graine 0, avec son temps ;
  - extrapolation du budget.

  Aucune mesure de qualité. Il est relu avant le complet. Si l'extrapolation dépasse 2 h, on amende plutôt que de prendre un raccourci.
- **Complet** : S0, bras 1 et témoin, bras 2 avec ses trois graines, juges, tableaux, `RESULTAT.md`.
- Un réglage choisi après un résultat devient une nouvelle brique nommée.

## 6. Sources

- Diagnostic de la tête, résultat complet (sha `312d5a40…`) et préinscription v1.1 du même dossier.
- P9-A, préinscription, §8 (F_R) et §9.1–9.2 (règles G et R).
- Phase 1, préinscription de l'architecture, E1 (recette TK).
- Avis de Grok p7 et de Codex p4 cités plus haut. Sources primaires citées par Codex : [RAC](https://arxiv.org/abs/2202.11233), [Menon et al.](https://arxiv.org/abs/2007.07314), [Wu et al.](https://arxiv.org/abs/2007.09654), [CHiLS](https://arxiv.org/abs/2302.02551).
