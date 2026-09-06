# -*- coding: utf-8 -*-
"""Couche données : collecte déterministe, avec statut de preuve sur chaque point.

Principe non négociable : aucun chiffre n'est produit par déduction, par
interpolation ou par défaut. Ce qui n'est pas récupéré part en NON_CONFIRME et
le brief l'écrit.
"""
from __future__ import annotations

import datetime as dt
import logging

from .calendrier import echeances
from .config import FRAICHEUR
from .models import Collecte, DataPoint, Statut
from .providers import bdf, ecb, equities, fred

log = logging.getLogger(__name__)


def _variation_pb(obs: list[tuple[dt.date, float]]) -> float | None:
    """Variation en points de base entre les deux dernières observations."""
    if len(obs) < 2:
        return None
    return (obs[-1][1] - obs[-2][1]) * 100


# --------------------------------------------------------------------------
# Taux
# --------------------------------------------------------------------------
def _oat_10a() -> DataPoint:
    p = DataPoint(cle="oat_10a", libelle="OAT 10 ans", unite="%",
                  unite_variation="pb")

    resultat = bdf.tec10()
    if resultat:
        identifiant, obs = resultat
        mensuel = ".M." in identifiant
        p.valeur = obs[-1][1]
        p.date_obs = obs[-1][0]
        p.variation = _variation_pb(obs)
        p.emetteur = "Banque de France"
        p.url = bdf.url_catalogue(identifiant)
        p.statut = Statut.CONFIRME
        p.note = ("Taux de l'échéance constante 10 ans. "
                  + ("Série mensuelle : ce niveau est une moyenne de mois, "
                     "il ne mesure pas le mouvement du jour." if mensuel else
                     "Série quotidienne."))
        p.appliquer_fraicheur(31 if mensuel else FRAICHEUR["taux"])
        return p

    obs = fred.serie("IRLTLT01FRM156N")
    if obs:
        p.valeur = obs[-1][1]
        p.date_obs = obs[-1][0]
        p.variation = _variation_pb(obs)
        p.emetteur = fred.emetteur("IRLTLT01FRM156N")
        p.url = fred.url_page("IRLTLT01FRM156N")
        p.statut = Statut.CONFIRME
        p.note = ("Série mensuelle de repli : moyenne de mois, ne mesure pas le "
                  "mouvement du jour. Le niveau quotidien n'a pas pu être "
                  "confirmé chez un émetteur.")
        p.appliquer_fraicheur(45)
        return p

    p.note = ("Aucune source émettrice n'a répondu pour le niveau quotidien de "
              "l'OAT 10 ans.")
    return p


def _bund_ou_courbe() -> DataPoint:
    """Bund 10 ans si disponible, sinon courbe zone euro AAA — jamais confondus."""
    p = DataPoint(cle="bund_10a", libelle="Bund 10 ans", unite="%",
                  unite_variation="pb")

    obs = fred.serie("IRLTLT01DEM156N")
    if obs:
        p.valeur, p.date_obs = obs[-1][1], obs[-1][0]
        p.variation = _variation_pb(obs)
        p.emetteur = fred.emetteur("IRLTLT01DEM156N")
        p.url = fred.url_page("IRLTLT01DEM156N")
        p.statut = Statut.CONFIRME
        p.note = "Série mensuelle : moyenne de mois, pas un niveau de clôture."
        p.appliquer_fraicheur(45)
    else:
        p.note = "Rendement du Bund non confirmé chez un émetteur."
    return p


def _courbe_euro(cle: str, libelle: str) -> DataPoint:
    p = DataPoint(cle=cle, libelle=libelle, unite="%", unite_variation="pb")
    obs = ecb.serie(cle)
    if obs:
        p.valeur, p.date_obs = obs[-1][1], obs[-1][0]
        p.variation = _variation_pb(obs)
        p.emetteur = "BCE"
        p.url = ecb.url_portail(cle)
        p.statut = Statut.CONFIRME
        p.note = ("Courbe des taux zone euro, émetteurs notés AAA. "
                  "Ce n'est ni l'OAT ni le Bund.")
        p.appliquer_fraicheur(FRAICHEUR["taux"])
    else:
        p.note = ("La série de courbe des taux BCE n'a pas répondu ce matin.")
    return p


def _spread_oat_bund(oat: DataPoint, bund: DataPoint) -> DataPoint:
    """Spread calculé uniquement si les deux jambes sont comparables.

    Soustraire une série quotidienne à une série mensuelle produirait un
    chiffre faux d'apparence crédible. Dans ce cas : NON_CONFIRME, motivé.
    """
    p = DataPoint(cle="spread_oat_bund", libelle="Spread OAT / Bund",
                  unite="pb", emetteur="Calcul interne")

    if not (oat.publiable and bund.publiable):
        p.note = ("Spread non calculé : au moins une des deux jambes n'est pas "
                  "confirmée à la source.")
        return p

    if oat.date_obs != bund.date_obs:
        p.note = (f"Spread non calculé : les deux jambes portent des dates "
                  f"différentes (OAT au {oat.date_obs}, Bund au {bund.date_obs}). "
                  f"Les soustraire produirait un écart non comparable.")
        return p

    p.valeur = (oat.valeur - bund.valeur) * 100
    p.date_obs = oat.date_obs
    p.statut = Statut.CONFIRME
    p.url = oat.url
    p.note = (f"Calculé par différence : {oat.libelle} ({oat.emetteur}) moins "
              f"{bund.libelle} ({bund.emetteur}), même date d'observation.")
    return p


def _fred_simple(cle: str, series_id: str, libelle: str,
                 fraicheur: int) -> DataPoint:
    p = DataPoint(cle=cle, libelle=libelle, unite="%", unite_variation="pb")
    obs = fred.serie(series_id)
    if obs:
        p.valeur, p.date_obs = obs[-1][1], obs[-1][0]
        p.variation = _variation_pb(obs)
        p.emetteur = fred.emetteur(series_id)
        p.url = fred.url_page(series_id)
        p.statut = Statut.CONFIRME
        p.appliquer_fraicheur(fraicheur)
    else:
        p.note = (f"Série {series_id} non récupérée : soit FRED_API_KEY est "
                  f"absente, soit la source n'a pas répondu.")
    return p


def _bce(cle: str, libelle: str) -> DataPoint:
    p = DataPoint(cle=cle, libelle=libelle, unite="%")
    obs = ecb.serie(cle)
    if obs:
        p.valeur, p.date_obs = obs[-1][1], obs[-1][0]
        p.emetteur = "BCE"
        p.url = ecb.url_portail(cle)
        p.statut = Statut.CONFIRME
        p.appliquer_fraicheur(FRAICHEUR["politique_monetaire"])
    else:
        p.note = ("Le portail de données de la BCE n'a pas répondu pour cette "
                  "série ce matin.")
    return p


# --------------------------------------------------------------------------
# Indices actions
# --------------------------------------------------------------------------
def _indice(cle: str) -> DataPoint:
    libelle = equities.INDICES[cle][0]
    p = DataPoint(cle=cle, libelle=libelle, unite="points",
                  unite_variation="%")
    r = equities.cloture(cle)
    if not r:
        p.note = "Aucune source de marché n'a répondu."
        return p

    p.date_obs = r.get("date")
    p.sources_convergentes = r.get("sources", [])

    if r.get("divergent"):
        p.statut = Statut.DIVERGENT
        v = r["valeurs"]
        noms = list(v)
        p.note = (f"Divergence entre sources : {noms[0]} donne "
                  f"{v[noms[0]]:.2f}, {noms[1]} donne {v[noms[1]]:.2f} "
                  f"(écart {r['ecart_pct']:.2f} %). Chiffre non publié.")
        return p

    if not r.get("suffisant"):
        p.note = (f"Une seule source disponible ({r.get('source_unique')}). "
                  f"La charte exige deux sources convergentes pour un indice.")
        return p

    p.valeur = r["niveau"]
    p.variation = r.get("variation_pct")
    p.emetteur = r["place"]
    p.url = ""
    p.statut = Statut.CONFIRME
    p.note = ("Clôture établie par convergence de deux sources de marché : "
              + " et ".join(p.sources_convergentes)
              + f". Place de cotation : {r['place']}.")
    p.appliquer_fraicheur(FRAICHEUR["indices"])
    return p


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def collecter() -> Collecte:
    log.info("Collecte des données de marché…")
    points: dict[str, DataPoint] = {}

    oat = _oat_10a()
    bund = _bund_ou_courbe()
    points[oat.cle] = oat
    points[bund.cle] = bund
    points["spread_oat_bund"] = _spread_oat_bund(oat, bund)

    for cle, libelle in (("courbe_euro_2a", "Courbe zone euro AAA 2 ans"),
                         ("courbe_euro_10a", "Courbe zone euro AAA 10 ans"),
                         ("courbe_euro_30a", "Courbe zone euro AAA 30 ans")):
        points[cle] = _courbe_euro(cle, libelle)

    points["treasury_10a"] = _fred_simple(
        "treasury_10a", "DGS10", "Treasury 10 ans", FRAICHEUR["taux"])
    points["fed_funds_haut"] = _fred_simple(
        "fed_funds_haut", "DFEDTARU", "Fed funds — borne haute",
        FRAICHEUR["politique_monetaire"])
    points["fed_funds_bas"] = _fred_simple(
        "fed_funds_bas", "DFEDTARL", "Fed funds — borne basse",
        FRAICHEUR["politique_monetaire"])

    points["bce_depot"] = _bce("bce_depot", "BCE — taux de facilité de dépôt")
    points["bce_refi"] = _bce("bce_refi", "BCE — taux de refinancement")

    for cle in equities.INDICES:
        points[cle] = _indice(cle)

    c = Collecte(date_run=dt.datetime.now(), points=points,
                 echeances=echeances())
    log.info("Collecte terminée — %s", c.sante)
    for p in c.manquants:
        log.info("  non publiable : %s (%s) — %s", p.libelle, p.statut.value, p.note)
    return c
