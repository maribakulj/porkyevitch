#!/usr/bin/env python3
"""Ce calcul peut-il conclure ? Puissance et effet minimal détectable, avant de lancer.

Usage :
    python3 -I labo/puissance.py --ic BAS HAUT --effet-plausible E [--n N] [--famille K] [--unilateral]
    python3 -I labo/puissance.py --se S --effet-plausible E ...

L'erreur-type vient d'un intervalle déjà mesuré sur le même banc avec le même effectif (un IC bootstrap apparié d'un
calcul voisin), ou d'un pilote. Si l'effectif prévu diffère, `--n N0:N1` la rééchelonne en 1/√n.
L'effet plausible vient d'une mesure passée et citée, jamais d'un espoir.

Le verdict suit la règle de la carte de recherche :
- puissance < 50 % à l'effet plausible : le calcul ne peut presque que rendre « pas de signal ». Ne pas lancer :
  redessiner (effectif, banc, contraste) ou demander un accord humain explicite ;
- de 50 à 80 % : faible, à justifier ;
- 80 % ou plus : le calcul peut conclure.

Le modèle est normal, et la règle « borne basse > 0 au niveau α » équivaut à Δ/se > z(1 − α). C'est une approximation,
suffisante pour savoir si un ordre de grandeur est atteignable, pas pour fixer un seuil à la troisième décimale.
Code de sortie : 0 peut conclure, 1 faible, 2 ne peut pas conclure.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from statistics import NormalDist

Z = NormalDist()


def se_depuis_ic(bas: float, haut: float, niveau: float = 0.95) -> float:
    """Erreur-type d'un intervalle bilatéral symétrique au niveau donné."""
    if haut <= bas:
        raise ValueError("l'intervalle doit avoir haut > bas")
    return (haut - bas) / (2 * Z.inv_cdf(0.5 + niveau / 2))


def alpha_effectif(alpha: float, famille: int, unilateral: bool) -> float:
    """Niveau par comparaison après Bonferroni, ramené à une queue."""
    a = alpha / famille
    return a if unilateral else a / 2


def puissance(effet: float, se: float, alpha: float = 0.05, famille: int = 1, unilateral: bool = False) -> float:
    z = Z.inv_cdf(1 - alpha_effectif(alpha, famille, unilateral))
    return Z.cdf(abs(effet) / se - z)


def effet_minimal(se: float, alpha: float = 0.05, cible: float = 0.8, famille: int = 1,
                  unilateral: bool = False) -> float:
    return (Z.inv_cdf(1 - alpha_effectif(alpha, famille, unilateral)) + Z.inv_cdf(cible)) * se


def facteur_effectif(se: float, effet: float, alpha: float = 0.05, cible: float = 0.8, famille: int = 1,
                     unilateral: bool = False) -> float:
    """Par combien multiplier l'effectif pour atteindre la puissance cible à cet effet (se ∝ 1/√n)."""
    return (effet_minimal(se, alpha, cible, famille, unilateral) / abs(effet)) ** 2


@dataclass
class Bilan:
    se: float
    puissance: float
    effet_minimal: float
    facteur: float
    verdict: str
    code: int


def bilan(se: float, effet: float, alpha: float = 0.05, famille: int = 1, unilateral: bool = False) -> Bilan:
    p = puissance(effet, se, alpha, famille, unilateral)
    if p < 0.5:
        verdict, code = "NE PEUT PAS CONCLURE : ne pas lancer sans redessiner, ou sans accord humain explicite", 2
    elif p < 0.8:
        verdict, code = "FAIBLE : à justifier dans la carte", 1
    else:
        verdict, code = "PEUT CONCLURE", 0
    return Bilan(se, p, effet_minimal(se, alpha, 0.8, famille, unilateral),
                 facteur_effectif(se, effet, alpha, 0.8, famille, unilateral), verdict, code)


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Puissance et effet minimal détectable, avant de lancer.")
    source = a.add_mutually_exclusive_group(required=True)
    source.add_argument("--ic", nargs=2, type=float, metavar=("BAS", "HAUT"), help="IC95 bilatéral déjà mesuré")
    source.add_argument("--se", type=float, help="erreur-type, si on l'a directement")
    a.add_argument("--effet-plausible", type=float, required=True, help="effet attendu, tiré d'une mesure citée")
    a.add_argument("--n", metavar="N0:N1", help="effectif de la mesure source : effectif prévu")
    a.add_argument("--alpha", type=float, default=0.05)
    a.add_argument("--famille", type=int, default=1, help="nombre de comparaisons (Bonferroni)")
    a.add_argument("--unilateral", action="store_true", help="règle « borne basse > 0 »")
    args = a.parse_args(argv)

    se = se_depuis_ic(*args.ic) if args.ic else args.se
    if args.n:
        n0, n1 = (float(x) for x in args.n.split(":"))
        se *= math.sqrt(n0 / n1)
    b = bilan(se, args.effet_plausible, args.alpha, args.famille, args.unilateral)
    print(f"erreur-type             {b.se:.4g}")
    print(f"puissance à {args.effet_plausible:g}   {b.puissance:.0%}")
    print(f"effet minimal (80 %)    {b.effet_minimal:.4g}")
    print(f"effectif nécessaire     × {b.facteur:.3g} l'effectif prévu, pour 80 % à l'effet plausible")
    print(b.verdict)
    return b.code


if __name__ == "__main__":
    sys.exit(main())
