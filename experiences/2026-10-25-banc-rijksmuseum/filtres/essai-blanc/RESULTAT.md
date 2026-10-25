# Étape 2, essai à blanc (Kaggle `mabaku/rijks-filtres-run` v1, 25/10/2026)

Scripts : `filtres_distances.py` e0fb13ff…, pilote 5c969c36… (commit a0dff53), feux verts Grok et Codex
(`porkyevitch-banc-filtres-{grok,codex}.md`). Entrée : 16 premiers des 53 éligibles de l'essai à blanc de la collecte (liste
eef74b15…). Technique seulement : la référence dHash est réduite à 16 lignes par fragment (192), ses distances ne servent à rien.

- `run.json` : script et liste aux empreintes attendues, `smoke = 16`, Tesla T4 ; vecteurs de la sortie v3 vérifiés (87 004).
- `controle_encodeur.json` : 64 images test réencodées, cosinus minimal 1,0, écart maximal 0 → recette identique.
- `resume.json` : 16 images gardées, 0 exclue ; 192 références, 0 indécodable ; 5 paires internes.
- `budget.json` : 154 s, RAM 3,5 Go (ru_maxrss en Kio / 1e6 ≈ Go à 2,4 % près), VRAM 2,9 Go, sorties 3,6 Mo.
- Les images des candidats, les voisins, les paires et les vecteurs (identifiants de candidats) sont hors git
  (`~/porkyevitch-donnees/rijks-filtres-essai/`) ; les 16 images rapatriées par la commande de sortie ont été effacées du Mac sans
  être ouvertes.

Point d'attention pour l'exécution complète (constat, aucun réglage) : contre seulement 192 références, les distances dHash
minimales des 16 candidats vont déjà de 63 à 96 bits, et 4 des 5 paires internes viennent du critère dHash (48 à 61 bits, cosinus
0,63-0,86). Contre les 87 004 références et entre ~8 000 candidats, les seuils dHash (< 50 pour le filtre, < 64 pour les copies
internes) peuvent retirer beaucoup d'objets ou réunir de très grandes composantes. La préinscription le traite déjà : comptes publiés
et arrêt si la faisabilité (≥ 150 composantes au test, ≥ 40 au dev) n'est pas atteinte, sans changer de seuil.
