# Guichet de calcul

Seule porte vers Kaggle et Colab. Il tourne sous un compte Unix à part (`labo`), qui détient seul les identifiants.
L'agent n'a qu'une commande sous ce compte, `guichet-agent`. Il peut soumettre, suivre et demander, mais ni approuver
ni lire les identifiants. Python 3.11 ou plus, bibliothèque standard seule.

## Ce qu'il garantit

- **Un calcul, une course active.** La clé d'un calcul est l'empreinte de son dossier (hors `kernel-metadata.json`),
  de son point d'entrée et de ses entrées déclarées. Ni le nom de l'expérience ni la plateforme n'y entrent. Une
  seconde soumission de la même clé est refusée, sur Kaggle comme sur Colab, même quand deux processus soumettent au
  même instant : l'index unique de SQLite tranche.
- **Un calcul réussi ne se refait pas.** Le guichet renvoie à sa sortie. Une réplication voulue se demande avec
  `--replication MOTIF` et attend ton accord.
- **Pas de bascule en doublon.** Une course en file sur Colab est annulée avant d'aller ailleurs. Sur Kaggle, dont le
  CLI ne sait pas annuler, la bascule attend ton accord. Si l'ancienne démarre quand même, `reconcilier` le
  signale et son temps est compté.
- **Incertain n'est pas fini.** Un délai dépassé au lancement, ou un lancement interrompu, rend la course INCONNUE.
  Un relevé illisible ne change rien. Une INCONNUE bloque la clé jusqu'à une réponse distante. Sur Kaggle sans
  numéro de version, c'est toi qui tranches.
- **Réussi veut dire « artefacts présents ».** Les fichiers de `artefacts_attendus` doivent être dans la sortie
  rapatriée, non vides. Sinon la course est `ECHOUEE_ARTEFACTS`.
- **Un rapatriement raté n'est pas un calcul raté.** `reconcilier` retente le téléchargement, jamais le calcul.
- **Une relance identique après échec se motive** (`--motif`) : un même code redonne en général le même échec.
- **Durée et budget.** Une durée estimée au-delà de 3 h doit avoir été mesurée par un essai chronométré réussi
  (une estimation jamais mesurée finit en noyau coupé à 12 h, sans sortie). Une course GPU de plus de 3 h attend ton accord. Le guichet tient un budget GPU sur 7 jours
  glissants et un nombre maximal de courses GPU simultanées.
- **Une course GPU nomme sa carte de recherche** (`carte_recherche` dans la carte de calcul). Sans elle, ou si son
  bloc ` ```toml recherche ` est incomplet, refus. Le guichet **recalcule** la puissance à partir des nombres de la carte
  (il ne croit pas un verdict écrit) : une course qui ne peut pas conclure, exploratoire, ou dont la prémisse n'est pas
  vérifiée attend ton accord. Le format est en tête de `guichet/recherche.py`. Une course CPU n'en a pas besoin.
- **Ce qui part est ce qui a été haché.** Le guichet copie le dossier, hache la copie et lance la copie. Il refuse
  les liens symboliques, les liens physiques et tout chemin pris dans son propre espace.

## Ce qu'il ne garantit pas

- Que la carte de recherche dise vrai. Le guichet vérifie qu'elle est complète et refait le calcul de puissance, mais
  l'effet plausible et l'IC cités restent à relire (`skills/carte-de-recherche`, agent `relecteur-conception`).
- Que la carte déclare tout ce dont la suite aura besoin. Le guichet ne devine pas un artefact non déclaré
  (`tests/test_incidents.py` le dit en clair). Le résumé te montre les artefacts déclarés de chaque demande.
- Que les vrais CLI répondent toujours dans les formats attendus. Les adaptateurs sont testés contre de faux CLI
  (`tests/test_adaptateurs.py`), pas contre Kaggle ni Colab. Le premier usage réel doit être un petit calcul CPU.
- Une frontière contre un agent qui aurait ton mot de passe, ou qui écrirait dans un interpréteur qui t'appartient.
  `installer.sh` vérifie ce second point.

## Installation sur le Mac (une fois)

Non testée sur macOS : l'essai complet des comptes et de sudoers a été fait sous Linux.

1. **Le compte.** Crée un compte standard `labo` (Réglages > Utilisateurs et groupes, ou `sysadminctl -addUser labo`).
   Son dossier doit rester en `700`. C'est aussi ce qui empêche un lien physique vers ses fichiers.
2. **Un Python que l'agent ne peut pas modifier.** Celui de python.org (installé par root) convient. Celui de Homebrew
   non, car il appartient à ton compte. `installer.sh` refuse un interpréteur modifiable par un autre compte que
   root ou `labo`.
3. **Les CLI dans le compte `labo`.** Sous `labo` : un venv avec `kaggle` (`python3 -m venv ~/.venv-guichet &&
   ~/.venv-guichet/bin/pip install kaggle`) et le CLI `colab` dans `~/.local/bin`.
4. **Les identifiants.** Sous `labo`, place `~/.kaggle/kaggle.json` et fais `gcloud auth application-default login`.
   **Puis régénère le jeton Kaggle et révoque les identifiants Google de ton propre compte**
   (`gcloud auth application-default revoke`). L'agent a eu accès aux anciens : les déplacer ne suffit pas.
5. **Le dossier des sorties.** Un dossier écrit par `labo` et lisible par toi, par exemple `/Users/Shared/guichet-sorties` sur macOS.
6. **L'installation.** Lance `sudo sh tools/guichet/installer.sh /chemin/vers/python3 labo`, puis copie et adapte
   `~labo/guichet/config.toml`. Ajoute ensuite les deux lignes sudoers que le script affiche
   (`sudo visudo -f /etc/sudoers.d/guichet`).
7. **Le dépôt.** Il doit être lisible par `labo`, pour que le guichet puisse copier les dossiers de calcul.

Après une modification du guichet dans le dépôt, il faut relancer `installer.sh`. Le code qui tourne est la copie
de `/usr/local/lib/guichet`, propriété de root, jamais celle du dépôt.

## Usage

Agent :

    sudo -u labo guichet-agent soumettre experiences/…/carte.toml --plateforme kaggle
    sudo -u labo guichet-agent reconcilier
    sudo -u labo guichet-agent resume
    sudo -u labo guichet-agent demander-bascule R-… --vers colab --motif "file Kaggle bloquée depuis 1 h"

Humain (ton mot de passe à chaque appel) :

    sudo -u labo guichet resume
    sudo -u labo guichet approuver D-…
    sudo -u labo guichet refuser D-… --motif "…"
    sudo -u labo guichet trancher R-… EN_COURS --version 7 --motif "version 7 vue sur le site"

Codes de sortie : `0` accepté, `2` refus, `3` accord requis, `4` incertain. **Ne passe jamais ces commandes dans un
tube** : le code de sortie deviendrait celui de la dernière commande du tube.

## La carte et le dossier

Le format de la carte est documenté en tête de `guichet/carte.py`. Le dossier contient le code, sa configuration,
et `kernel-metadata.json` pour Kaggle (`code_file` = `point_entree`, `enable_gpu` = `gpu`). Les grosses données n'y
vont pas : sur Kaggle, elles passent par les `dataset_sources` du noyau ; sur Colab, le calcul les télécharge
lui-même, car la machine n'a aucun identifiant. Dans les deux cas, elles sont déclarées dans `[[entrees]]` avec leur
empreinte, et le calcul vérifie cette empreinte.

Le calcul écrit ses artefacts dans `os.environ.get("GUICHET_SORTIE", "/kaggle/working")`. Les motifs
d'`artefacts_attendus` sont relatifs à ce dossier.

## Tests

    python3 -I tests/test_guichet.py       # les règles, une par test
    python3 -I tests/test_incidents.py     # incidents types d'une boucle autonome, rejoués à vide
    python3 -I tests/test_adaptateurs.py   # Kaggle et Colab contre de faux CLI ; la chaîne Colab tourne vraiment

## Mise à jour depuis la version 0.1

La table `demandes` accepte une nouvelle nature d'accord, `RECHERCHE`. Un registre créé par la version 0.1 garde
l'ancienne contrainte : avant la mise à jour, s'assurer qu'aucune demande n'est en attente, puis renommer
`~labo/guichet/registre.sqlite` (le guichet en recrée un). Les courses passées restent lisibles dans l'ancien fichier.
