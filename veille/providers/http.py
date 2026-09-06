# -*- coding: utf-8 -*-
"""Client HTTP : timeouts courts, retry borné, aucune exception qui remonte.

Un provider qui échoue ne casse jamais le run — il rend None et la donnée
part en NON_CONFIRME. C'est le seul comportement acceptable pour un job
non supervisé à 6h30.
"""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

UA = "veille-patrimoniale/2.0 (usage interne, non commercial)"
TIMEOUT = 20
RETRIES = 3
BACKOFF = 2.0


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        accept: str = "text/csv") -> str | None:
    """GET avec retry. Rend le corps en texte, ou None si toutes les tentatives échouent."""
    h = {"User-Agent": UA, "Accept": accept}
    if headers:
        h.update(headers)
    for tentative in range(1, RETRIES + 1):
        try:
            r = requests.get(url, params=params, headers=h, timeout=TIMEOUT)
            if r.status_code == 200 and r.text.strip():
                return r.text
            log.warning("GET %s -> HTTP %s (tentative %s/%s)",
                        url, r.status_code, tentative, RETRIES)
        except requests.RequestException as exc:
            log.warning("GET %s -> %s (tentative %s/%s)",
                        url, exc.__class__.__name__, tentative, RETRIES)
        if tentative < RETRIES:
            time.sleep(BACKOFF * tentative)
    return None


def get_json(url: str, *, params: dict | None = None,
             headers: dict | None = None) -> dict | list | None:
    import json
    txt = get(url, params=params, headers=headers, accept="application/json")
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except ValueError:
        log.warning("Réponse non JSON depuis %s", url)
        return None
