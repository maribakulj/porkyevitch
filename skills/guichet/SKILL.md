---
name: guichet
description: Pour tout calcul sur Kaggle ou Colab (entraînement, encodage, mesure, sonde, essai à blanc) : le soumettre, le suivre, le basculer, en récupérer la sortie. Ne jamais lancer `kaggle kernels push` ni `colab new` directement. À utiliser aussi quand une file tarde, qu'un lancement a expiré, ou qu'on veut refaire un calcul.
allowed-tools: Bash(command -v guichet-agent) Bash(sudo -u labo guichet-agent *)
---

# Guichet de calcul

Le guichet détient seul les identifiants Kaggle et Colab, sous un compte Unix à part. Tu soumets une **carte** ; il
refuse les doublons, suit les courses, rapatrie et vérifie les sorties. Sa documentation complète est dans
`${CLAUDE_PLUGIN_ROOT}/labo/guichet/README.md`. Le format de la carte est en tête de
`${CLAUDE_PLUGIN_ROOT}/labo/guichet/guichet/carte.py`.

## Avant tout : le guichet est-il installé ?

```bash
command -v guichet-agent
```

Rien ne s'affiche : le guichet n'est pas installé sur cette machine. Ne lance rien par un autre chemin, ni Kaggle ni
Colab directement (un crochet du plugin le refuse de toute façon). Dis-le, et renvoie à l'installation, faite une fois
par machine par une personne : `${CLAUDE_PLUGIN_ROOT}/labo/guichet/README.md`.

## Avant de soumettre : le code doit avoir tourné

Une course perdue coûte plus cher qu'un essai. Avant toute course d'un noyau nouveau ou modifié :

1. **Partir du gabarit** `${CLAUDE_PLUGIN_ROOT}/gabarits/noyau/` (`run.py` et `tests/test_essai_local.py`) : paramètres
   lus dans `GUICHET_PARAMETRES`, entrées vérifiées par SHA-256, repères d'étape sur disque, pile en cas de plantage,
   contrôle de la sortie.
2. **Vérification statique** : `uvx pyflakes run.py` (un nom indéfini se voit là, pas après 40 minutes de file).
3. **Essai local complet** : tout le programme, sur le Mac, sur un faux dossier d'entrées (`GUICHET_ENTREES`) ou sur
   quelques éléments réels ; un faux encodeur ou une fausse tête si le GPU manque. Le test vérifie les comptes, pas
   seulement l'absence d'erreur.
4. **Données extérieures** : la première course n'en sort que le schéma (noms de champs, comptes), et toute requête
   réseau du noyau s'essaie d'abord depuis le Mac, dans les mêmes conditions (adresse, agent HTTP).
5. **Essai court sur la plateforme**, même code, seuls les `[parametres]` changent (par exemple `LIMITE = 300`). Au-delà
   d'une heure de GPU, le guichet exige cet essai réussi : nomme sa course dans `essai_par`.
6. Modifier le code avec l'outil d'édition, qui refuse un passage non unique, jamais par un script de remplacement ou
   `sed` ; les variantes d'un même calcul passent par `[parametres]`, pas par des copies du code.

## Soumettre

0. Pour une course GPU : la **carte de recherche** d'abord (skill `carte-de-recherche`). La carte de calcul la nomme
   dans `carte_recherche`. Sans elle, ou incomplète, le guichet refuse. Il recalcule lui-même la puissance : une course
   qui ne peut pas conclure, exploratoire, ou dont la prémisse n'est pas vérifiée attend un accord humain (code 3).
1. Un dossier avec le code, sa configuration et, pour Kaggle, `kernel-metadata.json` (`code_file` = le point
   d'entrée, `enable_gpu` = `gpu`). Pas de données lourdes, ni de lien symbolique.
2. Le calcul écrit ses artefacts dans `os.environ.get("GUICHET_SORTIE", "/kaggle/working")`.
3. Une carte TOML qui déclare `artefacts_attendus` : **tout** ce dont la suite aura besoin, modèles compris. Une
   course sans eux échoue, et ce que la carte ne nomme pas ne sera pas deviné.
4. Puis :

   ```bash
   sudo -u labo guichet-agent soumettre chemin/carte.toml --plateforme kaggle
   ```

## Lire la réponse : par le code de sortie, jamais à travers un tube

| Code | Sens | Que faire |
|---|---|---|
| 0 | accepté, lancé | `reconcilier` au prochain réveil |
| 2 | refus | lire le motif : il dit quoi faire. Ne pas contourner |
| 3 | accord humain requis | rien n'est lancé ; avancer sur autre chose, ou attendre |
| 4 | incertain | la course est INCONNUE ; `reconcilier` plus tard ; **ne rien relancer** |

## Suivre

```bash
sudo -u labo guichet-agent reconcilier
sudo -u labo guichet-agent resume
sudo -u labo guichet-agent etat R-…
sudo -u labo guichet-agent attendre R-… --max-min 30   # relève jusqu'à la fin : 0 réussie, 2 autre fin, 4 échéance
sudo -u labo guichet-agent bilan --depuis AAAA-MM-JJ   # durée vue de chaque course, totaux par chantier
```

- Une course en cours doit avoir un réveil armé ; `attendre`, lancé en arrière-plan, en tient lieu.
- Un point ou un rapport cite les durées du `bilan`, pas une estimation de mémoire.
- « Terminée, sortie non rapatriée » : `reconcilier` retente le téléchargement. Le calcul est fait, ne le relance pas.
- Un relevé illisible ne vaut ni « fini » ni « mort ».

## Ce qui est refusé, et la voie prévue

| Envie | Réponse du guichet | La voie |
|---|---|---|
| la file tarde, lancer ailleurs | refus : déjà actif | `demander-bascule R-… --vers colab --motif "…"` (accord humain depuis Kaggle) |
| refaire un calcul réussi (« contrôle croisé ») | refus : déjà fait, voici la sortie | relire la sortie ; sinon `--replication MOTIF` (accord humain) |
| relancer à l'identique après un échec | refus sans motif | corriger le code (calcul nouveau), ou `--motif` si la cause est extérieure |
| durée estimée > 3 h | refus : à mesurer | un essai chronométré d'abord, nommé dans `duree_mesuree_par` |
| course GPU > 1 h sans essai du même code | refus | essai court (mêmes code et entrées, autres `[parametres]`), nommé dans `essai_par` |
| point d'entrée qui ne se lit pas comme du Python | refus avant le départ | corriger, puis l'essai local |
| lancer une course GPU sans carte de recherche | refus | écrire la carte, la nommer dans `carte_recherche` |
| la carte dit « ne peut pas conclure » | accord humain requis | redessiner l'effectif ou le contraste, ou attendre l'accord |
| plus de N GPU à la fois, budget atteint | refus | attendre : c'est une issue normale |
