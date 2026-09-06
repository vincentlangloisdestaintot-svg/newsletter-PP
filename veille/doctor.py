# -*- coding: utf-8 -*-
"""Diagnostic des sources : quelles séries répondent réellement.

À lancer une fois avant la mise en production, puis quand une donnée disparaît
du brief. Le container de développement d'origine était derrière une allowlist
réseau : aucune de ces sources n'y était joignable. C'est donc ici, sur une
machine ayant accès à Internet, que les clés de séries se valident.

    python -m veille.doctor
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import sys

from .providers import bdf, ecb, equities, fred

log = logging.getLogger("doctor")

VERT, ROUGE, JAUNE, RAZ = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def _ligne(etat: str, libelle: str, detail: str = "") -> None:
    couleur = {"OK": VERT, "KO": ROUGE, "!!": JAUNE}[etat]
    print(f"  {couleur}[{etat}]{RAZ} {libelle:<42} {detail}")


def _fraicheur(d: dt.date) -> str:
    age = (dt.date.today() - d).days
    marque = "" if age <= 5 else f"  ← {age} j"
    return f"{d.isoformat()}{marque}"


def main() -> int:
    logging.basicConfig(level=logging.ERROR, format="%(message)s")
    print("\n=== Diagnostic des sources ===\n")

    print("Clés d'API présentes :")
    for nom in ("ANTHROPIC_API_KEY", "WEBSTAT_API_KEY", "FRED_API_KEY",
                "RESEND_API_KEY"):
        _ligne("OK" if os.environ.get(nom) else "!!", nom,
               "" if os.environ.get(nom) else "absente — provider ignoré")

    print("\nBCE — ECB Data Portal (sans clé) :")
    for cle in ecb.SERIES:
        obs = ecb.serie(cle, 2)
        if obs:
            _ligne("OK", cle, f"{obs[-1][1]:>10.4f}   {_fraicheur(obs[-1][0])}")
        else:
            _ligne("KO", cle, "aucune observation — clé de série à corriger")

    print("\nBanque de France — Webstat (clé requise) :")
    if not os.environ.get("WEBSTAT_API_KEY"):
        _ligne("!!", "TEC 10", "WEBSTAT_API_KEY absente — test impossible")
    else:
        trouve = False
        for identifiant in bdf.CANDIDATS_TEC10:
            obs = bdf.serie(identifiant, 2)
            if obs:
                _ligne("OK", identifiant,
                       f"{obs[-1][1]:>10.4f}   {_fraicheur(obs[-1][0])}")
                trouve = True
            else:
                _ligne("KO", identifiant, "pas de réponse exploitable")
        if not trouve:
            _ligne("!!", "TEC 10", "aucun candidat ne répond — l'OAT partira "
                                   "en non confirmé")

    print("\nFRED — Federal Reserve Bank of St. Louis (clé requise) :")
    if not os.environ.get("FRED_API_KEY"):
        _ligne("!!", "toutes séries", "FRED_API_KEY absente — test impossible")
    else:
        for series_id, (libelle, _) in fred.SERIES.items():
            obs = fred.serie(series_id, 3)
            if obs:
                _ligne("OK", f"{series_id} ({libelle})",
                       f"{obs[-1][1]:>8.3f}   {_fraicheur(obs[-1][0])}")
            else:
                _ligne("KO", f"{series_id} ({libelle})", "pas de réponse")

    print("\nIndices actions — règle des deux sources convergentes :")
    for cle, (libelle, *_rest) in equities.INDICES.items():
        r = equities.cloture(cle)
        if not r:
            _ligne("KO", libelle, "aucune source n'a répondu")
        elif r.get("divergent"):
            v = r["valeurs"]
            noms = list(v)
            _ligne("!!", libelle,
                   f"divergence {r['ecart_pct']:.2f} % — "
                   f"{noms[0]} {v[noms[0]]:.2f} / {noms[1]} {v[noms[1]]:.2f}")
        elif not r.get("suffisant"):
            _ligne("!!", libelle,
                   f"une seule source ({r.get('source_unique')}) — non publiable")
        else:
            _ligne("OK", libelle,
                   f"{r['niveau']:>10.2f}   {_fraicheur(r['date'])}   "
                   f"({' + '.join(r['sources'])})")

    print("\nLes lignes KO et !! deviendront des « non confirmé à la source »\n"
          "dans le brief. C'est le comportement voulu : un blanc assumé, pas\n"
          "un chiffre inventé.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
