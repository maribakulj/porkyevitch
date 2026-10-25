# Provenance — 2026-10-25-xanto-parties

Test pose/parties pour Xanto. Appartient au projet xanto : copié ici en attendant, à rendre à son agent.

- Source : `https://github.com/maribakulj/caypollard.git`, commit `c0bfe6c587452aba77cc552b9f43799839c81fc8` (branche pilote-figures), copie du 25/10/2026 par `tools/migrer.py`.
- Copie à l'identique (empreintes vérifiées) des fichiers suivis par git ; rien n'a été modifié.
- Les scripts copiés sont une archive : ils s'exécutent depuis un clone de caypollard à ce commit.
- Arbre de travail au moment de la copie : fichiers non suivis ou modifiés présents :
  - `?? results/xanto-parties/kaggle/caypollard-xanto-parts-run.log`

## Ce qui a réellement tourné

- `resultats/kaggle/out/run.json` : script `4fe64ea7699e…` — identique au `scripts/remote_xanto_parts.py` copié.

## Dépendances restées dans caypollard

- `scripts/remote_xanto_parts.py` : importe `caypollard.atelier.bricks`

## Fichiers copiés (ancien chemin → nouveau chemin, sha256)

| caypollard | porkyevitch | sha256 |
|---|---|---|
| `scripts/remote_xanto_parts.py` | `scripts/remote_xanto_parts.py` | `4fe64ea7699ee54e…` |
| `results/xanto-parties/PREINSCRIPTION.md` | `resultats/PREINSCRIPTION.md` | `44b14da9c1cabee1…` |
| `results/xanto-parties/RESULTAT.md` | `resultats/RESULTAT.md` | `c92944577f6e51de…` |
| `results/xanto-parties/kaggle/out/b0_controle.json` | `resultats/kaggle/out/b0_controle.json` | `4e2cca5365ac8375…` |
| `results/xanto-parties/kaggle/out/planche.png` | `resultats/kaggle/out/planche.png` | `ff242f48894919fd…` |
| `results/xanto-parties/kaggle/out/rangs.csv` | `resultats/kaggle/out/rangs.csv` | `44c008df1f033a92…` |
| `results/xanto-parties/kaggle/out/resume.json` | `resultats/kaggle/out/resume.json` | `18d84582ae9f59fe…` |
| `results/xanto-parties/kaggle/out/run.json` | `resultats/kaggle/out/run.json` | `399fb920bd598d0b…` |

## Laissés dans caypollard (non suivis par git : données lourdes ou sous licence)

- `results/xanto-parties/kaggle/caypollard-xanto-parts-run.log` (0.0 Mo) `598150210994f064…`
