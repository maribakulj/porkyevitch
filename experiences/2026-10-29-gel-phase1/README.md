# Phase 1 — script de gel des prédictions, pour relecture

29/10/2026, Codex wA:p6. **Code rédigé seulement : aucun script, blanc, téléchargement d'image ou calcul lancé.** Livraison prioritaire demandée par wA:p1 dans la boucle de Marcel. Rien n'a été écrit dans `porkyevitch` ou `lermolieff`.

## Objet exact

Produire les prédictions, sans aucune mesure ni verdict, conformément à la famille de sept comparaisons de la préinscription architecture, amendement 4. Il y a **huit systèmes distincts** : T0 ; T* (E0 : T-long) ; TK ; T-niv ; TK-niv ; T-H ; T-Z ; T-D. E0 compare T* à T0 ; les six autres comparent leur recette à T*. Le gel complet est donc **24 fichiers** : huit systèmes × ICAI test, Rijks dev, Rijks test, puis **un seul `MANIFEST.json` final**. Ni T-seuil ni T-long ne constituent une comparaison supplémentaire de la famille.

Les paramètres TK-niv ont été précalculés sur validation dans E1. Ses prédictions sont gelées avec toute la série ; **son activation dans les sept comparaisons reste conditionnelle à TK et T-niv retenus**, condition examinée seulement au futur verdict. Aucune condition n'est anticipée à partir des tests ni changée ici.

Le programme ne définit ni n'importe F1, H-F1, exact-F1, rappel, bootstrap, fonction d'évaluation ou sélection de seuil. Il ne calcule pas de mesure sur le dev non plus. Les contrôles portent sur SHA, identité, formes, finitude, reproductibilité et ensembles prédits, sans comparaison aux vérités d'évaluation. Les temps/mémoires et nombres de lignes du manifeste sont des métadonnées techniques d'intégrité, pas des agrégats de performance.

## Fichiers

- `scripts/gel_common.py` : parseur historique, `most_specific`, projection sans 86, IO atomiques, identité de reprise.
- `scripts/gel_models.py` : MLP de T0/T*/T-H, max descendant de T-H, T-Z et chargement du ML-Decoder officiel épinglé avec les deux adaptations de compatibilité d'E3.
- `scripts/gel_data.py` : documents et poids gelés, références d'apprentissage pour les voisins, entrées ICAI et Rijks, IIIF et encodage C-RADIO identique.
- `scripts/gel_predictions.py` : prédictions seules et publication atomique du sceau final.
- `scripts/kaggle_gel_run.py` : pilote, contrôles d'approbation, versions et créneau, watchdog ; aucune publication ni soumission Kaggle.
- `ENTREES_GELEES.json` : empreintes publiées des documents, poids, features, code ML-Decoder et fichiers C-RADIO à la révision fixée.
- `CODE_SHA256.json` : empreintes du code à relire ; `SOURCES.example.json` et `PILOTE.example.json` sont à compléter **après relecture**, dans un montage séparé.

## Références et décisions figées

| Système | Poids/époque | Décision sur validation, appliquée sans recherche |
| --- | --- | --- |
| T0 | `head.pt`, 14 | seuil 0,60 |
| T* | `t_long.pt`, 27 | seuil 0,60 |
| TK | T* | alpha 0,75 ; seuil 0,50 |
| T-niv | T* | seuils 0,60 / 0,60 / 0,60 |
| TK-niv | T* | alpha 0,75 ; seuils 0,50 / 0,50 / 0,50 |
| T-H | `t_h.pt`, 28 | max sur descendants ; seuil 0,25 |
| T-Z | `t_z.pt`, 29 | seuil 0,65 |
| T-D | `t_d.pt`, 27 | permutation E3 ; seuil 0,65 |

Ces valeurs proviennent de `reference.json` et des seuls JSON de validation E0–E3 ; le script les lit dans ces fichiers **après vérification des SHA publiés**, sans consulter les valeurs de leurs scores pour effectuer une sélection. Chaque checkpoint est vérifié par SHA avant désérialisation puis par vocabulaire, configuration, époque et seuil ; chargement strict des états. T0 nécessite aussi le montage historique `caypollard-iconclass-t0`, car E0 ne republie pas son `head.pt`.

Les têtes utilisent exactement leurs entrées natives et leurs lots de validation historiques : T0/T* 4 096, T-H 1 024, T-Z/T-D 256 ; float32, eval, dropout coupé. TK utilise uniquement les **81 951 lignes d'apprentissage non validation**, partage historique par groupes md5, vingt voisins, produit scalaire sur vecteurs C-RADIO sauvegardés, poids négatifs ramenés à zéro et normalisation historique, vote fermé aux ancêtres dans V. Même `topk`, même ordre d'accumulation, lots 1 024. Le contrôle alpha=1 exige l'identité avec T*. Aucun filtrage nouveau de copies ou changement de population.

Prédictions : `p >= seuil`, puis `most_specific`, puis retrait des codes commençant par 86. Les seuils par profondeur utilisent le nombre d'ancêtres **du code prédit**, sans vérité d'image. **Toutes les 788 lignes ICAI test sont conservées** : aucun filtrage d'image sur vérité projetée ici. Les éventuelles exclusions de dénominateur appartiennent au futur script de mesure, après gel.

## Accès aux données et absence de fuite vers les décisions

Lors de la rédaction, **`frozen.json` n'a jamais été parsé, affiché ou inspecté**. Seul son SHA-256 a été calculé sur ses octets : `2424b778d0a3e7c36e0aeea7ce5db60fcc52bc1eaa6c52a057fd957b142de0ca`. Le schéma a été lu dans le code source de `tirage_gel.py`. Aucune identité ni vérité de dev/test n'a été affichée. Les petits sidecars test ont seulement été hachés pour fixer leurs empreintes, jamais parsés dans cette rédaction.

À l'exécution future, le lecteur Rijks vérifie d'abord ce SHA, puis projette immédiatement chaque ligne sur **pid, URL IIIF, SHA d'image, largeur, hauteur**. Il ne lit pas les champs de vérité, de support, d'acteurs ou les arêtes de composante, et ne transmet que cette projection au téléchargement/prédicteur. Le parseur JSON charge nécessairement le fichier source en mémoire ; aucun de ses champs de vérité n'est accédé, utilisé, écrit ou imprimé. En mode blanc, seule la branche dev est projetée ; la branche test n'est pas parcourue.

Le `grid/test-00000-of-00001.json` ICAI contient des annotations : son **contenu reste opaque**, haché seulement contre l'empreinte attendue. Le script lit le npz de vecteurs (x/md5), la grille npy et le manifeste de features sans annotations. Les labels lus dans les sidecars **train** servent exclusivement à reconstruire V et les votes des voisins non validation. Pas de découverte récursive de fichiers montés ni d'ouverture des sorties mixtes Emblematica de l'encodeur.

Le téléchargement IIIF utilise **l'URL gelée exacte**, au plus une requête commencée par seconde, sur `https://iiif.micr.io/.../full/!800,800/0/default.jpg`. Les octets doivent avoir le SHA et les dimensions gelés. Erreur persistante, nouvelle compression distante ou SHA différent : arrêt de l'ensemble, **sans exclusion ni remplacement**. Le programme décode les pixels pour les encoder, sans les afficher ou produire de planche ; aucune image de test n'est regardée par un agent ici.

## Encodage et dépendances

C-RADIO `nvidia/C-RADIOv3-L@9d041346…`, encodeur en eval : RGB, carré gris 128 centré, 448 bicubique ; `CLIPImageProcessor(..., do_resize=False)` ; passage sous autocast fp16 par lots de 32 ; synthèse et moyenne spatiale normalisées séparément, concaténées puis renormalisées ; grille des seuls 784 jetons, moyenne adaptative 28×28 → 8×8 ; fichiers fp16. Les fonctions correspondent à `encode_cradio.py` épinglé `c3f12bb7…`, sans exécuter ce script qui contient d'autres corpus et contrôles historiques.

Le cache HF C-RADIO doit être monté **complet pour la révision fixée** avant session : fichiers Python, config, préprocesseur et `model.safetensors`. Chaque fichier est vérifié avant chargement contre Git blob SHA1 ou SHA-256 LFS, puis son SHA-256 est archivé. Métadonnées publiques seulement lues pour constituer cet inventaire ; aucun poids n'a été téléchargé ici. Chargement hors ligne, révision et code_revision épinglées ; `trust_remote_code=True` est nécessaire au même C-RADIO que l'encodage historique, après vérification des sources. Aucun autre code de Hub n'est admis par le montage prévu.

ML-Decoder : fichier officiel MIT à `Alibaba-MIIL/ML_Decoder@8a9e984…`, SHA `59fbf54f…`, à monter dans les entrées, pas à télécharger pendant l'inférence. Attribution : auteurs de ML-Decoder / Alibaba-MIIL ; le pilote reprend seulement les deux adaptations déjà relues dans E3 (arguments causaux ignorés, accès `self_attn` exposé). Pas d'import du script E3, qui ferait démarrer son entraînement.

Les versions du modèle de configuration reprennent l'environnement historique fourni par wA:p1 (E3). Toute divergence doit être auditée avant blanc, jamais choisie sur les tests. Le pilote ne fait aucune installation. Les accès HF sont hors ligne et sans jeton ; seul IIIF utilise le réseau à l'exécution. `CUDA_VISIBLE_DEVICES=0` : un seul T4 utilisé ; wA:p1 vérifie toujours le compte partagé et le créneau, car Kaggle peut réserver deux T4 à une session.

## Blanc et gel complet, deux étapes explicites

Ce lot doit être relu **Grok p2 puis Codex p4 avant toute exécution**. Le pilote refuse les configurations non complétées. Point d'entrée futur : `kaggle_gel_run.py --config /kaggle/input/<configuration réelle>/pilote.json --mode smoke` ou `--mode freeze`. Aucun de ces appels n'a été exécuté ici.

Le **blanc**, plafond une heure, utilise les 32 premières lignes de validation ICAI dans l'ordre canonique et les 32 premières images du dev Rijks gelé. Aucun des deux tests n'est ouvert. Il traverse les huit systèmes, contrôles de SHA/forme/vocabulaire, répétition identique de l'encodage de ce lot réel dev, et répétition des ensembles prédits de chaque tête. Il conserve seize fichiers de prédictions techniques et un manifeste marqué `predictions_frozen: false`. Il ne mesure ni H-F1 ni aucun autre score, ne change aucun paramètre et **ne lance rien ensuite**.

Le **gel complet**, plafond proposé quatre heures (à confirmer après blanc), exige le SHA du manifeste du blanc et les deux relectures de ses sorties dans la configuration, même code, mêmes versions et mêmes liaisons. Il produit exactement les 24 fichiers et le manifeste marqué `predictions_frozen: true`. En cas de blocage budget, amendement/relecture ; aucune méthode n'est supprimée pour finir dans le créneau.

Le processus surveille RAM, VRAM allouée/réservée et temps. Le pilote surveille aussi RAM du groupe, espace libre, taille des sorties et délai externe : RAM 15 Gio, VRAM allouée 14 Gio, sorties supplémentaires 5 Go, ≥6 Go libres à l'entrée. Ces plafonds techniques sont des propositions du présent pilote, **pas des mesures déjà obtenues**. Le montage des modèles/source n'est pas copié dans les sorties. La tête la plus chère et l'encodage doivent passer le blanc sans changement de lot caché.

## Sceau, reprise et lecture des sorties

Une sortie par `(banc, système)` contient identité de ligne, codes prédits projetés, paramètres figés et SHA des poids. Ni vérité, ni support, ni probabilité par code, ni F1. Le manifeste contient les SHA des 24 fichiers, leurs effectifs et empreintes d'ordre, les sources, recettes, famille et contrôles techniques.

Les caches d'encodage appartiennent à `OUT/.work` sur le disque durable Kaggle, jamais à `/tmp`. Une reprise n'est admise que si identité de code/versions/liaisons/mode identique et SHA des caches valides. Les fichiers non encore scellés sont recalculés/remplacés atomiquement, pas utilisés pour choisir quoi que ce soit. Après toutes les prédictions et vérifications, **`.work` est supprimé et le manifeste final publié en dernier**, atomiquement. Une fois scellé, le dossier n'est plus réécrit : reprise = vérification des SHA seulement. Une interruption entre nettoyage et publication demande un nouveau dossier ; aucun sceau partiel n'est accepté.

Le pilote vérifie encore la famille complète, les SHA et l'absence d'autre fichier final. Sur échec, il refuse/révoque le manifeste de sortie. Les messages console sont des états constants ; stdout/stderr des dépendances sont masqués pour éviter qu'une exception HTTP n'affiche une URL gelée. Le dossier final réussi contient **seulement les prédictions et leur manifeste**. Les caches résiduels d'une session échouée sont des fichiers intermédiaires non scellés, jamais un résultat permettant d'ouvrir les mesures.

**Fin absolue de ce programme : le sceau des prédictions.** Les planches d'écarts du dev, leur regard, les agrégats des tests, bootstrap et verdicts de toute la famille sont une étape séparée, absente du code livré. Il n'y a aucune ouverture automatique des mesures après gel.

## Vérification locale effectuée

AST et compilation Python en mémoire, parsing des JSON documentaires, contrôle des SHA des sources et `git diff --check` seulement. Aucun module de cette expérience importé/exécuté, aucun poids/tensor/image ouvert, aucun fichier de liste frozen affiché. La validité d'exécution et le coût restent à vérifier dans le blanc après les deux relectures.
