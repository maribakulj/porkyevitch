# P9-A — préparateur et blanc proposés pour relecture

29/10/2026, Codex wA:p6. **Code écrit, jamais exécuté.** Préinscription conservée octet pour octet : SHA-256 `25f1040f5b657d7b94896cba41852f59c2f6e3042a555f798c126ca8698d3585`. Grok p2 et Codex p4 ont donné leur feu vert à ce document seulement ; leurs rapports ne valent pas relecture du présent code.

Ce lot réalise **la préparation et le blanc de la section 10.2**. Il contient les quatre têtes, leur perte, l'optimiseur et la reprise, mais **aucun mode d'entraînement scientifique complet, de sélection des 571 candidats ou de bootstrap**. Ces étapes ne peuvent pas être déclenchées par ce pilote. Elles viendront dans un autre lot après mesure et relecture du blanc. La préinscription entière, ses règles G/R et son budget restent le contrat du futur calcul scientifique ; aucune règle n'est modifiée ici.

## Pièces à copier pour relecture

- `scripts/p9a_common.py` : constantes gelées, fonctions E3, métrique par code à liste fixe, IO atomiques et budget.
- `scripts/p9a_inputs.py` : liste positive des 44 fichiers des onze fragments train, contrôles complets à distance, partages, fréquences, vocabulaire, réduction transitive et lecture des seuls poids B.
- `scripts/p9a_heads.py` : F, `controle_global`, A et C ; même W initiale ; couches linéaires sous AMP et opérations de champs/perte en float32.
- `scripts/p9a_prepare.py` : descriptions publiques anglaises et MiniLM épinglés, prototypes, permutations et planche initiale de douze images réelles.
- `scripts/p9a_smoke.py` : contrôle historique B, deux mises à jour par bras, invariants et reprise.
- `scripts/kaggle_p9a_run.py` : pilote hors ligne, une étape explicite, watchdog, aucun push Kaggle.
- `ENCODAGE_TRAIN_V3.json` : SHA déclarées par les sidecars train v3 et SHA des octets de ces sidecars locaux. **Aucun tenseur n'a été ouvert pour écrire cet inventaire.** Une divergence sur Kaggle arrête ; ne pas réécrire l'inventaire pour faire passer une entrée différente.
- `CODE_SHA256.json` : empreintes du protocole, de l'inventaire et des six fichiers Python. Le SHA de ce manifeste est à inscrire dans la configuration de lancement après relecture.
- `PILOTE.example.json` et `SOURCES.example.json` : modèles volontairement non exécutables sans compléter les liaisons.

Le code ne fait ni `glob` ni exploration récursive des sources d'encodage. Les parcours récursifs présents ne portent que sur **les propres sorties** pour leur taille ; le petit glob des scripts sert uniquement à leur provenance. Il n'ouvre ni `run.json` global de l'encodeur, ni contrôle mixte, ni test, ni Emblematica, ni Rijksmuseum. Aucun code d'E3 n'est importé ou exécuté : les trois fonctions et la petite architecture T-Z ont été retranscrites d'après le fichier épinglé.

## Entrées à lier par wA:p1, après relecture

Le dossier `experiment_root` est la copie distante de cette expérience. `sources.json` lie explicitement les dossiers montés ; aucun nom de montage n'est deviné.

1. Sortie d'encodage **v3**, `full/`, avec seulement les onze noms autorisés ouverts. Les autres fichiers du montage restent fermés.
2. E3 complet : `t_z.pt`, `e3.json` et `run.json` exacts. Le SHA des poids, époque, seuil, architecture et vocabulaire sont obligatoires. Le blanc refait B en float32, par lots 256, sur la validation seule et exige le H-F1 historique à 10⁻⁶ près.
3. Sept fichiers de descriptions `iconclass/data` sous `txt/en/` à la révision `737ce365…`. Le code embarque leurs Git blob SHA1 ; il archive aussi leurs SHA-256. Il ne s'appuie pas sur une fusion non documentée des descriptions : une clé exacte conflictuelle arrête.
4. Cache HF MiniLM contenant la révision `1110a243…`, sans téléchargement dans ce pilote. Les six fichiers attendus sont contrôlés **avant chargement**, contre les Git blob/LFS SHA publics de cette révision ; poids `model.safetensors` SHA-256 `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`. Aucun code distant, aucun jeton.
5. Petit cache des octets originaux des douze premières images V-réglage évaluables. Le code ne télécharge pas de parquet. Ce cache doit être préparé à distance depuis les seules lignes `data/train-*.parquet` de la révision Brillfull gelée, par une préparation revue, puis monté. Le md5 de chaque image est comparé au md5 de features. Pas de vignettes JPEG recompressées à la place des octets originaux.

Format du cache d'images : `manifest.json`, avec la clé `dataset` identique à `SOURCES`, puis `rows`, une liste de `{ "shard": "train-00000-of-00011", "row": <indice réel>, "md5": "<md5 réel>", "file": "<md5 réel>.image" }`. Cet exemple est un **schéma**, pas une ligne ni une image de test. Les identités requises sont calculées par la formule écrite dans la préinscription. Si elles ne sont pas disponibles dans le cache, le préparateur s'arrête ; aucune substitution de cas.

`ENCODAGE_TRAIN_V3.json` fige seulement les SHA déjà présentes dans les petits sidecars consultés. La vérification à distance refait les SHA des grilles/vecteurs, vérifie finitude et alignements, puis reconstruit les comptes sur tout l'apprentissage. Les fréquences de validation ne servent ni aux priors ni aux textes ni au graphe.

## Étapes distantes distinctes

**Ne rien lancer à la livraison de ce lot.** Après relecture Grok p2 puis Codex p4 du code exact et attribution d'un créneau par wA:p1, remplir les modèles dans un petit montage de configuration séparé. Figer toutes les versions de `approved_versions` avant le lancement ; un écart fait arrêter le pilote. Aucune installation de dépendances ne se fait dans le pilote.

L'unique point d'entrée prévu est `kaggle_p9a_run.py --config /kaggle/input/<configuration réelle>/pilote.json --stage prepare` ou `--stage smoke`. Ces formes sont des instructions pour une future session approuvée ; aucune n'a été exécutée ici. Les scripts de préparation/blanc refusent leur entrée directe sans l'environnement transmis par le pilote.

**Préparation :** CPU distant ≤1 h, ou un T4 visible avec plafond ≤0,5 h pour l'étape entière. Elle ne fait aucun passage des nouvelles têtes. Elle archive `donnees.json`, `textes.json`, `prototypes.npz`, trois fichiers de permutations de dix époques et la planche HTML/PNG avec son manifeste. Ces permutations concernent le futur régime scientifique ; le blanc utilise toujours les 128 premières lignes canoniques. Le cache HF reste en lecture seule.

**Regard initial :** faire ouvrir les douze images de `planche_initiale/index.html`, puis lier un reçu réel, préparé par l'orchestrateur après cet examen :

```json
{
  "stage": "initial_board_viewed",
  "viewer": "<personne ou agent qui a réellement regardé>",
  "viewed_at": "<horodatage réel>",
  "preparation_sha256": "<SHA-256 de preparation.json>",
  "manifest_sha256": "<SHA-256 de planche_initiale/manifest.json>"
}
```

Le code ne fabrique pas ce reçu et ne prétend pas constater à lui seul un regard humain ou visuel. Il vérifie que ce reçu désigne exactement la planche et la préparation montées. La préparation et le blanc sont deux sessions explicites, sans enchaînement automatique.

**Blanc :** un seul GPU visible, obligatoirement T4. Revalidation des entrées et prototypes ; reproduction complète de B, puis F/G/A/C avec les 128 lignes fit et les 64 premières lignes V-réglage. La seule ouverture de V-diagnostic en inférence est celle de B, exception historique inscrite dans le protocole ; aucune nouvelle tête ne le voit. Aucune sortie de métrique nouvelle sur validation complète.

Deux mises à jour principales de lot effectif 64 par bras. Checkpoint après la première ; seconde mise à jour, puis rechargement de ce checkpoint et **rejeu technique de la même seconde mise à jour**, pour comparer états/probabilités/ensembles à la continuation sans interruption. Ce rejeu ne constitue pas une troisième mise à jour conservée. Le passage V-réglage est donc répété pour vérifier la reprise. L'état sauvegardé contient modèle, optimiseur, scaler, RNG Python/numpy/torch/CUDA et position dans la liste canonique.

Micro-lot 64 d'abord ; en cas d'OOM avec plafonds respectés, redémarrer **tous les bras** avec 32, puis 16, même W et mêmes lignes. Les tentatives abandonnées sont marquées OOM et conservées comme traces techniques ; elles ne deviennent pas des résultats scientifiques. Un NaN, une violation de graphe ou d'un plafond ne déclenche aucun ajustement. Le partage du gradient aux égalités d'un minimum se fait par `torch.amin`, entre parents réels ; les cases de padding sont +inf.

Le blanc vérifie A=G à l'initialisation, les priors et comptes de paramètres, l'égalité bit à bit de W et des cibles, gradients finis, hiérarchie locale/agrégée, duplication pondérée d'une cellule et identité A/G à un seul niveau avec **les mêmes caractéristiques réelles**. Le cas à un niveau est un contrôle de formule, pas un faux corpus. L'ASL est appliquée à p, pas à sigmoid(p) ; R est ajoutée une seule fois par mise à jour, même avec accumulation.

La métrique rare technique porte sur les 64 lignes et conserve **toute R calculée sur 81 951 lignes**, y compris les codes sans support ; elle est comparée à un deuxième calcul indépendant par code. Le seuil technique 0,65 est fixe, sans sélection ; il ne remplace pas la future grille scientifique. `alpha_zero` ne prend que 0,65 et retourne directement les ensembles de B. Aucun verdict G/R n'est calculé au blanc.

## Budget, sorties et limites de cette livraison

Le pilote impose le plafond externe d'une heure au blanc, démarrage compris, avec surveillance RAM/disque ; il termine le groupe de processus au dépassement. Le processus écrit ses mesures RAM et VRAM allouée/réservée après chaque phase et mise à jour, avec plafond 12 Gio alloués, 15 Gio RAM processus et 5 Go durables. `CUDA_VISIBLE_DEVICES=0` limite l'usage à un GPU ; **l'orchestrateur reste responsable du créneau et de l'allocation Kaggle effective**, y compris si l'offre Kaggle réserve deux T4 à la session. Aucun deuxième GPU n'est utilisé par ce code.

Les fichiers `driver.json`, `execution.log`, `budget.json`, `reference_validation.json`, `blanc.json`, états de reprise et sorties techniques V-réglage permettent la relecture. **Le statut global faisant foi est `driver.json` et son code de sortie**, pas un fichier partiel laissé par un processus arrêté. Les sorties des quatre bras sont dans le dossier du micro-lot commun ayant passé ; les autres dossiers restent explicitement des tentatives abandonnées.

L'extrapolation des deux mises à jour est étiquetée **entraînement seul, borne de temps incomplète**. Elle n'est jamais un feu vert pour 10 époques : la validation, le mélange, les 571 candidats et leurs fonctions de mesure restent à budgéter dans le futur script scientifique. Au-dessus de 12 h d'entraînement estimées, amendement requis ; en dessous, **relecture toujours requise et budget total non certifié**. Les temps froid/chaud incluent ici les contrôles et synchronisations explicitement présents, pas une promesse de débit steady-state.

Vérification locale de cette livraison : lecture statique, `ast.parse` et compilation Python en mémoire **sans exécution**, vérification des SHA documentaires/inventaire, `git diff --check`. Aucun import des modules P9-A, aucun chargement de torch ou de données, aucun prototype, vignette, score, entraînement, blanc ou kernel Kaggle lancé. La validité numérique et les performances restent à établir par le blanc revu.

Références techniques primaires consultées pour l'implémentation : [AMP PyTorch](https://docs.pytorch.org/docs/2.11/notes/amp_examples.html), [mode hors ligne Transformers](https://huggingface.co/docs/transformers/installation#offline-mode), [fichiers MiniLM épinglés](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41), [descriptions Iconclass épinglées](https://github.com/iconclass/data/tree/737ce365e3e6ab5302bafc22428ee37e57becee1/txt/en).

## Correctif du 29/10 : descriptions officielles en conflit (Claude wA:pH, remplaçant de Codex p6)

La préparation Kaggle s'est arrêtée dans `descriptions()` : `conflicting exact description: 83(SHAKESPEARE, Othello, Act 4, scene 1)`. Comptage sur les sept fichiers épinglés (blobs vérifiés, 44 331 clés) : **un seul conflit**, et aucun doublon identique. Les deux lignes en conflit sont dans `txt_en_shakespeare.txt` : la ligne 483 et la ligne 486. La ligne 486 suit l'acte 4, scène 3, et décrit la rixe de Cassio et Roderigo, c'est-à-dire l'acte 5, scène 1 : c'est vraisemblablement une coquille de la source, qu'on ne corrige pas ici. Cette clé n'est **pas** dans V (vocabulaire de 7 907 codes lu dans `t_long.pt` d'E0 sans charger de tenseur) ; aucun code Shakespeare n'est dans V.

Règle déterministe, écrite avant usage : une clé qui a plusieurs descriptions différentes est **retirée du dictionnaire et journalisée** (`dictionary_conflicts_dropped_outside_vocab` dans `preparation.json` : chemins, lignes, SHA-256 des descriptions) si elle est hors de V. Un conflit sur une clé de V **arrête** la préparation. Les doublons identiques sont gardés une fois. V étant fermé par ancêtres, les textes ne consultent jamais une clé hors de V : aucun texte ni prototype ne dépend de ce retrait. Un test le vérifie. La préinscription est inchangée.

Tests : `tests/test_descriptions.py`, hors manifeste. Les fonctions sont extraites par AST, sans torch. Cinq cas synthétiques plus un cas sur les fichiers publics épinglés et le vocabulaire E0 réels, tous OK. Aucun lancement.
