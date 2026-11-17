"""Le guichet : seule porte vers Kaggle et Colab.

Ce qu'il garantit, parce que lui seul détient les identifiants :
- un même calcul (même clé) n'a jamais deux courses actives, quelle que soit la plateforme ;
- un calcul déjà réussi ne se refait pas sans accord humain (réplication) ;
- une course en file sur une plateforme qui ne sait pas annuler ne se double pas ailleurs sans accord humain ;
- un délai dépassé ou une réponse illisible rend la course INCONNUE, et rien ne la relance avant qu'elle soit tranchée ;
- une course n'est réussie que si les artefacts déclarés sont dans sa sortie rapatriée ;
- un échec de rapatriement n'est pas un échec de calcul : on retente le rapatriement, jamais le calcul ;
- une durée estimée au-delà du seuil doit avoir été mesurée ; une longue course GPU demande un accord ;
- le budget GPU de la semaine et le nombre de courses GPU simultanées sont tenus.

Ce qu'il ne garantit pas : qu'un calcul mérite d'être fait, ni que la carte déclare tout ce dont la suite aura besoin.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import arbre, carte as cartes, registre
from .plateformes import Distant, LancementIncertain, LancementRefuse

SEMAINE = 7 * 24 * 3600
SOUMISE_PERIMEE = 30 * 60  # une course restée SOUMISE au-delà : le lancement a été interrompu, état inconnu


@dataclass
class Config:
    budget_gpu_hebdo_h: float = 30.0
    seuil_accord_gpu_h: float = 3.0
    duree_a_mesurer_h: float = 3.0
    max_gpu_simultanes: int = 2
    taille_max_dossier_mo: int = 200
    sorties: str = ""
    kaggle_cli: str = "kaggle"
    colab_cli: str = ""

    @classmethod
    def lire(cls, chemin: Path) -> "Config":
        if not chemin.exists():
            return cls()
        d = tomllib.loads(chemin.read_text())
        inconnus = set(d) - set(cls.__dataclass_fields__)
        if inconnus:
            raise ValueError(f"config.toml : champs inconnus {sorted(inconnus)}")
        return cls(**d)


@dataclass
class Reponse:
    code: str  # OK, ACCEPTEE, REFUS, ACCORD_REQUIS, INCERTAINE
    message: str
    course: str | None = None
    demande: str | None = None
    lignes: list[str] = field(default_factory=list)

    @property
    def sortie(self) -> int:
        return {"OK": 0, "ACCEPTEE": 0, "REFUS": 2, "ACCORD_REQUIS": 3, "INCERTAINE": 4}[self.code]


def _duree(s: float) -> str:
    s = int(s)
    return f"{s // 3600} h {s % 3600 // 60:02d}" if s >= 3600 else f"{s // 60} min"


class Guichet:
    def __init__(self, racine: Path, config: Config, plateformes: dict, maison_protegee: Path,
                 horloge=time.time):
        self.racine, self.config, self.plateformes = racine, config, plateformes
        self.maison_protegee, self.horloge = maison_protegee, horloge
        self.c = registre.ouvrir(racine / "registre.sqlite")
        self.sorties = Path(config.sorties) if config.sorties else racine / "sorties"

    # ------------------------------------------------------------------------------------------------ soumettre

    def soumettre(self, chemin_carte: Path, plateforme: str | None = None, motif: str | None = None,
                  replication: str | None = None) -> Reponse:
        chemin_carte = Path(chemin_carte)
        if arbre.est_sous(chemin_carte, self.maison_protegee):
            return Reponse("REFUS", "carte dans l'espace du guichet : refusé")
        try:
            c = cartes.lire(chemin_carte)
        except cartes.CarteInvalide as e:
            return Reponse("REFUS", f"carte invalide : {e}")
        plateforme = plateforme or c.plateformes[0]
        if plateforme not in c.plateformes:
            return Reponse("REFUS", f"la carte ne permet pas {plateforme} (permises : {', '.join(c.plateformes)})")
        if plateforme not in self.plateformes:
            return Reponse("REFUS", f"plateforme {plateforme} non configurée dans le guichet")
        if arbre.est_sous(c.dossier, self.maison_protegee):
            return Reponse("REFUS", "dossier dans l'espace du guichet : refusé")
        if not c.dossier.is_dir():
            return Reponse("REFUS", f"dossier introuvable : {c.dossier}")

        nom_instantane = registre.identifiant("I")
        instantane = self.racine / "instantanes" / nom_instantane
        try:
            empreinte, enveloppe = arbre.copier_et_hacher(c.dossier, instantane,
                                                          self.config.taille_max_dossier_mo * 2**20)
        except (arbre.DossierRefuse, OSError) as e:
            shutil.rmtree(instantane, ignore_errors=True)
            return Reponse("REFUS", f"dossier refusé : {e}")
        if not (instantane / c.point_entree).is_file():
            shutil.rmtree(instantane, ignore_errors=True)
            return Reponse("REFUS", f"point d'entrée absent du dossier : {c.point_entree}")
        k = cartes.cle(empreinte, c)

        r = self._admettre(c, k, plateforme, instantane, enveloppe, motif=motif, replication=replication,
                           accords=set())
        if r.code == "REFUS":
            shutil.rmtree(instantane, ignore_errors=True)
        if r.code != "ACCEPTEE":
            return r
        return self._lancer(r.course)

    def _slug(self, plateforme: str, instantane: Path, ident: str) -> str | None:
        if plateforme == "kaggle":
            try:
                return json.loads((instantane / arbre.ENVELOPPE_KAGGLE).read_text())["id"]
            except (OSError, ValueError, KeyError):
                return None
        return ident.lower()

    def _admettre(self, c: cartes.Carte, k: str, plateforme: str, instantane: Path, enveloppe: str | None, *,
                  motif: str | None, replication: str | None, accords: set, source: str | None = None) -> Reponse:
        """Vérifie et insère, dans une seule transaction. Rend ACCEPTEE (course insérée, à lancer), REFUS ou
        ACCORD_REQUIS (demande insérée)."""
        ident = registre.identifiant("R")
        slug = self._slug(plateforme, instantane, ident)
        if slug is None:
            return Reponse("REFUS", "kernel-metadata.json absent ou sans « id » : Kaggle ne saurait pas quoi lancer")
        try:
            return self._admettre_tx(c, k, plateforme, instantane, enveloppe, ident, slug, motif=motif,
                                     replication=replication, accords=accords, source=source)
        except sqlite3.IntegrityError:
            # Filet de l'index unique : une soumission concurrente du même calcul a gagné.
            return Reponse("REFUS", "une soumission concurrente du même calcul vient d'être admise : rien n'est lancé")

    def _admettre_tx(self, c, k, plateforme, instantane, enveloppe, ident, slug, *, motif, replication, accords,
                     source) -> Reponse:
        maintenant = self.horloge()
        with registre.Transaction(self.c) as db:
            active = db.execute(f"SELECT * FROM courses WHERE cle = ? AND etat IN {registre.ACTIFS}", (k,)).fetchone()
            if active:
                return Reponse("REFUS", self._deja_active(active, maintenant), course=active["id"])
            if plateforme == "kaggle":
                occupe = db.execute(
                    f"SELECT id FROM courses WHERE plateforme = 'kaggle' AND slug = ? AND (etat IN {registre.ACTIFS}"
                    " OR (etat = 'ABANDONNEE' AND fin_vue IS NULL))", (slug,)).fetchone()
                if occupe:
                    return Reponse("REFUS", f"le noyau Kaggle {slug} est déjà occupé par {occupe['id']} ; "
                                            "`kaggle kernels status` ne suit que sa dernière version, un second "
                                            "lancement rendrait le premier invisible. Donne un autre « id ».")
            reussie = db.execute("SELECT * FROM courses WHERE cle = ? AND etat = 'REUSSIE' ORDER BY cree_a DESC",
                                 (k,)).fetchone()
            if reussie and "REPLICATION" not in accords:
                if not replication:
                    return Reponse("REFUS", f"calcul déjà fait : {reussie['id']} ({reussie['plateforme']}, "
                                            f"réussie), sortie {reussie['sortie']}. Relis cette sortie. Une "
                                            "réplication voulue se demande avec --replication MOTIF et un accord "
                                            "humain.", course=reussie["id"])
                return self._demande(db, "REPLICATION", c, k, plateforme, instantane, enveloppe, reussie["id"],
                                     replication, f"réplication de {reussie['id']} : {replication}")
            if not reussie:
                echec = db.execute("SELECT * FROM courses WHERE cle = ? AND etat IN ('ECHOUEE', 'ECHOUEE_ARTEFACTS')"
                                   " ORDER BY cree_a DESC", (k,)).fetchone()
                if echec and not motif:
                    return Reponse("REFUS", f"même calcul que {echec['id']}, qui a échoué ({echec['detail']}). "
                                            "Un code identique redonne en général le même échec. Si la cause est "
                                            "extérieure (machine, réseau, file), dis-le avec --motif.",
                                   course=echec["id"])
            if c.duree_estimee_s > self.config.duree_a_mesurer_h * 3600:
                mesure = db.execute("SELECT id FROM courses WHERE id = ? AND etat = 'REUSSIE'",
                                    (c.duree_mesuree_par,)).fetchone() if c.duree_mesuree_par else None
                if not mesure:
                    return Reponse("REFUS", f"durée estimée {_duree(c.duree_estimee_s)} au-delà de "
                                            f"{self.config.duree_a_mesurer_h:g} h : elle doit être mesurée. Lance "
                                            "d'abord un essai chronométré sur les vraies données, puis nomme sa "
                                            "course réussie dans « duree_mesuree_par ».")
            if c.gpu:
                n = db.execute(f"SELECT COUNT(*) FROM courses WHERE gpu = 1 AND etat IN {registre.ACTIFS}"
                               ).fetchone()[0]
                if n >= self.config.max_gpu_simultanes:
                    return Reponse("REFUS", f"{n} courses GPU déjà actives (maximum {self.config.max_gpu_simultanes})"
                                            ". Attendre est une issue normale.")
                utilise = self._budget_utilise(db, maintenant)
                total = self.config.budget_gpu_hebdo_h * 3600
                if utilise + c.duree_estimee_s > total:
                    return Reponse("REFUS", f"budget GPU de la semaine : {_duree(utilise)} engagées sur "
                                            f"{_duree(total)}, cette course en demande {_duree(c.duree_estimee_s)}.")
                if c.duree_estimee_s > self.config.seuil_accord_gpu_h * 3600 and "DUREE" not in accords:
                    return self._demande(db, "DUREE", c, k, plateforme, instantane, enveloppe, None, motif,
                                         f"course GPU de {_duree(c.duree_estimee_s)}, au-delà de "
                                         f"{self.config.seuil_accord_gpu_h:g} h")
            db.execute("INSERT INTO courses (id, cle, experience, plateforme, etat, gpu, slug, duree_estimee_s, "
                       "cree_a, instantane, enveloppe_sha, carte, motif, replication_de) "
                       "VALUES (?, ?, ?, ?, 'SOUMISE', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (ident, k, c.experience, plateforme, int(c.gpu), slug, c.duree_estimee_s, maintenant,
                        str(instantane), enveloppe, c.en_json(), motif or replication,
                        reussie["id"] if reussie else source))
            registre.noter(db, ident, f"admise sur {plateforme}, clé {k[:12]}")
        return Reponse("ACCEPTEE", "", course=ident)

    def _demande(self, db, nature, c, k, plateforme, instantane, enveloppe, source, motif, raison) -> Reponse:
        ident = registre.identifiant("D")
        db.execute("INSERT INTO demandes (id, nature, etat, carte, instantane, cle, enveloppe_sha, plateforme, "
                   "course_source, motif, raison, cree_a) VALUES (?, ?, 'EN_ATTENTE', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (ident, nature, c.en_json(), str(instantane), k, enveloppe, plateforme, source, motif, raison,
                    self.horloge()))
        registre.noter(db, ident, f"demande {nature} : {raison}")
        return Reponse("ACCORD_REQUIS", f"accord humain requis ({raison}). Demande {ident} : rien n'est lancé "
                                        "d'ici là. Avance sur autre chose ou attends.", demande=ident)

    def _deja_active(self, r: sqlite3.Row, maintenant: float) -> str:
        age = _duree(maintenant - r["cree_a"])
        texte = f"calcul déjà actif : {r['id']} sur {r['plateforme']}, {r['etat']} depuis {age}."
        if r["etat"] == "INCONNUE":
            return texte + " Son état distant est inconnu : `reconcilier`, et rien ne part tant qu'il n'est pas tranché."
        if r["etat"] == "EN_FILE":
            return texte + " Pour changer de plateforme : `demander-bascule`, jamais un second lancement."
        return texte + " Attends sa fin."

    # ----------------------------------------------------------------------------------------------- lancement

    def _lancer(self, ident: str) -> Reponse:
        r = self.c.execute("SELECT * FROM courses WHERE id = ?", (ident,)).fetchone()
        c = cartes.Carte.depuis_json(r["carte"])
        p = self.plateformes[r["plateforme"]]
        try:
            slug, version = p.lancer(Path(r["instantane"]), c, ident)
        except LancementRefuse as e:
            self._etat(ident, "REFUSEE", detail=f"lancement refusé : {e}", fin=True)
            return Reponse("REFUS", f"{r['plateforme']} a refusé le lancement, rien n'est parti : {e}", course=ident)
        except LancementIncertain as e:
            self._etat(ident, "INCONNUE", detail=str(e))
            return Reponse("INCERTAINE", f"{ident} : impossible de savoir si le calcul est parti ({e}). Il est "
                                         "INCONNU : `reconcilier` plus tard ; ne relance rien.", course=ident)
        self.c.execute("UPDATE courses SET etat = 'EN_FILE', slug = ?, version = ? WHERE id = ?",
                       (slug, version, ident))
        registre.noter(self.c, ident, f"lancée : {slug} version {version}")
        return Reponse("ACCEPTEE", f"{ident} lancée sur {r['plateforme']} ({slug}, version {version}). "
                                   "`reconcilier` pour suivre.", course=ident)

    def _etat(self, ident: str, etat: str, detail: str | None = None, debut: bool = False, fin: bool = False,
              sortie: str | None = None) -> None:
        maintenant = self.horloge()
        self.c.execute("UPDATE courses SET etat = ?, detail = COALESCE(?, detail), "
                       "debut_vu = CASE WHEN ? AND debut_vu IS NULL THEN ? ELSE debut_vu END, "
                       "fin_vue = CASE WHEN ? AND fin_vue IS NULL THEN ? ELSE fin_vue END, "
                       "sortie = COALESCE(?, sortie) WHERE id = ?",
                       (etat, detail, debut, maintenant, fin, maintenant, sortie, ident))
        registre.noter(self.c, ident, f"{etat}" + (f" : {detail}" if detail else ""))

    # --------------------------------------------------------------------------------------------- reconcilier

    def reconcilier(self) -> Reponse:
        lignes = []
        maintenant = self.horloge()
        suivies = self.c.execute(f"SELECT * FROM courses WHERE etat IN {registre.ACTIFS} "
                                 "OR (etat = 'ABANDONNEE' AND fin_vue IS NULL) ORDER BY cree_a").fetchall()
        for r in suivies:
            ident, etat = r["id"], r["etat"]
            if etat == "SOUMISE":
                if maintenant - r["cree_a"] > SOUMISE_PERIMEE:
                    self._etat(ident, "INCONNUE", "lancement interrompu : rien ne dit s'il est parti")
                    lignes.append(f"{ident} : lancement interrompu, INCONNUE")
                continue
            p = self.plateformes.get(r["plateforme"])
            if p is None:
                lignes.append(f"{ident} : plateforme {r['plateforme']} non configurée, non suivie")
                continue
            releve = p.etat(r["slug"], r["version"])
            lignes.append(self._appliquer(r, releve, p))
        return Reponse("OK", "rien à suivre" if not lignes else f"{len(lignes)} course(s) suivie(s)", lignes=lignes)

    def _appliquer(self, r: sqlite3.Row, releve, p) -> str:
        ident, etat = r["id"], r["etat"]
        if releve.etat is Distant.INCONNU:
            # Une réponse illisible ne change rien : ni « fini », ni « rien ne tourne ».
            self.c.execute("UPDATE courses SET detail = ? WHERE id = ?", (f"relevé illisible : {releve.detail}", ident))
            return f"{ident} : relevé illisible, état {etat} conservé ({releve.detail})"
        if etat == "INCONNUE" and not r["version"]:
            # Kaggle après un push sans réponse : le statut porte sur la dernière version du noyau, qui peut être
            # une version antérieure. Rien ne permet de l'attribuer à cette course : un humain tranche.
            self.c.execute("UPDATE courses SET detail = ? WHERE id = ?",
                           (f"distant : {releve.etat.value} ({releve.detail}), version inconnue", ident))
            return (f"{ident} : distant {releve.etat.value}, mais la version lancée est inconnue ; "
                    "`guichet trancher` après vérification sur le site")
        if etat == "ABANDONNEE":
            if releve.etat in (Distant.TERMINEE, Distant.ECHOUEE):
                self._etat(ident, "ABANDONNEE", f"a fini malgré l'abandon ({releve.etat.value})", fin=True)
                p.liberer(r["slug"])
                return f"{ident} (abandonnée) : finie à distance, temps compté au budget"
            if releve.etat is Distant.EN_COURS:
                self._etat(ident, "ABANDONNEE", "TOURNE malgré l'abandon : doublon en cours", debut=True)
                return f"{ident} (abandonnée) : ELLE TOURNE, doublon. Arrête-la depuis le site si tu peux."
            return f"{ident} (abandonnée) : toujours en file"
        if releve.etat is Distant.EN_FILE:
            self._etat(ident, "EN_FILE", releve.detail or None)
            return f"{ident} : en file"
        if releve.etat is Distant.EN_COURS:
            self._etat(ident, "EN_COURS", releve.detail or None, debut=True)
            return f"{ident} : en cours"
        sortie = self.sorties / ident
        if releve.etat is Distant.ECHOUEE:
            try:
                p.rapatrier(r["slug"], r["version"], sortie)
            except Exception:  # journal d'échec : utile, pas indispensable
                pass
            self._etat(ident, "ECHOUEE", f"échec distant : {releve.detail}", fin=True, sortie=str(sortie))
            p.liberer(r["slug"])
            return f"{ident} : ÉCHEC distant ({releve.detail}) ; journaux dans {sortie}"
        # TERMINEE
        try:
            p.rapatrier(r["slug"], r["version"], sortie)
        except Exception as e:
            self._etat(ident, etat, f"terminée à distance, rapatriement échoué : {e}", fin=True)
            return f"{ident} : terminée, sortie NON rapatriée ({e}) ; `reconcilier` retentera — ne relance pas le calcul"
        c = cartes.Carte.depuis_json(r["carte"])
        manquants = [a for a in c.artefacts_attendus
                     if not any(f.is_file() and f.stat().st_size > 0 for f in sortie.glob(a))]
        p.liberer(r["slug"])
        if manquants:
            self._etat(ident, "ECHOUEE_ARTEFACTS", f"artefacts absents : {manquants}", fin=True, sortie=str(sortie))
            return f"{ident} : terminée SANS {manquants} ; elle ne compte pas comme réussie"
        self._etat(ident, "REUSSIE", "artefacts présents", fin=True, sortie=str(sortie))
        return f"{ident} : RÉUSSIE, sortie {sortie}"

    # ------------------------------------------------------------------------------------- bascule, annulation

    def demander_bascule(self, ident: str, vers: str, motif: str) -> Reponse:
        r = self.c.execute("SELECT * FROM courses WHERE id = ?", (ident,)).fetchone()
        if r is None:
            return Reponse("REFUS", f"course inconnue : {ident}")
        if r["etat"] != "EN_FILE":
            return Reponse("REFUS", f"{ident} est {r['etat']} : seule une course EN_FILE se bascule "
                                    "(une course qui tourne se laisse finir ; une INCONNUE se réconcilie d'abord)")
        c = cartes.Carte.depuis_json(r["carte"])
        if vers == r["plateforme"] or vers not in c.plateformes or vers not in self.plateformes:
            return Reponse("REFUS", f"bascule vers {vers} impossible (carte : {', '.join(c.plateformes)})")
        if not motif:
            return Reponse("REFUS", "une bascule se motive (--motif)")
        p = self.plateformes[r["plateforme"]]
        if p.peut_annuler:
            if not p.annuler(r["slug"], r["version"]):
                return Reponse("REFUS", f"annulation de {ident} non confirmée : pas de bascule, pas de doublon")
            self._etat(ident, "ANNULEE", f"annulée pour bascule vers {vers} : {motif}", fin=True)
            a = self._admettre(c, r["cle"], vers, Path(r["instantane"]), r["enveloppe_sha"], motif=motif,
                               replication=None, accords={"DUREE"}, source=ident)
            return self._lancer(a.course) if a.code == "ACCEPTEE" else a
        with registre.Transaction(self.c) as db:
            return self._demande(db, "BASCULE", c, r["cle"], vers, Path(r["instantane"]), r["enveloppe_sha"], ident,
                                 motif, f"bascule de {ident} ({r['plateforme']}, qui ne sait pas annuler) vers {vers} "
                                        f": si l'ancienne démarre quand même, le calcul sera fait deux fois. {motif}")

    def annuler(self, ident: str) -> Reponse:
        r = self.c.execute("SELECT * FROM courses WHERE id = ?", (ident,)).fetchone()
        if r is None or r["etat"] not in registre.ACTIFS:
            return Reponse("REFUS", f"{ident} : pas de course active de ce nom")
        p = self.plateformes[r["plateforme"]]
        if not p.peut_annuler:
            return Reponse("REFUS", f"{r['plateforme']} ne sait pas annuler depuis le CLI : arrête-la sur le site, "
                                    "puis `guichet trancher`")
        if not p.annuler(r["slug"], r["version"]):
            return Reponse("REFUS", f"annulation de {ident} non confirmée")
        self._etat(ident, "ANNULEE", "annulée", fin=True)
        return Reponse("OK", f"{ident} annulée", course=ident)

    # --------------------------------------------------------------------------------------- réservé à l'humain

    def approuver(self, ident: str) -> Reponse:
        d = self.c.execute("SELECT * FROM demandes WHERE id = ?", (ident,)).fetchone()
        if d is None or d["etat"] != "EN_ATTENTE":
            return Reponse("REFUS", f"{ident} : pas de demande en attente de ce nom")
        c = cartes.Carte.depuis_json(d["carte"])
        accords = {"DUREE", d["nature"]}
        if d["nature"] == "BASCULE":
            with registre.Transaction(self.c) as db:
                src = db.execute("SELECT * FROM courses WHERE id = ?", (d["course_source"],)).fetchone()
                if src["etat"] != "EN_FILE":
                    db.execute("UPDATE demandes SET etat = 'REFUSEE', tranchee_a = ? WHERE id = ?",
                               (self.horloge(), ident))
                    return Reponse("REFUS", f"{src['id']} est passée {src['etat']} entre-temps : bascule sans objet")
                db.execute("UPDATE courses SET etat = 'ABANDONNEE', detail = ? WHERE id = ?",
                           (f"abandonnée pour bascule ({ident}), toujours suivie", src["id"]))
                registre.noter(db, src["id"], f"ABANDONNEE par {ident}")
        a = self._admettre(c, d["cle"], d["plateforme"], Path(d["instantane"]), d["enveloppe_sha"], motif=d["motif"],
                           replication=d["motif"] if d["nature"] == "REPLICATION" else None, accords=accords,
                           source=d["course_source"])
        if a.code != "ACCEPTEE":
            if d["nature"] == "BASCULE":  # l'ancienne redevient la course du calcul
                self.c.execute("UPDATE courses SET etat = 'EN_FILE' WHERE id = ? AND etat = 'ABANDONNEE'",
                               (d["course_source"],))
            return Reponse("REFUS", f"accordée mais non admissible maintenant : {a.message}")
        self.c.execute("UPDATE demandes SET etat = 'ACCORDEE', tranchee_a = ?, course_creee = ? WHERE id = ?",
                       (self.horloge(), a.course, ident))
        return self._lancer(a.course)

    def refuser(self, ident: str, motif: str) -> Reponse:
        n = self.c.execute("UPDATE demandes SET etat = 'REFUSEE', tranchee_a = ?, motif = COALESCE(motif, '') || ? "
                           "WHERE id = ? AND etat = 'EN_ATTENTE'", (self.horloge(), f" | refus : {motif}", ident)
                           ).rowcount
        return Reponse("OK" if n else "REFUS", f"{ident} refusée" if n else f"{ident} : pas en attente")

    def trancher(self, ident: str, etat: str, motif: str, version: str | None = None) -> Reponse:
        permis = ("EN_FILE", "EN_COURS", "ECHOUEE", "ANNULEE", "ABANDONNEE")
        if etat not in permis:
            return Reponse("REFUS", f"état parmi {permis} ; « réussie » ne se décrète pas, elle se rapatrie")
        n = self.c.execute("UPDATE courses SET etat = ?, version = COALESCE(?, version), detail = ?, "
                           "fin_vue = CASE WHEN ? THEN ? ELSE fin_vue END WHERE id = ?",
                           (etat, version, f"tranché par l'humain : {motif}", etat in ("ECHOUEE", "ANNULEE"),
                            self.horloge(), ident)).rowcount
        registre.noter(self.c, ident, f"tranchée {etat} : {motif}")
        return Reponse("OK" if n else "REFUS", f"{ident} : {etat}" if n else f"{ident} : inconnue")

    # ---------------------------------------------------------------------------------------- lecture, budget

    def _budget_utilise(self, db, maintenant: float) -> float:
        total = 0.0
        for r in db.execute("SELECT * FROM courses WHERE gpu = 1 AND cree_a >= ?", (maintenant - SEMAINE,)):
            if r["debut_vu"] and r["fin_vue"]:
                total += r["fin_vue"] - r["debut_vu"]
            elif r["etat"] in registre.ACTIFS or (r["etat"] == "ABANDONNEE" and r["fin_vue"] is None):
                total += r["duree_estimee_s"]
            elif r["fin_vue"] and r["etat"] in ("REUSSIE", "ECHOUEE_ARTEFACTS", "ABANDONNEE"):
                total += r["duree_estimee_s"]  # finie entre deux relevés : on ne sait pas, on compte l'estimation
        return total

    def resume(self) -> Reponse:
        m = self.horloge()
        lignes = [f"Budget GPU (7 jours) : {_duree(self._budget_utilise(self.c, m))} sur "
                  f"{_duree(self.config.budget_gpu_hebdo_h * 3600)}"]
        demandes = self.c.execute("SELECT * FROM demandes WHERE etat = 'EN_ATTENTE' ORDER BY cree_a").fetchall()
        lignes.append(f"Demandes en attente de toi : {len(demandes)}")
        for d in demandes:
            c = cartes.Carte.depuis_json(d["carte"])
            lignes.append(f"  {d['id']}  {d['nature']}  {c.experience} sur {d['plateforme']} : {d['raison']}")
            lignes.append(f"      artefacts déclarés : {', '.join(c.artefacts_attendus)}")
        actives = self.c.execute(f"SELECT * FROM courses WHERE etat IN {registre.ACTIFS} OR "
                                 "(etat = 'ABANDONNEE' AND fin_vue IS NULL) ORDER BY cree_a").fetchall()
        lignes.append(f"Courses suivies : {len(actives)}")
        for r in actives:
            lignes.append(f"  {r['id']}  {r['etat']:<10} {r['plateforme']:<6} {r['experience']} depuis "
                          f"{_duree(m - r['cree_a'])}" + (f" — {r['detail']}" if r["detail"] else ""))
        finies = self.c.execute(f"SELECT * FROM courses WHERE etat IN {registre.TERMINAUX} AND fin_vue >= ? "
                                "ORDER BY fin_vue", (m - 24 * 3600,)).fetchall()
        lignes.append(f"Finies depuis 24 h : {len(finies)}")
        for r in finies:
            lignes.append(f"  {r['id']}  {r['etat']:<17} {r['experience']}" +
                          (f" — {r['detail']}" if r["etat"] != "REUSSIE" else f" — {r['sortie']}"))
        return Reponse("OK", "\n".join(lignes))

    def etat(self, ident: str) -> Reponse:
        r = self.c.execute("SELECT * FROM courses WHERE id = ?", (ident,)).fetchone()
        if r is None:
            return Reponse("REFUS", f"course inconnue : {ident}")
        champs = ("id", "experience", "plateforme", "etat", "slug", "version", "cle", "sortie", "detail")
        return Reponse("OK", "\n".join(f"{k:<11} {r[k]}" for k in champs))
