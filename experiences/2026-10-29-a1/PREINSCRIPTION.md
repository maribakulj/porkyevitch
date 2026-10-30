# A1 — GFM sous un q de voisins, restreint aux ensembles fermés émissibles : préinscription

Version 2, 30 octobre 2026. Claude wA:pH, remplaçant de Codex maths wA:p6. La version 1 (29/10, sha `6d331c57…`, précisée le 30/10 en `a75116a8…`) est remplacée par celle-ci. Elle intègre la contre-expertise de Codex p4 (`~/Documents/reviews/porkyevitch-algos-production-codex-contre.md`, section A1). Les points repris sont marqués **[P4]**.

Document écrit **avant tout code** de cette méthode. Il reste à relire par Grok p2, puis à faire auditer par Codex p4 avec le futur script. **Aucun calcul n'est autorisé par ce texte seul.**

Statut : série **exploratoire**. La validation ICAI a déjà été consultée en phase 1 (choix de B, de son époque, de son seuil). Le nouveau partage ne la rend pas confirmatoire.

## 1. Ce qui est essayé, et ce qui n'est pas revendiqué

**La règle.** C'est le *General F-measure Maximizer* (GFM) de Waegeman, Dembczyński, Jachnik, Cheng et Hüllermeier ([arXiv:1310.4849](https://arxiv.org/abs/1310.4849), théorème 5.1, algorithme 1, équations 17–19), appliqué à une loi q construite pour chaque image.

**Le lien avec le H-F1.** Quand prédiction et vérité sont fermées par ancêtres, le H-F1 d'une image est le F1 plat des deux ensembles fermés (Kiritchenko et al. 2006 ; proposition 1 de [arXiv:2410.01305](https://arxiv.org/abs/2410.01305)).

**Antériorité, dite franchement [P4].**
- GFM, section 7.1.1, remplace déjà la loi par la **distribution empirique des étiquettes des voisins d'apprentissage**, et sa section 7.2.1 l'expérimente. Utiliser les empreintes des voisins avec GFM n'est donc pas nouveau.
- Les seules variantes de modélisation propres à A1 sont : le poids C-RADIO des voisins, l'inclinaison η par les logits de B, et l'atome B (π₀).
- **La restriction aux ensembles fermés ne demande aucun algorithme nouveau** (section 4) : sous des atomes fermés, le tri de GFM la respecte de lui-même.
- La seule contrainte qui demande un solveur est l'**émissibilité des éléments maximaux** : un nœud `86` ne peut pas être émis seul.
- La version 1 motivait un sac à dos sur la forêt du parseur par la fermeture. **Cette motivation était fausse et elle est retirée.**

**Optimalité.** Elle est exacte **pour la loi q**, pas pour la loi des données [P4]. Le support de q peut manquer des codes vrais. Une décision optimale sous q peut donc être moins bonne sur les images. Elle n'est pas « la règle de Bayes du H-F1 ».

**Questions posées, dans l'ordre :**
1. Le logiciel est-il exact ? Pour cela :
   - le tri, le solveur contraint et un PLNE de référence doivent donner le même optimum ;
   - avec π₀ = 1, on doit retrouver exactement B.
2. À q identique, la décision GFM bat-elle le seuil sur les marginales de q (mécanisme) ?
3. La recette bat-elle B selon la règle G (produit) ?
4. **Témoin [P4]** : les contraintes d'émission changent-elles réellement les décisions par rapport au tri seul ?

## 2. Données et interdits

**Données.**
- Brillfull `davanstrien/iconclass-vlm-brillfull`, révision `8045366ff092a06e8e1c4e47f1eb43cb2a54d732` (CC0).
- Les onze fragments `train-*` de l'encodage C-RADIO v3, avec le partage E3 inchangé : 81 951 lignes d'apprentissage, 4 265 de validation, dont 4 241 évaluables (vérité non vide après `drop86`).
- Mêmes contrôles d'empreintes et d'alignement que P9-A.

**Mesures sur la validation ICAI seule.** L'apprentissage ne fournit que les atomes de q : les vecteurs C-RADIO et les codes des lignes d'apprentissage. Les atomes d'apprentissage sont **admis** [P4] aux conditions suivantes :
- voisins pris dans les seules 81 951 lignes d'apprentissage, partage md5 historique intact ;
- aucun label de validation pour choisir les voisins ou construire leurs empreintes ;
- hyperparamètres choisis sur V-réglage seulement.

L'image interrogée intervient par ses traits et par les sorties de B, jamais par sa vérité.

**Référence B = T-Z.**
- Époque 29, seuil 0,65, checkpoint `06e3de0f…`.
- Ses probabilités viennent du **cache float32** du diagnostic de la tête (`probabilites_validation.npz`, sha `c7df9d3d…`, tableau `B_TZ` 4 265 × 7 907, colonnes dans l'ordre de `vocabulaire.json`). Ce n'est jamais une copie fp16 (audit diagnostic D2).
- Avant toute autre mesure, le script vérifie trois choses :
  - le SHA du cache ;
  - l'égalité exacte du SHA des décisions projetées (`ea2502e1…`, manifeste du diagnostic) ;
  - le H-F1 reproduit par ce cache, 0,5890847528448202 à 10⁻⁶ près.
- Ce recalcul CPU égale la valeur historique T4. On ne promet pas plus que l'égalité des décisions de ce passage.

**Interdits.** Le fragment `test-*` et tout fichier de test ICAI, les sorties mixtes, `emb*`, le banc Rijksmuseum (dev compris), le test IconArt, Emblematica, ICARUS. Monter un dossier qui en contient ne donne pas le droit de les ouvrir.

**Fonctions d'évaluation.** Parseur, `most_specific`, `drop86` et `hier_f1` sont une transcription exacte d'E3 (`e3_spatial.py:108-141`). La vérité d'une image est `drop86(Y)`, fermée par ancêtres dans `hier_f1`. Les vérités hors V restent dans T et dans |T| [P4].

**Partage de la validation (inchangé).** Il se fait par groupes md5 : un groupe va en **V-réglage** si le premier octet de `sha256("A1-2026-10-29|" + md5)` est < 128, sinon en **V-diagnostic**. Les effectifs et l'absence de md5 commun sont publiés avant toute mesure.

## 3. Structure (étape 0, condition d'arrêt)

Le script vérifie, sur V (7 907 codes) et sur toutes les empreintes d'apprentissage :
- **(c) fermeture** : V est fermé par `ancestors` ;
- **(t) transitivité et ordre** : si a ∈ ancestors(b), alors ancestors(a) ⊆ ancestors(b), et |ancestors(a)| < |ancestors(b)| pour a ≠ b. La profondeur |ancestors(·)| est donc un ordre topologique.

Un échec de (c) ou de (t) **arrête la série**. La structure en forêt n'est plus une condition : la version 1 en faisait une, elle était inutile [P4]. On publie à titre descriptif :
- la part des codes simples dont les ancêtres forment une chaîne ;
- le nombre de nœuds `86` présents comme ancêtres de composés ;
- la distribution de |U| par image pour chaque K.

## 4. Modèle q et décodeur

**Atomes.**
- T_j est la fermeture de `drop86(Y_j)` pour la ligne d'apprentissage j. Elle contient les codes hors V, et son cardinal |T_j| les compte.
- T₀ est la fermeture de l'ensemble projeté de B pour l'image.
- Voisins : les K lignes d'apprentissage de plus grand produit scalaire entre vecteurs C-RADIO normalisés. Les égalités de cosinus sont départagées par (fragment, ligne) croissant.
- C'est **par lignes**, pas par groupes. Le script vérifie si cette recette coïncide avec celle de la tête TK et publie l'écart. Il ne le suppose pas [P4].

**Poids.**
- `π_j ∝ exp(cos_j/τ + η · ℓ̄_j)`, où ℓ̄_j est la moyenne sur a ∈ T_j ∩ V de `logit(clip(p_a^B, 10⁻⁶, 1 − 10⁻⁶))`. On prend ℓ̄_j = 0 si T_j ∩ V est vide.
- Le softmax est stable : on soustrait le maximum, puis on normalise à la somme 1.
- Les atomes d'empreinte identique sont fusionnés en additionnant leurs masses, ce qui est exact. On publie le nombre effectif d'empreintes distinctes.
- Un atome vide (T_j = ∅) garde sa masse et contribue 0 à toute utilité.
- Mélange final : `q = π₀ δ_{T₀} + (1 − π₀) Σ_j π_j δ_{T_j}`.

**Utilité.** `U(S) = Σ_{a∈S} w_a(|S|)`, avec `w_a(k) = Σ_j q_j · 2 · 1[a ∈ T_j] / (k + |T_j|)`, et U(∅) = 0. L'univers est `U = (T₀ ∪ ⋃_j T_j) ∩ V`, fermé par (c).

**Émission.** On note N = {a ∈ U : a commence par `86`} les nœuds **non émissibles**. Le code émis est `P = drop86(maximaux(S))`. Si aucun maximal de S n'est dans N, alors la fermeture de P est S, et l'utilité de la sortie émise est U(S). Sinon, la sortie émise est plus petite que S. L'ensemble réalisable est donc : S fermé, S ⊆ U, **aucun maximal de S dans N**. On ne retire pas les nœuds `86` avant l'optimisation, puisque les composés peuvent les imposer [P4].

**Propriété utilisée [P4].** Si a est un ancêtre de b, alors `1[a∈T_j] ≥ 1[b∈T_j]` pour tout atome fermé, donc `w_a(k) ≥ w_b(k)` pour tout k ≥ 1. On trie U par `(−w_a(k), |ancestors(a)|, code Unicode)`. Les k premiers forment un ensemble **fermé**, qui maximise Σ w sur **tous** les ensembles de cardinal k. La preuve vaut sur tout DAG d'ancêtres cohérent.

**Décodeur.**
1. **Chemin rapide (tri GFM).** Pour chaque k = 1…|U|, on prend `S_k = les k premiers du tri`. Soit `k* = argmax_k U(S_k)`. Égalités : plus petit k. On compare **explicitement** au vide : si `max_k U(S_k) = 0`, alors S = ∅. On note `U_tri = U(S_{k*})`.
2. **Certificat.** Si aucun maximal de `S_{k*}` n'est dans N, alors `S_{k*}` est optimal pour le problème contraint, puisque `U_tri` majore l'optimum contraint et qu'il est atteint. On émet `drop86(maximaux(S_{k*}))`.
3. **Sinon, solveur contraint exact.** La valeur `U_tri(k) = U(S_k)` majore l'optimum contraint de cardinal k. On parcourt les k par borne décroissante, et pour chacun on résout un PLNE HiGHS (`scipy.optimize.milp`) :
   - variables x_a ∈ {0, 1}, a ∈ U ; contrainte Σ x_a = k ;
   - fermeture : x_b ≤ x_a pour chaque ancêtre direct ou indirect a de b ;
   - émission : x_a ≤ Σ_{d descendant propre de a dans U} x_d pour chaque a ∈ N. Un maximal ne peut donc pas être non émissible ;
   - objectif : max Σ w_a(k) x_a.

   On s'arrête dès que la borne du k suivant est ≤ la meilleure valeur certifiée. Égalités : plus petit k ; à k égal, un second PLNE à valeur fixée (≥ optimum − 10⁻¹²) minimise Σ rang(a)·x_a, où rang est la position dans le tri. Une égalité résiduelle prend la solution HiGHS, déterministe à version fixée ; elle est comptée.
4. **Témoin « tri non contraint » [P4].** C'est `drop86(maximaux(S_{k*}))` émis sans certificat. Il dit combien de décisions les contraintes d'émission changent réellement.

**Garanties et coût, sans promesse générale [P4].**
- Le chemin rapide est polynomial : O(|U|² log |U|) par image.
- Le solveur contraint n'a pas de garantie de temps polynomial.
- Chaque PLNE a une limite de 10 s. Un PLNE qui l'atteint sans écart dual ≤ 10⁻⁹ n'est **pas certifié** : l'image prend la meilleure solution réalisable et elle est marquée.
- On publie : la part d'images certifiées par le tri, la part passée au solveur, les tailles, le nombre de PLNE, leurs statuts, les bornes duales et les temps.

**Contrôle « même q, seuil ».** Les marginales sont `m_a = Σ_j q_j 1[a∈T_j]`, monotones le long des ancêtres. On émet `drop86(most_specific({a ∈ U \ N : m_a ≥ t}))`.

**Cas π₀ = 1.** Les poids valent `2·1[a∈T₀]/(k+|T₀|)`. Le tri donne T₀ pour k = |T₀|, avec U = 1, et ses maximaux sont les codes de B, déjà sans `86`. Le chemin rapide rend donc exactement B. Si T₀ est vide, tous les poids sont nuls et la comparaison au vide rend ∅, comme B.

## 5. Réglage, figé avant V-diagnostic

Ce réglage est inchangé.
- Grille sur V-réglage seulement : K ∈ {16, 32, 64}, τ ∈ {0,02 ; 0,05 ; 0,1}, η ∈ {0 ; 1 ; 2}, π₀ ∈ {0 ; 0,25 ; 0,5 ; 0,75}, soit 108 configurations.
- Critère : H-F1 moyen sur V-réglage. Égalités : K plus petit, puis τ plus grand, puis η plus petit, puis π₀ plus grand.
- Le contrôle seuil utilise **le q retenu pour A1**, avec son propre meilleur t ∈ {0,05 ; 0,10 ; … ; 0,95} sur V-réglage.
- Analyse secondaire, nommée : le contrôle seuil avec sa propre meilleure configuration q.
- La configuration retenue, ses SHA et les 108 scores sont scellés **avant** d'ouvrir V-diagnostic.

## 6. Étapes et règles de décision

**E0 — structure** (section 3). Arrêt si (c) ou (t) échoue.

**E1 — identité, avant toute mesure de qualité.**
- **(i)** Sur les 64 premières images de V-réglage, avec K = 4, τ = 0,05, η = 1 et π₀ = 0,25 (valeurs fixées ici), puis sur 16 images à K = 64 :
  - le tri égale un PLNE **fermeture seule** à 10⁻⁹ près, pour **chaque** k ;
  - le décodeur final égale un PLNE **contraint** résolu pour tous les k, sans élagage, à 10⁻⁹ près.
- **(ii)** Avec π₀ = 1, les ensembles émis égalent les ensembles projetés de B sur **4 241/4 241** images.
- **(iii)** Pour chaque image décodée, l'utilité recalculée sur **la fermeture de la sortie réellement émise** égale la valeur du décodeur à 10⁻⁹ près [P4].
- **(iv)** Chaque PLNE des sous-ensembles (i) est certifié optimal.

Un seul échec **réfute le logiciel** : aucune mesure de qualité n'est calculée, et la correction devient une nouvelle version relue.

Avant tout code, les tests synthétiques comprennent :
- des DAG aléatoires vérifiés par exhaustion, sur tous les cardinaux ;
- l'exemple de Codex à maximal interdit : cinq atomes équiprobables `{r, a_i, c_i}` avec r non émissible, où l'optimum fermé {r} vaut 0,5 et l'optimum émissible 0,4666666667.

**E2 — planche avant les chiffres.** 12 images de V-réglage, tirées par `default_rng(1029)` parmi les groupes. On y montre les codes de B, ceux d'A1 retenu et les utilités sous q. On regarde, on ne règle rien. Un changement motivé par ce regard est une nouvelle brique.

**E3 — qualité sur V-diagnostic, une seule ouverture.**

Bootstrap apparié par groupes md5, 10 000 tirages, intervalles percentiles à 95 %. Il **décrit l'incertitude d'échantillonnage d'une décision déterministe**. Il n'efface pas la variabilité de l'entraînement historique de B [P4]. Les cas sont évalués **dans cet ordre**, et le premier qui s'applique est retenu :

- **Mécanisme**, contraste A1 − (même q, seuil), point Δ, intervalle [L, H] :
  1. H < 0,003 → **réfuté dans ce régime** ;
  2. sinon, Δ ≥ 0,003 → **mécanisme utile** ;
  3. sinon → **indécidable**.
- **Produit (règle G)**, contraste A1 − B :
  1. ΔH-F1 ≥ +0,005 et ΔF1 exact ≥ −0,01 → **recette candidate** ;
  2. sinon → **non recommandée**.

  Le décodeur ne s'entraîne pas : les « trois graines » de G sont remplacées par le bootstrap, sans autre assouplissement.
- **Strate de forte proximité [P4].** C'est la strate « plus proche voisin cos ≥ 0,95 », contre les autres. On publie, pour les deux strates : nombre d'images, gains, pertes et contribution pondérée au gain A1 − B. Si une recette candidate tire plus de la moitié de son gain de cette strate alors qu'elle représente moins de 20 % des images, elle **n'est pas recommandée**. On ne dit **pas** pour autant que le gain est « dû à la recopie » : la proximité n'est pas une preuve de copie, et un gain peut être concentré pour d'autres raisons. Les copies ne sont pas vérifiées avec le test.
- Si le mécanisme passe mais pas G, la décision GFM est utile à q donné, mais ce q ne suffit pas à battre B. On ne la recommande pas pour la production.
- **Témoin du tri**, descriptif : on publie la part d'images où le chemin rapide n'est pas certifié et le H-F1 du témoin « tri non contraint ». Si les contraintes ne changent aucune décision, on le dit, et le solveur contraint n'est pas présenté comme la source d'un gain.

**Toujours publié** : H-F1, F1 exact, F1 dans les cinq tranches de fréquence, distribution de |S| et du nombre de codes émis, part d'images modifiées par rapport à B, part d'images certifiées par le tri, part passée au solveur, part non certifiée, latence du décodage seul sur un vCPU (P50, P95, P99). Si le P95 dépasse 20 ms, on ne dit pas que le coût de production est négligeable. Aucune voie « rares » n'est déclarée dans cette série.

## 7. Calcul, sorties, relectures

- **Calcul.** Kaggle **CPU** seulement, ≤ 2 h, créneau accordé par wA:p1, RAM ≤ 8 Go, sorties ≤ 1 Go dans `~/porkyevitch-donnees/maths/a1/`. Rien sur le Mac au-delà de la relecture des sorties.
- **Budget [P4].** Le budget de 2 h est **incertain** : 108 configurations × environ 2 100 images, |U|, k et passages au solveur. Le blanc mesure tous ces facteurs et extrapole le travail total. Si l'extrapolation dépasse le budget, on s'arrête et on amende avant le complet. **Aucun raccourci non exact** n'est introduit pour le sauver.
- **Blanc** (≤ 20 min CPU) : E0 complet ; E1-(i) sur 8 images ; E1-(ii) sur 64 images ; reproduction de B depuis le cache ; mesure des temps et extrapolation. Aucun score de V-diagnostic. Ses sorties sont relues avant le passage complet.
- **Sorties** : `structure.json`, `identite.json`, `reglage.json` (108 scores, configuration scellée), planche, `diagnostic.json`, `budget.json`, `RESULTAT.md`. Ni image ni corpus dans Git.
- **Relectures.** Le script est relu par Grok p2 puis Codex p4 avant le blanc, et les sorties du blanc sont relues avant le calcul complet. Un réglage choisi après un résultat devient une nouvelle brique nommée.

## 8. Ce qui change depuis la version 1

- Le sac à dos sur la forêt et l'énumération des composés sont retirés. Ils sont remplacés par le tri GFM avec départage topologique, exact sous la seule fermeture, et par un solveur contraint réservé aux maximaux non émissibles (`86`).
- La condition d'arrêt « forêt » est retirée ; restent la fermeture et la transitivité.
- Antériorité : GFM §7.1.1 et §7.2.1 utilisent déjà les voisins d'apprentissage.
- Ajouts : le témoin « tri non contraint », l'ordre explicite des cas de décision, la strate dite de forte proximité (pas de copie), les garanties de temps sans promesse générale, le traitement des vides, du clipping et du softmax, et la source float32 des probabilités de B.
- Inchangés : le partage, la grille, les seuils +0,003 et +0,005, E1-(ii) et E2.

## 9. Sources

- Waegeman et al., *On the Bayes-optimality of F-measure maximizers*, [arXiv:1310.4849](https://arxiv.org/html/1310.4849) : théorème 5.1, algorithme 1, équations 17–19, sections 7.1.1 et 7.2.1. Lu par Grok p7 et Codex p4.
- [arXiv:2410.01305v2](https://arxiv.org/abs/2410.01305), proposition 1, lue par Grok p7.
- Contre-expertise Codex p4, section A1 : preuve de fermeture du tri, contre-exemple à maximal interdit, vérification synthétique 700/700.
- Brouillon de Codex p6, proposition A (`docs/algos-production-brouillon-p6.md`), et rapport `docs/algos-production.md`, section 2.
