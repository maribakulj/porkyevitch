# Règle de décision rejouable et témoin avant la course

Deux instruments de contrôle pour une expérience confirmatoire. Bibliothèque standard seulement.

## Convention

Chaque expérience confirmatoire a, dans son dossier (hors du noyau de calcul) :

- `regle.py` : une fonction pure `issue(recu: dict) -> dict` qui lit **seulement** le reçu d'agrégats publié et rend l'issue
  écrite dans la carte, `{"statut": ..., "motifs": [...]}` (des clés descriptives en plus sont permises, hors du statut).
  Elle est écrite à partir du texte de la carte et n'importe rien du noyau : `rejouer.py` refuse tout import hors de la
  bibliothèque standard. Une constante facultative `CONCLUSIFS` liste les statuts conclusifs.
- `temoins/` : un JSON par cas, écrit avant la course.

## Rejouer

    python3 labo/regle/rejouer.py --regle regle.py --recu recu.json [--complement NOM=autre.json] \
        [--attendu STATUT] [--sortie DOSSIER]

Écrit `issue-recalculee.json` (empreintes SHA-256 de la règle, du reçu et des compléments, puis l'issue ; ni date ni
chemin, donc les mêmes octets à chaque rejeu). Code 1 si l'issue diffère de `--attendu`, 2 en cas d'erreur. Un
complément est lu par la règle sous `recu["complements"][NOM]`. Un verdict qui s'appuie sur ce rejeu porte
`recalcule_par` (voir `labo/graphe`).

## Témoin

    python3 labo/regle/temoin.py --regle regle.py --recus-temoins temoins/ [--sortie DOSSIER]

Chaque témoin est `{"description", "doit_conclure": false, "issues_interdites": [...], "recu": {...}, "complements": {...}}`,
un reçu simulé (données nulles). Un témoin qui atteint une issue interdite (à défaut, `CONCLUSIFS` de la règle) passe la
règle : code 1, le témoin est nommé. Écrit `controle-temoin.json` (empreintes, issue obtenue, verdict du contrôle).
Un témoin `"doit_conclure": true` avec `issues_attendues` sert de contrôle de sensibilité.

## Décideur

`labo/graphe/decideur.py` propose un candidat « instrument manquant » pour toute carte confirmatoire dont le dossier n'a
ni `regle.py` ni `temoins/*.json`.

## Tests

    python3 -I labo/regle/tests/test_regle.py
