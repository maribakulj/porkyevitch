# Boucle autonome de wA:p1 — lermolieff (Iconclass + graphe de scène)

Mandat de Marcel (29/10/2026, mot pour mot dans l'esprit) : une vraie boucle, intelligente ; wA:p1 gère l'équipe et la partie
lermolieff ; **décisions importantes prises sans sa supervision, après contre-expertise de Codex**, en faisant au mieux avec les avis ;
avancer intelligemment, optimiser le temps ; **Kaggle et Colab utilisables librement** ; le Grok littérature est un **vrai
challenger** qui vérifie chaque nouvelle piste par des revues et des propositions ; **Codex fait une contre-expertise de Grok avant
de se lancer**. La mission 3D2D (wA:pC) est un autre chantier : ne pas la piloter, seulement lui répondre (créneaux, données gelées).

## Cap : un « dots.mocr » de l'iconographie

Ce qu'un VLM fait bien (lire une image d'œuvre, nommer et situer les objets et figures, dire leurs relations, donner les codes
Iconclass), mais **assez rapide et robuste pour la production** : analyser un vaste corpus, s'intégrer à un pipeline qui classe,
retrouve et relie les images. Analogie de Marcel : un VLM comme Fable fait un excellent OCR ; on veut l'équivalent de dots.mocr ou
LightOnOCR, aussi bon mais déployable.

Exigences de production (à mesurer, pas à supposer) : débit (images/s par GPU, et sur CPU), latence, mémoire, déterminisme,
sorties structurées valides (JSON, RDF), versions et licences propres (code, poids, données), lot massif, reprise sur erreur,
calibration des scores, évaluation par support (peinture, estampe, dessin), aucune fuite des tests.

Architecture visée (hypothèse de travail, révisable par la boucle) : un encodeur partagé (C-RADIO ou mieux), et des têtes rapides :
(1) codes Iconclass (phase 1 + phase 2) ; (2) objets avec rectangles ; (3) relations entre objets ; (4) vecteurs pour la recherche
(image, objets). Apprises par **distillation** d'un VLM professeur (Gemini en `agy -p`, Opus) sur un grand corpus d'images ouvertes,
plus les vérités existantes (ICAI, IconArt, ArtDL…). Le professeur ne voit jamais les codes de l'image quand il écrit le graphe.

## Rôle de Codex maths (wA:p6), précisé par Marcel le 29/10

Marcel a créé l'agent maths pour trouver des **algorithmes compétitifs qui ne passent pas par un VLM ni par un gros réseau**, ou qui
n'utilisent l'IA que pour optimiser. SegSwap était cité non pour son mécanisme, mais parce qu'il **répond efficacement à un besoin grâce à un
algorithme mathématique nouveau** (mot de Marcel). Le but est donc d'inventer de tels algorithmes, pas seulement d'en appliquer. Pistes de ce type à explorer en continu (chacune challengée par Grok p7, avec antériorité) :
décision optimale pour la mesure (choisir l'ensemble de codes qui maximise l'H-F1 attendu à partir des probabilités, au lieu d'un
seuil) ; décodage exact sous contraintes de l'arbre Iconclass ; cascades (filtre bon marché, calcul coûteux seulement si
incertain) ; index et quantification pour la recherche à grande échelle ; appariement de graphes de scène par transport optimal ;
compression et accélération des têtes (quantification, élagage, distillation) ; tout algorithme géométrique ou combinatoire qui
remplace un appel de modèle.

## Jalons (dans l'ordre, chacun préinscrit et relu)

1. **Phase 1 close** : prédictions des sept essais sur test ICAI + dev/test Rijksmuseum, verdicts, fiche HF mise à jour, fusion
   travail → main.
2. **Pilote graphes Gemini** : validité, planche, coût ; correction de lecture si besoin (nouvelle brique) ; SAM 3 ; IconArt.
3. **Iconclass phase 2** : P9-A (en cours), diagnostic, palier 1 (rares, ensembles, texte des codes, CSRA), adaptation de
   l'encodeur, ICARUS.
4. **Données de distillation à l'échelle** : graphes Gemini sur 5 000 puis davantage d'images ouvertes (licences vérifiées).
5. **Élève multi-tâche** : objets + relations + Iconclass sur encodeur partagé ; mesure contre le professeur et contre les vérités.
6. **Production** : export (ONNX/TensorRT si utile), traitement par lots, débit mesuré, paquet lermolieff, documentation.

## Protocole de décision

- **Décision importante** (changer de cap, abandonner ou ouvrir une piste, dépenser > 10 h GPU ou > 10 unités Colab, modifier une
  règle de décision, publier) : (a) Grok wA:p7 donne l'état de l'art et l'antériorité ; (b) **Codex wA:p6 fait la contre-expertise**
  de la proposition et de l'avis de Grok ; (c) wA:p1 décide, écrit la décision, ses raisons et les avis dans `DECISIONS.md`, et
  prévient Marcel en une ligne. Pas d'attente de Marcel, sauf pour ce qu'il s'est réservé : passage en public (lermolieff, HF).
- **Nouvelle piste** : Grok wA:p7 challenge (revue sourcée, antériorité, proposition de recherche) → Codex wA:p6 contre-expertise →
  préinscription → relecture Grok wA:p2 → audit Codex wA:p4 → essai à blanc → audit des sorties → calcul complet.
- Règles inchangées : relecture avant tout calcul ; règle de décision écrite avant ; réglage après résultat = nouvelle brique ;
  images avant métriques ; tests fermés ; Gemini en `agy -p` ; pas de jeton HF sur Kaggle ; rien de lourd sur le Mac ; ≤ 2 GPU
  Kaggle à la fois (compte partagé, vérifier `kaggle kernels list --mine`, laisser la place à wA:pC) ; jamais de /tmp pour du durable.

## Une itération de la boucle

1. Relever : tâches de fond terminées, nouveaux rapports dans `~/Documents/reviews` (porkyevitch-*), état des onglets wA:p2-p8
   (`herdr agent get`, `herdr agent read`), noyaux Kaggle/Colab.
2. Débloquer : agent bloqué (connexion, `/login` requis → prévenir Marcel), demande de permission inattendue, noyau en erreur.
3. Avancer : pour chaque fil, lancer l'étape suivante dès que ses feux verts existent ; donner une tâche à tout agent inactif qui a
   quelque chose d'utile à faire ; paralléliser ce qui est indépendant.
4. Tracer : `JOURNAL-BOUCLE.md` (une ligne par action), `DECISIONS.md` ; commits et poussées sur `travail`.
5. Informer Marcel seulement aux jalons, aux décisions importantes, ou quand il doit agir (connexion, /login).
6. Choisir le délai du prochain réveil selon ce qu'on attend (calcul Kaggle : sa durée ; relectures : 10-20 min ; rien : 20-30 min).
