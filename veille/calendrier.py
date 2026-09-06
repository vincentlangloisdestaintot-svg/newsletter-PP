# -*- coding: utf-8 -*-
"""Échéances récurrentes tombant aujourd'hui ou dans les 48 heures."""
from __future__ import annotations

import calendar
import datetime as dt
import logging

from .config import CALENDRIER
from .models import Echeance

log = logging.getLogger(__name__)

HORIZON = 2  # jours


def _dates_fixes(aujourdhui: dt.date) -> list[Echeance]:
    try:
        import yaml
    except ImportError:
        log.warning("PyYAML absent — échéances fixes ignorées.")
        return []
    if not CALENDRIER.exists():
        return []
    try:
        conf = yaml.safe_load(CALENDRIER.read_text(encoding="utf-8")) or {}
    except Exception as exc:                                   # noqa: BLE001
        log.warning("calendrier.yml illisible (%s) — échéances fixes ignorées.", exc)
        return []

    out: list[Echeance] = []
    for bloc in conf.values():
        if not isinstance(bloc, dict):
            continue
        for d in bloc.get("dates") or []:
            date = d if isinstance(d, dt.date) else _parse(d)
            if date and 0 <= (date - aujourdhui).days <= HORIZON:
                out.append(Echeance(date, bloc.get("emetteur", ""),
                                    bloc.get("intitule", ""), bloc.get("url", "")))
    return out


def _parse(valeur) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(valeur)[:10])
    except ValueError:
        return None


def _dates_calculees(aujourdhui: dt.date) -> list[Echeance]:
    """Échéances déductibles du calendrier civil (charte, section 8)."""
    out: list[Echeance] = []
    for delta in range(HORIZON + 1):
        j = aujourdhui + dt.timedelta(days=delta)
        dernier = calendar.monthrange(j.year, j.month)[1]

        if j.day >= dernier - 1:
            out.append(Echeance(
                j, "INSEE",
                "Estimation provisoire de l'inflation (fin de mois)",
                "https://www.insee.fr/fr/statistiques"))
        if 13 <= j.day <= 16:
            out.append(Echeance(
                j, "INSEE",
                "Indice des prix à la consommation, chiffres définitifs (mi-mois)",
                "https://www.insee.fr/fr/statistiques"))
        if 28 <= j.day <= min(31, dernier):
            out.append(Echeance(
                j, "France Assureurs",
                "Collecte assurance vie du mois précédent",
                "https://www.franceassureurs.fr/espace-presse/"))
        if j.month in (1, 8) and j.day == 1:
            out.append(Echeance(
                j, "Ministère de l'Économie / Banque de France",
                "Révision des taux de l'épargne réglementée",
                "https://www.banque-france.fr/fr/statistiques/taux-et-cours"))
        if j.month in (9, 10, 11, 12) and j.day == 1:
            out.append(Echeance(
                j, "Parlement",
                "Séquence PLF en cours : dépôt, amendements, navette",
                "https://www.assemblee-nationale.fr/"))
    return out


def echeances(aujourdhui: dt.date | None = None) -> list[Echeance]:
    j = aujourdhui or dt.date.today()
    toutes = _dates_fixes(j) + _dates_calculees(j)
    # Une même échéance couvrant plusieurs jours de la fenêtre n'est retenue
    # qu'une fois, à sa date la plus proche : sinon l'instruction éditoriale se
    # remplit de doublons.
    vues, uniques = set(), []
    for e in sorted(toutes, key=lambda x: x.date):
        cle = (e.emetteur, e.intitule)
        if cle not in vues:
            vues.add(cle)
            uniques.append(e)
    return uniques
