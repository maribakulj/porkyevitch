# A1 — Décodeur GFM restreint aux ensembles fermés : préinscription

Version 1, 29 octobre 2026. Claude wA:pH, remplaçant de Codex maths wA:p6. Document écrit **avant tout calcul** de cette méthode. Il intègre le challenge de Grok p7 (`~/Documents/reviews/porkyevitch-algos-production-grok.md`) et attend la contre-expertise de Codex p4, puis la relecture Grok p2 et l'audit Codex p4 du futur script. **Aucun calcul n'est autorisé par ce texte seul.**

Statut : série **exploratoire**. La validation ICAI a déjà été consultée en phase 1. Le nouveau partage ne la rend pas confirmatoire.

## 1. Ce qui est essayé, et ce qui n'est pas revendiqué

**Application nommée.** La règle de décision est le *General F-measure Maximizer* (GFM) de Waegeman, Dembczyński, Jachnik, Cheng et Hüllermeier ([arXiv:1310.4849](https://arxiv.org/abs/1310.4849), théorème 5.1, algorithme 1, équations 17–19). À cardinal k fixé, le poids d'un élément est `Δ_ak = Σ_s 2 P(a∈T, |T|=s) / (s+k)`. Quand prédiction et vérité sont fermées par ancêtres, le H-F1 par image est le F1 plat des vecteurs fermés (Kiritchenko et al. 2006, proposition 1 de [arXiv:2410.01305](https://arxiv.org/abs/2410.01305)). A1 applique donc GFM en **restreignant l'ensemble réalisable aux ensembles fermés** que la projection historique peut émettre.

**Revendication retirée.** A1 n'est pas « la règle de Bayes du H-F1 ». L'optimalité est **exacte pour la distribution q choisie** (section 4), pas pour la loi des données. Ce qui reste propre à A1, sans revendication d'invention :
- le pas interne n'est plus « les k plus grands Δ », mais un sac à dos sur la forêt du parseur, suivi d'une énumération des feuilles composées ;
- q est un mélange d'empreintes, qui contient le seuil historique comme cas particulier (π₀ = 1).

**Questions posées, dans l'ordre.**
1. Le logiciel est-il exact ? Il doit donner le même optimum qu'un PLNE de référence, et rendre exactement B quand π₀ = 1.
2. À q identique, la décision GFM fermée bat-elle le seuil sur les marginales de q (effet du mécanisme) ?
3. La recette bat-elle la référence B selon la règle G (utilité pour le produit) ?

## 2. Données et interdits

- Brillfull `davanstrien/iconclass-vlm-brillfull`, révision `8045366ff092a06e8e1c4e47f1eb43cb2a54d732` (CC0). Les onze fragments `train-*` de l'encodage C-RADIO v3, partage E3 inchangé : 81 951 lignes d'apprentissage, 4 265 de validation, 4 241 évaluables (vérité non vide après `drop86`). Mêmes contrôles d'empreintes et d'alignement que P9-A.
- **Validation ICAI seule pour toute mesure.** L'apprentissage ne sert qu'à fournir les atomes de q : vecteurs C-RADIO et codes des lignes d'apprentissage, comme la tête TK de la phase 1.
- Référence **B = T-Z** : époque 29, seuil 0,65, H-F1 de validation 0,5890847528448202, checkpoint `06e3de0fa7c2871f6ff132791aa7594ce22614a13dc5609cebf2c2a33019bcd6`, script E3 `b20b98f1…`. On utilise ses probabilités de validation et ses ensembles projetés historiques. Le script doit reproduire le H-F1 de B à 10⁻⁶ avant toute autre mesure. *Précision du 30/10 (audit Codex p4 du diagnostic, D2), sans changement de méthode :* les probabilités de B viennent du cache **float32** du diagnostic de la tête (`probabilites_validation.npz`, jamais une copie fp16), ou d'un recalcul float32 sous le même contrôle. La tolérance de 10⁻⁶ s'applique au H-F1 **reproduit par ce cache** (manifeste du diagnostic), avec en plus l'égalité exacte du SHA des décisions projetées. L'écart de ce recalcul CPU avec la valeur historique T4 (0,5890847528448202) est celui que publie le diagnostic, borné à 10⁻⁴ ; on ne promet pas 10⁻⁶ face à la valeur T4.
- Interdits : fragment `test-*` et tout fichier de test ICAI, sorties mixtes, `emb*`, banc Rijksmuseum (dev compris), test IconArt, Emblematica, ICARUS. Monter un dossier qui en contient ne donne pas le droit de les ouvrir.
- Parseur, `most_specific`, `drop86` et `hier_f1` : transcription exacte d'E3 (`e3_spatial.py:108-141`). La vérité d'une image est `drop86(Y)`, puis fermée par ancêtres dans `hier_f1`. Les vérités hors vocabulaire restent dans T.

**Partage de la validation.** Par groupes md5 : un groupe va en **V-réglage** si le premier octet de `sha256("A1-2026-10-29|" + md5)` est < 128, sinon en **V-diagnostic**. Ce sel est neuf : le partage de P9-A n'est pas réutilisé. Effectifs et absence de md5 commun publiés avant toute mesure.

## 3. Structure du parseur (étape 0, condition d'arrêt)

Lu dans le code : pour un code sans `:`, `ancestors` ajoute les préfixes de jetons (chiffre, lettres, `(...)`). Pour `A:B`, il ajoute les préfixes de chaque partie, puis le code entier. Le script vérifie, sur V (7 907 codes) et sur toutes les empreintes d'apprentissage :

- **(a) forêt** : pour tout code simple c, les ancêtres propres de c forment une **chaîne** (ordonnés par inclusion de leurs propres ancêtres) ;
- **(b) feuilles composées** : aucun code contenant `:` n'est l'ancêtre propre d'un autre code ;
- **(c) fermeture** : V est fermé par ancêtres.

Un échec de (a), (b) ou (c) **arrête la série** et appelle un amendement : le temps polynomial et l'algorithme tombent avec eux. On publie aussi, pour chaque K de la grille, la distribution du nombre c de composés candidats par image.

## 4. Modèle q et décodeur

**Atomes.** T_j est l'empreinte (fermeture de `drop86(Y_j)`) de la ligne d'apprentissage j. T₀ est la fermeture de l'ensemble projeté de B pour l'image. Les voisins sont les K plus proches lignes d'apprentissage par produit scalaire des vecteurs C-RADIO normalisés (même vecteur que TK).

**Poids.** `π_j ∝ exp(cos_j/τ + η · moyenne_{a ∈ T_j ∩ V} logit p_a^B)`. On fait la moyenne et non la somme, pour ne pas favoriser les grandes empreintes. Les atomes d'empreinte identique sont fusionnés, ce qui est exact. Mélange final : `q = π₀ δ_{T₀} + (1 − π₀) Σ_j π_j δ_{T_j}`.

**Ensemble réalisable.** On note V⁺ = V privé des codes commençant par `86`. S est fermé par ancêtres, inclus dans `U = (T₀ ∪ ⋃_j T_j) ∩ V`, et ses éléments maximaux sont dans V⁺. Un nœud `86` n'entre dans S que comme ancêtre d'un composé retenu. Le code émis est `P = maximaux(S)`, si bien que `most_specific(P) = P`, puis `drop86`, comme la projection historique.

**Utilité.** `U(S) = Σ_{a∈S} w_a(|S|)`, avec `w_a(k) = Σ_j q_j · 2 · 1[a ∈ T_j] / (k + |T_j|)`. Un atome vide contribue 0. U(∅) = 0.

**Décodeur.** Pour chaque k = 1…|U| :
1. sac à dos sur la forêt des codes simples (fusion des enfants par convolution max-plus, tableaux bornés à min(taille, k)) ;
2. pour chaque sous-ensemble des c composés candidats, on force leurs ancêtres et on ajoute leurs poids ;
3. on prend le maximum sur k.

Si c > 8, l'image passe au PLNE de référence (repli exact), et la part d'images concernées est publiée.

**Égalités** : on choisit le plus petit |S|, puis l'ordre Unicode des éléments triés. Avec π₀ = 1 et T₀ non vide, l'optimum unique est T₀ (utilité 1). Avec T₀ vide, la règle d'égalité donne l'ensemble vide, comme B.

**Contrôle « même q, seuil ».** Marginales `m_a = Σ_j q_j 1[a∈T_j]`, monotones le long des ancêtres puisque les atomes sont fermés. On émet `most_specific({a ∈ V⁺ ∩ U : m_a ≥ t})`, puis `drop86`.

## 5. Réglage, figé avant V-diagnostic

Grille sur V-réglage seulement : K ∈ {16, 32, 64}, τ ∈ {0,02 ; 0,05 ; 0,1}, η ∈ {0 ; 1 ; 2}, π₀ ∈ {0 ; 0,25 ; 0,5 ; 0,75}, soit 108 configurations. Critère : H-F1 moyen sur V-réglage. En cas d'égalité : K plus petit, puis τ plus grand, puis η plus petit, puis π₀ plus grand. Le contrôle seuil utilise **le q retenu pour A1** et son propre meilleur t ∈ {0,05 ; 0,10 ; … ; 0,95} sur V-réglage. Analyse secondaire, nommée : le contrôle seuil avec sa propre meilleure configuration q. La configuration retenue, ses SHA et les 108 scores de V-réglage sont scellés **avant** d'ouvrir V-diagnostic.

## 6. Étapes et règles de décision

**E0 — structure** (section 3). Arrêt si (a), (b) ou (c) échoue.

**E1 — identité, avant toute mesure de qualité.**
- (i) Sur 64 images de V-réglage (les 64 premières dans l'ordre canonique), avec U restreint à T₀ et aux 4 premiers voisins (K = 4, τ = 0,05, η = 1, π₀ = 0,25, valeurs fixées ici) : la valeur optimale du décodeur et celle d'un **PLNE de référence** (scipy `milp`/HiGHS, un problème par k, contraintes de fermeture, de composés et de maximaux émissibles) diffèrent d'au plus 10⁻⁹ sur les 64 images. Même contrôle sur 16 images à K = 64.
- (ii) π₀ = 1 : les ensembles émis égalent les ensembles projetés de B sur **4 241/4 241** images évaluables.
- (iii) Pour chaque image décodée, l'utilité recalculée directement sur l'ensemble émis égale la valeur du décodeur à 10⁻⁹ près.

Un seul échec **réfute le logiciel** : aucune mesure de qualité n'est calculée, et la correction devient une nouvelle version relue.

**E2 — planche avant les chiffres.** 12 images de V-réglage, tirées par `default_rng(1029)` parmi les groupes : codes de B, codes d'A1 retenu, utilités sous q. On regarde, on ne règle rien. Un changement motivé par ce regard est une nouvelle brique.

**E3 — qualité sur V-diagnostic, une seule ouverture.** Bootstrap apparié par groupes md5, 10 000 tirages, descriptif.
- **Mécanisme (contraste principal)** : A1 − (même q, seuil). Mécanisme utile si ΔH-F1 ≥ **+0,003**. **Réfuté dans ce régime** si la borne supérieure à 95 % est < 0,003. Indécidable sinon.
- **Produit (règle G)** : A1 − B. Recette recommandée seulement si ΔH-F1 ≥ **+0,005** et ΔF1 exact ≥ **−0,01**. Le décodeur est déterministe et ne s'entraîne pas : les « trois graines » de G sont remplacées par le bootstrap, sans autre assouplissement.
- Si le mécanisme passe mais pas G, la décision GFM fermée est utile à q donné, mais ce q ne suffit pas à battre B. On ne la recommande pas pour la production.
- **Copie de voisins (objection Grok)**, déclarée maintenant : strate « plus proche voisin cos ≥ 0,95 » contre les autres. Si plus de la moitié du gain A1 − B vient de cette strate alors qu'elle représente moins de 20 % des images, le gain est déclaré **dû à la recopie d'empreintes**, et la recette n'est pas recommandée.

**Toujours publié** : H-F1, F1 exact, F1 dans les cinq tranches de fréquence, distribution de |S| et du nombre de codes émis, part d'images modifiées par rapport à B, part de replis PLNE, latence du décodage seul sur un vCPU (P50, P95, P99). Si le P95 dépasse 20 ms, on ne dit pas que le coût de production est négligeable. Aucune voie « rares » n'est déclarée dans cette série.

## 7. Calcul, sorties, relectures

- Kaggle **CPU** seulement, ≤ 2 h, créneau accordé par wA:p1, RAM ≤ 8 Go, sorties ≤ 1 Go dans `~/porkyevitch-donnees/maths/a1/` après rapatriement. Rien sur le Mac au-delà de la relecture des sorties. Ordre de grandeur : kNN de 4 265 requêtes contre 81 951 vecteurs 4 096 (≈ 1,4 × 10¹² multiplications-additions), grille de 108 configurations sur environ 2 100 images. Ce sont des estimations ; le blanc les remplacera par des mesures.
- **Blanc** (≤ 20 min CPU) : E0 complet, E1-(i) sur 8 images, E1-(ii) sur 64 images, reproduction de B. Aucun score de V-diagnostic. Sorties relues avant le passage complet.
- Sorties : `structure.json`, `identite.json`, `reglage.json` (108 scores, configuration scellée), planche, `diagnostic.json`, `budget.json`, `RESULTAT.md`. Ni image ni corpus dans Git.
- Script relu par Grok p2 puis Codex p4 avant le blanc ; sorties du blanc relues avant le calcul complet. Un réglage choisi après un résultat devient une nouvelle brique nommée.

## 8. Sources

- Waegeman et al., *On the Bayes-optimality of F-measure maximizers*, [arXiv:1310.4849v3](https://arxiv.org/abs/1310.4849), théorème 5.1, algorithme 1, équations 17–19, lus par Grok p7.
- [arXiv:2410.01305v2](https://arxiv.org/abs/2410.01305), proposition 1 (hF1 = F1 sur prédictions cohérentes) et contre-exemple au seuil, lus par Grok p7.
- Bi et Kwok, IEEE TKDE 2015, et ICDM 2012 : pertes de Hamming, de rang et HMC, pas le H-F1 (lecture Grok p7).
- Brouillon de Codex p6, proposition A (`docs/algos-production-brouillon-p6.md`), et rapport `docs/algos-production.md`, section 2.
- Johnson et Niemi 1983 (sac à dos sur arbre) : non vérifié par Grok. L'algorithme est décrit ici en entier et ne dépend pas de cette référence.
