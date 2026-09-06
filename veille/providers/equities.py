# -*- coding: utf-8 -*-
"""Indices actions — règle des deux sources convergentes.

Aucune API d'émetteur (Euronext, Deutsche Börse, NYSE, Nasdaq) n'est
gratuitement accessible. La charte prévoit ce cas : un indice peut être publié
sur la base d'au moins deux sources de marché convergentes, nommées.

Ce module interroge deux sources indépendantes et ne rend une valeur que si
elles convergent sous le seuil de tolérance. Sinon : DIVERGENT, avec les deux
chiffres nommés — jamais un arbitrage silencieux.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import logging

from . import http

log = logging.getLogger(__name__)

TOLERANCE = 0.0015          # 0,15 % d'écart maximal entre les deux sources

# clé interne -> (libellé, symbole Stooq, symbole Yahoo, place)
INDICES = {
    "cac40":   ("CAC 40", "^cac", "^FCHI", "Euronext Paris"),
    "dax":     ("DAX", "^dax", "^GDAXI", "Deutsche Börse"),
    "estx50":  ("Euro Stoxx 50", "^stx", "^STOXX50E", "Qontigo"),
    "sp500":   ("S&P 500", "^spx", "^GSPC", "NYSE / Nasdaq"),
    "nasdaq":  ("Nasdaq Composite", "^ndq", "^IXIC", "Nasdaq"),
}

STOOQ = "https://stooq.com/q/d/l/"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/"


def _stooq(symbole: str) -> list[tuple[dt.date, float]] | None:
    txt = http.get(STOOQ, params={"s": symbole, "i": "d"})
    if not txt or "Date" not in txt[:80]:
        return None
    obs: list[tuple[dt.date, float]] = []
    for row in csv.DictReader(io.StringIO(txt)):
        try:
            obs.append((dt.date.fromisoformat(row["Date"]), float(row["Close"])))
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(obs)[-10:] or None


def _yahoo(symbole: str) -> list[tuple[dt.date, float]] | None:
    data = http.get_json(f"{YAHOO}{symbole}", params={"range": "1mo", "interval": "1d"})
    if not isinstance(data, dict):
        return None
    try:
        res = data["chart"]["result"][0]
        horodatages = res["timestamp"]
        closes = res["indicators"]["quote"][0]["close"]
    except (KeyError, IndexError, TypeError):
        return None
    obs: list[tuple[dt.date, float]] = []
    for ts, c in zip(horodatages, closes):
        if c is None:
            continue
        obs.append((dt.datetime.utcfromtimestamp(ts).date(), float(c)))
    return sorted(obs)[-10:] or None


def cloture(cle: str) -> dict | None:
    """Rend la clôture d'un indice si deux sources convergent.

    Sortie : dict avec niveau, variation en %, date de séance, sources nommées,
    et un drapeau `divergent` documenté quand les sources ne s'accordent pas.
    """
    if cle not in INDICES:
        return None
    libelle, sym_stooq, sym_yahoo, place = INDICES[cle]

    a, b = _stooq(sym_stooq), _yahoo(sym_yahoo)
    dispo = [(nom, obs) for nom, obs in (("Stooq", a), ("Yahoo Finance", b)) if obs]
    if not dispo:
        return None

    base = {"libelle": libelle, "place": place}

    if len(dispo) == 1:
        nom, obs = dispo[0]
        # Une seule source : la charte exige deux sources convergentes.
        return {**base, "divergent": False, "source_unique": nom,
                "niveau": obs[-1][1], "date": obs[-1][0],
                "variation_pct": _variation(obs), "sources": [nom],
                "suffisant": False}

    (n1, o1), (n2, o2) = dispo
    v1, v2 = o1[-1][1], o2[-1][1]
    ecart = abs(v1 - v2) / max(abs(v1), abs(v2), 1e-9)
    if ecart > TOLERANCE:
        return {**base, "divergent": True, "suffisant": False,
                "valeurs": {n1: v1, n2: v2}, "ecart_pct": ecart * 100,
                "date": max(o1[-1][0], o2[-1][0]), "sources": [n1, n2]}

    return {**base, "divergent": False, "suffisant": True,
            "niveau": (v1 + v2) / 2, "date": max(o1[-1][0], o2[-1][0]),
            "variation_pct": _variation(o1), "sources": [n1, n2]}


def _variation(obs: list[tuple[dt.date, float]]) -> float | None:
    if len(obs) < 2 or obs[-2][1] == 0:
        return None
    return (obs[-1][1] / obs[-2][1] - 1) * 100
