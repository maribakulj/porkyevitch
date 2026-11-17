---
name: carte-de-recherche
description: Avant de concevoir une expérience, une préinscription ou un entraînement, ou avant de lancer un calcul, vérifier qu'il peut conclure et qu'il change une décision. Six questions et un calcul de puissance. À utiliser aussi avant de clore une piste sur un résultat « pas de signal ».
---

# Carte de recherche

Une revue de code impeccable sur un dispositif qui ne peut rien conclure reste un échec. Cette carte s'écrit **avant**
le code et la préinscription détaillée, en quelques lignes par question. Le gabarit est
`${CLAUDE_PLUGIN_ROOT}/gabarits/carte-de-recherche.md`.

## Les six questions

1. **Quelle décision ce calcul change-t-il ?** Écrire les issues possibles et la décision qui suit chacune. Si
   toutes les issues mènent à la même décision, ne pas lancer.
2. **Peut-il conclure ?** Donner l'effet plausible et sa source (une mesure passée, citée), l'effectif prévu, et
   l'erreur-type attendue (un IC déjà mesuré sur le même banc, ou un pilote). Puis lancer :

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/labo/puissance.py" --ic BAS HAUT --effet-plausible E [--n N0:N1] [--famille K] [--unilateral]
   ```

   Code 2 (« ne peut pas conclure ») : **ne pas lancer**. Redessiner l'effectif, le banc ou le contraste, ou
   demander un accord humain explicite. `--famille` applique Bonferroni, `--unilateral` la règle « borne basse > 0 ».
   Une règle de retenue exigeante sur un banc bruité peut rendre le verdict acquis d'avance : le calcul le montre.
3. **La prémisse est-elle vérifiée ?** Si le calcul suppose un fait non mesuré (« ce gain se transférera à l'autre
   collection »), le diagnostic le moins cher de ce fait passe d'abord, avant toute série.
4. **Le dispositif est-il comparable ?** Mêmes conditions d'apprentissage et de test pour ce qu'on compare. Par
   exemple, une tête apprise à une résolution et testée à une autre ne mesure pas l'effet de la résolution.
5. **Existe-t-il un contrôle direct du résultat ?** Si oui, vérifier le résultat plutôt que le processus. Des jours
   de preuve d'isolement d'un environnement ne valent pas un cosinus ≥ 0,999 sur des sorties de référence.
6. **Coût et artefacts.** Durée (mesurée par un essai chronométré au-delà de 3 h), et tout ce dont la suite aura
   besoin, **modèles compris**. Une étude qui ne sauvegarde pas ses états se refait entièrement.

## Lire un résultat

| Statut | Quand | Ce qu'il permet |
|---|---|---|
| `SOUTENU` | règle remplie, dispositif capable de la remplir | adopter, dans ces conditions |
| `NON_SOUTENU_DANS_CES_CONDITIONS` | puissance suffisante à l'effet plausible, effet non vu | écarter ce dispositif, pas l'idée |
| `NON_CONCLUANT` | puissance insuffisante, ou témoin illisible | **rien** : la piste ne se clôt pas, elle se suspend, avec ce qu'il faudrait pour conclure |
| `ECHEC_TECHNIQUE` | le calcul n'a pas mesuré ce qu'il devait | rien sur l'hypothèse |
| `NON_TESTE` | | |

Avant de clore une piste, relancer `${CLAUDE_PLUGIN_ROOT}/labo/puissance.py` sur le test qui la clôturerait. S'il rend le code 2, le
statut est `NON_CONCLUANT`.
