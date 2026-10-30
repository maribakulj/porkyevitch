# Petit élève v1 : amendement avant le complet (30/10/2026)

Claude wA:pH, à la demande de wA:p1. Les points viennent de l'audit de Codex p4 (« Points à reprendre avant le complet ») et des décisions D8 et du smoke. **`PREINSCRIPTION.md` reste intacte** : ce texte dit où le code s'en écarte et pourquoi. Rien n'est lancé.

## 1. Le regard avant les chiffres (Codex, point 1)

La préinscription veut que la planche soit regardée avant les chiffres. Le complet calculait pourtant les métriques et l'issue D2 avant de construire la planche. Il est maintenant coupé en deux étapes.

- **`full`** (T4) : têtes, témoins, chronométrage et planche. Elle écrit les **prédictions** (`predictions/`), le chronométrage (`timing.json`), `run.json` (sans mesure) et la planche (12 images), puis scelle le tout dans `MANIFEST_PREDICTIONS.json` (SHA de chaque fichier). **Aucune mesure n'est calculée.**
- **`mesures`** (CPU) : elle ne démarre qu'avec le reçu `recu_planche_pe.json`, de la forme `{"stage": "planche_petit_eleve_regardee", "manifest_sha256": <sha du manifeste>, "regards": [{"viewer": "wA:p1", "viewed_at": …}, {"viewer": "Grok …", "viewed_at": …}]}`. Comme pour la phase 1 et P9-A, il faut les deux regards et que chaque fichier scellé soit présent et inchangé. Les scripts doivent être ceux du passage scellé. Elle recalcule les mesures et la lecture D2 **depuis les prédictions scellées**, sans nouvelle inférence. Les règles restent celles de `pe_common.py`, inchangé.

Les sorties de l'élève (boîtes, scores, catégories, scores de relations) sont enregistrées telles que `predict` les rend, en float32. Un test vérifie que les mesures de relations sont identiques avant et après l'aller-retour.

## 2. Un débit comparable (Codex, point 2)

L'élève était chronométré sans `no_grad` et sans autocast autour de sa tête, face à OWLv2 en `no_grad` + fp16. Désormais, **chaque système chronométré** tourne sous `no_grad` et autocast fp16 : l'élève (encodeur et tête, `student_forward`), OWLv2, YOLOE (`quantize=16`) et Florence-2 (fp16). Les prédictions mesurées de l'élève restent en float32, comme avant.

## 3. Le repère des rectangles (Codex, point 3)

Le carré gris décalait l'image d'un nombre entier de pixels (`//2`), alors que les conversions de boîtes utilisaient `/2`. Il y avait donc un demi-pixel d'écart quand la différence des côtés est impaire. Les deux passent désormais par `pad_offsets`, qui donne les décalages entiers. Le contrôle d'aller-retour du blanc couvre maintenant aussi 641×480 et 480×641, et un test vérifie le cas impair.

## 4. Une panne au blanc (Codex, point 4)

Un contrôle de surapprentissage à `passed: false` fait maintenant échouer le smoke : `blanc.json` est écrit, puis le code sort avec une erreur, sans `SMOKE_DONE`. C'est une panne, qui ne peut autoriser ni les bras scientifiques ni l'entraînement sur S1b.

## 5. Révisions épinglées après le smoke relu (Grok p3, CONFORME)

- OWLv2 : `google/owlv2-base-patch16-ensemble` à `cfd3195ba4ea9592eec887ded089f4c08eff231d`.
- **Florence-2.** La révision relevée par le smoke, `microsoft/Florence-2-base` à `5ca5edf5bd017b9919c05d08aebef5e4c7ac3bac`, est consignée comme source. Son **code distant ne se charge pas** avec transformers 5.16 (`'Florence2LanguageConfig' object has no attribute 'forced_bos_token_id'`), et le patcher, ou rétrograder transformers pour tout le passage, toucherait l'encodeur ou OWLv2. Le code charge donc **le checkpoint converti officiel de transformers**, `florence-community/Florence-2-base` à `00921df66db728a9ceb750f5eca43e5c203a2051` (MIT), avec la classe native `Florence2ForConditionalGeneration`, sans code distant. La tâche est `<OD>`, 3 faisceaux, fp16. Ce sont les poids de Microsoft convertis par transformers. Je n'ai pas pu vérifier ici leur égalité numérique avec la révision `5ca5edf5` : c'est une substitution déclarée, et Florence-2 reste un témoin descriptif. Si le chargement échoue encore au smoke, l'indisponibilité est écrite, comme avant.

## 6. YOLOE-v8-S en mode texte (D8)

Tout est figé avant les 26, sur le code et les seules entrées d'entraînement.

| | |
|---|---|
| paquet | `ultralytics==8.4.177` (roue `de8fd2fc…`, 13/10/2026), installé par le pilote, avec torch exigé inchangé ; licence AGPL-3.0 consignée |
| poids | `yoloe-v8s-seg.pt`, assets `v8.3.0`, 31 135 890 octets, sha256 `ac2b90ed23011495a3e86d89caeb3432a15129cac8d849ba121293c8fc1e0536`, téléchargés et vérifiés par le script |
| encodeur de texte | `mobileclip:blt` (`mobileclip_blt.ts`, 599 764 649 octets). Son SHA est **relevé par le smoke**, puis épinglé (`YOLOE_TEXT_SHA256`) par un commit relu : **le complet refuse `None`** |
| requêtes | les huit chaînes `OWL_QUERIES` d'OWLv2, sans recherche de synonymes |
| seuil, NMS | score ≥ 0,1 (celui d'OWLv2), NMS par classe à 0,5 (`iou`), au plus 300 boîtes, `imgsz` 640, fp16 |
| sans classe | la même règle qu'OWLv2 : union des requêtes, NMS torchvision à 0,5, objets « autre » gardés au dénominateur |
| exécuté | têtes de détection **et de segmentation** (les masques sont calculés par le checkpoint `-seg` et non utilisés : leur coût est dans le débit) |
| mesures | rappel@10/20/30 sans classe et AP50 sans classe sur les 26 Gemini, en colonne descriptive. **Aucun veto sur D2** : OWLv2 reste la référence de la porte |
| débit | 96 images de chronométrage, lots de 32, prétraitement, NMS et masques compris. La préparation du texte est chronométrée à part |

## Ordre

Ces changements sont de nouveaux octets : relecture par Grok p2 puis Codex p4. Ensuite vient un **nouveau smoke**, qui doit montrer que Florence-2 se charge réellement et relever le SHA de `mobileclip_blt.ts`. Viennent enfin un commit relu qui épingle ce SHA, puis `full`, la planche regardée et le reçu, et enfin `mesures`. Restent à fixer, comme le demande Codex : la méthode des quantiles et les versions de l'environnement réellement éprouvé, à reprendre du smoke.

## 7. Corrections B1 et B2 de Codex p4 (audit de `8768ff1`), avant le complet

**B1 : le sceau doit être complet à la lecture.** `check_receipt` hachait seulement ce que le manifeste déclarait. Un manifeste avec douze planches, mais sans `run.json`, `timing.json` ni prédictions, passait, et ces fichiers pouvaient changer ensuite. Codex l'a reproduit. Désormais :
- le manifeste doit avoir `stage = predictions_sealed`, le SHA des listes, et **les douze noms de planche de `listes.json`, dans leur ordre** ;
- l'ensemble des fichiers scellés doit être **exactement** celui que les mesures lisent (`required_files`) : `run.json`, `timing.json`, l'a priori, OWLv2, YOLOE, les six bras de l'élève et le jeu des trente images S1b (JSON et relations), les douze planches, et `florence2.json` **si et seulement si** `run.json` déclare Florence-2 disponible. Il n'y a plus de lecture conditionnée par `is_file()` ;
- un fichier manquant, en trop ou modifié est refusé, comme un manifeste vide ;
- les longueurs des prédictions sont vérifiées (26 images, ou 30 pour S1b), sans troncature silencieuse par `zip`.

**B2 : le débit « complet » inclut les relations.** `student_forward` n'appelait pas `model.rel`, alors que `predict` l'appelle sur les 870 paires ordonnées de chaque image. La colonne `student_full_b32`, qui sert à calculer D, exécute maintenant la tête de relations sur ces 870 paires, sous `no_grad` et fp16. La colonne `student_detector_only_b32` est publiée à part. Un test par crochet compte 870 entrées par image dans la colonne complète, comme `predict`, et aucune dans la colonne détecteur seul.

La note du chronométrage dit maintenant que les colonnes ne couvrent pas la même portion du pipeline. YOLOE est chronométré avec son prétraitement, la NMS et les masques. L'élève et OWLv2 le sont sur leur forward seul, prétraitement à part. D est le rapport de deux forwards, pas un rapport de bout en bout.

**Après le smoke** : `blanc.json` relève maintenant `clip_tokenizer`, c'est-à-dire la version et, pour une installation git, le commit du tokenizer CLIP qu'ultralytics peut installer au premier usage, en plus du SHA de `mobileclip_blt.ts`. Les deux seront figés par un commit relu avant le complet. Reste aussi à fixer la méthode des quantiles du bootstrap : le cœur utilise le défaut de numpy, linéaire, à déclarer.

## 8. Épinglage pour le complet, après le smoke 2 (Grok p3, CONFORME)

Le smoke 2 a tourné sur `0315a1d`. Les valeurs ci-dessous sont reprises de son `blanc.json` :

| | valeur figée | contrôle au complet |
|---|---|---|
| OWLv2 | `cfd3195ba4ea9592eec887ded089f4c08eff231d` | révision chargée |
| Florence-2 natif | `florence-community/Florence-2-base` `00921df66db728a9ceb750f5eca43e5c203a2051` (source consignée : Microsoft `5ca5edf5…`) | **s'est chargé réellement au smoke 2** (2 et 7 boîtes) ; ce n'est plus une dérogation |
| MobileCLIP (`mobileclip_blt.ts`) | `a67804d1b0f07b8b9a20c1761ec0847f34660f5fa338ec70e8f3fce68ed95e54` | SHA exigé |
| tokenizer CLIP | `clip` 1.0, `https://github.com/ultralytics/CLIP.git` @ `7ffa84b3bfa40c42ecc1c77147a855e69cb2dd40` | version, URL et commit exigés |
| environnement | Python 3.13.15, torch 2.11.0+cu128, numpy 2.1.3, transformers 5.16.1, ultralytics 8.4.177, open_clip_torch 3.3.0, torchvision 0.26.0+cu128 | `versions()` exigé égal, sinon arrêt avant tout calcul |

**Quantiles** (déclarés, `pe_common.py` inchangé) : intervalle percentile 2,5 / 97,5 %, `numpy.quantile` par défaut (méthode **linéaire**). Les tirages non finis sont retirés, et le nombre de tirages définis est publié (`draws`). La méthode est écrite dans `resultats.json` (`quantile_method`).

Le pilote passe à `STAGE = "full"`. L'étape `mesures` suivra la planche regardée et le reçu des deux regards.

## 9. D11 : entrées en archive `.bin` épinglée (pilote seul)

Kaggle a supprimé les jeux `porky-*`, dont `porky-petit-eleve-v1`, qui portait 166 images JPG. La cause n'est pas sûre : le nom, ou les dessins de nus, dont `p034` et `p163`.

- **Les entrées** (listes, noms, scripts, 166 images, 158 graphes Gemini, 30 S1b) viennent maintenant en **un seul tar non compressé**, `pe-entrees.bin`, sha `b48cb32c…`, dans le jeu `pkyevitch-pe-entrees`.
- **Construction reproductible** par `outils/construire_entrees_bin.py` : les listes et les scripts sont contrôlés contre `CODE_SHA256.json`, et les images et graphes contre `listes.json`. Les ensembles fermés sont refusés. Les membres sont triés, avec mtime 0, uid/gid 0, au format USTAR. Deux constructions donnent les mêmes octets. Le pilote n'est pas dans l'archive, puisque son SHA l'épingle.
- **Le pilote** `kaggle_pe_run.py` :
  - trouve exactement un `pe-entrees.bin` ;
  - l'extrait avec `safe_extract`, la fonction relue du pilote de mesure de la phase 1, à l'identique : SHA épinglé, refus des chemins absolus, de `..`, des liens et des fichiers spéciaux, avant toute écriture ;
  - ne cherche `listes.json` et les scripts **que là**.
- **L'extraction se fait dans `/tmp/pkyevitch`**, et non dans `/kaggle/working` : Kaggle publie ce dossier comme sortie du noyau, et les images ne doivent pas y réapparaître.
- **Si le dossier scellé du complet** (12 planches JPG) doit aussi être re-téléversé, il viendra en `pe-scelle.bin`, avec un SHA épinglé par un commit relu (`SCELLE_SHA256`, aujourd'hui `None`, donc refusé). Sinon, on monte la sortie du noyau du complet, comme avant.
- **`pe_kaggle.py` et `pe_common.py` sont inchangés.** C'est obligatoire : le sceau du complet vérifie leur SHA avant les mesures. `STAGE` reste `full` ; le passage à `mesures` sera un commit séparé, après la planche et le reçu.
- **Limite restante** : le complet écrit ses planches JPG dans sa sortie, `/kaggle/working`. Les en retirer obligerait à changer `pe_kaggle.py`, ce que le sceau interdit.
- **Tests** : `tests/test_pe_bin.py`, 7 tests :
  - extraction hors de `/kaggle/working` ;
  - SHA faux, deux archives, destination existante ;
  - membres `..`, absolus et liens refusés sans rien écrire ;
  - scripts non relus refusés, et `listes.json` exigé à la racine ;
  - dossier scellé pris dans la sortie du noyau, ou dans l'archive seulement avec un SHA épinglé ;
  - reconstruction réelle reproductible, égale au SHA épinglé.
