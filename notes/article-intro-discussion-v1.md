# Introduction et Discussion (v1, privé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1. La v1 intègre la relecture hostile de Grok p7 (`~/Documents/reviews/porkyevitch-article-relecteur-hostile-grok.md`) : l'objection du filtre du banc, une claim plus étroite, les contre-vérifications de Codex faites. La v0 reste intacte.

**Sources.**
- La structure proposée par Grok p7 (`~/Documents/reviews/porkyevitch-article-structure-grok.md`), écrite avant la phase 2 et mise à jour ici par les résultats de la phase 2.
- L'état de l'art de Grok p7 (`porkyevitch-etat-art-grok.md`, `porkyevitch-etiquettes-manquantes-grok.md`). On n'y prend que les pages qu'il a ouvertes, et les chiffres d'auteurs restent des chiffres d'auteurs.
- `~/porkyevitch/DECISIONS.md`, Méthodes v3 et Résultats v2.

**Aucun chiffre nouveau** : les chiffres cités sont ceux de Résultats v2 et de Méthodes v3, et renvoient à sa section.

**Titre de travail** (Grok p7, mis à jour) : *Recettes exploratoires sur encodeur gelé pour l'Iconclass : un accord de catalogue sur ICAI, aucune brique retenue sur un banc du Rijksmuseum gelé, et des diagnostics.*

---

## Introduction

**Le problème.** Iconclass décrit le contenu des images par une notation hiérarchique de dizaines de milliers de codes. Les catalogues l'emploient pour dire ce qu'une œuvre représente : personnages, scènes, objets, attributs. Prédire ces notations à partir de l'image seule pourrait un jour aider l'indexation des collections. Cet article ne propose pas un tel système : il mesure si des recettes simples, sur un encodeur gelé, améliorent l'accord avec un catalogue, et sur quel banc. Le vocabulaire étudié est réduit aux 7 907 codes vus au moins cinq fois en apprentissage, avec leurs ancêtres (Méthodes §2).

Trois traits rendent la tâche difficile et sa mesure délicate :
- **la hiérarchie** : un code plus précis implique ses ancêtres ;
- **la longue traîne** : la plupart des codes sont rares ;
- **le catalogue incomplet** : une notation absente de la notice n'est pas une notation fausse.

Un F1 calculé contre le catalogue mesure donc un **accord avec le catalogue**, pas une justesse visuelle.

**Ce qui existe.** Les travaux dont le texte a été ouvert traitent des tâches voisines, avec d'autres métriques. Leurs chiffres ne se convertissent pas en F1 hiérarchique d'image :
- **Springstein et al. (WACV 2024)** classent à grande échelle des concepts Iconclass, après un pré-apprentissage image–texte, et mesurent un mAP par concept ;
- **Banar, Daelemans et Kestemont (2021)** apparient des œuvres à des définitions de codes. L'image seule y reste loin du texte ;
- **Cetinić (2021)** produit des légendes iconographiques ;
- **ArtDL, IconArt et DEArt** détectent ou classent quelques motifs ou classes sur la peinture.

Aucun de ces protocoles ouverts ne mesure un F1 hiérarchique d'accord avec un catalogue sur une famille de comparaisons préinscrite, avec un second banc tenu hors des choix.

Sur les étiquettes manquantes, la littérature distingue plusieurs régimes :
- l'apprentissage positif–non étiqueté (Bekker et Davis) ;
- l'apprentissage à une seule positive (Cole et al., Zhou et al.) ;
- les pertes qui tolèrent les faux négatifs (Hill et SPLC, Zhang et al.) ;
- l'évaluation sous propension (Schultheis et al.) et l'audit des étiquettes d'un test (Northcutt et al.).

Elle montre qu'une correction des scores par un taux d'oubli unique n'est pas identifiée quand la propension d'oubli dépend du contenu.

**La question.** Sur des traits gelés d'un encodeur visuel général (C-RADIOv3-L), avec une famille de comparaisons et une règle de retenue écrites avant la mesure, une recette de tête améliore-t-elle l'accord hiérarchique avec le catalogue **à la fois** sur le test ICAI et sur un banc extérieur du Rijksmuseum ? Si non, que peut-on dire de l'échec, sans rouvrir les tests ?

**Ce que nous apportons**, en restant à la mesure de ce qui a été fait :
1. **Un protocole exploratoire et un artefact scellés.** Une famille de sept comparaisons est fixée d'avance. La règle de retenue est conjointe : une borne unilatérale sur le Rijksmuseum, et une non-infériorité sur ICAI. Le bootstrap est apparié, par image pour ICAI et par composante pour le Rijksmuseum. Les prédictions sont gelées avant l'ouverture des scores. Toutes les relectures et tous les audits sont faits par des modèles, et sont déclarés comme tels.
2. **Un banc du Rijksmuseum gelé.** 1 201 images en 908 composantes de dépendance, plus un dev de 301 images. Le banc n'a jamais servi à choisir une tête. Il est filtré contre l'apprentissage : toute composante qui contient une image proche d'une image d'apprentissage (hachage perceptuel, ou cosinus C-RADIO ≥ 0,95) est retirée. Ce filtre définit ce que le banc mesure : l'accord **hors des quasi-doublons**, pas le musée tel qu'il se présente.
3. **Des résultats négatifs propres.** Aucune brique n'est retenue en phase 1. En phase 2, trois sondes sur la validation ont été préinscrites puis mesurées :
   - A1, la décision par maximisation du F1 sous une loi de voisins, bat la référence sur la validation, mais son gain tient surtout à la loi tirée des voisins ;
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

## Discussion

**Ce que les résultats disent.**
- **L'accord ICAI ne passe pas au Rijksmuseum.** T\* et TK améliorent l'accord avec le catalogue ICAI, avec des intervalles entièrement positifs. Leurs écarts sur le Rijksmuseum ont des intervalles qui contiennent 0. Les recettes spatiales y perdent (Résultats §1). Aucune brique n'est retenue selon la règle écrite d'avance.
- **Le seul gain de la phase 2 reste un gain de validation.** A1 bat B sur V-diagnostic, mais un seuil sur la même loi de voisins fait aussi bien. Le décodeur n'est donc pas le gain (§4). Cette règle, figée et mesurée une fois sur le dev, n'établit pas de transfert : l'écart est négatif et l'intervalle contient 0 (§4 bis).
- **Ce n'est pas une réfutation.** Un intervalle qui contient zéro ne réfute pas toute amélioration. Le dev est petit, et il avait déjà été consulté.
- **Ce que le banc exclut par construction.** C'est l'objection principale à ce résultat négatif, et nous la tenons pour sérieuse. Trois faits se tiennent : le banc retire, avec leur composante entière, les images à cosinus C-RADIO ≥ 0,95 avec l'apprentissage (84 composantes, Méthodes §1) ; 48 % du gain d'A1 sur la validation vient de la strate cos ≥ 0,95, qui réunit 30 % des images (§4) ; cette strate est vide sur le dev (§4 bis). Une partie du gain de validation d'A1 peut donc venir de quasi-doublons, un régime que le banc a retiré par construction, avec l'encodeur même qui définit les voisins. C'est une lecture compatible, pas une preuve : la proximité C-RADIO n'est pas une copie, et A1 n'a pas été mesurée sur les proches retirés. Le négatif d'A1-dev se lit donc étroitement : sur un banc dont on a retiré les proches au sens de C-RADIO, la règle figée ne bat pas B. Il ne dit pas que la règle échouerait sur les notices du musée avant ce filtre.
- **Deux idées de tête ne battent pas la référence dans leur régime.**
  - D3 : le vote de voisins sur les codes rares coupe des faux positifs mais perd des vrais ; il porte pourtant un signal, puisqu'il bat une mémoire permutée. La tête des enfants, routée par le parent, perd en rappel conditionnel (§5).
  - P9-A : l'imbrication de la hiérarchie dans les zones n'apporte rien de mesurable par rapport au même calcul après agrégation (§6).
- Ces négatifs sont bornés à leurs recettes : un poids non réglé, dix époques, une graine.

**Ce que les diagnostics suggèrent, sans l'établir.**
- **Le catalogue.** Selon des juges-modèles (deux regards d'accord sur 53 couples sur 100, puis un arbitre), une grande part des prédictions sûres comptées fausses sont vraies au sens large, en oubli précis ou en code générique (§2). Un F1 de catalogue sous-estime donc la justesse visuelle d'une quantité inconnue. La littérature sur les étiquettes manquantes dit pourquoi on ne peut pas la corriger par un taux unique : la propension d'oubli n'est pas constante, et le rappel corrigé demanderait le nombre vrai de positifs. Nous publions les trois comptes plutôt qu'une correction.
- **Le non-transfert.** Le diagnostic D10 ne soutient pas l'idée simple que les codes fréquents et profonds seraient absents des notices du Rijksmuseum : les voisins d'apprentissage les portent pour une majorité de paires, bien au-dessus du hasard (§3). La tête laisse un écart comparable entre ce que portent les voisins et ce qu'elle rend, sur les deux banques. Sur les codes communs, l'écart entre banques se réduit, ce qui est compatible avec un effet de composition.

  Deux précautions (Codex) :
  - une union de voisins est une disponibilité sans coût en faux positifs, et l'écart disponibilité–rappel **n'est pas un gain récupérable** ;
  - ni la cause catalogue ni la cause vision n'est établie (D10).

**Les distillations de graphes de scène.** Le petit élève, une tête légère sur l'encodeur gelé, ne bat pas un a priori de rectangles fixes en rappel, et reste loin d'OWLv2 en précision moyenne, tout en étant plus rapide (§7). Le juge est la fidélité au professeur Gemini, sur 26 images, et non une vérité de localisation. Par la règle écrite d'avance, ce prototype ne justifie pas une campagne d'annotation à l'échelle. Il ne réfute ni le second annotateur ni la distillation. La suite décidée (D16) est une seule brique préinscrite : le transfert d'un détecteur existant.

**Limites.**
- **Tout est exploratoire.** Il y a une seule graine par série, sauf la tête des enfants de D3 et le petit élève, à trois graines. La validation ICAI et le dev du Rijksmuseum ont été consultés plusieurs fois, et les tests historiques une fois. Aucune conclusion confirmatoire n'est possible sans un banc jamais consulté.
- **Les juges sont des modèles.** Relectures, regards de planches, audit et professeurs de graphes sont des modèles de langage multimodaux, dont les biais peuvent être communs. Aucun regard humain n'a été fait (D5).
- **La mesure est un accord de catalogue.** Elle dépend des conventions de chaque catalogue et de sa complétude.
- **Les incidents sont déclarés** (Méthodes §8) : la lecture d'une ligne de métadonnées du test, sans vérité ; les suppressions de jeux par Kaggle ; et des défauts de code trouvés par les relectures, tous corrigés avant les mesures concernées.
- **Les vérifications sont faites par des modèles.** Les contre-vérifications de Codex des Résultats §3 à §7 sont toutes faites et conformes (Résultats §9). Elles vérifient le code et les lectures ; elles ne valent pas une revue par des pairs.

**Ce qui suivrait, si l'on continue.**
- **Mesurer la justesse visuelle** demanderait un regard humain préinscrit, sur un échantillon stratifié du dev.
- **Tester l'effet des négatifs faux du catalogue** se ferait par une perte qui les tolère (Hill, ou l'ignorance des non-observés), jugée par un regard du même dessin que l'audit, et non par le F1 du catalogue. Ce n'est qu'une hypothèse : ce diagnostic ne l'identifie pas.
- **Toute revendication de transfert** demanderait un banc neuf.
- **Mesurer A1 avec et sans les proches**, sur une population qui garde les quasi-doublons et les marque, dirait quelle part du gain vient d'eux. Ce banc ne le permet pas.

Aucune de ces suites n'est engagée par cet article.
