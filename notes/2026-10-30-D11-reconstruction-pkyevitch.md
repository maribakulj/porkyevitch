# D11 : inventaire et plan de reconstruction `pkyevitch-*` (rien lancé)

30 octobre 2026. Claude wA:pH, à la demande de wA:p1.

**Constat.** Kaggle a supprimé presque tous les jeux de données `mabaku/porky-*`. Selon Marcel, la cause n'est pas sûre : le nom, ou les images de nus. Ne survivent que `porky-e0-entree`, `porky-e1-entree`, `porky-e2-entree` et `porky-e3-entree`. **Les noyaux `porky-*` et leurs sorties existent encore** (liste de 30/10, 08 h). `porky-p9a-seed` et `porky-pe-run` sont en cours.

**Règles adoptées.**
- Plus aucun nom `porky-` sur Kaggle : tout nouveau jeu ou noyau s'appelle `pkyevitch-*`.
- Toute image potentiellement sensible qui doit être **téléversée** passe par une archive `.bin` épinglée, extraite par le pilote.

**Bonne nouvelle.** **Aucun chemin `porky-` n'est écrit en dur dans le code relu.** On n'en trouve que dans des commentaires. Les chemins vivent dans des **fichiers de configuration** (`pilote_science.json`, les liaisons `sources.json`) et dans les entrées fines des noyaux. Les pilotes d'A1, D3, du petit élève et de D10 cherchent leurs entrées **par motif et par SHA**, pas par chemin. Les entrées sont toutes vérifiées par SHA : un renommage ne change aucune valeur contrôlée, seulement des chemins.

## 1. Ce qui a disparu, et la copie locale à re-téléverser

| Ancien jeu (supprimé) | Contenu | Copie sur le Mac | SHA à vérifier | Nouveau nom |
|---|---|---|---|---|
| `porky-gel-code` | code relu du gel | `~/porkyevitch/experiences/2026-10-29-gel-phase1/` | `CODE_SHA256.json` `c3a538cc…` ; `gel_*.py` `e228e390` / `cc0686d3` / `f84ebc46` / `0ac075ad` ; `ENTREES_GELEES.json` `6bde8229…` | `pkyevitch-gel-code` |
| `porky-gel-config` | `reference.json`, `ml_decoder.py`, liaison | `scratchpad/p9a-pull/gel-config/` (téléchargé le 30/10) | `reference.json` `365a0d66…`, `ml_decoder.py` `59fbf54f…` ; **nouvelle** `sources.json` (chemins `pkyevitch-*`) | `pkyevitch-gel-config` |
| `porky-banc-gel` | `frozen.json` (adresses IIIF, **aucune image**) | `~/porkyevitch-donnees/rijks-gel/frozen.json` | `2424b778…` | `pkyevitch-banc-gel` |
| `porky-non-transfert-code` | D10 | `~/porkyevitch-donnees/non-transfert/upload-3/code` (maths `19ec006`) | `CODE_SHA256.json` `45088fb5…` | `pkyevitch-non-transfert-code` |
| `porky-a1-d3-code` | scripts A1 et D3, plus `ENCODAGE_TRAIN_V3.json` | maths `2002c98` (A1) et `60c3bed` (D3) ; inventaire `~/porkyevitch/experiences/2026-10-29-p9-a/ENCODAGE_TRAIN_V3.json` | A1 `aa08303d…`, D3 `2538ae29…`, inventaire `ff424e64…` | `pkyevitch-a1-d3-code` |
| (nouveau) | blancs relus d'A1 et de D3 | `~/porkyevitch-donnees/a1-blanc/a1-blanc/blanc.json`, `.../d3-blanc/d3-blanc/blanc.json` | `81003a86…`, `b913a273…` | `pkyevitch-a1-d3-blancs` |
| `porky-p9a-science-code` | code scientifique P9-A | `~/porkyevitch-donnees/p9a/upload-devis-0b/code` (maths `29faa62`) | `CODE_SHA256_SCIENCE.json` `3b266217…` | `pkyevitch-p9a-science-code` |
| `porky-p9a-iconclass` | 7 fichiers anglais Iconclass | `~/porkyevitch-donnees/p9a/iconclass/` (`txt/en/`) | blobs Git vérifiés par le code (`descriptions`) | `pkyevitch-p9a-iconclass` |
| `porky-p9a-minilm` | cache HF MiniLM | `~/porkyevitch-donnees/p9a/minilm/hub` (87 Mo, 6 fichiers) | SHA publics vérifiés par le code | `pkyevitch-p9a-minilm` |
| `porky-p9a-prep-config` | liaison P9-A et reçu initial | `scratchpad/p9a-pull/prep-config/` | `regard_initial.json` `8f18375f…` ; **nouvelle** `sources.json` | `pkyevitch-p9a-prep-config` |
| `porky-p9a-seed-config`, `-devis-config` | configs | `upload-seed-0`, `upload-devis-0b` | (à réécrire avec les chemins `pkyevitch-*`) | `pkyevitch-p9a-*-config` |
| `porky-petit-eleve-v1` | listes, noms, scripts, **166 images JPG**, graphes, S1b | `~/porkyevitch-donnees/petit-eleve/upload/` (scripts déjà à `df6ebc2`, `pe_kaggle` `91996fe0…`) | `MANIFEST.txt` du dossier, `listes.json` `87e45b41…` | **`pkyevitch-pe-entrees`, en `.bin`** (section 3) |
| `porky-p9a-code`, `-p9a-config`, `-diag-code`, `-e*-entree`… | code des étapes passées (blanc, images, diagnostic) | dans `~/porkyevitch` | — | **non nécessaires** pour les suites ci-dessous |

## 2. Pour chaque suite : quoi téléverser, quoi monter, quoi change

**Sorties de noyaux montées telles quelles.** On ne peut pas renommer une sortie de noyau `porky-*`, mais elle existe encore. On la monte sous son ancien nom tant qu'elle existe (voir le risque, section 4). Sont concernées : `caypollard-encode-cradio`, `porky-e0-run`, `porky-e1-run`, `porky-e2-run`, `porky-e3-run`, `porky-radio-cache`, `porky-diag-run`, `porky-gel-run`, `porky-p9a-*`, `porky-a1-run`, `porky-pe-run`.

### D10, relance

- **Téléverser** : `pkyevitch-non-transfert-code`, `pkyevitch-gel-code`, `pkyevitch-gel-config` (nouvelle `sources.json`), `pkyevitch-banc-gel`.
- **Monter**, en plus des sorties `porky-e0…e3-run`, `porky-radio-cache`, `porky-gel-run`, `porky-diag-run` et `caypollard-encode-cradio` : `caypollard-iconclass-t0`, toujours présent.
- **Change.**
  - La liaison du gel change de SHA (nouveaux chemins).
  - **Le pilote D10 épingle `BINDING = 60639678…`** : il faut un mini-commit qui épingle le SHA de la nouvelle liaison. C'est une ligne, avec un test. `nt_run` et `nt_core` restent inchangés, et `metadata()` revérifie les SHA de tous les documents et poids.
  - Nouveau noyau `pkyevitch-non-transfert`, dont l'entrée fine pointe sur `pkyevitch-non-transfert-code`.
- **Images** : aucune dans les jeux. Les 301 images du dev sont téléchargées en IIIF pendant le calcul, puis effacées.

### D3, complet

- **Téléverser** : `pkyevitch-a1-d3-code` et `pkyevitch-a1-d3-blancs`.
- **Monter** : `caypollard-encode-cradio` et `porky-diag-run`. **Ne pas monter `porky-d3-run`** : il contient le même `blanc.json`, et le pilote exige exactement un fichier de ce SHA.
- **Change** : rien dans le code. Nouveau noyau `pkyevitch-d3-run`.
- **Images** : aucune.

### A1, diagnostic

- **Téléverser** : `pkyevitch-a1-d3-code` (le pilote A1 doit d'abord passer à `STAGE = diagnostic`, commit relu), `pkyevitch-a1-d3-blancs` (blanc `81003a86`), et un jeu pour le reçu `recu_planche_a1.json`, une fois la planche du réglage regardée.
- **Monter** : `caypollard-encode-cradio`, `porky-diag-run`, et `porky-a1-run`, dont la dernière version est le réglage (`MANIFEST_REGLAGE.json`). Une copie locale existe : `~/porkyevitch-donnees/a1-reglage/`, `MANIFEST_REGLAGE` `8f75d500…`.
- **Images** : la planche du réglage est un HTML de codes, sans image.

### P9-A, suite (planches, puis mesures, après la graine 0 en cours)

- **Téléverser** :
  - `pkyevitch-p9a-science-code` (`3b266217`, inchangé) ;
  - `pkyevitch-p9a-iconclass` ;
  - `pkyevitch-p9a-minilm` ;
  - `pkyevitch-p9a-prep-config`, avec une **nouvelle** `sources.json` aux chemins `pkyevitch-*` ;
  - une config par étape (`pkyevitch-p9a-planches-config`, puis `-mesures-config`), avec `binding_sha256` = la nouvelle liaison.
- **Pourquoi aucun changement de code** : `planches` et `mesures` n'appellent pas `load_preparation`, qui épingle l'ancienne liaison `9294a792`. Elles ne lisent la liaison qu'à travers `TrainData` (SHA de l'inventaire) et les descriptions Iconclass (blobs vérifiés). L'identité de la course reste portée par `gel.json`.
- **Monter** : la sortie de la graine, `porky-p9a-seed`, puis celle des planches pour les mesures.
- **Correction du 30/10** (`notes/2026-10-30-p9a-graines-1-2.md`) : l'étape `seed` ne lit que `encoder_root`, `baseline_pt`, `e3_json` et `e3_run_json` (sorties de noyaux encore présentes) et le SHA du fichier de liaison. Re-téléverser l'ancien `sources.json` `9294a792` à l'identique, dans un jeu `pkyevitch-*`, suffit donc pour une relance ou pour les graines 1 et 2. Ni nouvelle préparation ni amendement ne sont nécessaires. Le paragraphe suivant surestimait ce coût.
- **Attention**, si la graine en cours devait être **relancée** : `seed` appelle `load_preparation`, qui exige la liaison `9294a792`. Celle-ci pointe vers deux jeux supprimés. Une relance demanderait alors une nouvelle préparation, un nouveau regard de la planche initiale et un amendement relu. C'est le cas le plus coûteux de l'inventaire.
- **Images** : l'étape `planches` télécharge les originaux Brillfull et les écrit dans **sa propre sortie de noyau**, sous l'extension `.image` (octets bruts) : rien n'est téléversé. L'étape `mesures` monte cette sortie. La faire passer par un `.bin` demanderait de modifier le pilote relu `kaggle_p9a_science.py` (extraction, puis `--planches` vers le dossier extrait). **Coût** : un petit diff du pilote, des tests, puis Grok p2 et Codex p4. **Je propose de ne le faire que si une sortie de noyau est à son tour supprimée.**

### Petit élève, mesures (après le complet en cours)

- **Téléverser** :
  - les entrées en **`.bin`** (section 3) ;
  - le reçu `recu_planche_pe.json`, dans un petit jeu sans image ;
  - et, si la sortie `porky-pe-run` est menacée, le **dossier scellé** du complet, qui contient 12 planches JPG, lui aussi en `.bin`.
- **Monter** : `caypollard-encode-cradio` et la sortie du complet.
- **Change.** Le pilote `kaggle_pe_run.py` doit accepter les archives : trouver exactement un `pe-entrees.bin` (et un `pe-scelle.bin`), vérifier leur SHA épinglé, les extraire de façon sûre (fonction `safe_extract` déjà relue du pilote de mesure de la phase 1), puis passer les dossiers extraits à `pe_kaggle.py`. **`pe_kaggle.py` reste inchangé** : son SHA est vérifié par le sceau du complet, et le changer invaliderait les mesures. **Coût** : un diff du pilote seul, environ 40 lignes, des tests (extraction sûre, SHA, refus d'un second `.bin`), puis Grok p2 et Codex p4.

## 3. Archives `.bin` pour les images (prudence de Marcel)

- **Format** (comme `mesure-dev.bin`) : un tar **non compressé** (`COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -cf`), renommé `.bin` pour que Kaggle ne le décompresse pas, avec un SHA-256 épinglé dans le pilote.
- **Extraction sûre** : refus des chemins absolus, de `..`, des liens et des fichiers spéciaux, extraction dans `/kaggle/working/<nom>-in`.
- **Concernés** :
  - les 166 images du petit élève, avec leurs graphes, S1b, listes et scripts (`pkyevitch-pe-entrees`) ;
  - le dossier scellé du complet, s'il faut le re-téléverser.
- **Non concernés** :
  - D10 et D3, sans image ;
  - le dev Rijksmuseum, jamais téléversé (téléchargé en IIIF) ;
  - les planches P9-A, écrites dans des sorties de noyau.
- **Les sorties de noyaux existantes** `porky-p9a-images` et `porky-p9a-prepare` contiennent les 12 images initiales de P9-A (octets bruts et vignettes de la planche initiale). Seule une relance de la graine les remonterait.

## 4. Risques et sauvegardes à faire tout de suite (rapatrier, sans rien lancer)

Si Kaggle supprime aussi les **noyaux** `porky-*`, plusieurs sorties sont **sans copie complète sur le Mac** :

| Sortie | État local | Priorité |
|---|---|---|
| `porky-diag-run` (`probabilites_validation.npz` `c7df9d3d…`) | **copie locale vide** (0 octet, SHA `e3b0c442…`) | **haute** : D10, D3 et A1 en dépendent |
| `porky-e1-run`, `porky-e2-run`, `porky-e3-run` (dont `t_z.pt`) | absentes | haute : référence B, et D10 via la liaison du gel |
| `porky-e0-run` (`t_long.pt` `5a1b3041…`) | présent (`e0-complet`) | — |
| `porky-gel-run` (sceau `3c468faa…`) | présent (`gel-phase1/freeze-2`) | — |
| `porky-a1-run` (réglage) | présent (`a1-reglage`) | — |
| `porky-radio-cache` | absent ; retéléchargeable depuis HF (révision épinglée, SHA vérifiés) | moyenne |
| `porky-p9a-prepare`, `-images`, `-smoke`, `-devis` | partiel (`p9a/`) | moyenne (relance de la graine seulement) |
| `porky-p9a-seed`, `porky-pe-run` | en cours | **à rapatrier dès la fin** |

Si une sortie de noyau disparaît, on la re-téléverse depuis le Mac en jeu `pkyevitch-*`, en `.bin` si elle contient des images. On réécrit alors la liaison concernée : les SHA sont inchangés, seuls les chemins changent. Les pilotes qui trouvent leurs entrées par motif (A1, D3, D10, petit élève) n'ont pas à changer. P9-A ne demande qu'une nouvelle config, sauf pour une relance de la graine.

## 5. Ordre proposé

1. Rapatrier `porky-diag-run` et `porky-e1…e3-run` vers le Mac, et Drive si besoin : `kaggle kernels output … --page-size 200`, puis vérifier les SHA.
2. Mini-commit D10 (nouvelle liaison épinglée), puis téléversement `pkyevitch-*` et relance.
3. D3 complet : téléversement de `pkyevitch-a1-d3-code` et des blancs, puis nouveau noyau.
4. Diff du pilote du petit élève pour les `.bin`, relu pendant le complet, puis mesures.
5. P9-A planches : nouvelles configs et liaison, sans code. Le `.bin` des planches n'est à faire que si nécessaire.
6. A1 diagnostic : `STAGE = diagnostic` relu, puis le reçu de la planche du réglage.
