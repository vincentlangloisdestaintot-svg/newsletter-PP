# -*- coding: utf-8 -*-
"""Banque de France — Webstat (clé API gratuite, optionnelle).

Sans clé (WEBSTAT_API_KEY absente), ce provider rend None sans bruit : les
données concernées partiront en NON_CONFIRME, ce qui est le comportement voulu.

L'OAT 10 ans n'a pas d'API émettrice publique en accès libre. Le TEC 10
(taux de l'échéance constante 10 ans), publié par la Banque de France, est la
référence française pertinente. La clé de série quotidienne doit être figée
empiriquement via `python -m veille.doctor` avant mise en production.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import os

from . import http

log = logging.getLogger(__name__)

BASE = "https://api.webstat.banque-france.fr/webstat-fr/v1/data"
CATALOGUE = "https://webstat.banque-france.fr/fr/catalogue"

# Candidats pour le TEC 10. `doctor` retient le premier qui répond en quotidien.
CANDIDATS_TEC10 = [
    "FM.D.FR.EUR.FR2.BB.FRTEC10.HSTA",
    "FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA",
    "FM.M.FR.EUR.FR2.BB.FRMOYTEC10.HSTA",   # mensuel — repli explicitement dégradé
]


def _cle() -> str | None:
    return os.environ.get("WEBSTAT_API_KEY") or None


def serie(identifiant: str, n: int = 5) -> list[tuple[dt.date, float]] | None:
    cle = _cle()
    if not cle:
        log.info("WEBSTAT_API_KEY absente — provider Banque de France ignoré.")
        return None
    dataset = identifiant.split(".")[0]
    txt = http.get(
        f"{BASE}/{dataset}/{identifiant}",
        params={"format": "csv", "lastNObservations": n},
        headers={"X-IBM-Client-Id": cle},
    )
    if txt is None:
        return None
    obs: list[tuple[dt.date, float]] = []
    for row in csv.DictReader(io.StringIO(txt), delimiter=";"):
        periode = row.get("TIME_PERIOD") or row.get("time_period")
        valeur = row.get("OBS_VALUE") or row.get("obs_value")
        if not periode or not valeur:
            continue
        try:
            obs.append((dt.date.fromisoformat(periode[:10]),
                        float(str(valeur).replace(",", "."))))
        except ValueError:
            continue
    return sorted(obs) or None


def tec10(n: int = 5) -> tuple[str, list[tuple[dt.date, float]]] | None:
    """Essaie les candidats dans l'ordre. Rend (identifiant retenu, observations)."""
    for identifiant in CANDIDATS_TEC10:
        obs = serie(identifiant, n)
        if obs:
            return identifiant, obs
    return None


def url_catalogue(identifiant: str) -> str:
    dataset = identifiant.split(".")[0].lower()
    return f"{CATALOGUE}/{dataset}/{identifiant}"
