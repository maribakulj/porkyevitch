# Méthodes (v6, privé)

30 octobre 2026. Claude wA:pH, pour wA:p1. La v2 ajoute les méthodes **réellement exécutées** en phase 2 (section 6) : A1 et A1-dev, D3, P9-A avec la règle des graines, le diagnostic de non-transfert, le petit élève avec la règle D2, et l'audit O/A/E. Elle ajoute aussi les incidents qui touchent la méthode (section 8) et le protocole de relecture mis à jour par D12 et D13 (section 9). La v1.1 reste intacte à côté.

La v3 (relecture hostile de Grok p7, demande de wA:p1) : A1-dev est décrite comme **mesurée** ; le plafond de 20 objets est situé au tirage, après le filtrage ; la version des relecteurs Sonnet est consignée ; les contre-vérifications de Codex sont faites. La v2 reste intacte.

La v4 corrige l'audit factuel de Codex (`~/Documents/reviews/porkyevitch-article-codex.md`, B1–B7, N1–N12) sans nouveau calcul : attribution des comptes du filtre au filtre combiné, chronologie du test ICAI, statut des jugements O/A/E, deux contrôles d'A1, repli de précision de D3, portée de la phase 2. La v3 reste intacte.

La v5 (finitions, demande de wA:p1) : citations primaires dans le texte (références : `article-references-v1.md`) et renvoi à Résultats v3 corrigé. Rien ne change au fond ; la v4 reste intacte. La v6 ajoute seulement l'année de la référence du bootstrap ; la v5 reste intacte.

Ce texte décrit des **méthodes**. Les chiffres de résultats sont dans `article-resultats-v3.md`. Les sources sont les préinscriptions, sous `~/porkyevitch/experiences/` et `~/porkyevitch-maths/experiences/`, et les décisions de `~/porkyevitch/DECISIONS.md`, désignées par leur numéro. Les points à vérifier ou à trancher sont marqués [à vérifier].

## 0. Qui fait quoi : des modèles, pas des experts humains

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

## 1. Données

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

## 2. Représentation et têtes

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

## 3. Mesure

**Hiérarchie.** Elle est lue directement dans la notation : les ancêtres d'un code sont ses préfixes de jetons (chiffres, lettres, parenthèses), partie par partie pour un code composé. Ce n'est pas l'arbre officiel d'Iconclass. Une comparaison avec cet arbre n'est pas reprise dans cet article.

**Projection.** Le chapitre 86 (proverbes et locutions) est retiré de la vérité comme des prédictions. Une image dont la vérité projetée est vide est exclue du dénominateur. Il en reste 787 sur 788 au test ICAI, 4 241 sur 4 265 en validation, et toutes au test du Rijksmuseum, où c'est un critère d'éligibilité.

**Mesure principale : le F1 hiérarchique (H-F1).** Pour une image, c'est le F1 entre la fermeture par ancêtres de la vérité et celle de la prédiction. Le H-F1 rapporté est la moyenne de ce F1 sur les images. La prédiction s'obtient par un seuil, puis par la suppression des ancêtres déjà impliqués, puis par la projection.

**Mesures secondaires de la phase 1**, toutes descriptives (en phase 2, F_R sert en revanche de juge à la voie R de D3 et de P9-A) :
- le F1 des codes exacts ;
- le F1 par tranche de profondeur (1–2, 3–4, 5 et plus) ;
- le F1 par fréquence d'apprentissage du code (5–20, 21–100, plus de 100) ;
- le rappel des codes rares ;
- la part des vérités hors du vocabulaire, que toute tête à vocabulaire fixe ne peut pas prédire.

## 4. Protocole de la phase 1

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

Les deux bornes sont prises au niveau 1 − 0,05/7 ≈ 99,29 % (correction de Bonferroni sur la famille). Elles viennent d'un bootstrap (Efron et Tibshirani, 1994) de 10 000 tirages, apparié entre systèmes. Au Rijksmuseum, on tire des composantes entières, et la moyenne est recalculée sur les images des composantes tirées ; à ICAI, on tire des images. Les intervalles bilatéraux à 95 % sont publiés à titre descriptif.

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

## 5. Diagnostic sur la validation

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

## 6. Méthodes de la phase 2, exécutées

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

## 7. Ce que ces méthodes ne permettent pas de dire

- Un gain de F1 est un gain d'accord avec le catalogue, pas une preuve de justesse visuelle.
- Toutes les séries sont exploratoires. La phase 1 a une graine unique et des tests déjà consultés pour ICAI. La phase 2 travaille sur la validation et un dev déjà consultés. Aucune revendication confirmatoire n'est possible sans un banc jamais consulté.
- Les relectures, regards et audits sont faits par des modèles (section 0), **jamais par un expert humain**. **Aucun regard humain n'est prévu pour l'instant** (D5). Les proportions de l'audit (O, A, E) sont celles de juges-modèles ; elles ne corrigent aucun score.
- Les graphes de scène sont jugés par fidélité à un professeur, pas par une vérité de localisation.
- Le diagnostic de non-transfert est descriptif. Il ne départage pas catalogue et vision, et n'établit pas la cause du non-transfert (D10).

## 8. Incidents qui touchent la méthode

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

## 9. Protocole de relecture (D12, D13)

1. **Préinscription** : écrite avant le code. Elle fixe les règles de lecture, les populations, les graines et les plafonds.
2. **Relecture** : depuis le 30/10 (D13), toutes les relectures (code, diffs, sorties, regards de planches) sont faites par des **sous-agents Claude Sonnet indépendants**. Ils sont lancés par l'orchestrateur avec un brief complet, et chacun écrit un rapport.
3. **Audit final avant lancement** : Codex p4. Si Codex est indisponible, l'audit est fait par un second sous-agent Sonnet indépendant, qui n'a pas fait la première relecture (D12, D13). Le lancement peut alors partir.
4. **Contre-vérification** : au retour de Codex, il contre-vérifie ces audits **avant** que les résultats servent à une décision, à une publication ou à une étape suivante. Les résultats en attente sont marqués comme tels dans les `LECTURE.md` et dans les Résultats. Au 30/10, toutes les contre-vérifications de la phase 2 (non-transfert, A1, A1-dev, D3, P9-A, petit élève) sont faites et **conformes** (wA:p1).
5. **Lancement et lecture** : chaque étape est lancée par l'orchestrateur, sans enchaînement automatique. Les sorties sont relues, puis on rédige une `LECTURE.md`, avec les lectures permises et interdites, avant toute suite.
6. **Décisions** : elles sont consignées dans `DECISIONS.md`, avec l'avis d'un challenger (Grok) et la contre-expertise de Codex.
