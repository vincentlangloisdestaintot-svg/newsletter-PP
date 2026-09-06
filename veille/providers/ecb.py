# -*- coding: utf-8 -*-
"""BCE — ECB Data Portal (SDMX REST, sans clé).

Base : https://data-api.ecb.europa.eu/service/data/{dataset}/{cle_serie}
Format csvdata : colonnes incluant KEY, TIME_PERIOD, OBS_VALUE.

Séries utilisées — toute clé est déclarée ici, jamais en dur ailleurs, et
vérifiable par `python -m veille.doctor`.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import logging

from . import http

log = logging.getLogger(__name__)

BASE = "https://data-api.ecb.europa.eu/service/data"
PORTAIL = "https://data.ecb.europa.eu/data/datasets"

# Clés de séries. Statut de vérification indiqué en commentaire :
# [confirmée] = page dédiée existante sur le portail BCE
# [à vérifier] = plausible mais non validée empiriquement — `doctor` tranche.
SERIES = {
    # Taux de la facilité de dépôt, quotidien — [confirmée]
    "bce_depot": ("FM", "D.U2.EUR.4F.KR.DFR.LEV"),
    # Taux des opérations principales de refinancement, quotidien — [à vérifier]
    "bce_refi": ("FM", "D.U2.EUR.4F.KR.MRR_FR.LEV"),
    # Courbe des taux zone euro, notations AAA, spot 10 ans, quotidien — [à vérifier]
    "courbe_euro_10a": ("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y"),
    "courbe_euro_2a": ("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y"),
    "courbe_euro_30a": ("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y"),
    # Change EUR/USD, référence quotidienne BCE — [à vérifier]
    "eurusd": ("EXR", "D.USD.EUR.SP00.A"),
}


def _parse_csvdata(txt: str) -> list[tuple[dt.date, float]]:
    obs: list[tuple[dt.date, float]] = []
    for row in csv.DictReader(io.StringIO(txt)):
        periode, valeur = row.get("TIME_PERIOD"), row.get("OBS_VALUE")
        if not periode or valeur in (None, "", "NaN"):
            continue
        try:
            if len(periode) == 10:
                d = dt.date.fromisoformat(periode)
            elif len(periode) == 7:            # mensuel : dernier jour du mois
                an, mois = int(periode[:4]), int(periode[5:7])
                d = (dt.date(an + mois // 12, mois % 12 + 1, 1) - dt.timedelta(days=1))
            else:
                continue
            obs.append((d, float(valeur)))
        except (ValueError, TypeError):
            continue
    return sorted(obs)


def serie(cle: str, n: int = 5) -> list[tuple[dt.date, float]] | None:
    """Rend les n dernières observations d'une série déclarée, ou None."""
    if cle not in SERIES:
        log.error("Série BCE inconnue : %s", cle)
        return None
    dataset, serie_key = SERIES[cle]
    txt = http.get(f"{BASE}/{dataset}/{serie_key}",
                   params={"lastNObservations": n, "format": "csvdata"})
    if txt is None:
        return None
    obs = _parse_csvdata(txt)
    return obs or None


def url_portail(cle: str) -> str:
    dataset, serie_key = SERIES[cle]
    return f"{PORTAIL}/{dataset}/{dataset}.{serie_key}"
