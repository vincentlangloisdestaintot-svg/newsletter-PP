# -*- coding: utf-8 -*-
"""FRED — Federal Reserve Bank of St. Louis (clé API gratuite, optionnelle).

Sert le périmètre américain et le Bund, pour lesquels aucune API émettrice
gratuite simple n'existe. FRED redistribue des données officielles en les
créditant : c'est un redistributeur institutionnel, pas un agrégateur de presse.
Chaque point publié cite l'émetteur d'origine (Trésor américain, Fed,
Bundesbank via OCDE) ET la page FRED.
"""
from __future__ import annotations

import datetime as dt
import logging
import os

from . import http

log = logging.getLogger(__name__)

BASE = "https://api.stlouisfed.org/fred/series/observations"
PAGE = "https://fred.stlouisfed.org/series"

# series_id -> (libellé, émetteur d'origine à citer)
SERIES = {
    "DGS10":  ("Treasury 10 ans", "U.S. Department of the Treasury"),
    "DGS2":   ("Treasury 2 ans", "U.S. Department of the Treasury"),
    "DGS30":  ("Treasury 30 ans", "U.S. Department of the Treasury"),
    "IRLTLT01DEM156N": ("Bund 10 ans (mensuel)", "OCDE d'après Deutsche Bundesbank"),
    "IRLTLT01FRM156N": ("OAT 10 ans (mensuel)", "OCDE d'après Banque de France"),
    "DFEDTARU": ("Fed funds — borne haute", "Federal Reserve"),
    "DFEDTARL": ("Fed funds — borne basse", "Federal Reserve"),
}


def _cle() -> str | None:
    return os.environ.get("FRED_API_KEY") or None


def serie(series_id: str, n: int = 10) -> list[tuple[dt.date, float]] | None:
    cle = _cle()
    if not cle:
        log.info("FRED_API_KEY absente — provider FRED ignoré.")
        return None
    data = http.get_json(BASE, params={
        "series_id": series_id, "api_key": cle, "file_type": "json",
        "sort_order": "desc", "limit": n,
    })
    if not isinstance(data, dict):
        return None
    obs: list[tuple[dt.date, float]] = []
    for o in data.get("observations", []):
        if o.get("value") in (None, "", "."):
            continue
        try:
            obs.append((dt.date.fromisoformat(o["date"]), float(o["value"])))
        except (ValueError, KeyError):
            continue
    return sorted(obs) or None


def url_page(series_id: str) -> str:
    return f"{PAGE}/{series_id}"


def emetteur(series_id: str) -> str:
    return SERIES.get(series_id, ("", "FRED"))[1]
