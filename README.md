# porkyevitch

Une boîte à outils pour mener des recherches sur des modèles avec des agents : entraîner sur Kaggle et Colab sans
dépenser deux fois, vérifier qu'un calcul peut conclure avant de le lancer, et donner aux agents du code prêt plutôt
que de le leur faire réécrire. Elle s'installe comme **plugin Claude Code** dans n'importe quel projet.

Le dépôt est **neutre**. Il ne contient ni journal, ni expérience, ni rien d'un projet particulier : chaque projet a
son propre dépôt, privé, avec son journal. Les modèles aboutis sont publiés chacun dans leur dépôt.

## Ce qu'il contient

| Dossier | Quoi |
|---|---|
| `skills/` | `guichet` (soumettre et suivre un calcul) et `carte-de-recherche` (ce calcul peut-il conclure ?) |
| `agents/` | `relecteur-conception` : relecture de conception indépendante, en lecture seule, qui ne reçoit que la carte, le code et les résultats |
| `hooks/` | Un crochet sur Bash : `kaggle kernels push` et `colab new/run/exec` lancés directement sont refusés, avec la commande du guichet ; la sortie de `guichet-agent` ne passe pas dans un tube |
| `bin/` | `puissance` et `neutralite`, en commandes courtes (dans le PATH de Bash quand le plugin est actif) |
| `labo/guichet/` | La seule porte vers Kaggle et Colab, sous un compte Unix à part. Pas de doublon, pas de relance sur un état inconnu, sorties vérifiées, budget tenu. Une course GPU nomme sa carte de recherche, dont le guichet recalcule la puissance. Voir son README |
| `labo/graphe/` | Graphe de recherche facultatif (rdflib, pyshacl) : vocabulaire, formes SHACL, générateur, rapport par hypothèse, écriture d'un verdict que les formes peuvent refuser. Voir son README |
| `labo/puissance.py` | Puissance et effet minimal détectable à partir d'un IC déjà mesuré ; refuse ce qui ne peut pas conclure |
| `porky/` | Colab en ligne de commande (`colab.py` : chaîne qui ne laisse jamais le noyau inactif, envoi en morceaux), montage du Drive (`drivemount.py`), sauvegarde vers un dépôt Hugging Face privé (`sauvegarde_hf.py`) |
| `gabarits/` | `BOUCLE.md` (règles d'une boucle autonome), `carte-de-recherche.md` et `noyau/` (noyau de calcul pour le guichet et son essai local complet), à copier dans un projet |
| `outils/neutralite.py` | Le contrôle qui garde ce dépôt neutre |

## Trois règles d'entrée

1. **On extrait, on n'invente pas.** Un outil n'entre ici qu'après avoir servi pour de vrai dans un projet, avec ses
   tests. Une capacité testée, jamais une promesse.
2. **Neutre, et vérifié.** `outils/neutralite.py` refuse chemins personnels, adresses, identifiants de décision ou
   d'onglet d'agent. Chaque projet le lance aussi avec sa propre liste de termes (`--termes`), gardée dans son dépôt
   privé, avant de contribuer ici.
3. **Le générique d'abord.** Ce qui est propre à un domaine (par exemple l'iconographie) va dans un dossier de
   domaine à part, jamais dans `labo/` ni `porky/`.

## Dans un projet

Installer le plugin (dans Claude Code) :

    /plugin marketplace add maribakulj/porkyevitch
    /plugin install porkyevitch@porkyevitch

Puis copier `gabarits/BOUCLE.md` dans le dépôt privé du projet, et installer le guichet une fois par machine
(`labo/guichet/README.md`).

## Tests

    python3 -I outils/neutralite.py
    for f in labo/guichet/tests/test_*.py labo/tests/test_*.py labo/graphe/tests/test_*.py outils/tests/test_*.py hooks/tests/test_*.py; do python3 -I "$f"; done

Chaque changement d'un fichier livré monte la version de `.claude-plugin/plugin.json` (`outils/version.py`, vérifié
en CI) : une version inchangée laisse les projets sur l'ancienne copie.

Python 3.11 ou plus, bibliothèque standard seule, sauf `porky/sauvegarde_hf.py` (`huggingface_hub`) et `labo/graphe/` (`rdflib`, `pyshacl`, facultatifs : ses tests sont sautés sans eux).
