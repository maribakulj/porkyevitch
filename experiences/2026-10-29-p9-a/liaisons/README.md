# Liaisons P9-A après D11 (30/10/2026)

`sources-p9a-pkyevitch.json` (sha `a5f2bff5…`) est la liaison `sources.json` des étapes **planches** et **mesures**. Kaggle a supprimé `porky-p9a-iconclass` et `porky-p9a-minilm` ; ces deux jeux sont re-téléversés **à l'identique** sous les noms `pkyevitch-p9a-iconclass` et `pkyevitch-p9a-minilm`. Seuls leurs deux chemins changent. Les sorties de noyaux (`caypollard-encode-cradio`, `porky-e3-run`, `porky-p9a-images`) gardent leur nom.

- Elle se téléverse sous le nom `sources.json`, dans `pkyevitch-p9a-prep-config`. La config de chaque étape l'épingle (`binding_sha256`).
- `planches` et `mesures` n'appellent pas `load_preparation`. Elles lisent la liaison par `TrainData`, avec les SHA de l'inventaire, et par `descriptions`, avec les blobs Iconclass vérifiés. Aucun code ne change.
- **L'étape `seed` reste liée à l'ancienne liaison `9294a792…`**, épinglée dans `preparation.json`. Une relance de la graine demanderait donc une nouvelle préparation, un nouveau regard de la planche initiale et un amendement relu.
