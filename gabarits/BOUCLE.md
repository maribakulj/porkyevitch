# Boucle autonome — règles de fonctionnement

Gabarit à copier dans le dépôt privé d'un projet, puis à compléter : mandat, cap, rôles des agents, jalons. Les
règles ci-dessous sont celles qui ont manqué dans une boucle réelle ; chacune répond à un échec observé.

## Mandat

<Qui décide quoi. L'agent principal décide seul, sauf ce qui figure dans « Accords humains ».>

## Chantiers ouverts : deux au plus

- Chaque chantier nomme le livrable qu'il nourrit (une section d'article, un modèle publié). Sans livrable, pas de
  chantier.
- Ouvrir un troisième chantier demande d'en fermer ou d'en suspendre un.
- **Un agent inactif n'est pas un problème.** On ne lui invente pas de tâche.

## Avant tout calcul

La carte de recherche (skill `carte-de-recherche`) : décision, puissance, prémisse, comparabilité, contrôle direct,
coût et artefacts. **Si le calcul ne peut pas conclure, on ne le lance pas.**

## Calcul : tout passe par le guichet

- Aucun lancement direct ; l'agent n'a pas les identifiants (skill `guichet`).
- Le budget sert à utiliser, pas à économiser : ce qui disparaît, c'est le doublon.
- Une file bloquée se bascule, elle ne se double pas. Un résultat existant se relit, il ne se refait pas.
- INCONNUE n'est jamais « morte ». Un rapatriement raté n'est pas un calcul raté.

## Revues

- La première relecture porte sur la **conception** (les questions de la carte), avant le code.
- La conformité des sorties à la préinscription se vérifie **par script** quand c'est possible, pas par un agent.
- Le relecteur conseille, l'agent principal décide et signe, en quelques lignes, sans recopier l'avis.
- Le relecteur ne reçoit que la carte, le code et les résultats, jamais le raisonnement de l'auteur.
- Un relecteur indisponible ne fige pas la boucle : l'item attend, l'autre chantier avance.
- Nombre de relectures : <1 pour le courant, 2 pour ce qui engage du calcul ou une piste, 3 pour le délicat>.

## Accords humains

Trois choses, et elles seules, attendent un oui ou un non :

1. ouvrir un chantier ;
2. clore ou suspendre une piste, avec le statut du résultat et **ce qui n'a pas été testé** (une piste
   `NON_CONCLUANT` ne se clôt pas) ;
3. ce que le guichet renvoie en accord : longue course GPU, réplication, bascule sans annulation.

Un résumé par jour, cinq lignes au plus à trancher. En attendant, on avance sur l'autre chantier, ou on attend.

## Une itération

1. **Relever** : `guichet-agent reconcilier`, rapports de relecture, état des agents.
2. **Débloquer** : connexions, permissions inattendues.
3. **Avancer**, sur les chantiers ouverts seulement. **Attendre est une issue normale.**
4. **Tracer** : journal (une ligne par action), décisions, commits dans le dépôt privé.
5. **Informer** : le résumé quotidien ; tout de suite seulement si l'humain doit agir.
6. **Réveil** : selon ce qu'on attend. Une course en cours doit toujours avoir un réveil armé.
