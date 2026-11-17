---
name: guichet
description: Pour tout calcul sur Kaggle ou Colab (entraînement, encodage, mesure, sonde, essai à blanc) : le soumettre, le suivre, le basculer, en récupérer la sortie. Ne jamais lancer `kaggle kernels push` ni `colab new` directement. À utiliser aussi quand une file tarde, qu'un lancement a expiré, ou qu'on veut refaire un calcul.
---

# Guichet de calcul

Le guichet détient seul les identifiants Kaggle et Colab, sous un compte Unix à part. Tu soumets une **carte** ; il
refuse les doublons, suit les courses, rapatrie et vérifie les sorties. Sa documentation complète est dans
`${CLAUDE_PLUGIN_ROOT}/labo/guichet/README.md`. Le format de la carte est en tête de
`${CLAUDE_PLUGIN_ROOT}/labo/guichet/guichet/carte.py`.

## Soumettre

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
```

- Une course en cours doit avoir un réveil armé.
- « Terminée, sortie non rapatriée » : `reconcilier` retente le téléchargement. Le calcul est fait, ne le relance pas.
- Un relevé illisible ne vaut ni « fini » ni « mort ».

## Ce qui est refusé, et la voie prévue

| Envie | Réponse du guichet | La voie |
|---|---|---|
| la file tarde, lancer ailleurs | refus : déjà actif | `demander-bascule R-… --vers colab --motif "…"` (accord humain depuis Kaggle) |
| refaire un calcul réussi (« contrôle croisé ») | refus : déjà fait, voici la sortie | relire la sortie ; sinon `--replication MOTIF` (accord humain) |
| relancer à l'identique après un échec | refus sans motif | corriger le code (calcul nouveau), ou `--motif` si la cause est extérieure |
| durée estimée > 3 h | refus : à mesurer | un essai chronométré d'abord, nommé dans `duree_mesuree_par` |
| plus de N GPU à la fois, budget atteint | refus | attendre : c'est une issue normale |
