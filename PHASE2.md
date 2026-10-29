# Phase 2 : pistes pour la tête Iconclass (plan à choisir, 28/10/2026)

Demande de Marcel (28/10) : rassembler en un seul endroit les pistes explorées ailleurs (étude des emblèmes `~/etude-02`, caypollard,
xanto, revue « graphe de scène » du 17/10) et jamais reportées dans le plan Iconclass. Ce document n'autorise aucun calcul : chaque
piste choisie devient une **série préinscrite**, relue (Grok p2 puis Codex p4) avant tout essai, essai à blanc compris.

Colonnes à compléter : **vérif.** = Grok wA:p7 (dépôt, poids, licence, date, preuve sur l'art) ; **coût** = Codex wA:p6 (Kaggle T4,
mémoire, heures, stockage). Le reste est rempli par wA:p1 depuis les notes existantes.

## Point de départ (phase 1, série E0-E3)

- Tête MLP sur le vecteur C-RADIOv3-L (4096), train `davanstrien/iconclass-vlm-brillfull` (révision 8045366, CC0).
- Validation (5 % par groupes md5) : T* = T-long 0,5780 ; TK (vote des voisins) 0,5839 ; T-H (hiérarchie forcée) 0,5566 ;
  T-D (ML-Decoder sur les 64 zones) 0,5832 ; **T-Z (requête apprise sur les zones) 0,5891**, meilleure époque = 29/30.
- Les verdicts (test ICAI 788 + banc Rijksmuseum) ne sont pas encore ouverts. Une piste de phase 2 part de la **meilleure tête
  retenue** au verdict, ou de T* si aucune ne l'est.

Coûts : Codex wA:p6, `~/Documents/reviews/porkyevitch-phase2-couts-codex.md` (28/10). Correction : 94 324 = total encodé ; train ICAI = 86 216
(81 951 apprentissage + 4 265 validation, 4 241 évaluables).

## Juge commun (sans annotation)

- Score H-F1 hiérarchique sur la validation ICAI, puis sur le dev Rijksmuseum une fois le banc gelé ; tests fermés jusqu'au gel
  des prédictions de toute la série, comme en phase 1.
- Une piste « marche » si elle bat la tête de départ selon une règle écrite avant le calcul. Proposition de Codex (règle G) : branche
  ajoutée à la tête figée, gain H-F1 ≥ 0,005 sur toute la validation, F1 exact sans baisse de plus de 0,01, trois graines avant
  toute recommandation forte. Un échec d'une construction grossière
  ne réfute pas l'idée : chaque fiche dit ce qu'un échec réfuterait.
- Regarder des images réelles (planche de 12 écarts sur le dev) avant les chiffres.

## Les pistes

| # | piste | ce qu'on sait déjà | où | vérif. | coût |
|---|---|---|---|---|---|
| P1 | **ICARUS** : plus de données (19 sources, ~118 Go, CC BY 4.0, Zenodo 10.5281/zenodo.18980670) | Contient Emblematica Online ; audit des recouvrements obligatoire (préinscription architecture, « Hors de cette série ») | — | | audit métadonnées : 0 GPU, ≤ 1 h CPU ; puis +50 000 images : 3–8 h T4 |
| P2 | **Le savoir d'Iconclass côté étiquettes** : descriptions textuelles des codes (iconclass/data, CC0), plongement du graphe Iconclass (RDF2Vec, Node2Vec), tête « par similarité » qui peut prédire des codes rares ou jamais vus | caypollard H1 : un graphe porte une information complémentaire à l'image (15-18 % de voisins communs, MAP 0,364 contre 0,343 sur Emblematica) ; mélange simple > modèle appris. Attention aux fuites : le graphe ne doit contenir aucune annotation d'image du test | `~/caypollard/docs/RESULTS.md` | | aucune réextraction ; 0,5–2 h T4 + ≤ 4 h CPU ; graphe de concepts seul (jamais les vrais codes d'une image) |
| P3 | **Décodeur hiérarchique CAT** (Springstein et al., WACV 2024) | Prévu « plus tard » ; mAP par concept, non comparables à nos F1 | revue-sources/iconclass.md | | sonde 1–4 h T4 (16 384 images, 10 époques) ; complet 6–18 h T4 |
| P4 | **Poses des figures** comme entrées : ViTPose entraîné sur Human-Art, SDPose (MIT, évalué sur HumanArt) | Brique `vitpose-humanart` déjà dans l'atelier caypollard (utilisée pour Xanto) ; Human-Art : ViTPose-B 0,555 → 0,759 avec boîtes vraies, mais **la détection des personnes** est le goulot (0,270 → 0,410) ; Human-Art couvre danse, théâtre, acrobatie, cinéma + 15 scénarios artistiques | `~/etude-02/notes/sota_2026-10.md`, xanto-parties | | ViTPose-Human-Art : pilote 1–3 h, complet 4–16 h T4 ; SDPose : pilote 2–6 h, complet 8–40 h |
| P5 | **Traits plus fins par zone** : MATCHA, DIFT, Diffusion Hyperfeatures, SketchFusion (gravures au trait), DINOv3, C-RADIO 28×28 | T-Z montre que les zones aident (+0,011) ; « Telling Left from Right » : les traits confondent gauche et droite | sota_2026-10.md ; cadrage régions R2 | | C-RADIO 28×28 : pilote 1–3 h, complet 3–8 h T4 (cache 138 Go) ; DINOv3 2–7 h ; MATCHA/DIFT plus chers |
| P6 | **Régions appariées** (mission en cours) : R1 vérification de reprises, R3 vote Iconclass par zones ; ArtMiner, SegSwap, Shape-of-You, MARCO | Cadrage Codex p6 + littérature Grok p7 ; Marcel choisit R1 ou R3 | `~/Documents/reviews/porkyevitch-regions-*.md` | fait | fait |
| P7 | **Graphe de scène** comme entrées : OvSGTR (Apache 2.0, photos), relations de DEArt 2025 (art, générées automatiquement), SemArt-HOI (14 187 peintures, non publié), CompoVista / VisTCP (peinture chinoise) ; graphes « danse / spectacle » à rechercher | Revue du 17/10 : pas de vérité terrain de relations sur l'art ; Qwen 7B sans entraînement décrit surtout la disposition ; ici le juge est Iconclass, pas les relations | `experiences/2026-10-17-graphe-de-scene/` | | OvSGTR : pilote 1,5–6 h, complet 9–50 h T4 |
| P8 | **Adapter l'encodeur** (LoRA sur C-RADIO) | Écarté en phase 1 sauf si E3 montre une limite de l'encodeur ; à rediscuter après les verdicts | préinscription architecture | | pilote 3–10 h T4 ; complet 12–140 h, pas avant un débit mesuré |

## P9 : recherche de méthodes d'apprentissage propres à notre cas (demande de Marcel, 29/10)

Les pistes P1-P8 appliquent surtout des outils existants. P9 est un travail de recherche : partir de ce que notre cas a de
particulier et concevoir des méthodes d'apprentissage nouvelles, puis les construire et les tester sur des données réelles
(train et validation ICAI, Emblematica, dev Rijksmuseum après son gel). Responsable : Codex wA:p6 (maths, calcul) avec Grok wA:p7
(littérature, antériorité). Même discipline : problème formulé, hypothèse et règle de décision écrites avant le calcul.

Particularités de départ, à préciser par Codex :
- une seule étiquette par image (des codes) mais aucune zone : apprentissage à instances multiples sur les 64 zones ;
- une hiérarchie profonde et une très longue traîne (7 907 codes, beaucoup rares) : partage entre codes voisins, prototypes ;
- le changement de support (peinture, gravure, dessin, photo) : ce qui doit rester invariant et ce qui ne doit pas l'être ;
- les copies, en miroir ou non, et les chaînes de reprises : des paires positives gratuites pour un apprentissage contrastif ;
- les notices de musée (titres, descriptions, créateurs) comme supervision faible et bruitée ;
- le texte des emblèmes et les descriptions des codes : apprentissage conjoint image-texte sur notre domaine.

Livrable d'abord : un document de recherche (2-3 méthodes neuves, chacune avec son idée, ce qui la distingue de l'existant, le
plus petit essai qui la réfuterait, son coût), pas de code lancé.

## Ordre recommandé par wA:p1 (à confirmer par Marcel)

1. **P1, audit des métadonnées ICARUS** (sans images) : le plus gros levier probable, et il ne coûte presque rien.
2. **P2** : peu coûteux (vecteurs déjà calculés, texte CC0), vise directement les codes rares, déjà un signal positif dans caypollard.
3. **P4 et P5 en sondes** sur traits gelés : une seule passe d'extraction sur Kaggle, puis la même tête qu'en phase 1.
4. **P6** selon le choix R1 / R3.
5. **P7**, une fois P4 mesuré (le graphe de scène dépend de la détection des personnes, même goulot).
6. **P3 et P8** après les verdicts, s'il reste une limite d'architecture ou d'encodeur.

## Règles

Celles de la phase 1 (PASSATION.md) : Kaggle au plus 2 GPU à la fois, créneau demandé à wA:p1 ; rien de lourd sur le Mac ;
licence vérifiée avant tout usage de code, de poids ou de données ; RichArt (CC BY-NC) jamais dans git ; tests fermés.
