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
