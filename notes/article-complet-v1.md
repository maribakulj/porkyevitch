# Recettes exploratoires sur encodeur gelé pour l'Iconclass : un accord de catalogue sur ICAI, aucune brique retenue sur un banc du Rijksmuseum gelé, et des diagnostics

Article complet v1, privé, 30 octobre 2026. Assemblé par `notes/assemble_article.py` à partir de `article-intro-discussion-v3.md`, `article-methodes-v5.md`, `article-resultats-v3.md`, `article-references-v1.md` et des tableaux de `notes/figures/`, sans changement de fond.

## Résumé (208 mots)

Sur des traits gelés d'un encodeur visuel général (C-RADIOv3-L), une recette de tête peut-elle améliorer l'accord entre des notations Iconclass prédites et le catalogue, à la fois sur le test ICAI et sur un banc extérieur du Rijksmuseum ? La série est exploratoire ; relectures et jugements sont faits par des modèles, sans regard humain. En phase 1, une famille de sept comparaisons et une règle de retenue conjointe sont écrites avant la mesure, et les prédictions sont gelées avant l'ouverture des scores. Aucune brique n'est retenue : deux recettes améliorent l'accord ICAI, mais leurs intervalles sur le Rijksmuseum contiennent zéro. En phase 2, sur la validation, une décision par maximisation du F1 sous une loi tirée des voisins bat la référence, surtout grâce à cette loi. Sa règle la plus simple, figée et mesurée une fois sur le dev du Rijksmuseum, n'établit pas de transfert, sur un banc filtré, aux seuils préinscrits, contre les images proches de l'apprentissage. Deux sondes sur la traîne et la profondeur, des champs de preuve hiérarchiques et un prototype de distillation de graphes de scène sont négatifs. Des diagnostics descriptifs décrivent l'écart entre banques sans en établir la cause. Le F1 mesure ici un accord avec un catalogue, pas une justesse visuelle.

## 1. Introduction

**Le problème.** Iconclass décrit le contenu des images par une notation hiérarchique de dizaines de milliers de codes. Les catalogues l'emploient pour dire ce qu'une œuvre représente : personnages, scènes, objets, attributs. Prédire ces notations à partir de l'image seule pourrait un jour aider l'indexation des collections. Cet article ne propose pas un tel système : il mesure si des recettes simples, sur un encodeur gelé, améliorent l'accord avec un catalogue, et sur quel banc. Le vocabulaire étudié est réduit aux 7 907 codes vus au moins cinq fois en apprentissage, avec leurs ancêtres (Méthodes §2).

Trois traits rendent la tâche difficile et sa mesure délicate :
- **la hiérarchie** : un code plus précis implique ses ancêtres ;
- **la longue traîne** : la plupart des codes sont rares ;
- **le catalogue incomplet** : une notation absente de la notice n'est pas une notation fausse.

Un F1 calculé contre le catalogue mesure donc un **accord avec le catalogue**, pas une justesse visuelle.

**Ce qui existe.** Les travaux dont le texte a été ouvert traitent des tâches voisines, avec d'autres métriques. Leurs chiffres ne se convertissent pas en F1 hiérarchique d'image :
- **Springstein et al. (2024)** classent à grande échelle des concepts Iconclass, après un pré-apprentissage image–texte, et mesurent un mAP par concept ;
- **Banar, Daelemans et Kestemont (2021)** apparient des œuvres à des définitions de codes. L'image seule y reste loin du texte ;
- **Cetinic (2021)** produit des légendes iconographiques ;
- **ArtDL (Milani et Fraternali, 2021), IconArt (Gonthier et al., 2018) et DEArt (Reshetnikov et al., 2022)** détectent ou classent quelques motifs ou classes sur la peinture.

Parmi les travaux cités, aucun protocole ne mesure un F1 hiérarchique d'accord avec un catalogue sur une famille de comparaisons préinscrite, avec un second banc tenu hors des choix. Cela ne prouve pas qu'aucun travail analogue n'existe.

Sur les étiquettes manquantes, la littérature distingue plusieurs régimes :
- l'apprentissage positif–non étiqueté (Bekker et Davis, 2020) ;
- l'apprentissage à une seule positive (Cole et al., 2021 ; Zhou et al., 2022) ;
- les pertes qui tolèrent les faux négatifs (Hill et SPLC, Zhang et al., 2021) ;
- l'évaluation sous propension (Schultheis et al., 2022) et l'audit des étiquettes d'un test (Northcutt et al., 2021).

Elle montre qu'une correction des scores par un taux d'oubli unique n'est pas identifiée quand la propension d'oubli dépend du contenu.

**La question.** Sur des traits gelés d'un encodeur visuel général (C-RADIOv3-L), avec une famille de comparaisons et une règle de retenue écrites avant la mesure, une recette de tête améliore-t-elle l'accord hiérarchique avec le catalogue **à la fois** sur le test ICAI et sur un banc extérieur du Rijksmuseum ? Si non, que peut-on dire de l'échec, sans rouvrir les tests ?

**Ce que nous apportons**, en restant à la mesure de ce qui a été fait :
1. **Un protocole exploratoire et un artefact scellés.** Une famille de sept comparaisons est fixée d'avance. La règle de retenue est conjointe : une borne unilatérale sur le Rijksmuseum, et une non-infériorité sur ICAI. Le bootstrap est apparié, par image pour ICAI et par composante pour le Rijksmuseum. Les prédictions sont gelées avant l'ouverture des scores. Toutes les relectures et tous les audits sont faits par des modèles, et sont déclarés comme tels.
2. **Un banc du Rijksmuseum gelé.** 1 201 images en 908 composantes de dépendance, plus un dev de 301 images. Le banc n'a jamais servi à choisir une tête. Il est filtré contre l'apprentissage : toute composante qui contient une image proche d'une image de référence (dHash < 50 bits ou cosinus C-RADIO ≥ 0,95) est retirée en entier. Ce filtre définit ce que le banc mesure : l'accord **sur un banc filtré aux seuils préinscrits**, pas le musée tel qu'il se présente. Il ne garantit pas l'absence de toute copie.
3. **Des résultats négatifs propres.** Aucune brique n'est retenue en phase 1. En phase 2, trois sondes sur la validation ont été préinscrites puis mesurées :
   - A1, la décision par maximisation du F1 sous une loi de voisins, bat la référence sur la validation ; son gain tient surtout à la loi tirée des voisins ;
   - sa règle la plus simple, figée et mesurée une fois sur le dev du Rijksmuseum, n'établit pas de transfert ;
   - D3, deux sondes sur la traîne et la profondeur, et P9-A, les champs de preuve hiérarchiques, ne sont pas retenus.

   Un prototype de distillation de graphes de scène ne passe pas sa porte (« pas de signal »).
4. **Des diagnostics qui localisent sans conclure.**
   - Sur la validation : traîne, profondeur, corrélation des erreurs.
   - Un audit des prédictions sûres absentes du catalogue, par des juges-modèles (deux regards d'accord sur 53 couples sur 100, puis un arbitre) : O 29, A 46, E 25. Ce n'est pas un score.
   - Un diagnostic descriptif du non-transfert : les voisins d'apprentissage portent souvent les codes fréquents et profonds que la tête ne rend pas, sur les deux banques.

Ce que nous n'apportons pas : ni système d'indexation, ni méthode retenue, ni gain démontré sur un musée, ni cause établie du non-transfert, ni regard humain. Toutes les séries sont exploratoires.

**Plan.** La section Méthodes décrit les données, la représentation, la mesure, les protocoles des deux phases, les incidents et la relecture. Les Résultats suivent l'ordre des décisions : la phase 1, puis le diagnostic de validation, le non-transfert, A1 et A1-dev, D3, P9-A et le petit élève. La Discussion dit ce que ces résultats permettent de dire et ce qu'ils interdisent.

---

## 2. Méthodes

Ce texte décrit des **méthodes**. Les chiffres de résultats sont dans `article-resultats-v3.md`. Les sources sont les préinscriptions, sous `~/porkyevitch/experiences/` et `~/porkyevitch-maths/experiences/`, et les décisions de `~/porkyevitch/DECISIONS.md`, désignées par leur numéro. Les points à vérifier ou à trancher sont marqués [à vérifier].

### 0. Qui fait quoi : des modèles, pas des experts humains

Toutes les relectures, tous les regards sur images et tous les audits de cette étude sont faits par des **modèles de langage multimodaux**. Aucun n'est une annotation experte, et aucun n'est présenté comme tel. Aucun historien de l'art n'a annoté ni vérifié les images. Les versions et réglages des juges sont déclarés par l'orchestrateur ; leur provenance n'est pas encore archivée de façon immuable dans les pièces de l'article. Les juges ne sont ni experts, ni indépendants au sens statistique. Les rôles ont changé le 30/10 (D13, section 9) :

| Rôle | Modèle |
|---|---|
| Orchestration, décisions de protocole, premier regard sur les planches et sur l'audit | Claude Opus 5.5 (Anthropic) |
| Conception mathématique, préinscriptions et code des méthodes de la phase 2 | Claude Opus 5.5 (Anthropic) ; d'abord Codex (OpenAI), pour les premiers jets |
| Relecture des préinscriptions et du code, second regard, **jusqu'à D13** | Grok 4.7 (xAI), effort *xhigh* |
| Relectures du code, des diffs et des sorties, regards de planches, **depuis D13** | sous-agents Claude Sonnet (Anthropic), indépendants, lancés par l'orchestrateur : Claude Sonnet 5.5 (claude-sonnet-5-5), lancés par wA:p1 (Claude Opus 5.5) via l'outil Agent |
| Challenger des décisions, littérature, regards ponctuels, **depuis D13** | Grok 4.7 (xAI) |
| Audit final du code avant lancement et contre-expertise des décisions | Codex GPT-6.1-Sol (OpenAI), effort *high* ; en son absence, un second sous-agent Sonnet indépendant (D12, D13), puis contre-vérification par Codex |
| Troisième regard, à l'aveugle, sur les désaccords de l'audit | Gemini 3.8 Flash (Google), réglage *medium*, via `agy` |
| Professeurs des graphes de scène | Gemini 3.8 Flash (réglage *medium*, pilote) ; Claude Haiku 5.5 (consigne S1b) |

Versions relevées dans les panneaux le 30/10/2026. Le rédacteur de ce texte est Claude Opus 5.5. Ces modèles ont des biais propres et peuvent se tromper ensemble. Un accord entre deux modèles n'a donc pas la valeur d'un accord entre deux experts. Les catalogues (ICAI, Rijksmuseum) restent la seule source humaine des vérités.

### 1. Données

**ICAI.** Nous utilisons le jeu `iconclass-vlm-brillfull` (davanstrien, Hugging Face), dérivé de l'Iconclass AI Test Set (Posthumus, 2020) (révision `8045366` ; la fiche du jeu déclare CC0, déclaration de source et non vérification juridique) : des images de reproductions d'œuvres, chacune annotée par des notations Iconclass venant de son catalogue.
- **Apprentissage et validation.** L'apprentissage compte 86 216 images. 5 % de groupes d'images identiques à l'octet (même md5) en sont tirés pour la validation, avec une graine fixe. On obtient 81 951 images d'apprentissage et 4 265 de validation, dont 4 241 gardent une vérité non vide après la projection décrite en section 3.
- **Test.** Le test ICAI compte 788 images. Il **avait déjà été consulté avant cette série** (préinscription d'architecture), ce qui lui retire toute portée confirmatoire. Dans cette série, ses agrégats sont restés fermés jusqu'au gel des prédictions et au reçu des regards, puis il a été ouvert une fois pour les verdicts de la phase 1. Il n'est plus lu en phase 2.

**Banc du Rijksmuseum.** C'est un banc extérieur construit pour cette série, à partir des données ouvertes du Rijksmuseum (Rijksmuseum Data Services). Ses images et ses scores de test n'ont été ouverts qu'après le gel des prédictions de la phase 1. Seule la réserve d'audit, tirée à part, a été regardée avant le tirage, pour auditer les filtres (préinscription du banc, chronologie).
- **Notices.** La source déclare les métadonnées sous CC0 et marque les reproductions retenues comme domaine public. C'est une déclaration de source vérifiée pour les objets sélectionnés, pas une expertise juridique.
- **Tirage.** 3 000 identifiants ont été tirés par type de support (peinture, estampe, dessin). On n'a gardé que les objets éligibles : droits vérifiés, image alignable avec ses codes, et vérité non vide après projection.
- **Composantes de dépendance.** Les objets liés sont réunis en composantes connexes. Les liens viennent des métadonnées : même série, même attribution, même source, etc. Ils viennent aussi des copies internes. Une composante n'est jamais scindée : le filtre retire tous ses membres. Le plafond de 20 objets par composante s'applique au nombre d'images retenues au tirage ; les comptes de retrait portent sur tous les membres, ce qui explique 5 912 objets pour 84 composantes.
- **Filtrage contre les données d'apprentissage.** Toute composante qui contient une image proche d'une image de référence est retirée en entier. Une image est proche si sa distance de hachage perceptuel est inférieure à 50 bits, ou si son cosinus C-RADIO est ≥ 0,95. La référence compte 87 004 images : les 86 216 du fragment d'apprentissage source, avant le partage interne, et les 788 du test ICAI. Ces seuils ont été audités sur la réserve avant le tirage. Le filtre **combiné** (dHash < 50 bits **ou** cosinus ≥ 0,95), propagé à la composante entière, retire **84 composantes hors réserve, soit 5 912 objets avant plafonnement** (`2026-10-25-banc-rijksmuseum/gel/resume_gel.json`, `75f9c2a0`, champs `feasibility`). Les sources ne décomposent pas ce compte entre les deux critères. Le filtre retire ce que ses seuils détectent ; il ne garantit pas l'absence de toute copie.
- **Répartition.** Une réserve d'audit prend 10 % des composantes, arrondi supérieur (142 sur 1 417). Le reste est permuté par une graine fixe et versé, composante par composante, d'abord au test, puis au dev.
- **Effectifs.** Le test compte **1 201 images** en **908 composantes** (402 peintures, 462 estampes, 337 dessins). Le dev compte **301 images** en **239 composantes**. Le dev a servi aux planches de la phase 1, puis, en phase 2, au diagnostic de non-transfert (D10) et à la mesure unique d'A1-dev (D17). Le test Rijksmuseum, ouvert une fois pour les verdicts de la phase 1, n'est plus lu.

**Vérité du Rijksmuseum.** Ce sont les notations Iconclass des notices, dédoublonnées. Un code absent de la notice compte comme négatif, alors qu'il peut être vrai. C'est une limite commune aux deux bancs, discutée en section 5.

### 2. Représentation et têtes

Toutes les têtes reposent sur un même encodeur figé, **C-RADIOv3-L** (révision épinglée ; NVIDIA, fiche de modèle ; famille RADIO, Ranzinger et al., 2024). Le prétraitement est le suivant : image remise dans un carré gris, 448 px, interpolation bicubique, calcul en fp16. On en tire deux sorties :
- un **vecteur** de 4 096 dimensions (jeton de synthèse et moyenne spatiale, chacun normalisé, puis normalisation L2 de la concaténation) ;
- une **grille** de 8 × 8 zones de 1 024 dimensions (moyenne adaptative des 28 × 28 jetons).

Le vocabulaire **V** compte 7 907 codes : les codes vus au moins 5 fois en apprentissage, avec tous leurs ancêtres.

La référence initiale **T0** est un perceptron à deux couches sur le vecteur, entraîné avec une perte asymétrique (ASL, Ben-Baruch et al., 2021). Les essais de la phase 1 sont six briques, qui donnent sept comparaisons avec T\* contre T0 ; TK-niv est conditionnelle :
- un vote des 20 voisins d'apprentissage (TK) ;
- des seuils par profondeur (T-niv) ;
- leur combinaison (TK-niv) ;
- la cohérence parent–enfant de C-HMCNN (Giunchiglia et Lukasiewicz, 2020), réentraînée (T-H) ;
- deux recettes spatiales sur la grille : une mise en commun apprise (T-Z) et ML-Decoder (Ridnik et al., 2021) (T-D).

Tous les réglages (époque, seuil, poids du vote) sont choisis sur la validation ICAI seule.

### 3. Mesure

**Hiérarchie.** Elle est lue directement dans la notation : les ancêtres d'un code sont ses préfixes de jetons (chiffres, lettres, parenthèses), partie par partie pour un code composé. Ce n'est pas l'arbre officiel d'Iconclass. Une comparaison avec cet arbre n'est pas reprise dans cet article.

**Projection.** Le chapitre 86 (proverbes et locutions) est retiré de la vérité comme des prédictions. Une image dont la vérité projetée est vide est exclue du dénominateur. Il en reste 787 sur 788 au test ICAI, 4 241 sur 4 265 en validation, et toutes au test du Rijksmuseum, où c'est un critère d'éligibilité.

**Mesure principale : le F1 hiérarchique (H-F1).** Pour une image, c'est le F1 entre la fermeture par ancêtres de la vérité et celle de la prédiction. Le H-F1 rapporté est la moyenne de ce F1 sur les images. La prédiction s'obtient par un seuil, puis par la suppression des ancêtres déjà impliqués, puis par la projection.

**Mesures secondaires de la phase 1**, toutes descriptives (en phase 2, F_R sert en revanche de juge à la voie R de D3 et de P9-A) :
- le F1 des codes exacts ;
- le F1 par tranche de profondeur (1–2, 3–4, 5 et plus) ;
- le F1 par fréquence d'apprentissage du code (5–20, 21–100, plus de 100) ;
- le rappel des codes rares ;
- la part des vérités hors du vocabulaire, que toute tête à vocabulaire fixe ne peut pas prédire.

### 4. Protocole de la phase 1

**Préinscription.** Les règles ont été écrites et relues avant tout calcul, puis amendées avant le premier calcul concerné, chaque fois avec date et motif :
- la famille de comparaisons ;
- le juge extérieur ;
- la projection ;
- les seuils de décision ;
- l'ordre d'ouverture.

Chaque script, essai à blanc compris, a été relu avant d'être lancé : par Grok, puis audité par Codex (section 0). Ces relectures sont faites par des modèles : elles cherchent des erreurs de logique et de code, sans valoir une revue par des pairs.

**Référence.** T\* est choisie sur la validation seule, parmi T0, T0 au seuil élargi et T0 entraînée plus longtemps (30 époques). Ce choix compte comme l'une des comparaisons de la famille.

**Famille de sept comparaisons**, fixée d'avance : T\* − T0, TK, T-niv, TK-niv, T-H, T-Z et T-D, ces six dernières contre T\*. TK-niv n'est exécutée que si TK et T-niv sont toutes deux retenues, mais elle garde sa place dans la famille.

**Règle de retenue.** Une brique est retenue si deux conditions sont réunies :
- la borne inférieure unilatérale de Δ_Rijks est > 0 ;
- celle de Δ_ICAI est > −0,01 (non-infériorité).

Les deux bornes sont prises au niveau 1 − 0,05/7 ≈ 99,29 % (correction de Bonferroni sur la famille). Elles viennent d'un bootstrap (Efron et Tibshirani) de 10 000 tirages, apparié entre systèmes. Au Rijksmuseum, on tire des composantes entières, et la moyenne est recalculée sur les images des composantes tirées ; à ICAI, on tire des images. Les intervalles bilatéraux à 95 % sont publiés à titre descriptif.

**Gel avant mesure.**
- Les prédictions des huit systèmes sur les trois bancs (test ICAI, dev et test du Rijksmuseum) ont été produites puis **scellées**. Ce sont 24 fichiers, avec un manifeste et leurs empreintes.
- Pour chaque comparaison, une **planche de 12 images du dev** montre la vérité et les deux prédictions. Ce sont les images où l'écart de H-F1 est le plus grand.
- Ces planches ont été regardées par **deux regards de modèles**, Claude (orchestration) puis Grok, consignés dans un reçu, **avant** l'ouverture d'un seul score de test. Ces regards vérifient le matériau et les prédictions affichées ; ce ne sont pas des jugements d'experts. Le code de mesure refuse d'ouvrir les tests sans ce reçu, lié aux planches par empreinte.

L'ordre d'ouverture est écrit : vérités ICAI, vérités du Rijksmuseum, comparaisons dans l'ordre de la famille, TK-niv seulement si sa condition est remplie, puis les verdicts, et enfin les mesures descriptives.

**Statut.** La série est **exploratoire** :
- une seule graine par brique ;
- le test ICAI avait déjà été consulté au moment de la préinscription, ce qui le rend non confirmatoire ;
- le choix est fait sur une validation consultée plusieurs fois.

Une conclusion confirmatoire demanderait un nouveau banc jamais consulté.

### 5. Diagnostic sur la validation

Le diagnostic est purement descriptif. Il a été préinscrit, et il porte sur la seule validation ICAI, pour la meilleure référence de validation B (T-Z) et pour T\*.

- **Longue traîne.** Le macro-F1 des 4 073 codes vus 5 à 20 fois à l'apprentissage vaut 0,07 pour B. Il monte à 0,20 sur les seuls codes présents en validation. Sous 5 exemples, le F1 est pratiquement nul.
- **Profondeur.** Le rappel des nœuds de la vérité passe de 0,86 en profondeur 1 à 0,38 en profondeur 6, pendant que la précision baisse moins, de 0,74 à 0,64. Fréquence et profondeur restent confondues tant qu'elles ne sont pas croisées.
- **Seuils par tranche.** Un seuil par tranche de fréquence, ajusté sur la validation elle-même par montée coordonnée, ne gagne que +0,0013. C'est un score ajusté, optimiste : ce n'est ni une borne supérieure, ni une recette.
- **Erreurs corrélées.** Les erreurs de T\* et de B sont fortement corrélées (Pearson du H-F1 par image : 0,82). Cela ne mesure pas l'information absente des traits.
- **Audit des « confiants absents ».** On a tiré au hasard, avec une graine fixe, 100 couples (image, code) parmi les codes les plus spécifiques que B prédit avec une probabilité ≥ 0,9 et que la vérité fermée ne contient pas, au plus deux par image (95 images). Ce ne sont pas nécessairement les codes émis au seuil de production 0,65, et ce n'est pas un échantillon de toutes les erreurs du système. Les juges les ont classés en trois catégories :
  - **O**, motif jugé visible et code précis (oubli possible du catalogueur) ;
  - **A**, motif jugé visible, code générique ;
  - **E**, motif jugé absent ou sens jugé faux.

  Deux regards indépendants ont été faits, par Claude et par Grok. Ils s'accordent sur 53 couples sur 100. Les 47 désaccords ont été arbitrés à l'aveugle par Gemini, avec une règle écrite après les deux premiers regards et leurs désaccords, mais avant le troisième, par le juge le plus strict ; un contrôle a confirmé que les 47 images avaient bien été ouvertes. Comptes arbitrés : **O 29, A 46, E 25**. Les juges-modèles ont classé 75 de ces 100 couples en O ou A, selon cette règle. Ce n'est **ni une vérité ni une borne du F1** : l'échantillon est conditionné aux sorties sûres absentes, les vrais positifs ni prédits ni catalogués ne sont pas mesurés, et aucun taux d'oubli global ni sens du biais du F1 n'en découle. L'audit n'est pas un score : la règle penche vers le juge le plus strict, et une mesure corrigée demanderait une règle et un taux d'oubli établis d'avance.
- **Conséquence pour la lecture des scores.** Les F1 mesurent un accord avec le catalogue, pas la justesse visuelle. Un oubli du catalogueur est compté comme un faux positif.

### 6. Méthodes de la phase 2, exécutées

Toutes ces séries sont **exploratoires**. Elles portent sur la validation ICAI, déjà consultée en phase 1, ou sur le dev Rijksmuseum, déjà ouvert pour les planches. Chacune a une préinscription, un code relu puis audité, et une lecture écrite d'avance (`LECTURE.md`). Chacune a aussi un essai à blanc technique, sauf A1-dev, dont les tests et les contrôles d'identité sont faits dans la mesure unique. **Aucune ligne de test n'est lue.** La référence de comparaison interne est B = T-Z, sauf mention contraire. La référence publiée reste T\* (D10).

**A1, décision par maximisation du F1 sous une loi de voisins** (`2026-10-29-a1`, préinscription v2).
- *Loi q* : les atomes sont les étiquettes fermées des K voisins d'apprentissage (cosinus des vecteurs C-RADIO), pondérés par `exp(cos/τ + η·ℓ̄)`, où ℓ̄ est la moyenne des logits de B sur l'atome. On y mêle l'atome B avec le poids π₀.
- *Décodeur* : le tri du *General F-measure Maximizer* (GFM ; Waegeman et al., 2014), départagé par la profondeur, donne l'ensemble fermé optimal. Un programme linéaire en nombres entiers (HiGHS ; Huangfu et Hall, 2018) ne sert qu'aux maximaux non émissibles. Les défauts de HiGHS sont contournés : prétraitement coupé et objectif mis à l'échelle (section 8).
- *Réglage* : une grille de 108 configurations (K, τ, η, π₀) est essayée sur V-réglage, la moitié de la validation tirée par md5. Le choix est scellé (`reglage.json`) avant toute ouverture de V-diagnostic.
- *Contrôle « même q, seuil »* : sur la **même** loi q qu'A1 (configuration choisie : K = 16, τ = 0,02, η = 0, π₀ = 0,25), on émet les codes de marginale `m_a ≥ t`, avec t choisi sur V-réglage (t = 0,3). Cela sépare l'apport de q de celui du décodeur ; la lecture préinscrite du mécanisme compare A1 à ce contrôle.
- *Contrôle « q propre, seuil »* (analyse secondaire) : un seuil sur une configuration de q réglée séparément sur V-réglage (η = 1, t = 0,3). C'est cette règle, figée, que mesure A1-dev.
- *Diagnostic* : une seule ouverture de V-diagnostic, après le regard de la planche de réglage et un reçu à deux regards. Le budget total de la série est de 2 h CPU (préinscription A1).

**A1-dev, le seuil figé sur q, une mesure sur le dev Rijksmuseum** (`2026-10-30-a1-dev-rijks`, D17). Préinscrite, codée, relue, puis **mesurée une fois** ; le résultat est dans Résultats v3 §4 bis.
- *Règle* : la recette secondaire scellée au réglage, sans aucun réajustement : K = 16, τ = 0,02, η = 1, π₀ = 0,25, t = 0,3. Le choix est **adaptatif**, et déclaré comme tel.
- *Mesure* : le H-F1 sur les 301 images et 239 composantes du dev, contre B (principal) et T\* (référence figée).
- *Lecture* : bootstrap de composantes. « Signal exploratoire de transfert » seulement si Δ > 0 et la borne basse est > 0, strictement. Sinon, transfert non établi.
- *Garde* : cinq contrôles d'identité avant toute mesure. Il s'agit de reproduire la valeur de validation, les prédictions scellées de T-Z et de T\*, et B quand π₀ = 1.

**D3, deux sondes sur traits gelés** (`2026-10-30-d3-traine-profondeur`).
1. *Vote des 20 voisins limité aux codes rares* (5–20 exemples), avec un poids fixe de 0,25, mélangé à B. Il est jugé par la règle G puis par la voie R, à côté d'un témoin à mémoire permutée. Les décisions au seuil se lisent sur le vote effectif.
2. *Tête linéaire des enfants*, routée par le parent qu'atteint la fermeture des prédictions de B, sur 3 graines. La règle cherchait un seuil, sur V-réglage, à précision au moins égale à celle de B (0,308). **Aucun des 19 seuils ne l'atteint**, aux trois graines (précision maximale 0,250 / 0,249 / 0,250) : le repli préinscrit et signalé a été appliqué, t = 0,95 (`bras2.json`, `t_flagged_no_precision`). Le bras 2 n'est donc **pas** mesuré à précision contrôlée. Ses comptes portent sur V-lecture. On publie la couverture, le rappel conditionnel, le rappel total et les faux positifs, comptés en **codes bruts exacts**, et non par la reconnaissance du concept par fermeture.
- Les voisins sont calculés en numpy sur CPU. C'est une dérogation déclarée : la préinscription annonçait le GPU.

**P9-A, champs de preuve hiérarchiques** (`2026-10-29-p9-a`).
- *Bras* : quatre bras appariés (F, contrôle global, A, C), dix époques chacun, avec un lot effectif de 64.
- *Précision* : les produits sont en fp16, avec un GradScaler. Un pas à gradients non finis est sauté et journalisé. On arrête si l'échelle tombe sous 1, ou au 13e saut d'un bras dans une époque. Ce sont les seuils de D7, fixés avant toute relance.
- *Sélection* : 571 candidats par bras sur V-réglage (10 époques × 3 mélanges × 19 seuils, plus la référence α = 0). La sélection est scellée avant le gel, puis les prédictions de validation sont gelées.
- *Mesures* : planches regardées par wA:p1 et un Grok, puis reçu. Ensuite viennent les mesures H, E et F_R, la règle G, puis la voie R, et le mécanisme A − contrôle global sur V-diagnostic. Bootstrap de 10 000 tirages par groupes md5.
- *Règle des graines (§9.4)* : les graines 1 et 2 des quatre bras ne sont lancées **que si** A ou un contrôle obtient G ou R à la graine 0. Elle a été appliquée mécaniquement : graines 1 et 2 non lancées (D15).

**Diagnostic de non-transfert** (`2026-10-30-non-transfert`, D10), descriptif, sur le dev Rijksmuseum et la validation ICAI.
- *Cible* : les codes vus plus de 100 fois à l'apprentissage, de profondeur ≥ 3.
- *Événements par paire (image, code)* : présence dans la fermeture de T\*, émission exacte, passage au-dessus du seuil, disponibilité chez les 20 voisins de poids positif, vote pondéré au seuil de TK, contrôle de prévalence par 20 images tirées au hasard.
- *Lecture* : table appariée tête × voisinage, neuf cases fréquence × profondeur, codes communs à poids égal, bootstrap par composantes ou par groupes md5.
- *Garde* : le dev est réencodé, et T\* et TK recalculés doivent égaler leurs prédictions scellées. Seul le membre « dev » du banc est décodé.

**Petit élève et règle D2** (`2026-10-30-petit-eleve`).
- *Tête* : un détecteur de type DETR (Carion et al., 2020) (30 requêtes, appariement hongrois) et une tête de relations, sur des jetons C-RADIO de 28 × 28 et de 8 × 8, avec 3 graines.
- *Données* : 106 graphes Gemini d'apprentissage et 26 de réglage.
- *Juge* : les 26 graphes Gemini d'évaluation. C'est une fidélité au professeur, pas une vérité de localisation.
- *Témoins* : l'a priori de rectangles, OWLv2 (Minderer et al., 2023), Florence-2 (Xiao et al., 2023 ; checkpoint converti officiel, chargé par la classe native) et YOLOE-v8-S en mode texte (Wang et al., 2025), en colonne descriptive (D8).
- *Ordre* : l'étape `full` écrit et **scelle** les prédictions et la planche, sans métrique de qualité sur l'évaluation avant le reçu ; le contrôle de surapprentissage et le débit y sont déjà mesurés. L'étape `mesures` n'ouvre les chiffres qu'après le reçu des deux regards.
- *Débit* : chaque système est chronométré sous `no_grad` et fp16 ; pour l'élève, avec sa tête de relations.
- *Règle D2* : trois états, Loc, AP et D. Loc compare le rappel@30 de l'élève à l'a priori, AP compare l'AP50 de l'élève à OWLv2, et D est le rapport de débit. Les états se combinent en une issue fixée d'avance : « pas de signal » interdit à ce prototype de justifier la campagne d'annotation, sans réfuter ni le professeur ni la distillation.

**Audit des « confiants absents », en trois regards.** C'est la méthode de la section 5. Deux regards indépendants (Claude, Grok) classent 100 couples en O, A ou E. Les désaccords sont arbitrés à l'aveugle par Gemini, selon une règle écrite d'avance par le juge le plus strict, avec contrôle de l'ouverture des images. Ce n'est pas un score.

### 7. Ce que ces méthodes ne permettent pas de dire

- Un gain de F1 est un gain d'accord avec le catalogue, pas une preuve de justesse visuelle.
- Toutes les séries sont exploratoires. La phase 1 a une graine unique et des tests déjà consultés pour ICAI. La phase 2 travaille sur la validation et un dev déjà consultés. Aucune revendication confirmatoire n'est possible sans un banc jamais consulté.
- Les relectures, regards et audits sont faits par des modèles (section 0), **jamais par un expert humain**. **Aucun regard humain n'est prévu pour l'instant** (D5). Les proportions de l'audit (O, A, E) sont celles de juges-modèles ; elles ne corrigent aucun score.
- Les graphes de scène sont jugés par fidélité à un professeur, pas par une vérité de localisation.
- Le diagnostic de non-transfert est descriptif. Il ne départage pas catalogue et vision, et n'établit pas la cause du non-transfert (D10).

### 8. Incidents qui touchent la méthode

**Lecture d'une ligne de métadonnées du test** (30/10, consignée dans la préinscription D10, section 1).
- *Ce qui s'est passé.* Pour connaître l'ordre des clés du banc gelé (`frozen.json`), le rédacteur a affiché ses 400 premiers octets. Le membre du test étant placé en premier, il a vu les métadonnées d'**une** image du test : identifiant, adresses IIIF, support, composante. Il n'a vu ni vérité Iconclass ni prédiction.
- *Effet.* Rien de cette ligne n'entre dans un calcul.
- *Règle adoptée.* On n'affiche jamais d'octets bruts d'un fichier qui contient le test, et l'on ne lit une structure que par ses clés, par programme. Depuis, les scripts ne décodent que le membre « dev », et le test n'est même pas décodé en UTF-8.

**Suppression de jeux de données par Kaggle** (D11, 30/10).
- *Ce qui s'est passé.* Kaggle a supprimé presque tous les jeux nommés `porky-*`. La cause n'est pas sûre : le nom, ou les dessins de nus de certaines images.
- *Nommage.* Les jeux ont été re-téléversés **à l'identique** sous les noms `pkyevitch-*`. Seuls les chemins des liaisons changent. Les SHA vérifiés par le code ne changent pas. Les cœurs scientifiques relus n'ont pas changé ; plusieurs pilotes ont été amendés pour les chemins et le transport `.bin`, puis relus.
- *Images.* Les images potentiellement sensibles qui doivent être téléversées passent par une archive `.bin` épinglée. Le pilote l'extrait de façon sûre **hors de `/kaggle/working`**, pour que ces entrées ne réapparaissent pas dans les sorties publiées. Cela ne garantit pas qu'aucune planche dérivée ne soit produite en sortie.
- *Limites.* Les sorties de noyaux `porky-*` existantes sont montées sous leur ancien nom. Certaines contiennent des planches.
- *Leçon.* Les copies locales des sorties peuvent être partielles : l'export Kaggle s'arrête à 20 fichiers par défaut.

**Défauts trouvés par les relectures et les essais, avant toute mesure concernée.** Chaque défaut a été corrigé dans un commit séparé, relu, et testé sur une reproduction.
- **HiGHS** (A1) :
  - le prétraitement rendait un faux optimum certifié ;
  - l'écart d'arrêt absolu était de 10⁻⁶.

  Les deux sont reproduits et contournés.
- **Plafonds non appliqués** (A1, D3, Codex) : les pilotes n'avaient ni délai ni surveillance globale. Ils ont maintenant un moniteur (temps depuis le départ, mémoire, sorties, disque), arrêtent tout le groupe de processus, et refusent une sortie déjà remplie (B3). Le plafond du diagnostic d'A1 est ramené au budget restant de la série.
- **Repli silencieux sur CPU** (D3) : supprimé. Un T4 est exigé et journalisé.
- **Faux arrêt sur gradients non finis** (P9-A, devis 0) : le code refusait tout dépassement fp16. Il saute désormais le pas, avec des seuils d'arrêt écrits avant la relance (D7).
- **Invariant de conservation en fp16** (P9-A, blanc 1) : le contrôle algébrique se fait maintenant en float64, et la sensibilité fp16 est publiée.
- **Reçu des planches toujours refusé** (P9-A, sous-agent Sonnet) : `budget.json` était réécrit après le scellement. Il est exempté, et les planches ne sont pas refaites.
- **Décision au seuil sur un vote reconstruit** (D10, Codex) : la reconstruction en float64 pouvait inverser une décision prise par TK en float32. Les événements suivent désormais le vote effectif, et la reconstruction sert d'oracle.
- **Deux GPU visibles et écriture d'un entier numpy** (D10) : deux échecs techniques, survenus après les contrôles d'identité ou avant toute mesure, puis corrigés.
- **Regard avant les chiffres, débit et sceau** (petit élève, Codex) :
  - les mesures ont été séparées de la planche ;
  - le chronométrage inclut les relations ;
  - le décalage d'un demi-pixel est corrigé ;
  - le sceau doit être complet à la lecture ;
  - Florence-2 passe par sa conversion officielle.
- **Score de B dans `gel.json`** (P9-A, D14) : écart déclaré, non bloquant.

### 9. Protocole de relecture (D12, D13)

1. **Préinscription** : écrite avant le code. Elle fixe les règles de lecture, les populations, les graines et les plafonds.
2. **Relecture** : depuis le 30/10 (D13), toutes les relectures (code, diffs, sorties, regards de planches) sont faites par des **sous-agents Claude Sonnet indépendants**. Ils sont lancés par l'orchestrateur avec un brief complet, et chacun écrit un rapport.
3. **Audit final avant lancement** : Codex p4. Si Codex est indisponible, l'audit est fait par un second sous-agent Sonnet indépendant, qui n'a pas fait la première relecture (D12, D13). Le lancement peut alors partir.
4. **Contre-vérification** : au retour de Codex, il contre-vérifie ces audits **avant** que les résultats servent à une décision, à une publication ou à une étape suivante. Les résultats en attente sont marqués comme tels dans les `LECTURE.md` et dans les Résultats. Au 30/10, toutes les contre-vérifications de la phase 2 (non-transfert, A1, A1-dev, D3, P9-A, petit élève) sont faites et **conformes** (wA:p1).
5. **Lancement et lecture** : chaque étape est lancée par l'orchestrateur, sans enchaînement automatique. Les sorties sont relues, puis on rédige une `LECTURE.md`, avec les lectures permises et interdites, avant toute suite.
6. **Décisions** : elles sont consignées dans `DECISIONS.md`, avec l'avis d'un challenger (Grok) et la contre-expertise de Codex.

## 3. Résultats

Ce texte est écrit **uniquement** à partir des fichiers relus et de leurs `LECTURE.md`. Chaque chiffre renvoie à son fichier source ; les chemins sont relatifs à `~/porkyevitch/experiences/`, avec les 8 premiers caractères du SHA-256.

**Ce que ces résultats sont.**
- Toutes les séries sont **exploratoires** : une seule graine, sauf mention, un encodeur gelé (C-RADIOv3), et la projection sans le chapitre 86.
- Un F1 mesure un **accord avec un catalogue**, pas une justesse visuelle.
- Toutes les relectures et tous les regards sont faits par des **modèles** : sous-agents Claude Sonnet 5.5 lancés par wA:p1 (Claude Opus 5.5), Claude, Grok, Gemini, Codex. Aucun regard humain (D5).
- Les sections 3 à 7 ont été contre-vérifiées par Codex p4 après l'audit (D12, D13) : toutes **conformes**.

### 1. Phase 1 : sept comparaisons, aucune brique retenue

Sources : `2026-10-30-mesure-phase1/resultats/test/verdicts.json` (`5a4193cc`) et `.../mesures_test.json` (`e6ac6206`).

- **Règle préinscrite.** Une brique est retenue si la borne inférieure unilatérale à 99,29 % (1 − 0,05/7) de Δ_Rijks est > 0 et celle de Δ_ICAI > −0,01.
- **Bootstrap** : 10 000 tirages, graine 0, appariés. L'unité est l'image pour ICAI (787 images, une vérité vide exclue) et la composante pour le Rijksmuseum (1 201 images, 908 composantes).
- **Contrôle** : T0 mesure 0,5459 sur ICAI, égal à la valeur préinscrite.

| Brique | Réf. | Δ ICAI | borne 99,29 % | IC95 | Δ Rijks | borne 99,29 % | IC95 | Retenue |
|---|---|---:|---:|---|---:|---:|---|---|
| T\* | T0 | +0,0277 | +0,0188 | [+0,0206 ; +0,0352] | +0,0026 | −0,0061 | [−0,0046 ; +0,0097] | non |
| TK | T\* | +0,0075 | +0,0012 | [+0,0024 ; +0,0128] | +0,0015 | −0,0066 | [−0,0051 ; +0,0083] | non |
| T-niv | T\* | 0 | 0 | [0 ; 0] | 0 | 0 | [0 ; 0] | non |
| T-H | T\* | −0,0268 | −0,0376 | [−0,0354 ; −0,0184] | −0,0082 | −0,0193 | [−0,0173 ; +0,0006] | non |
| T-Z | T\* | −0,0052 | −0,0190 | [−0,0165 ; +0,0060] | −0,0325 | −0,0477 | [−0,0448 ; −0,0207] | non |
| T-D | T\* | +0,0035 | −0,0099 | [−0,0072 ; +0,0142] | −0,0532 | −0,0678 | [−0,0649 ; −0,0412] | non |
| TK-niv | T\* | — | — | — | — | — | — | non exécutée (TK et T-niv non retenues) |

**H-F1 absolus** (`mesures_test.json`) :
- ICAI test : T0 0,5459, T\* 0,5736, TK 0,5811, T-H 0,5469, T-Z 0,5685, T-D 0,5771 ;
- Rijksmuseum test : T0 0,4192, T\* 0,4218, TK 0,4233, T-H 0,4136, T-Z 0,3893, T-D 0,3686.

**Phrase tenable.** Aucune des sept comparaisons ne passe la porte conjointe. T\* et TK augmentent l'accord avec le catalogue ICAI. Aucun gain Rijksmuseum de ces recettes n'est démontré. Les recettes spatiales T-Z et T-D ont des écarts Rijksmuseum entièrement sous zéro.

**À ne pas dire** : que le transfert est nul au sens général, que T-D gagne sur ICAI, qu'une brique a été choisie, ou que T-Z et T-D isolent le coût du seul retrait du jeton de synthèse. Ces réserves viennent de la contre-expertise de Codex et de la lecture de Grok (`~/Documents/reviews/porkyevitch-phase1-lecture-*.md`).

### 2. Diagnostic de la tête sur la validation ICAI, et audit des « confiants absents »

Source : `2026-10-30-diagnostic-tete/resultats/complet/diagnostic.json` (`312d5a40`), descriptif, référence B = T-Z ; chiffres repris de la section 5 de Méthodes v1.1.

- **Traîne.** Le macro-F1 des 4 073 codes vus 5 à 20 fois à l'apprentissage vaut 0,07 pour B, et 0,20 sur les seuls codes présents en validation.
- **Profondeur.** Le rappel des nœuds de la vérité passe de 0,86 en profondeur 1 à 0,38 en profondeur 6. La précision passe de 0,74 à 0,64.
- **Seuils par tranche**, ajustés sur la validation elle-même : +0,0013. C'est un score optimiste, ni une borne ni une recette.
- **Erreurs de T\* et de B fortement corrélées** : Pearson du H-F1 par image 0,82.
- **Audit** : 100 couples (image, code) prédits par B avec p ≥ 0,9 et absents de la vérité fermée. Deux regards (Claude, Grok) s'accordent sur 53 couples sur 100. Les 47 désaccords sont arbitrés à l'aveugle par Gemini, selon la règle du juge le plus strict. Résultat : **O 29, A 46, E 25** : les juges-modèles ont classé 75 couples sur 100 en O ou A selon cette règle. **Ce n'est ni un score, ni une vérité, ni une borne du F1** : l'échantillon est conditionné aux codes les plus spécifiques prédits à p ≥ 0,9 (95 images), la règle d'arbitrage, écrite avant le troisième regard, penche vers le juge le plus strict, et les vrais positifs ni prédits ni catalogués ne sont pas mesurés.

### 3. Pourquoi le gain ne passe pas au Rijksmuseum : diagnostic descriptif

Source : `2026-10-30-non-transfert/resultats/diagnostic.json` (`1cb6fce9`), lecture `.../LECTURE.md`. Les sorties sont jugées conformes par un sous-agent Sonnet.

**Cible G** : codes vus plus de 100 fois à l'apprentissage, de profondeur ≥ 3. On compare le dev Rijksmuseum (211 paires) et la validation ICAI (11 176 paires).

| Événement | Dev Rijksmuseum | Validation ICAI |
|---|---:|---:|
| R_tête (fermeture de T\*) | 0,355 | 0,517 |
| tête, code exact | 0,294 | 0,474 |
| disponibilité chez les 20 voisins (poids > 0) | 0,687 | 0,851 |
| vote seul au seuil de TK | 0,185 | 0,305 |
| contrôle de prévalence (20 images au hasard) | 0,199 | 0,350 |

Sur les 128 codes communs aux deux banques (moyenne par code), la tête vaut 0,330 au Rijksmuseum et 0,375 sur ICAI, et la disponibilité 0,661 et 0,767.

**Lectures permises** (`LECTURE.md`) :
- La cible conditionne sur des paires positives connues : elle ne mesure pas les omissions des notices. L'hypothèse « ces codes sont absents des notices du Rijksmuseum » n'est pas soutenue en bloc. Les voisins portent ces codes pour environ 7 paires sur 10, bien au-dessus du hasard (+0,49).
- Le rappel de la tête est inférieur à la disponibilité-union des voisins, d'un écart comparable dans les deux banques (environ +0,33). La disponibilité est une union de 20 voisinages, sans coût en faux positifs : cet écart n'est pas une réserve de rappel récupérable à précision comparable. Il suggère d'examiner les décisions de la tête, sans identifier un défaut réparable ni sa cause. (La `LECTURE.md` emploie « sous-exploite » ; l'article ne reprend pas ce mot, selon la réserve de D10 et de la contre-expertise de Codex.)
- Sur les codes communs, l'écart de tête entre banques passe de 0,16 à 0,045. C'est compatible avec un effet de composition des codes, sans le prouver.

**Interdits** : « notices omises », « l'encodeur ne les contient pas », « le seuil est la cause », toute promesse pour le musée, tout choix tiré de ces chiffres.

**Réserves** : le dev est petit (76 des 128 codes communs n'ont qu'une paire), et la comparaison sur codes communs n'a pas d'intervalle.

### 4. A1 : décodage optimal sous une loi de candidats tirée des voisins (validation)

Source : `2026-10-29-a1/resultats/diagnostic/diagnostic.json` (`6adb2404`), lecture `.../LECTURE.md`, sur 2 100 images éligibles de V-diagnostic. Les sorties sont jugées conformes par un sous-agent Sonnet.

- A1 obtient un H-F1 de **0,6076** contre **0,5860** pour B (+0,022), et un F1 exact supérieur de +0,034. La règle préinscrite le déclare « recommended ».
- **Deux contrôles, à ne pas confondre.**
  - *Même q* (`threshold_same_q`, la loi d'A1, η = 0) : 0,6017. Au même q, le décodeur gagne **+0,006** (IC descriptif [+0,0025 ; +0,0094]) ; la lecture préinscrite du mécanisme classe ce cas en « mécanisme utile ».
  - *q propre* (`threshold_own_q`, analyse secondaire, configuration réglée séparément, η = 1) : 0,6102, légèrement au-dessus d'A1.
- **Lecture.** La plus grande part du gain sur B (+0,022) vient de q. Au même q, le décodeur apporte un petit gain observé. Face au contrôle à q propre, sa nécessité n'est pas démontrée. « Recommended » veut dire « bat B ».
- **Non affirmable** :
  - que le décodeur apporte l'essentiel du gain, ou qu'il est nécessaire ;
  - que le gain est indépendant de la proximité : 48 % du gain vient de 30 % des images dont le premier voisin a un cosinus ≥ 0,95, et proximité ne veut pas dire copie ;
  - une recommandation de production ;
  - les latences et les F1 par tranche, qui n'ont pas d'intervalle.
- **Portée** : validation ICAI seule, référence B = T-Z. Ce n'est pas une amélioration de T\* ni du musée (D10, Codex).

### 4 bis. A1-dev : le seuil figé sur q, une mesure sur le dev Rijksmuseum, transfert non établi

Sources : `2026-10-30-a1-dev-rijks/resultats/dev.json` (`3cc297f4`), `driver.json` (`0b63716f`) et `LECTURE.md`. Préinscription : `porkyevitch-maths/experiences/2026-10-30-a1-dev-rijks/PREINSCRIPTION.md` (`bb956db1`), D17. Les sorties sont jugées conformes par un sous-agent Sonnet.

- **Règle figée**, sans réajustement : la recette secondaire d'A1 scellée au réglage, K = 16, τ = 0,02, η = 1, π₀ = 0,25, t = 0,3. Elle est mesurée **une fois**, sur les 301 images du dev (239 composantes, toutes évaluables). Le choix est adaptatif et déclaré comme tel.
- **H-F1** : règle 0,4146, B (T-Z) 0,4191, T\* 0,4205.

| Contraste | Δ | IC95, composantes, 10 000 tirages, graine 20261034 |
|---|---:|---|
| règle − B (principal) | −0,0044 | [−0,0341 ; +0,0205] |
| règle − T\* (référence figée) | −0,0059 | [−0,0323 ; +0,0194] |

- Contre B, la règle gagne sur 99 images, perd sur 148 et fait jeu égal sur 54.
- **Lecture préinscrite** : Δ ≤ 0 et l'intervalle contient 0, donc **pas de signal exploratoire de transfert**. **Le gain d'A1 reste un gain de validation ICAI.** L'intervalle est large, et ne réfute pas toute amélioration.
- **Contrôles d'identité passés**, avant la mesure :
  - T-Z et T\* recalculés égalent le sceau (0 image sur 301 diffère) ;
  - la projection propre à A1 égale B, et π₀ = 1 redonne B ;
  - la règle redonne 0,6101628934369521 sur V-diagnostic ;
  - aucune ligne de test n'est lue (`test_rows` 0).
- **Descriptif, sans intervalle et sans valeur de décision** :
  - par support, la règle vaut 0,437, 0,394 et 0,416 (dessin, peinture, estampe), contre 0,465, 0,396 et 0,401 pour B ;
  - le F1 exact vaut 0,123 pour la règle, 0,106 pour B et 0,112 pour T\* ;
  - la strate de forte proximité (cos ≥ 0,95) est vide sur le dev.
- **Interdits** (`LECTURE.md`) : rien sur le test, sur le décodeur ni sur le musée.
- **Ce que le banc exclut par construction** (objection de Grok p7, corrigée selon Codex). Trois faits se tiennent : le filtre combiné du banc (dHash < 50 bits **ou** cosinus C-RADIO ≥ 0,95 avec une image de référence, propagé à la composante entière) retire 84 composantes hors réserve, soit 5 912 objets avant plafonnement (Méthodes §1) ; les sources ne décomposent pas ce compte entre les deux critères ; 48 % du gain d'A1 sur la validation vient de la strate cos ≥ 0,95, qui réunit 30 % des images (§4) ; cette strate est vide sur le dev (§4 bis). Une partie du gain de validation d'A1 peut donc venir d'images très proches de l'apprentissage au sens de C-RADIO, un régime que le filtre retire, au moins pour ce que ses seuils détectent. C'est une **hypothèse compatible, pas une preuve** : une forte proximité n'est pas une copie, A1 n'a pas été mesurée sur les objets retirés, et le filtre ne garantit pas l'absence de toute copie. La phrase tenable est étroite : **sur un banc filtré aux seuils préinscrits**, la règle figée n'établit pas de gain sur B. C'est une absence de gain établi, pas la preuve d'une dégradation, ni un jugement sur le musée avant ce filtre.

### 5. D3 : traîne et profondeur, résultat négatif (validation)

Sources : `2026-10-30-d3-traine-profondeur/resultats/complet/bras1.json` (`90409cd5`) et `bras2.json` (`b7dd1e25`), lecture `.../LECTURE.md`. Les sorties sont jugées conformes par un sous-agent Sonnet.

- **Bras 1**, vote des 20 voisins sur les codes rares, poids fixe 0,25 : **non retenu**.
  - Sur la **validation entière** (4 265 lignes, 4 241 évaluables) : F_R vaut 0,048 contre 0,070 pour B (IC95 de l'écart [−0,018 ; −0,013]), et H −0,004.
  - Sur **V-lecture** (2 145 lignes, 2 130 évaluables), descriptif et sans intervalle : F_R 0,025 contre 0,038.
  - Il réduit les faux positifs (714 contre 2 071) mais perd des vrais positifs (230 contre 357).
  - Il bat le témoin à mémoire permutée (F_R 0,039) : la mémoire porte un signal, insuffisant pour battre B.
  - Le négatif est borné à cette recette, dont le poids n'est pas réglé.
- **Bras 2**, tête linéaire des enfants, 3 graines, sur **V-lecture** : **non retenu**.
  - **La contrainte de précision n'a jamais été atteinte** : aucun des 19 seuils n'atteint, sur V-réglage, la précision de B (0,308 ; maxima 0,250 / 0,249 / 0,250). Le repli signalé (t = 0,95) a été appliqué aux trois graines. Le verdict négatif ne change pas, mais il n'est pas obtenu à précision contrôlée.
  - Le rappel conditionnel vaut 0,14 contre 0,61 pour B, et le F1 sur les enfants 0,11 contre 0,32. Pas de « descente améliorée ».
  - La porte issue de B ne laisse passer que 55 % des vrais enfants.
  - Cela ne dit rien d'une tête sur les grilles, ni de la séparabilité des frères.
- Les comptes de descente portent sur des **codes bruts exacts**, pas sur la reconnaissance des concepts par fermeture (préinscription D3, et `CODE.md`).

### 6. P9-A, graine 0 : prototypes textuels et imbrication locale, négatif (validation)

Sources : `2026-10-29-p9-a/resultats/mesures-0/verdicts.json` (`6a026547`) et `mesures.json`, lecture `.../LECTURE.md`, décisions D14 et D15. Le gel est `13f75f3a`. Les verdicts sont jugés conformes par un sous-agent Sonnet.

| Bras | ΔH | ΔE | ΔF_R | verdict |
|---|---:|---:|---:|---|
| F | +0,0043 | +0,0000 | −0,0026 | non retenu |
| contrôle global | +0,0019 | −0,0079 | −0,0023 | non retenu |
| A | +0,0015 | −0,0073 | −0,0032 | non retenu |
| C | +0,0018 | −0,0054 | −0,0026 | non retenu |

- Le seuil de la règle G est ΔH ≥ 0,005. Les intervalles de ΔF_R sont entièrement négatifs (`LECTURE.md`), et la garde E est respectée.
- **Mécanisme d'imbrication locale non soutenu**, en général comme sur les codes rares. Sur V-diagnostic, A − contrôle global vaut −0,0003 en H, avec un intervalle [−0,0017 ; +0,0011] selon `LECTURE.md`, et −0,0007 en F_R.
- La phrase « reading » de `verdicts.json` est un gabarit : **ne pas la citer**.
- **Graines 1 et 2 non lancées** (D15). La règle préinscrite §9.4 a été appliquée mécaniquement : aucun bras n'obtient G ou R à la graine 0. La graine 0 est publiée comme résultat **exploratoire négatif**, sans recommandation.
- `gel.json` contient le score de référence de B (0,58908) : c'est un écart déclaré, jugé non bloquant (D14).

### 7. Petit élève v1 : porte D2, « pas de signal »

Source : `2026-10-30-petit-eleve/resultats/mesures/resultats.json` (`5463d532`), lecture `.../LECTURE.md`. Les sorties sont jugées conformes par un sous-agent Sonnet.

**Le juge** est formé des 26 graphes Gemini d'évaluation. Il mesure la **fidélité à Gemini, pas une vérité de localisation**. La planche a été regardée avant les chiffres, par wA:p1 et Grok wA:p7.

- **Loc−.** Le rappel@30 de l'élève (28×28) vaut 0,225 / 0,230 / 0,246 selon la graine, contre **0,258** pour l'a priori de rectangles fixes. L'écart est de −0,033 / −0,029 / −0,012. Les intervalles contiennent 0 ; leurs bornes hautes valent +0,016 / +0,023 / +0,043 (la `LECTURE.md` dit « < 0,15 »). L'élève ne bat pas l'a priori.
- **AP?** L'AP50 élève − OWLv2, moyenné sur 7 catégories, vaut de −0,04 à −0,06 selon la graine. L'AP50 sans classe de l'élève va de 0,048 à 0,086 sur les six bras (28×28 et 8×8), contre **0,199** pour OWLv2.
  - Les fichiers donnent 0,062 / 0,050 / 0,067 pour les bras 28×28 (graines 0, 1, 2) et 0,080 / 0,086 / 0,048 pour les bras 8×8.
- **D+.** L'élève complet traite 24,9 images/s en lot de 32, avec la tête de relations, contre 10,9 pour OWLv2, soit D = 2,29. Il s'agit de forwards seulement, et les colonnes ne couvrent pas la même portion du pipeline.
- **Témoins descriptifs.** YOLOE-v8-S texte obtient un rappel@30 de 0,152 et un AP50 sans classe de 0,116. Florence-2 retrouve 0,246 de rappel sur toutes ses boîtes, avec 3,3 boîtes par image. OWLv2 a un rappel@30 de 0,307.
- L'élève produit environ 21 objets par image au score ≥ 0,5 (de 19,8 à 23,0 selon le bras), contre environ 9 chez Gemini (doublons, pas de NMS). C'est cohérent avec les deux regards des planches.
- **Conséquence préinscrite (D2).** Ce prototype ne justifie pas la campagne d'annotation à l'échelle. Il ne réfute ni Haiku ni la distillation. Le test tranche 300 reste suspendu.

### 8. Ce que l'ensemble ne dit pas

- Aucune brique n'est retenue en phase 1. A1 « bat B » sur la validation ; son gain tient surtout à q, avec un petit apport observé du décodeur au même q. Sa règle la plus simple, figée et mesurée une fois sur le dev Rijksmuseum, **n'établit pas de transfert** (section 4 bis). D3 et P9-A sont négatifs dans leur régime. Aucun de ces résultats ne promet un gain sur le Rijksmuseum.
- **Fin de la partie Iconclass de ce tour (D17).** Une seule mesure était prévue avant d'écrire, et elle est faite. Il n'y a pas de kNN en produit ni de réapprentissage de type Hill dans ce tour. La référence publiée reste T\*.
- La cause du non-transfert **n'est pas établie** (D10). Le diagnostic décrit un rappel de la tête inférieur à la disponibilité-union des voisins, et un effet de composition possible. Il n'identifie ni un défaut réparable ni sa cause, et ne tranche pas entre catalogue et vision.
- Une seule graine, sauf pour D3 bras 2 et le petit élève (3 graines).
- Les juges sont des modèles : Gemini pour le petit élève, Claude, Grok et Gemini pour l'audit O/A/E.

### 9. Contre-vérification de Codex

- §3 non-transfert, §4 A1, §4 bis A1-dev, §5 D3, §6 P9-A (verdicts, D14, D15) et §7 petit élève : contre-vérifiés par Codex, tous **conformes** (wA:p1, 30/10). Plus rien n'est en attente.
- La section 1 reprend les verdicts déjà contre-expertisés par Codex dans sa lecture de la phase 1.
- Ces contre-vérifications portent sur les sorties et leurs lectures ; elles ne valident pas chaque formulation de l'article. L'audit factuel de l'article (`porkyevitch-article-codex.md`) a demandé les corrections de cette v3.

## 4. Discussion

**Ce que les résultats disent.**
- **L'accord ICAI ne passe pas au Rijksmuseum.** T\* et TK améliorent l'accord avec le catalogue ICAI, avec des intervalles entièrement positifs. Leurs écarts sur le Rijksmuseum ont des intervalles qui contiennent 0. Les recettes spatiales y perdent (Résultats §1). Aucune brique n'est retenue selon la règle écrite d'avance.
- **Le seul gain de la phase 2 reste un gain de validation.** A1 bat B sur V-diagnostic. L'essentiel du gain vient de la loi q. Au même q, le décodeur apporte un petit gain observé (+0,006) ; un seuil sur une configuration de q réglée séparément fait aussi bien qu'A1, si bien que la nécessité du décodeur n'est pas démontrée (§4). Cette règle, figée et mesurée une fois sur le dev, n'établit pas de transfert : l'écart est négatif et l'intervalle contient 0 (§4 bis).
- **Ce n'est pas une réfutation.** Un intervalle qui contient zéro ne réfute pas toute amélioration. Le dev est petit, et il avait déjà été consulté.
- **Ce que le banc exclut par construction.** C'est l'objection principale à ce résultat négatif, et nous la tenons pour sérieuse. Trois faits se tiennent : le filtre combiné du banc (dHash < 50 bits **ou** cosinus C-RADIO ≥ 0,95 avec une image de référence, propagé à la composante entière) retire 84 composantes hors réserve, soit 5 912 objets avant plafonnement (Méthodes §1) ; les sources ne décomposent pas ce compte entre les deux critères ; 48 % du gain d'A1 sur la validation vient de la strate cos ≥ 0,95, qui réunit 30 % des images (Résultats §4) ; cette strate est vide sur le dev (Résultats §4 bis). Une partie du gain de validation d'A1 peut donc venir d'images très proches de l'apprentissage au sens de C-RADIO, un régime que le filtre retire, au moins pour ce que ses seuils détectent. C'est une **hypothèse compatible, pas une preuve** : une forte proximité n'est pas une copie, A1 n'a pas été mesurée sur les objets retirés, et le filtre ne garantit pas l'absence de toute copie. La phrase tenable est étroite : **sur un banc filtré aux seuils préinscrits**, la règle figée n'établit pas de gain sur B. C'est une absence de gain établi, pas la preuve d'une dégradation, ni un jugement sur le musée avant ce filtre.
- **Deux idées de tête ne battent pas la référence dans leur régime.**
  - D3 : le vote de voisins sur les codes rares coupe des faux positifs mais perd des vrais ; il porte pourtant un signal, puisqu'il bat une mémoire permutée. La tête des enfants, routée par le parent, perd en rappel conditionnel ; la contrainte de précision visée n'a jamais été atteinte, et le seuil de repli a été appliqué (§5).
  - P9-A : aucun avantage utile de l'imbrication de la hiérarchie dans les zones n'est soutenu, dans cette graine et cette recette (§6).
- Ces négatifs sont bornés à leurs recettes : poids non réglé pour le vote de D3, repli de précision pour la tête des enfants (trois graines), une graine et dix époques par bras pour P9-A.

**Ce que les diagnostics suggèrent, sans l'établir.**
- **Le catalogue.** Selon des juges-modèles (deux regards d'accord sur 53 couples sur 100, puis un arbitre), 75 des 100 prédictions sûres absentes du catalogue ont été jugées O ou A (§2). Cela dit que le catalogue ne contient pas tout ce que ces juges voient sur cet échantillon conditionné. Cela ne dit pas dans quel sens le F1 de catalogue s'écarte d'un F1 sur une vérité complète : les vrais positifs ni prédits ni catalogués ne sont pas mesurés, et un F1 calculé sur un catalogue incomplet n'est pas en général une borne inférieure. La littérature sur les étiquettes manquantes montre, sous ses hypothèses, qu'une correction par un taux unique n'est pas identifiée quand la propension d'oubli varie ; nos 100 couples ne mesurent pas cette propension. Nous publions les trois comptes, sans correction.
- **Le non-transfert.** Le diagnostic D10 ne soutient pas l'idée simple que les codes fréquents et profonds seraient absents des notices du Rijksmuseum : les voisins d'apprentissage les portent pour une majorité de paires, bien au-dessus du hasard (§3). Le rappel de la tête reste inférieur à la disponibilité-union des voisins, d'un écart comparable sur les deux banques ; cet écart suggère d'examiner les décisions de la tête, sans identifier un défaut réparable ni sa cause. Sur les codes communs, l'écart entre banques se réduit, ce qui est compatible avec un effet de composition.

  Deux précautions (Codex) :
  - une union de voisins est une disponibilité sans coût en faux positifs, et l'écart disponibilité–rappel **n'est pas un gain récupérable** ;
  - ni la cause catalogue ni la cause vision n'est établie (D10).

**Les distillations de graphes de scène.** Le petit élève, une tête légère sur l'encodeur gelé, ne bat pas un a priori de rectangles fixes en rappel, et reste loin d'OWLv2 en précision moyenne, tout en étant plus rapide, en forwards seulement (§7). Le juge est la fidélité au professeur Gemini, sur 26 images, et non une vérité de localisation. Par la règle écrite d'avance, ce prototype ne justifie pas une campagne d'annotation à l'échelle. Il ne réfute ni le second annotateur ni la distillation. La suite décidée (D16) est une seule brique préinscrite : le transfert d'un détecteur existant.

**Limites.**
- **Tout est exploratoire.** Il y a une seule graine par série, sauf la tête des enfants de D3 et le petit élève, à trois graines. La validation ICAI et le dev du Rijksmuseum ont été consultés plusieurs fois. Le test ICAI avait déjà été consulté avant cette série ; ici, ses agrégats sont restés fermés jusqu'au gel, puis ont été ouverts une fois. Le test du Rijksmuseum a été ouvert une fois, pour les verdicts de la phase 1. Aucune conclusion confirmatoire n'est possible sans un banc jamais consulté.
- **Les juges sont des modèles.** Relectures, regards de planches, audit et professeurs de graphes sont des modèles de langage multimodaux, dont les biais peuvent être communs ; ils ne sont ni experts ni indépendants au sens statistique. Aucun regard humain n'a été fait (D5).
- **La mesure est un accord de catalogue.** Elle dépend des conventions de chaque catalogue et de sa complétude.
- **Les incidents sont déclarés** (Méthodes §8) : la lecture d'une ligne de métadonnées du test, sans vérité ; les suppressions de jeux par Kaggle ; et des défauts de code trouvés par les relectures, tous corrigés avant les mesures concernées.
- **Les vérifications sont faites par des modèles.** Les contre-vérifications de Codex des Résultats §3 à §7 sont toutes faites et conformes (Résultats §9). Elles vérifient le code, les sorties et les lectures ; elles ne valident pas chaque formulation de l'article, et ne valent pas une revue par des pairs.

**Ce qui suivrait, si l'on continue.**
- **Mesurer la justesse visuelle** demanderait un regard humain préinscrit, sur un échantillon stratifié du dev.
- **Tester l'effet des négatifs faux du catalogue** se ferait par une perte qui les tolère (Hill, Zhang et al., 2021 ; ou l'ignorance des non-observés, Cole et al., 2021), jugée par un regard du même dessin que l'audit, et non par le F1 du catalogue. Ce n'est qu'une hypothèse : ce diagnostic ne l'identifie pas.
- **Toute revendication de transfert** demanderait un banc neuf.
- **Mesurer A1 avec et sans les proches**, sur une population qui garde les images proches au sens des seuils et les marque, dirait quelle part du gain vient d'eux. Ce banc ne le permet pas.

Aucune de ces suites n'est engagée par cet article.

## Références

Chaque entrée a été vérifiée sur une page primaire ouverte le 30/10/2026, par Grok p7 (rapports d'état de l'art, des étiquettes manquantes et des références de production), par un sous-agent Claude Sonnet 5.5 ou par wA:pH. La colonne de droite dit d'où vient la vérification. Pour les entrées vérifiées par Grok seulement, les prénoms ne sont pas donnés, faute d'avoir été relus. Le lieu de publication n'est donné que s'il figure sur la page ouverte ; sinon, l'entrée cite la prépublication arXiv. Ne sont pas cités, faute de page vérifiable : Dembczyński et al. (NIPS 2011), Dunn (1961), le supplément de Springstein et al., ArtDL 2.0, Banar et al. (JOCCH 2023).

#### Données, vocabulaire et ressources

| Référence | Vérifiée par |
|---|---|
| Posthumus, E. (2020). *Iconclass AI Test Set*. <https://iconclass.org/testset/> | Grok p7 (page ouverte ; l'accès a échoué au second contrôle par DNS) |
| davanstrien (s. d.). *iconclass-vlm-brillfull*, jeu de données Hugging Face, révision `8045366`, licence déclarée CC0-1.0. <https://huggingface.co/datasets/davanstrien/iconclass-vlm-brillfull> | sous-agent Sonnet (fiche : cc0-1.0, apprentissage 86,2 k, test 788) |
| Rijksmuseum (s. d.). *Rijksmuseum Data Services*. <https://data.rijksmuseum.nl/> Les droits des objets retenus (métadonnées CC0, reproductions domaine public) sont ceux déclarés par la source et relevés à la collecte (préinscription du banc) ; la page ouverte ne restate pas ces licences. | sous-agent Sonnet (page ouverte) ; droits : sources locales du banc |

#### Encodeur et modèles

| Référence | Vérifiée par |
|---|---|
| Ranzinger, M., Heinrich, G., Kautz, J., & Molchanov, P. (2024). AM-RADIO: Agglomerative Vision Foundation Model — Reduce All Domains Into One. *CVPR 2024*, 12490–12500. arXiv:2312.06709. <https://arxiv.org/abs/2312.06709> | sous-agent Sonnet |
| NVIDIA (s. d.). *C-RADIOv3-L*, fiche de modèle, NVIDIA Open Model License. <https://huggingface.co/nvidia/C-RADIOv3-L> | sous-agent Sonnet (la fiche ne demande pas de citation particulière) |
| Minderer, M., Gritsenko, A., & Houlsby, N. (2023). Scaling Open-Vocabulary Object Detection. arXiv:2306.09683. <https://arxiv.org/abs/2306.09683> ; poids `google/owlv2-base-patch16-ensemble`, Apache-2.0. | sous-agent Sonnet ; Grok p7 |
| Xiao, B., Wu, H., Xu, W., Dai, X., Hu, H., Lu, Y., Zeng, M., Liu, C., & Yuan, L. (2023). Florence-2: Advancing a Unified Representation for a Variety of Vision Tasks. arXiv:2311.06242. <https://arxiv.org/abs/2311.06242> ; poids `florence-community/Florence-2-base` (conversion transformers officielle), MIT. | sous-agent Sonnet |
| Wang, A., Liu, L., Chen, H., Lin, Z., Han, J., & Ding, G. (2025). YOLOE: Real-Time Seeing Anything. *ICCV 2025*. arXiv:2503.07465. <https://arxiv.org/abs/2503.07465> ; code <https://github.com/THU-MIG/yoloe>, AGPL-3.0. | sous-agent Sonnet ; Grok p7 |
| Carion, N., Massa, F., Synnaeve, G., Usunier, N., Kirillov, A., & Zagoruyko, S. (2020). End-to-End Object Detection with Transformers. arXiv:2005.12872. <https://arxiv.org/abs/2005.12872> | sous-agent Sonnet |

#### Têtes, pertes, décision et calcul

| Référence | Vérifiée par |
|---|---|
| Ben-Baruch, E., Ridnik, T., Zamir, N., Noy, A., Friedman, I., Protter, M., & Zelnik-Manor, L. (2021). Asymmetric Loss For Multi-Label Classification. *ICCV 2021*. arXiv:2009.14119. <https://arxiv.org/abs/2009.14119> | sous-agent Sonnet |
| Giunchiglia, E., & Lukasiewicz, T. (2020). Coherent Hierarchical Multi-Label Classification Networks. *NeurIPS 2020*. arXiv:2010.10151. <https://arxiv.org/abs/2010.10151> | sous-agent Sonnet |
| Ridnik, T., Sharir, G., Ben-Cohen, A., Ben-Baruch, E., & Noy, A. (2021). ML-Decoder: Scalable and Versatile Classification Head. arXiv:2111.12933. <https://arxiv.org/abs/2111.12933> | sous-agent Sonnet |
| Waegeman, W., Dembczyński, K., Jachnik, A., Cheng, W., & Hüllermeier, E. (2014). On the Bayes-Optimality of F-Measure Maximizers. *Journal of Machine Learning Research*, 15(103), 3513–3568. <https://jmlr.org/papers/v15/waegeman14a.html> | sous-agent Sonnet (pages de la page JMLR) |
| Huangfu, Q., & Hall, J. A. J. (2018). Parallelizing the dual revised simplex method. *Mathematical Programming Computation*, 10(1), 119–142. doi:10.1007/s12532-017-0130-5. Logiciel HiGHS, MIT : <https://github.com/ERGO-Code/HiGHS> | wA:pH (citation demandée par le dépôt) |
| Efron, B., & Tibshirani, R. J. *An Introduction to the Bootstrap*. Chapman & Hall/CRC. doi:10.1201/9780429246593 | sous-agent Sonnet (titre, auteurs et DOI ; année non relue) |

#### Iconclass et art : travaux voisins

| Référence | Vérifiée par |
|---|---|
| Springstein et al. (2024). Visual Narratives: Large-Scale Hierarchical Classification of Art-Historical Images. *WACV 2024*. <https://openaccess.thecvf.com/content/WACV2024/papers/Springstein_Visual_Narratives_Large-Scale_Hierarchical_Classification_of_Art-Historical_Images_WACV_2024_paper.pdf> ; code <https://github.com/TIBHannover/iconclass-classification> | Grok p7 (PDF ouvert) ; Codex (dépôt) ; liste complète des auteurs non relue |
| Banar, Daelemans & Kestemont (2021). Multi-modal Label Retrieval for the Visual Arts: The Case of Iconclass. Atelier ARTIDIGH 2021. <https://www.scitepress.org/Papers/2021/103906/103906.pdf> | Grok p7 (PDF ouvert) ; Codex (copie iconclass.org) ; actes et pages non relus |
| Cetinic, E. (2021). Iconographic Image Captioning for Artworks. Atelier FAPER, ICPR 2020. arXiv:2102.03942. <https://arxiv.org/abs/2102.03942> | sous-agent Sonnet ; Grok p7 |
| Milani, F., & Fraternali, P. (2021). A Data Set and a Convolutional Model for Iconography Classification in Paintings (ArtDL). *ACM Journal on Computing and Cultural Heritage*, 14(4), 1–18. arXiv:2010.11697. <https://arxiv.org/abs/2010.11697> | sous-agent Sonnet ; Grok p7 |
| Gonthier, N., Gousseau, Y., Ladjal, S., & Bonfait, O. (2018). Weakly Supervised Object Detection in Artworks (IconArt). Atelier VISART, ECCV 2018. arXiv:1810.02569. <https://arxiv.org/abs/1810.02569> | sous-agent Sonnet ; Grok p7 |
| Reshetnikov, A., Marinescu, M.-C., & More Lopez, J. (2022). DEArt: Dataset of European Art. Atelier VISART VI, ECCV 2022. arXiv:2211.01226. <https://arxiv.org/abs/2211.01226> | sous-agent Sonnet ; Grok p7 |

#### Étiquettes manquantes et évaluation

| Référence | Vérifiée par |
|---|---|
| Bekker & Davis (2020). Learning from positive and unlabeled data: a survey. *Machine Learning*. arXiv:1811.04820v2. <https://arxiv.org/html/1811.04820v2> | Grok p7 |
| Cole, Mac Aodha, Lorieul, Perona, Morris & Jojic (2021). Multi-Label Learning from Single Positive Labels. arXiv:2106.09708. <https://arxiv.org/html/2106.09708v1> | Grok p7 |
| Zhou, Chen, Wang, Chen & Heng (2022). Acknowledging the Unknown for Multi-label Learning with Single Positive Labels. arXiv:2203.16219. <https://arxiv.org/html/2203.16219v1> | Grok p7 |
| Zhang, Cheng, Huang, Wen, Feng, Li & Guo (2021). Simple and Robust Loss Design for Multi-Label Learning with Missing Labels. arXiv:2112.07368. <https://arxiv.org/abs/2112.07368> | Grok p7 |
| Schultheis, Wydmuch, Babbar & Dembczyński (2022). On Missing Labels, Long-tails and Propensities in Extreme Multi-label Classification. *KDD 2022*. doi:10.1145/3534678.3539466. <https://arxiv.org/html/2207.13186> | Grok p7 |
| Northcutt, Athalye & Mueller (2021). Pervasive Label Errors in Test Sets Destabilize Machine Learning Benchmarks. *NeurIPS 2021, Datasets and Benchmarks*. arXiv:2103.14749. <https://arxiv.org/abs/2103.14749> | Grok p7 |


## Tableaux

#### Tableau 1 — Effectifs

Sources : Méthodes v4 §1 (ICAI ; effectifs recoupés par Codex), `2026-10-30-mesure-phase1/resultats/test/verdicts.json` (`5a4193cc`) (dénominateurs de test), `2026-10-30-a1-dev-rijks/resultats/dev.json` (`3cc297f4`) (dev).

| Banque | Effectif | Nature |
|---|---|---|
| ICAI apprentissage | 81 951 images | effectif |
| ICAI validation | 4 265 images, dont 4 241 évaluables | effectif |
| ICAI test | 787 images au dénominateur (1 vérité vide exclue) | effectif |
| Rijksmuseum test | 1 201 images, 908 composantes | effectif |
| Rijksmuseum dev | 301 images, 239 composantes | effectif |

#### Tableau 2 — Phase 1 : sept comparaisons, règle conjointe

Sources : `2026-10-30-mesure-phase1/resultats/test/verdicts.json` (`5a4193cc`), `2026-10-30-mesure-phase1/resultats/test/mesures_test.json` (`e6ac6206`).

| Système | Réf. | H ICAI | H Rijks | Δ ICAI | borne 99,29 % | IC95 ICAI | Δ Rijks | borne 99,29 % | IC95 Rijks | Retenue |
|---|---|---|---|---|---|---|---|---|---|---|
| T0 | — | 0,5459 | 0,4192 | — | — | — | — | — | — | référence |
| T* | T0 | 0,5736 | 0,4218 | 0,0277 | 0,0188 | [0,0206 ; 0,0352] | 0,0026 | −0,0061 | [−0,0046 ; 0,0097] | non |
| TK | T* | 0,5811 | 0,4233 | 0,0075 | 0,0012 | [0,0024 ; 0,0128] | 0,0015 | −0,0066 | [−0,0051 ; 0,0083] | non |
| T-niv | T* | 0,5736 | 0,4218 | 0,0000 | 0,0000 | [0,0000 ; 0,0000] | 0,0000 | 0,0000 | [0,0000 ; 0,0000] | non |
| T-H | T* | 0,5469 | 0,4136 | −0,0268 | −0,0376 | [−0,0354 ; −0,0184] | −0,0082 | −0,0193 | [−0,0173 ; 0,0006] | non |
| T-Z | T* | 0,5685 | 0,3893 | −0,0052 | −0,0190 | [−0,0165 ; 0,0060] | −0,0325 | −0,0477 | [−0,0448 ; −0,0207] | non |
| T-D | T* | 0,5771 | 0,3686 | 0,0035 | −0,0099 | [−0,0072 ; 0,0142] | −0,0532 | −0,0678 | [−0,0649 ; −0,0412] | non |
| TK-niv | T* | — | — | — | — | — | — | — | — | non exécutée |

Règle : retenue si borne unilatérale Δ_Rijks > 0 et borne Δ_ICAI > −0,01 (niveau 1 − 0,05/7). IC95 descriptifs.

#### Tableau 3 — Diagnostic de la tête B (T-Z) sur la validation ICAI, par profondeur

Sources : `2026-10-30-diagnostic-tete/resultats/complet/diagnostic.json` (`312d5a40`).

| Profondeur | Rappel des nœuds | Précision | Nœuds vrais |
|---|---|---|---|
| 1 | 0,86 | 0,74 | 8 555 |
| 2 ‡ | 0,69 | 0,68 | 10 599 |
| 3 ‡ | 0,58 | 0,67 | 13 457 |
| 4 ‡ | 0,49 | 0,66 | 13 933 |
| 5 ‡ | 0,43 | 0,65 | 12 981 |
| 6 | 0,38 | 0,64 | 9 454 |

Codes vus 5–20 fois : macro-F1 0,07 sur 4 073 codes, 0,20 sur les codes présents en validation. Seuils par tranche ajustés sur la validation elle-même : +0,0013 de H-F1 (score optimiste, ni borne ni recette). Pearson du H-F1 par image, T* contre B : 0,82. ‡ Profondeurs 2 à 5 : lues dans le même fichier et vérifiées par Codex, mais non citées par les Résultats (à relire avant usage).

#### Tableau 4 — Jugements de modèles sur 100 « confiants absents » (validation, B p ≥ 0,9)

Source : `2026-10-30-diagnostic-tete/resultats/regard-confiants/ACCORD.md` (`97af4703`), ligne des comptes arbitrés. Codes les plus spécifiques prédits à p ≥ 0,9 et absents de la vérité fermée, au plus deux par image (95 images). Deux regards de modèles (Claude, Grok), d'accord sur 53 couples sur 100 ; désaccords arbitrés à l'aveugle par Gemini, selon une règle écrite avant le troisième regard par le juge le plus strict. **Ni un score, ni une vérité, ni une borne du F1.**

| Catégorie | Couples |
|---|---|
| O : motif jugé visible, code précis | 29 |
| A : motif jugé visible, code générique | 46 |
| E : motif jugé absent ou sens jugé faux | 25 |

#### Tableau 5 — Non-transfert, cible G (codes > 100, profondeur ≥ 3), descriptif

Sources : `2026-10-30-non-transfert/resultats/diagnostic.json` (`1cb6fce9`).

| Événement | dev Rijks (211 paires) | validation ICAI (11 176 paires) |
|---|---|---|
| tête (fermeture) | 0,355 | 0,517 |
| tête (exact) | 0,294 | 0,474 |
| disponible chez les voisins | 0,687 | 0,851 |
| vote seul au seuil de TK | 0,185 | 0,305 |
| contrôle aléatoire | 0,199 | 0,350 |

La disponibilité est une union de 20 voisinages, sans coût en faux positifs : l'écart à la tête n'est pas un gain récupérable. Lectures interdites : « notices omises », « l'encodeur ne les contient pas », « le seuil est la cause », toute cause du non-transfert (D10).

#### Tableau 6 — A1 sur la validation, puis sa règle figée sur le dev Rijksmuseum

Sources : `2026-10-29-a1/resultats/diagnostic/diagnostic.json` (`6adb2404`), `2026-10-30-a1-dev-rijks/resultats/dev.json` (`3cc297f4`).

| Banque | Système | H-F1 |
|---|---|---|
| V-diagnostic ICAI | A1 (décodeur, q avec η = 0) | 0,6076 |
|  | seuil, même q qu'A1 (η = 0) | 0,6017 |
|  | seuil, q propre réglé à part (η = 1, secondaire) | 0,6102 |
|  | B (T-Z) | 0,5860 |
| dev Rijksmuseum | règle figée (seuil, q propre, η = 1) | 0,4146 |
|  | B (T-Z) | 0,4191 |
|  | T* | 0,4205 |

Dev : règle − B −0,0044 [−0,0341 ; 0,0205] ; règle − T* −0,0059 [−0,0323 ; 0,0194] (composantes, 10 000 tirages, graine 20261034) : transfert non établi.

#### Tableau 7 — D3, résultat négatif : bras 1 sur la validation entière et sur V-lecture, bras 2 sur V-lecture

Sources : `2026-10-30-d3-traine-profondeur/resultats/complet/bras1.json` (`90409cd5`), `2026-10-30-d3-traine-profondeur/resultats/complet/bras2.json` (`b7dd1e25`).

| Sonde | Mesure | Bras | B | IC95 de l'écart | Retenue |
|---|---|---|---|---|---|
| Bras 1 (vote rares, poids 0,25), validation entière (4 241 évaluables) | F_R | 0,048 | 0,070 | [−0,018 ; −0,013] | non |
|  | témoin permuté F_R | 0,039 |  |  |  |
| Bras 1, V-lecture (2 130 évaluables), descriptif | F_R | 0,025 | 0,038 | — |  |
| Bras 2 (tête des enfants), V-lecture, graine 0, t = 0,95 (repli) | rappel conditionnel / F1 enfants | 0,14 / 0,11 | 0,61 / 0,32 |  | non |
| Bras 2 (tête des enfants), V-lecture, graine 1, t = 0,95 (repli) | rappel conditionnel / F1 enfants | 0,14 / 0,11 | 0,61 / 0,32 |  | non |
| Bras 2 (tête des enfants), V-lecture, graine 2, t = 0,95 (repli) | rappel conditionnel / F1 enfants | 0,14 / 0,11 | 0,61 / 0,32 |  | non |

Comptes en codes bruts exacts. La porte issue de B laisse passer 55 % des vrais enfants. Bras 2 : aucun seuil n'atteint sur V-réglage la précision de B ; le repli signalé (t = 0,95) a été appliqué aux trois graines, le bras n'est donc pas mesuré à précision contrôlée. L'IC du bras 1 porte sur la validation entière seulement.

#### Tableau 8 — P9-A, graine 0 (validation ICAI), aucun bras retenu

Sources : `2026-10-29-p9-a/resultats/mesures-0/verdicts.json` (`6a026547`).

| Bras | ΔH | ΔE | ΔF_R | Verdict |
|---|---|---|---|---|
| F | 0,0043 | 0,0000 | −0,0026 | non_retenue |
| contrôle global | 0,0019 | −0,0079 | −0,0023 | non_retenue |
| A | 0,0015 | −0,0073 | −0,0032 | non_retenue |
| C | 0,0018 | −0,0054 | −0,0026 | non_retenue |

Seuil de la règle G : ΔH ≥ 0,005. Graines 1 et 2 non lancées (§9.4, D15).

#### Tableau 9 — Petit élève, 26 graphes Gemini (fidélité au professeur), lecture D2

Sources : `2026-10-30-petit-eleve/resultats/mesures/resultats.json` (`5463d532`).

| Système | rappel@30 | AP50 sans classe | objets/image (score ≥ 0,5) |
|---|---|---|---|
| 28×28_seed0 | 0,225 | 0,062 | 19,8 |
| 28×28_seed1 | 0,230 | 0,050 | 23,0 |
| 28×28_seed2 | 0,246 | 0,067 | 21,1 |
| 8×8_seed0 ‡ | 0,258 | 0,080 | 20,8 |
| 8×8_seed1 ‡ | 0,287 | 0,086 | 20,5 |
| 8×8_seed2 ‡ | 0,250 | 0,048 | 21,5 |
| a priori (rectangles fixes) | 0,258 | — | — |
| OWLv2 | 0,307 | 0,199 | — |
| YOLOE-v8-S texte (descriptif) | 0,152 | 0,116 | — |

Lecture D2 (bras 28×28) : Loc-, AP?, D+ → « pas de signal ». Débit, forwards seulement (lot 32) : élève complet 24,9 img/s, OWLv2 10,9 img/s (D = 2,29). Florence-2 : rappel 0,246 sur toutes ses boîtes. ‡ Bras 8×8 : secondaires, hors règle D2, vérifiés par Codex mais non cités par les Résultats (à relire avant usage).

## Figures

Les PNG sont produits par `notes/figures/make_figures.py` (non versionnés : `.gitignore`).

![Figure 1 — Phase 1 : écarts et IC95 sur ICAI et sur le Rijksmuseum ; aucune brique retenue.](figures/figure1_phase1_ecarts.png)

*Figure 1 — Phase 1 : écarts et IC95 sur ICAI et sur le Rijksmuseum ; aucune brique retenue.*

![Figure 2 — Non-transfert, descriptif ; sans cause établie.](figures/figure2_non_transfert.png)

*Figure 2 — Non-transfert, descriptif ; sans cause établie.*

![Figure 3 — A1-dev : transfert non établi.](figures/figure3_a1_dev.png)

*Figure 3 — A1-dev : transfert non établi.*

![Figure 4 — P9-A, graine 0 : aucun bras retenu.](figures/figure4_p9a.png)

*Figure 4 — P9-A, graine 0 : aucun bras retenu.*

![Figure 5 — Petit élève : les bras 28×28 ne battent pas l'a priori ; bras 8×8 en panneau descriptif.](figures/figure5_petit_eleve.png)

*Figure 5 — Petit élève : les bras 28×28 ne battent pas l'a priori ; bras 8×8 en panneau descriptif.*
