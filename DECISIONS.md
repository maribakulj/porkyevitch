# Décisions de la boucle wA:p1

| date | décision | avis Grok | contre-expertise Codex | raisons |
|---|---|---|---|---|
| 29/10 | **D1 — Cap production et ordre des jalons.** (1) Un encodeur partagé, supervisions séparées : la tête Iconclass apprend sur les vraies étiquettes, le graphe sur les pseudo-étiquettes ; le lien graphe → Iconclass est une expérience. (2) Les trois régimes de Marcel gardés, mais le régime « commun » doit partager quelque chose d'entraînable (adaptateur commun ou couplage explicite) : têtes disjointes sur encodeur figé = aucun transfert. (3) Ordre : jalon 2 (pilote graphes) → petit élève du jalon 5 en parallèle du jalon 3 → données à l'échelle (4) → élève consolidé (5) → article et reproductibilité (6) ; un petit élève sur les graphes du pilote AVANT de payer 5 000 graphes. (4) Références à battre : OWLv2 base et Florence-2, chronométrés et mesurés sur apprentissage/dev, jamais choisis sur le test IconArt. (5) Cibles indicatives, non bloquantes : prototype T4 ≥ 2 img/s, CPU 8 vCPU ≥ 0,2 img/s. (6) Consigne des graphes à enrichir en relations d'action (Haiku et Gemini restent trop spatiaux). (7) Haiku validé (test de 20) devient source d'étiquettes candidate, à appeler en non interactif comme Gemini. | Grok p7 : assemblage de briques connues ; porte de débit et de licence avant l'élève ; Iconclass à part ; chronométrer OWLv2 et Florence-2 sur IconArt ; pas de tête de relations sans inventaire figure–symbole | Codex p4 : PoC d'abord, licences notées sans veto ; supervisions séparées ≠ encodeurs séparés ; adaptateur partagé pour le régime commun ; chronométrer sur train/dev ; petit élève avant 5 000 graphes ; cibles 2 img/s T4, 0,2 img/s CPU | Priorité article de Marcel ; Codex corrige le défaut de conception des trois régimes ; Grok a raison sur la mesure du débit et des références, pas sur la licence (hors sujet pour l'instant). |
| 30/10 | **D2 — Passage à l'échelle des annotations.** (1) Pas de campagne de 5 000 graphes maintenant. (2) Petit élève d'abord, version 1 de la préinscription intégrant les réserves de Codex (26 images groupées ≠ 244 observations indépendantes ; référence Gemini ≠ vérité humaine ; un échec sur 106 graphes Gemini ne réfute ni Haiku ni la distillation ; contrôle de surapprentissage ; Florence-2 gardée comme seconde référence). (3) Tranche de **300 images d'apprentissage annotées par Haiku S1b**, stratifiée par chapitre Iconclass, lancée **en parallèle** du petit élève (coût ≈ 30 min avec trois annotateurs) ; son usage pour l'entraînement reste conditionné à la porte du petit élève (lecture D2 de sa préinscription), mais elle sert dès maintenant à mesurer S1b contre Gemini et à donner des actions que les graphes Gemini n'ont pas. (4) Tirage stratifié par un script relu (Grok p2, Codex p4). | Grok p7 : petit élève d'abord sur les graphes Gemini, quelques centaines de S1b seulement si signal | Codex p4 : favorable petit élève puis tranche S1b de 300 ; défavorable à 5 000 immédiats ; réserves ci-contre | Le coût de 300 graphes Haiku est négligeable et ils sont nécessaires quel que soit le verdict (les 106 graphes Gemini n'ont presque pas d'actions) ; lancer en parallèle gagne une itération. L'écart avec l'ordre « puis » de Codex est assumé : seule l'utilisation des 300 graphes pour l'entraînement attend la porte. |
| 30/10 | **D3 — Codes rares et profondeur, d'après le diagnostic.** Préinscrire deux petits essais sur les vecteurs et grilles déjà calculés, validation seule, référence B = T-Z : (1) **vote de voisins limité aux codes rares** (R5-20 = codes à 5-20 exemples d'apprentissage, explicitement dans V ; n_brut ≠ n_fermé ; codes hors V non émissibles) ; (2) **tête des seuls enfants** (un classifieur par parent, rappel conditionnel compté quand le parent est dans la FERMETURE prédite). Publier couverture du parent, rappel conditionnel, rappel total et faux positifs ; l'H-F1 reste le juge (règle G), et la voie R (codes rares) pour l'essai (1). Pas de CAT, CHiLS, RAC complet ni perte distribution-balanced de bout en bout pour l'instant. | Grok p7 : les deux défauts ne se réparent pas par le même levier ; ne pas commencer par CAT/CHiLS/RAC/DB (classe unique par image, ou remontée au parent qui a déjà perdu avec T-H) ; deux plus petits essais ci-contre | Codex p4 : favorable, avec les corrections ci-contre ; le Jaccard des erreurs ne prouve pas un manque de traits ; +0,0013 ne borne pas les autres ajustements | Les deux essais visent directement les deux défauts mesurés, coûtent peu (traits gelés) et n'ouvrent aucun test. |

## D4 (30/10/2026) : mesure phase 1, désérialisation de frozen.json pendant l'étape dev

Constat : `mesure_phase1.py --stage dev` analyse le JSON entier de frozen.json, branche test comprise, puis ne garde que le dev
(limite 1 du README de wA:pH). Décision de wA:p1 : accepté à condition qu'aucune vérité de test ne soit lue au-delà de la
désérialisation, ni écrite, ni journalisée. Contre-vérifié par Codex p4 et Grok p2 (sentinelle de la branche test absente des 32
fichiers écrits et des journaux). Étape dev lancée sous ces feux verts (sorties, commit 776d316).
Désaccord : Grok p7 (relecteur supplémentaire) bloque ce point (`porkyevitch-mesure-phase1-grok.md`). Question posée : un chemin
concret de fuite vers les planches, dev.json, les journaux ou une décision humaine. S'il en montre un, le dev sera refait avec une
projection dev seule, épinglée ; sinon, le désaccord reste consigné ici.
Réponse de Grok p7 (30/10) : aucun chemin concret ; « mesure_phase1.py:141 ne garde que doc["dev"]["items"], la ligne 142 fait
del doc, et les planches, dev.json et les journaux n'écrivent que des objets issus de cette liste ». **D4 maintenue** : le dev
n'est pas refait ; le désaccord de principe reste consigné.

## D5 (30/10/2026) : présentation des relectures et des regards dans l'article

Toutes les relectures de code, les regards de planches et les audits sont faits par des modèles (Claude, Grok, Gemini, Codex),
jamais par un humain : l'article le dit explicitement, en nommant les rôles et les modèles, et ne présente aucun regard comme
une annotation experte. Pas de regard humain sur un sous-ensemble pour l'instant (Marcel n'annote pas) : c'est une limite écrite.
Les comptes O/A/E sont présentés comme un audit par modèles, avec l'accord entre juges (53/100) et la règle écrite d'avance.

## D6 (30/10/2026) : usage de la tranche 300 S1b (après challenge Grok p7 et contre-expertise Codex p4)

M0 est **descriptif, sans porte** (à lancer après l'audit Codex de ses octets). Les interrupteurs de la note v1 sont abandonnés.
La v2 donne la direction (juge principal = 26 Gemini, consensus Haiku = colonne de fidélité, aucune décision d'achat sur +0,05),
mais le devis est à préciser avant toute dépense (v3 de wA:pH) : aucune garantie de puissance sur 60 images ; Gemini et
consensus mesurent la fidélité, pas la localisation ; les relations du petit élève v1 SONT entraînées, donc les retirer est une
ablation nommée qui exige de réentraîner E0 ; poids objet ½ ≠ cible de probabilité ½ (préciser la perte, le « pas d'objet » et
l'union au-delà de 30) ; E1′ ne sépare pas la quantité du professeur. L'entraînement sur les 300 reste conditionné par D2 (porte
du petit élève). Rapports : porkyevitch-tranche300-grok.md, porkyevitch-tranche300-codex.md.

## D7 (30/10/2026) : P9-A, gradients non finis en fp16 (devis échoué au 12e pas du bras G)

Diagnostic wA:pH : vraisemblablement un dépassement fp16 normal que GradScaler sauterait, mais que update() interdit. Correctif
dans p9a_run.py seulement (le blanc 2 reste valable) : variante update_amp qui laisse GradScaler sauter un pas à gradients non
finis, vérifie que les poids n'ont pas changé et journalise le saut. Seuils fixés avant relance : arrêt si l'échelle passe sous 1
(divergence) ; plafond de 1 % de pas sautés par époque et par bras, au-delà amendement exigé. Relecture Grok p2 et audit Codex p4
avant la relance du devis.

## D8 (30/10/2026) : baselines de production (après avis Grok p7 et contre-expertise Codex p4)

YOLOE-v8-S en mode texte (8 requêtes figées) est ajouté au protocole T4 du petit élève : débit mesuré par nous sur les 96 images
d'entraînement et rappel sans classe sur les 26 graphes Gemini, à côté d'OWLv2 et de Florence-2, descriptif, sans changer D2.
RF-DETR Nano en option de débit seulement ; les autres modèles hors du test minimal. Les débits publiés (TensorRT, autre matériel)
ne sont jamais repris comme résultats. À figer avant les 26 : poids, versions, NMS, seuil ; préparation du texte hors régime
établi, même portion de pipeline chronométrée. Préalable : corriger le chronométrage de l'élève (no_grad/autocast, comme OWLv2)
et le chargement de Florence-2. Gemini mesure la fidélité, pas la vérité.

## D9 (30/10/2026) : arbitrages de la note tranche 300 v3 (wA:pH 4f8359b)

(3) Relations : **détecteur sans relations pour tous les bras du test**, E0 réentraîné sous ce code, en ablation nommée ; le petit
élève v1 (avec relations) reste une colonne de comparaison. Raison : M0 et le comptage montrent que l'instabilité de S1b est
dans la détection (4 objets sur 10 non retrouvés), et la question posée est « ces données aident-elles la détection ». Les
relations restent dans le produit (petit élève v1) ; leur apport sera une autre brique.
(4) Références séparées comme proposé. **Option des 60 Gemini acceptée** : passe Gemini (agy -p, une session par image, lecture
d'image vérifiée) sur les 60 de validation interne, figée AVANT toute sortie d'entraînement ; juge principal = 86 images
(26 + 60), fidélité au professeur Gemini, pas vérité de localisation (D5).
Le reste de la v3 est adopté. La préinscription viendra après la porte D2 (complet du petit élève).

## D10 (30/10/2026) : priorités après la phase 1 (Grok p7 challenger, contre-expertise Codex p4)

1. L'article publie des recettes et un artefact **exploratoires** : aucune brique retenue, aucun gain démontré sur le
   Rijksmuseum ; T* et TK améliorent l'accord avec le catalogue ICAI seulement. Un F1 mesure un accord de catalogue.
2. Référence Iconclass du petit élève et de la carte : **T\***. P9-A, A1 et D3 gardent T-Z comme référence, sans changer leurs
   règles ni leurs interdits, mais ce sont des **sondes de validation**, pas une tête à publier.
3. Cause du non-transfert : **non établie**. La lecture de Grok (codes fréquents profonds absents des notices Rijksmuseum) n'est
   qu'une hypothèse : fréquence > 100 et profondeur sont deux marges, pas leur croisement. Diagnostic à préinscrire, dev et
   validation seulement, selon le protocole de Codex (R_tête contre R_vote pondéré, table appariée, contrôle de prévalence,
   croisement fréquence × profondeur), script audité avant lancement.
4. Priorités : ce diagnostic et le petit élève, puis les sondes P9-A / A1 / D3 déjà prêtes.

## D11 (30/10/2026) : noms Kaggle

Kaggle a supprimé les jeux de données mabaku/porky-* (nom pris pour NSFW ; c'est une référence à Pynchon). Ce n'était pas la
modération des images de planches, contrairement à l'hypothèse du journal. Désormais tout jeu de données ou noyau Kaggle se
nomme **pkyevitch-*** ; les noyaux porky-* encore vivants sont rapatriés puis recréés sous le nouveau nom quand on les relance.
Les pilotes qui citent un chemin /kaggle/input/…/porky-… doivent être amendés (relecture) avant toute relance.
Précision (Marcel, 30/10) : la cause exacte n'est pas sûre ; le nom « porky » est probable, mais les images de nus dessinés
ont pu jouer aussi. Double prudence : noms pkyevitch-* ET images de planches ou d'évaluation potentiellement sensibles
transmises dans une archive .bin épinglée (que Kaggle n'ouvre pas), comme pour la mesure de la phase 1.

## D12 (30/10/2026) : audit de remplacement quand Codex est indisponible (accord de Marcel)

Quand Codex p4 n'a plus de crédits (ou ne répond pas), l'audit final avant lancement est fait par un Grok qui n'a PAS fait la
première relecture de ces octets (p7 ou p3 selon disponibilité), avec la même exigence (rapport, FEU VERT ou BLOCAGE, pins).
Le lancement peut alors partir. À son retour, Codex contre-vérifie ces audits AVANT que les résultats servent à une décision,
une publication ou une étape suivante. Pendant une indisponibilité, la boucle avance aussi sur tout ce qui ne demande pas
d'audit (dossiers de lancement, préinscriptions, rédaction).

## D13 (30/10/2026) : relectures par sous-agents Sonnet (Marcel)

Marcel juge les Grok lents et inadaptés à la relecture. Désormais, **toutes les relectures** (code, diffs, sorties, regards
de planches) sont faites par des **sous-agents Sonnet** lancés par wA:p1 (Agent, model=sonnet), indépendants, avec un brief
complet et un rapport écrit dans ~/Documents/reviews/porkyevitch-*-sonnet.md. L'audit final de Codex p4 avant lancement reste
inchangé (D12 : si Codex est indisponible, un second sous-agent Sonnet indépendant fait l'audit de remplacement). Les Grok
ne relisent plus ; leurs rôles sont à réaffecter (littérature, challenger).

## D14 (30/10/2026) : P9-A, gel.json contient le score de B

gel.json porte B_reference {H_F1 0,58908 sur 4 241 éligibles}, alors que RUNNER.md dit « aucune mesure ». Décision wA:p1 :
non bloquant. Ce score est celui de la référence B (T-Z), déjà publié par le devis et le diagnostic (contrôle d'intégrité
autorisé sur B seul) ; aucun score de bras (A, C, F, contrôle) n'y figure, et la sélection est scellée avant le gel
(selection_sha256 repris dans gel.json). Écart déclaré au RUNNER ; Codex le contre-vérifiera. gel.json = 13f75f3a….

## D15 (30/10/2026) : P9-A, graines 1 et 2 non lancées

Règle préinscrite §9.4 appliquée mécaniquement : aucun bras G/R à la graine 0 (verdicts.json 6a026547…) ⇒ graines 1 et 2
non lancées ; graine 0 publiée comme résultat exploratoire négatif. (Relu par Sonnet ; Codex contre-vérifiera.)

## D16 (30/10/2026) : suite du petit élève après D2 (Grok p7 challenger, contre-expertise Codex p4)

Le petit élève v1 (tête sur C-RADIO gelé) s'arrête là (D2 « pas de signal »). Une seule brique suivante, préinscrite :
**transfert de YOLOE-v8-S**, couches de localisation explicitement entraînées sur les 106 graphes Gemini, budget global
écrit d'avance, même règle Loc/AP/D, mêmes 26 images (donc exploratoire : ces 26 ont déjà servi de juge). Aucune ouverture
automatique de la campagne Haiku (300) ; OWLv2 n'est pas « adopté » par défaut. Si encore Loc−, la piste élève s'arrête.
Rapports : porkyevitch-apres-d2-grok.md, porkyevitch-apres-d2-codex.md. Licence AGPL de YOLOE notée, pas une porte.

## D17 (30/10/2026) : partie Iconclass après la phase 2 (Grok p7, contre-expertise Codex p4)

Une seule mesure, puis écrire : A1 avec q figé (eta = 1) et son seuil scellé au réglage, sans réajustement, mesuré une fois
en H-F1 sur le dev Rijksmuseum (301 images, 239 composantes ; pas les 211 paires de D10), contre B = T-Z (comparaison
principale) et T* (référence figée), bootstrap par composantes, règle écrite d'avance ; aucune ligne de test, aucun réglage
sur le dev. Pas de kNN en produit ni de Hill dans ce tour. Rapports : porkyevitch-apres-phase2-grok.md / -codex.md.

## D18 (30/10/2026) : comparaison avec des VLM (accord de Marcel)

Marcel lance la comparaison VLM contre modèle rapide (objectif initial). Systèmes : **Haiku 5.5** (VLM bon marché, déjà
validé chez nous pour les graphes), **Gemini 3.8 Flash** (déjà dans le dispositif), **Opus 5.5 sur une petite tranche
seulement** (repère de plafond, pas candidat de production). Préinscription v1 de wA:pH (vocabulaire fermé principal,
invalidité, refus, répétabilité, coûts et temps symétriques) à mettre en v2 avec ces trois systèmes ; famille ajustée.
Images : Gemini a déjà reçu ces images ICAI/dev aux pilotes ; même pratique, déclarée. Relecture Sonnet puis audit Codex.

## D19 (30/10/2026) : amendement données du test YOLOE (Marcel : 106 images trop peu ; Grok p7, contre-expertise Codex)

Entraînement en deux temps (recommandation Codex) : pré-apprentissage externe sur DEArt (cc-by-nc-sa-4.0, usage interne,
sans les 1 066 fichiers Rijksmuseum) et ODOR (cc-by-4.0, après jointure de source), puis adaptation sur 106 Gemini + 240
S1b d'apprentissage. Avant tout usage : détection de copies entre DEArt/ODOR et nos réserves (ICAI, juges, banc gelé),
recouvrement ICAI mesuré. Correspondance des 70 noms DEArt et 139 classes ODOR vers les 8 super-catégories GELÉE avant
l'entraînement, supervision partielle explicite (ce que deviennent les boîtes « autre »). Juge = 79 images (26 + 53),
références recalculées, 26 et 53 publiés séparément, lecture exploratoire ; les 60 de validation interne réservés entiers.
Préparation des images sur Kaggle CPU seulement (~18,2 Go d'archives DEArt), jamais sur le Mac ; plafond 14 400 s T4 avec
nouveau devis complet. Licence notée, pas une porte. Rapports porkyevitch-yoloe-donnees-grok.md / -codex.md.
