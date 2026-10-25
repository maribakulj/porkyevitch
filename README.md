# porkyevitch

Entraînements et évaluations à distance (Colab, Kaggle) pour les projets de Marcel, à commencer par caypollard. Dépôt privé.

- `porky/` : outils communs, écrits une fois : `colab.py` (cellule chaînée qui ne laisse jamais le noyau inactif, attente de drapeaux,
  envoi en morceaux de 50 Mo, surveillance de la session et du journal) ; `drivemount.py` (montage du Drive sur une machine Colab
  depuis la ligne de commande : le lien d'autorisation s'ouvre dans le navigateur, un clic de Marcel). Les mesures Iconclass
  viendront de `lermolieff` (public).
- `tools/migrer.py` : copie des expériences depuis caypollard, avec leur provenance.
- `experiences/AAAA-MM-JJ-nom/` : un dossier par expérience, toujours le même gabarit : `PREINSCRIPTION.md` (règles écrites avant
  calcul), script(s), `RESULTAT.md`, `PROVENANCE.md` (d'où viennent les fichiers, empreintes de ce qui a réellement tourné),
  `relectures.md` (résumé des relectures de Codex), artefacts légers ; les gros fichiers sont sur le Drive (`Mon Drive/porkyevitch/`)
  avec leur empreinte.

Règles : règle fixée d'avance ; relecture de Codex avant tout calcul, essai à blanc compris ; regarder les images avant les chiffres ;
un réglage choisi après coup est une nouvelle brique ; Colab au-delà de 10 unités sur l'accord de Marcel.

## Expériences

| dossier | quoi | état |
|---|---|---|
| `2026-10-17-graphe-de-scene` | graphe de scène : LoRA Qwen 7B, tête maison, Qwen sans entraînement | close (copiée de caypollard) |
| `2026-10-25-iconclass-tete` | tête Iconclass sur C-RADIOv3-L, test ICAI | close (copiée) |
| `2026-10-25-iconclass-externe` | banc extérieur Emblematica, tête et VLM | close (copiée) |
| `2026-10-25-iconclass-tete-pe` | même tête sur PE-Spatial, comparaison par usage | close (copiée) |
| `2026-10-25-xanto-parties` | pose et parties pour Xanto | close, à rendre au projet xanto |
| `2026-10-25-iconclass-architecture` | essais d'architecture de la tête | préinscrite, feu vert de Codex |
