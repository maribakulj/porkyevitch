"""Adaptateurs de plateformes. Ils sont les seuls à toucher Kaggle et Colab, et ils tournent sous le compte du guichet.

Règle commune : une réponse qu'on ne sait pas lire est INCONNU, jamais « fini » ni « rien ne tourne ». Un délai dépassé
au lancement est LancementIncertain : quelque chose a peut-être été lancé, donc la course passe INCONNUE et rien ne la
relance tant qu'une réponse distante n'a pas tranché.
"""

from __future__ import annotations

import enum
import json
import os
import re
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path


class Distant(enum.Enum):
    EN_FILE = "EN_FILE"
    EN_COURS = "EN_COURS"
    TERMINEE = "TERMINEE"
    ECHOUEE = "ECHOUEE"
    INCONNU = "INCONNU"


@dataclass
class Releve:
    etat: Distant
    detail: str = ""


class LancementIncertain(Exception):
    """Rien ne permet de dire si le calcul est parti."""


class LancementRefuse(Exception):
    """La plateforme a refusé clairement : rien n'est parti."""


class CliIntrouvable(Exception):
    """Le CLI de la plateforme n'a pas pu être exécuté : aucun appel n'a eu lieu."""


def _executer(cmd: list[str], env: dict, timeout: float, entree: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, input=entree, capture_output=True, text=True, timeout=timeout, env=env)
    except OSError as e:
        raise CliIntrouvable(f"{cmd[0]} : {e.strerror or e}") from None


def environnement(maison: Path) -> dict:
    """Environnement minimal des appels : HOME du guichet (où sont ~/.kaggle et les identifiants Google), PATH sûr.
    Rien n'est hérité de l'appelant."""
    return {"HOME": str(maison), "PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}


# --------------------------------------------------------------------------------------------------------- Kaggle

_STATUT_KAGGLE = re.compile(r'has status "(?:KernelWorkerStatus\.)?([A-Z_]+)"')
_VERSION_KAGGLE = re.compile(r"version (\d+) successfully pushed", re.IGNORECASE)
_CORRESPONDANCE = {"QUEUED": Distant.EN_FILE, "RUNNING": Distant.EN_COURS, "COMPLETE": Distant.TERMINEE,
                   "ERROR": Distant.ECHOUEE, "CANCEL_REQUESTED": Distant.ECHOUEE,
                   "CANCEL_ACKNOWLEDGED": Distant.ECHOUEE}


def lire_statut_kaggle(sortie: str) -> Releve:
    m = _STATUT_KAGGLE.search(sortie)
    if not m:
        return Releve(Distant.INCONNU, f"statut illisible : {sortie.strip()[:200]!r}")
    return Releve(_CORRESPONDANCE.get(m.group(1), Distant.INCONNU), m.group(1))


class Kaggle:
    """`kaggle kernels push / status / output`. Le CLI ne sait pas annuler une version poussée (aucune commande d'annulation) :
    une course en file sur Kaggle ne se bascule pas ailleurs sans accord humain."""

    nom = "kaggle"
    peut_annuler = False

    def __init__(self, cli: str, maison: Path):
        self.cli, self.env = cli, environnement(maison)

    def lancer(self, instantane: Path, carte, ident: str) -> tuple[str, str]:
        meta_chemin = instantane / "kernel-metadata.json"
        try:
            meta = json.loads(meta_chemin.read_text())
            slug = meta["id"]
        except (OSError, ValueError, KeyError):
            raise LancementRefuse("kernel-metadata.json absent ou sans « id » dans le dossier") from None
        if meta.get("code_file") != carte.point_entree:
            raise LancementRefuse(f"code_file ({meta.get('code_file')!r}) doit être le point d'entrée "
                                  f"({carte.point_entree!r})")
        if bool(meta.get("enable_gpu")) != carte.gpu:
            raise LancementRefuse("enable_gpu de kernel-metadata.json contredit « gpu » de la carte")
        cmd = [self.cli, "kernels", "push", "-p", str(instantane)]
        if carte.kaggle.get("accelerateur"):
            cmd += ["--accelerator", carte.kaggle["accelerateur"]]
        try:
            r = _executer(cmd, self.env, timeout=900)
        except subprocess.TimeoutExpired:
            raise LancementIncertain("kaggle kernels push : délai dépassé") from None
        except CliIntrouvable as e:
            raise LancementRefuse(str(e)) from None
        texte = r.stdout + r.stderr
        m = _VERSION_KAGGLE.search(texte)
        if m:
            return slug, m.group(1)
        if r.returncode != 0 and re.search(r"error|invalid|not found|forbidden|quota", texte, re.IGNORECASE):
            raise LancementRefuse(texte.strip()[:500])
        raise LancementIncertain(f"réponse de push non reconnue : {texte.strip()[:300]!r}")

    def etat(self, slug: str, version: str | None) -> Releve:
        # `status` porte sur la dernière version du noyau. Le guichet garantit qu'un seul de ses calculs actifs
        # utilise un noyau donné, et lui seul pousse : la dernière version est la sienne.
        try:
            r = _executer([self.cli, "kernels", "status", slug], self.env, timeout=120)
        except subprocess.TimeoutExpired:
            return Releve(Distant.INCONNU, "kaggle kernels status : délai dépassé")
        except CliIntrouvable as e:
            return Releve(Distant.INCONNU, str(e))
        return lire_statut_kaggle(r.stdout + r.stderr)

    def rapatrier(self, slug: str, version: str | None, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        r = _executer([self.cli, "kernels", "output", slug, "-p", str(destination)], self.env, timeout=3600)
        if r.returncode != 0:
            raise RuntimeError(f"kaggle kernels output : {(r.stdout + r.stderr).strip()[:300]}")

    def annuler(self, slug: str, version: str | None) -> bool:
        return False

    def liberer(self, slug: str) -> None:
        pass


# ---------------------------------------------------------------------------------------------------------- Colab
# Mêmes commandes et mêmes leçons que porky/colab.py (cellule unique qui ne laisse pas le noyau inactif, envoi en
# morceaux de 50 Mo, suivi par un journal sur la machine). Le code est repris ici et non importé : un module du dépôt,
# modifiable par l'agent, ne doit jamais s'exécuter avec les identifiants du guichet.

MORCEAU = 50 * 1024 * 1024


def lire_journal_colab(texte: str, ident: str) -> Releve:
    if f"FIN {ident} ok=True" in texte:
        return Releve(Distant.TERMINEE, "chaîne finie")
    if f"FIN {ident} ok=False" in texte or re.search(r"sortie [1-9]\d*", texte):
        return Releve(Distant.ECHOUEE, texte.strip()[-300:])
    if "debut calcul" in texte:
        return Releve(Distant.EN_COURS, "")
    return Releve(Distant.EN_FILE, "préparation")


class Colab:
    nom = "colab"
    peut_annuler = True

    def __init__(self, cli: str, maison: Path):
        self.cli, self.env = cli, environnement(maison)

    def _c(self, *args: str, entree: str | None = None, timeout: float = 600) -> subprocess.CompletedProcess:
        return _executer([self.cli, "--auth=adc", *args], self.env, timeout=timeout, entree=entree)

    def lancer(self, instantane: Path, carte, ident: str) -> tuple[str, str]:
        session = ident.lower()
        try:
            r = self._c("new", "-s", session, "--gpu", carte.colab.get("gpu", "T4") if carte.gpu else "none")
        except subprocess.TimeoutExpired:
            raise LancementIncertain("colab new : délai dépassé") from None
        except CliIntrouvable as e:
            raise LancementRefuse(str(e)) from None
        if "READY" not in r.stdout + r.stderr:
            raise LancementRefuse(f"colab new : {(r.stdout + r.stderr).strip()[:300]}")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "calcul.tar"
                with tarfile.open(archive, "w") as t:
                    t.add(instantane, arcname="calcul")
                morceaux = self._envoyer(session, archive, "/content/calcul.tar", Path(tmp))
            self._demarrer(session, ident, morceaux, carte.point_entree)
        except subprocess.TimeoutExpired:
            raise LancementIncertain("colab : délai dépassé pendant l'envoi ou le démarrage") from None
        except (RuntimeError, CliIntrouvable, OSError) as e:
            self.liberer(session)
            raise LancementRefuse(str(e)) from None
        return session, ident

    def _envoyer(self, session: str, archive: Path, distant: str, tmp: Path) -> list[str]:
        morceaux = []
        with open(archive, "rb") as f:
            k = 0
            while bloc := f.read(MORCEAU):
                p = tmp / f"m{k:03d}"
                p.write_bytes(bloc)
                r = self._c("upload", "-s", session, str(p), f"{distant}.{k:03d}", timeout=900)
                if "Uploaded" not in r.stdout + r.stderr:
                    raise RuntimeError(f"envoi du morceau {k} refusé : {(r.stdout + r.stderr).strip()[:200]}")
                morceaux.append(f"{distant}.{k:03d}")
                p.unlink()
                k += 1
        return morceaux

    def _demarrer(self, session: str, ident: str, morceaux: list[str], point_entree: str) -> None:
        code = "\n".join([
            "import subprocess, os, time",
            "J = '/content/guichet.log'",
            "open(J, 'w').close()",
            "def j(m): open(J, 'a').write(time.strftime('%H:%M:%S ') + m + '\\n')",
            "def run(nom, cmd):",
            "    r = subprocess.run(cmd + f' > /content/{nom}.log 2>&1', shell=True,",
            "                       env=dict(os.environ, GUICHET_SORTIE='/content/sortie'))",
            "    j(f'sortie {r.returncode} ({nom})')",
            "    return r.returncode == 0",
            f"ok = run('assemblage', 'cat {' '.join(morceaux)} > /content/calcul.tar && rm {' '.join(morceaux)}"
            " && tar -xf /content/calcul.tar -C /content && mkdir -p /content/sortie')",
            "if ok: j('debut calcul')",
            f"ok = ok and run('calcul', 'cd /content/calcul && python {point_entree}')",
            # Les journaux partent avec la sortie, réussite ou échec : un échec sans journal ne s'explique pas.
            "ok = run('archive', 'tar -cf /content/sortie.tar -C /content sortie assemblage.log"
            " $(test -f /content/calcul.log && echo calcul.log)') and ok",
            f"j(f'FIN {ident} ok={{ok}}')",
        ])
        # Une cellule longue rend « Timeout waiting for reply » au client alors qu'elle continue : on la lance en
        # arrière-plan et on suit le journal sur la machine (porky/colab.py).
        p = subprocess.Popen([self.cli, "--auth=adc", "exec", "-s", session], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True, env=self.env)
        p.stdin.write(code)
        p.stdin.close()

    def etat(self, slug: str, version: str | None) -> Releve:
        try:
            r = self._c("sessions", timeout=120)
        except (subprocess.TimeoutExpired, CliIntrouvable) as e:
            return Releve(Distant.INCONNU, f"colab sessions : {e}")
        if r.returncode != 0:
            return Releve(Distant.INCONNU, f"colab sessions : {(r.stdout + r.stderr).strip()[:200]}")
        if f"[{slug}]" not in r.stdout:
            return Releve(Distant.ECHOUEE, "session Colab disparue (machine reprise ou perdue)")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "guichet.log"
            try:
                r = self._c("download", "-s", slug, "/content/guichet.log", str(dest), timeout=300)
            except (subprocess.TimeoutExpired, CliIntrouvable) as e:
                return Releve(Distant.INCONNU, f"colab download : {e}")
            if "Downloaded" not in r.stdout or not dest.exists():
                return Releve(Distant.INCONNU, "journal de la machine illisible")
            return lire_journal_colab(dest.read_text(errors="replace"), version or "")

    def rapatrier(self, slug: str, version: str | None, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "sortie.tar"
            r = self._c("download", "-s", slug, "/content/sortie.tar", str(archive), timeout=3600)
            if "Downloaded" not in r.stdout or not archive.exists():
                raise RuntimeError(f"colab download de la sortie : {(r.stdout + r.stderr).strip()[:300]}")
            with tarfile.open(archive) as t:
                t.extractall(destination, filter="data")
            interne = destination / "sortie"
            if interne.is_dir():  # l'archive contient « sortie/… » : on remonte d'un niveau
                for x in interne.iterdir():
                    x.rename(destination / x.name)
                interne.rmdir()

    def annuler(self, slug: str, version: str | None) -> bool:
        try:
            r = self._c("stop", "-s", slug, timeout=120)
            listing = self._c("sessions", timeout=120)
        except (subprocess.TimeoutExpired, CliIntrouvable):
            return False
        return r.returncode == 0 and listing.returncode == 0 and f"[{slug}]" not in listing.stdout

    def liberer(self, slug: str) -> None:
        """Arrête la machine dès que la sortie est rapatriée : une session laissée ouverte consomme des unités."""
        try:
            self._c("stop", "-s", slug, timeout=120)
        except (subprocess.TimeoutExpired, CliIntrouvable):
            pass
