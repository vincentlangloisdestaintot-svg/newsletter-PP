# -*- coding: utf-8 -*-
"""Dates en français sans dépendre de la locale système (absente en CI)."""
from __future__ import annotations

import datetime as dt

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
              "août", "sept.", "oct.", "nov.", "déc."]


def _quantieme(jour: int) -> str:
    return "1er" if jour == 1 else str(jour)


def longue(d: dt.date) -> str:
    """« jeudi 3 septembre 2026 »"""
    return f"{JOURS[d.weekday()]} {_quantieme(d.day)} {MOIS[d.month - 1]} {d.year}"


def titre(d: dt.date) -> str:
    """« JEUDI 3 SEPT. 2026 »"""
    return (f"{JOURS[d.weekday()]} {_quantieme(d.day)} "
            f"{MOIS_COURT[d.month - 1]} {d.year}").upper()


def aujourdhui_paris() -> dt.date:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    except Exception:                                          # noqa: BLE001
        return dt.date.today()
