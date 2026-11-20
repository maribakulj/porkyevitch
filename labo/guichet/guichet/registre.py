"""Registre SQLite des courses et des demandes d'accord.

L'unicité est tenue par la base, pas par une vérification préalable : deux soumissions simultanées du même calcul
se heurtent à l'index `une_active_par_cle`, et la seconde est refusée même si les deux processus ont vérifié en même
temps. Une course est insérée **avant** d'être lancée ; c'est ce qui rend l'unicité vraie.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

ACTIFS = ("SOUMISE", "EN_FILE", "EN_COURS", "INCONNUE")
TERMINAUX = ("REUSSIE", "ECHOUEE", "ECHOUEE_ARTEFACTS", "ANNULEE", "REFUSEE")  # REFUSEE : la plateforme a refusé, rien n'a tourné
# ABANDONNEE : course remplacée par une bascule alors que sa plateforme ne sait pas l'annuler. Elle n'empêche plus de
# soumettre la clé, mais elle reste suivie jusqu'à sa fin distante, et son temps est compté au budget.
ETATS = ACTIFS + TERMINAUX + ("ABANDONNEE",)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    cle TEXT NOT NULL,
    experience TEXT NOT NULL,
    plateforme TEXT NOT NULL,
    etat TEXT NOT NULL CHECK (etat IN ({", ".join(repr(e) for e in ETATS)})),
    gpu INTEGER NOT NULL,
    slug TEXT,
    version TEXT,
    duree_estimee_s INTEGER NOT NULL,
    cree_a REAL NOT NULL,
    debut_vu REAL,
    fin_vue REAL,
    instantane TEXT NOT NULL,
    sortie TEXT,
    enveloppe_sha TEXT,
    carte TEXT NOT NULL,
    motif TEXT,
    replication_de TEXT,
    detail TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS une_active_par_cle ON courses (cle)
    WHERE etat IN ({", ".join(repr(e) for e in ACTIFS)});
CREATE UNIQUE INDEX IF NOT EXISTS un_noyau_actif ON courses (plateforme, slug)
    WHERE slug IS NOT NULL AND (etat IN ({", ".join(repr(e) for e in ACTIFS)})
                                OR (etat = 'ABANDONNEE' AND fin_vue IS NULL));
CREATE TABLE IF NOT EXISTS demandes (
    id TEXT PRIMARY KEY,
    nature TEXT NOT NULL CHECK (nature IN ('DUREE', 'REPLICATION', 'BASCULE', 'RECHERCHE')),
    etat TEXT NOT NULL CHECK (etat IN ('EN_ATTENTE', 'ACCORDEE', 'REFUSEE')),
    carte TEXT NOT NULL,
    instantane TEXT NOT NULL,
    cle TEXT NOT NULL,
    enveloppe_sha TEXT,
    plateforme TEXT NOT NULL,
    course_source TEXT,
    motif TEXT,
    raison TEXT NOT NULL,
    cree_a REAL NOT NULL,
    tranchee_a REAL,
    course_creee TEXT
);
CREATE TABLE IF NOT EXISTS purges (
    course TEXT NOT NULL,
    nom TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    taille INTEGER NOT NULL,
    purge_a REAL NOT NULL,
    PRIMARY KEY (course, nom)
);
CREATE TABLE IF NOT EXISTS journal (
    t REAL NOT NULL,
    objet TEXT NOT NULL,
    quoi TEXT NOT NULL
);
"""


def ouvrir(chemin: Path) -> sqlite3.Connection:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(chemin, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=FULL")
    c.executescript(_SCHEMA)
    return c


class Transaction:
    """BEGIN IMMEDIATE : le verrou d'écriture est pris avant les lectures, donc les vérifications et l'insertion
    voient le même état."""

    def __init__(self, c: sqlite3.Connection):
        self.c = c

    def __enter__(self) -> sqlite3.Connection:
        self.c.execute("BEGIN IMMEDIATE")
        return self.c

    def __exit__(self, typ, val, tb) -> None:
        self.c.execute("COMMIT" if typ is None else "ROLLBACK")


def noter(c: sqlite3.Connection, objet: str, quoi: str) -> None:
    c.execute("INSERT INTO journal (t, objet, quoi) VALUES (?, ?, ?)", (time.time(), objet, quoi))


def identifiant(prefixe: str) -> str:
    import secrets

    return f"{prefixe}-{time.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
