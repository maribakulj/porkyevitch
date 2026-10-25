# Passation de porkyevitch (25/10/2026)

De Claude w3:p1 (espace herdr caypollard) à l'orchestrateur Opus wA:p1. Validé par Marcel le 25/10/2026.

## Périmètre

porkyevitch = **tout l'entraînement et l'évaluation de modèles**, à distance (Kaggle, Colab). caypollard reste l'atelier (essayer les
nouveautés sur nos corpus, regarder les images, briques) ; quand caypollard a besoin d'un entraînement, il le demande ici, et le résultat
revient là-bas comme une brique nommée. lermolieff (`~/lermolieff`, futur dépôt public) publie la tête Iconclass.

## Qui fait quoi

| agent | rôle |
|---|---|
| wA:p1 Opus | orchestrateur : seul à écrire dans `~/porkyevitch` ; préinscriptions, scripts, lancements, rapatriements ; **peut fusionner `travail` dans `main`** (accord de Marcel du 25/10) |
| wA:p2 Grok | première relecture de chaque script et de chaque essai à blanc |
| wA:p3 Grok | vérification des résultats rapatriés (empreintes, comptes, cohérence) ; littérature |
| wA:p4 Codex | audit final avant chaque lancement, lecture seule, rapports dans `~/Documents/reviews/porkyevitch-*.md` |
| w3:p1 Claude / w3:p3 Codex | caypollard seulement ; joignables par `herdr agent prompt` pour une question d'historique |

## Règles de Marcel (sans exception)

- Répondre à Marcel en français, simplement ; lien cliquable vers chaque image ou page citée. Marcel n'annote pas.
- **Relecture avant tout calcul**, essai à blanc compris ; le calcul complet attend la relecture de l'essai à blanc.
- Règle de décision écrite avant le calcul ; un réglage choisi après avoir vu un résultat devient une nouvelle brique, nommée ; regarder
  des images réelles avant les métriques ; un échec d'une construction grossière ne réfute pas une idée.
- Rien de lourd sur le Mac (16 Go, disque presque plein : `df` avant toute copie ; liste exacte avant toute suppression). Kaggle :
  au plus 2 GPU à la fois (compte partagé avec d'autres projets). Colab au-delà de 10 unités : accord de Marcel.
- Jamais de clé écrite ni affichée ; jamais l'e-mail de Marcel vers un service tiers ; User-Agent « caypollard/0.1 (research
  prototype) ». Pas de jeton HF sur Kaggle.
- Dépôts publics (lermolieff, caypollard) : ni journaux, ni notes, ni chemins locaux, ni e-mail ; commits avec
  `241159986+maribakulj@users.noreply.github.com`. RichArt (CC BY-NC) jamais dans git.
- Commits : `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Outils et pièges

- Kaggle : `~/outils-seg/kaggle-env/bin/kaggle` (compte `mabaku`). `kernels output` pagine à 20 fichiers → `--page-size 200` ;
  `datasets create/version -r tar` (`-r skip` ignore les sous-dossiers) ; « Maximum batch GPU session count of 2 » = attendre.
- Colab : CLI google-colab-cli 0.7.5 ; `porky/colab.py`, `porky/drivemount.py` (un clic d'autorisation de Marcel par machine).
- Sauvegardes : dépôt HF privé `Ma-Ri-Ba-Ku/porkyevitch-sauvegardes` via `tools/sauvegarde_hf.py` (le jeton local sert sans être lu).
  Le Drive pour ordinateur se bloque quand le disque est plein.

## État au moment de la passation

| expérience | état | suite |
|---|---|---|
| `2026-10-25-iconclass-architecture` | préinscrite (amendements 2-4), feu vert Codex ; encodage C-RADIO complet : voir ci-dessous | E0 → reference.json → D → E1 → E2 → E3, chaque script relu |
| `2026-10-25-banc-rijksmuseum` | préinscription BLOQUANTE sur B1-B4 (rapport `porkyevitch-banc-rijksmuseum-codex.md`) ; étape 0 : voir ci-dessous | amender B1-B4 et synchroniser l'amendement 4 avec les effectifs de l'étape 0 ; script de collecte relu ; audit des filtres ; tirage ; gel |
| `2026-10-25-lermolieff-publication` | code `fdb9f29` relu (feu vert) ; essai distant : voir ci-dessous | VERSIONS.md ; publication (historique neuf d'un seul commit, GitHub public + `Ma-Ri-Ba-Ku/lermolieff-iconclass-{c-radio,pe-spatial}`) **après** le banc Rijksmuseum, relecture, et page montrée à Marcel |
| publication HF (dans lermolieff-publication) | cartes prêtes dans `~/lermolieff/hf/{c-radio,pe-spatial}` (README avec en-tête YAML, LICENSE MIT, NOTICE + licence NVIDIA pour c-radio, manifest.json) | ajouter : exemple d'usage, `model-index` (ICAI + Rijksmuseum), citation ; créer les dépôts **privés** avec huggingface_hub (jeton local jamais lu), envoyer, vérifier le sha de head.pt sur le Hub, montrer la page à Marcel, passer en public sur son accord, en même temps que GitHub |
| autres dossiers | clos (copiés de caypollard avec PROVENANCE.md) | `xanto-parties` est à rendre au projet xanto |

### Calculs du 25/10 : clos, vérifiés par Codex (aucune autorisation automatique pour E0 ni pour la publication)

- **Encodage complet C-RADIO** — kernel `mabaku/caypollard-encode-cradio` **version 3**, `MODE=full`, `encode_cradio.py` sha
  `c3f12bb7…`. FEU VERT résultat de Codex : contrôle T0 passé (ICAI 788/788 prédictions identiques, H-F1 0,547921570709416 =
  publié ; Emblematica 800/800 ; vecteurs max |Δ| 0), 12 fragments, 94 324 lignes. 94 324 images, 20,8 img/s, RAM 5,8 Go, VRAM
  3,1 Go. Les **tenseurs (13,15 Go) restent dans la sortie de la version 3** : à brancher en `kernel_sources` des essais ; **E0 doit
  d'abord vérifier à distance leurs SHA, formes, dtype et finitude** contre les sidecars (pas de rehash sur le Mac). Petits fichiers
  (35) dans `experiences/2026-10-25-iconclass-architecture/essais/encodage-full/` (commit 4ee9d13).
- **Essai distant lermolieff** — kernel `mabaku/lermolieff-smoke-run`, dataset `mabaku/lermolieff-smoke` (fdb9f29),
  `kaggle_smoke.py` sha `33aa811b…`. FEU VERT technique : les deux variantes sortent à 0, 32/32 identiques. `~/lermolieff`
  VERSIONS.md (commit local 32a5e9f, seul changement depuis fdb9f29). Sorties dans
  `experiences/2026-10-25-lermolieff-publication/essai-distant/`.
- **Étape 0 Rijksmuseum** — passage 2 (script `82b078b5…`, relu) : 842/900 éligibles vérifiés ; voir
  `experiences/2026-10-25-banc-rijksmuseum/etape0/RESULTAT.md`. Cache brut (5 416 réponses, 45 Mo, hors git) copié dans
  `~/porkyevitch-donnees/rijks-etape0/cache` (réutilisable : même clé URL + profil + Accept).

### Prochaines étapes, dans l'ordre

1. Banc Rijksmuseum : amendements B1-B4 (groupes de dépendance au-delà du créateur — ~30 % d'objets sans créateur identifié —,
   audit des filtres de copie hors test, algorithme de tirage, contrat de collecte avec chaîne de droits) et synchronisation de
   l'amendement 4 ; relecture ; script de collecte ; audit ; tirage ; gel.
2. Série d'essais : E0 (vérification distante des tenseurs puis T-seuil, T-long) → reference.json → D → E1 → E2 → E3.
3. Publication lermolieff après le banc (historique neuf d'un seul commit, voir le tableau ci-dessus).
4. Fusionner `travail` dans `main` quand un ensemble est relu (droit accordé par Marcel à wA:p1).

## Rapports de Codex

`~/Documents/reviews/porkyevitch-{migration,architecture-preinscription,encodage,banc-rijksmuseum}-codex.md` et les rapports
lermolieff ; à résumer dans `relectures.md` de chaque expérience.
