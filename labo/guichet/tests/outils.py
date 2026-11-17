"""Plateforme simulée et fabrique de cartes pour les tests. Aucun appel réseau, aucun crédit."""

from __future__ import annotations

import json
import sys
import tempfile
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guichet.guichet import Config, Guichet  # noqa: E402
from guichet.plateformes import Distant, LancementIncertain, Releve  # noqa: E402


class Fausse:
    """Plateforme simulée : on fixe à la main ce que « le site » répond."""

    def __init__(self, nom: str, peut_annuler: bool):
        self.nom, self.peut_annuler = nom, peut_annuler
        self.lances: list[tuple[str, str]] = []  # (slug, ident) de chaque lancement réel
        self.etats: dict[str, Releve] = {}
        self.fichiers: dict[str, dict[str, bytes]] = {}
        self.effet_lancement: Exception | None = None
        self.rapatriement_casse = False
        self.annulees: list[str] = []
        self.liberees: list[str] = []

    def lancer(self, instantane: Path, carte, ident: str):
        if self.effet_lancement:
            raise self.effet_lancement
        if self.nom == "kaggle":
            slug = json.loads((instantane / "kernel-metadata.json").read_text())["id"]
        else:
            slug = ident.lower()
        self.lances.append((slug, ident))
        self.etats[slug] = Releve(Distant.EN_FILE)
        return slug, str(len(self.lances))

    def etat(self, slug, version):
        return self.etats.get(slug, Releve(Distant.INCONNU, "jamais vu"))

    def rapatrier(self, slug, version, destination: Path):
        if self.rapatriement_casse:
            raise RuntimeError("téléchargement interrompu")
        destination.mkdir(parents=True, exist_ok=True)
        for nom, contenu in self.fichiers.get(slug, {}).items():
            (destination / nom).parent.mkdir(parents=True, exist_ok=True)
            (destination / nom).write_bytes(contenu)

    def annuler(self, slug, version):
        if not self.peut_annuler:
            return False
        self.annulees.append(slug)
        self.etats[slug] = Releve(Distant.ECHOUEE, "annulée")
        return True

    def liberer(self, slug):
        self.liberees.append(slug)


class Horloge:
    def __init__(self):
        self.t = 1_800_000_000.0

    def __call__(self):
        return self.t

    def avancer(self, secondes: float):
        self.t += secondes


class Banc:
    """Un guichet neuf dans un dossier temporaire, avec Kaggle (sans annulation) et Colab (avec)."""

    def __init__(self, **config):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.maison = base / "maison-labo"
        self.maison.mkdir()
        self.depot = base / "depot-agent"
        self.depot.mkdir()
        self.kaggle, self.colab = Fausse("kaggle", False), Fausse("colab", True)
        self.horloge = Horloge()
        self.config = Config(**config)
        self.g = self.nouveau()

    def nouveau(self) -> Guichet:
        """Un second processus sur le même registre."""
        return Guichet(self.maison / "guichet", self.config, {"kaggle": self.kaggle, "colab": self.colab},
                       maison_protegee=self.maison, horloge=self.horloge)

    def carte(self, nom: str = "calcul", code: str = "print('ok')\n", slug: str | None = None,
              duree: int = 2700, gpu: bool = True, artefacts=("recu.json",), mesuree: str = "",
              plateformes=("kaggle", "colab"), entrees=(("vecteurs", "a" * 64),)) -> Path:
        d = self.depot / nom
        noyau = d / "noyau"
        noyau.mkdir(parents=True, exist_ok=True)
        (noyau / "run.py").write_text(code)
        (noyau / "kernel-metadata.json").write_text(json.dumps(
            {"id": slug or f"compte/{nom}", "code_file": "run.py", "enable_gpu": gpu}))
        entrees_toml = "".join(f'\n[[entrees]]\nnom = "{n}"\nsha256 = "{s}"\n' for n, s in entrees)
        texte = textwrap.dedent(f"""\
            experience = "{nom}"
            dossier = "noyau"
            point_entree = "run.py"
            gpu = {str(gpu).lower()}
            duree_estimee_s = {duree}
            duree_mesuree_par = "{mesuree}"
            artefacts_attendus = {json.dumps(list(artefacts))}
            plateformes = {json.dumps(list(plateformes))}
            """) + entrees_toml
        chemin = d / "carte.toml"
        chemin.write_text(texte)
        return chemin

    def finir(self, plateforme: Fausse, slug: str, fichiers: dict[str, bytes], duree: float = 2700):
        plateforme.etats[slug] = Releve(Distant.EN_COURS)
        self.g.reconcilier()
        self.horloge.avancer(duree)
        plateforme.fichiers[slug] = fichiers
        plateforme.etats[slug] = Releve(Distant.TERMINEE)
        return self.g.reconcilier()

    def course(self, ident: str):
        return self.g.c.execute("SELECT * FROM courses WHERE id = ?", (ident,)).fetchone()

    def fermer(self):
        self.g.c.close()
        self._tmp.cleanup()


__all__ = ["Banc", "Fausse", "Distant", "Releve", "LancementIncertain"]
