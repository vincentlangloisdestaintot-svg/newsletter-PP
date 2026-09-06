# -*- coding: utf-8 -*-
"""Contrôle qualité mécanique, exécuté sur le texte produit.

Remplace la checklist auto-déclarative de la version précédente : un agent qui
se note lui-même à 6h30, sans personne pour vérifier, n'est pas un contrôle.
Ici les vérifications sont faites par du code, sur le livrable, après coup.

Le brief part toujours — un brief bloqué à 6h30 c'est zéro veille. Mais les
contrôles échoués remontent en tête de l'email, en clair.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from .models import Collecte, Statut


class Gravite(str, Enum):
    BLOQUANT = "bloquant"      # risque de conformité ou chiffre non sourcé
    ALERTE = "alerte"          # à relire avant réutilisation en book


@dataclass
class Constat:
    gravite: Gravite
    regle: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.gravite.value}] {self.regle} — {self.detail}"


# --- Domaines émetteurs acceptés en pied de bloc ---------------------------
DOMAINES_EMETTEURS = {
    "insee.fr", "aft.gouv.fr", "banque-france.fr", "webstat.banque-france.fr",
    "ecb.europa.eu", "data.ecb.europa.eu", "federalreserve.gov",
    "home.treasury.gov", "deutsche-finanzagentur.de", "ec.europa.eu",
    "franceassureurs.fr", "bofip.impots.gouv.fr", "impots.gouv.fr",
    "legifrance.gouv.fr", "assemblee-nationale.fr", "senat.fr",
    "amf-france.org", "acpr.banque-france.fr", "orias.fr",
    "economie.gouv.fr", "fitchratings.com", "spglobal.com", "moodys.com",
    "cmegroup.com", "courdecassation.fr", "conseil-etat.fr",
    "fred.stlouisfed.org", "stlouisfed.org", "oecd.org", "eurostat.ec.europa.eu",
    "vie-publique.fr", "journal-officiel.gouv.fr", "budget.gouv.fr",
}

# --- Vocabulaire proscrit (charte, section 6) ------------------------------
OPPORTUNITE = [
    r"\bfen[êe]tre\b", r"\bopportun", r"\bmoment favorable", r"\bbon moment",
    r"\bil faut (?:en )?profiter", r"\bpoint d'entr[ée]e", r"\bà saisir\b",
    r"\btiming id[ée]al", r"\bconjoncture porteuse",
]
RECOMMANDATION = [
    r"\bje (?:recommande|conseille)", r"\bnous recommandons",
    r"\bil faut (?:investir|arbitrer|placer|souscrire|sortir)",
    r"\bprivil[ée]gi(?:ez|er les)", r"\barbitrez\b", r"\bplacez\b",
    r"\bsouscrivez\b", r"\bmieux vaut (?:investir|arbitrer|placer)",
    r"\bà acheter\b", r"\bà vendre\b",
]
PROJECTION = [
    r"\bva (?:continuer|poursuivre|monter|baisser|progresser)\b",
    r"\bcontinuera\b", r"\bprogressera\b", r"\bbaissera\b", r"\baugmentera\b",
    r"\bne manquera pas de\b",
]

# Attributions fréquemment fausses (charte, section 2).
CITATIONS_APOCRYPHES = [
    ("sois le changement", "gandhi"),
    ("ils ne savaient pas que c'[ée]tait impossible", "twain"),
    ("la folie, c'est de faire", "einstein"),
    ("le capitalisme, c'est", "churchill"),
    ("donnez-moi un point d'appui", "archim"),
]

ALIAS_POINTS = {
    "oat_10a": ["oat"],
    "bund_10a": ["bund"],
    "spread_oat_bund": ["spread"],
    "treasury_10a": ["treasury", "t-note"],
    "bce_depot": ["bce", "dépôt", "depot"],
    "bce_refi": ["refi"],
    "fed_funds_haut": ["fed funds", "fed"],
    "fed_funds_bas": ["fed funds", "fed"],
    "cac40": ["cac"],
    "dax": ["dax"],
    "estx50": ["stoxx"],
    "sp500": ["s&p", "sp 500", "s & p"],
    "nasdaq": ["nasdaq"],
}

NC = {"n.c.", "nc", "n.c", "non confirmé", "non confirme", "—", "-", ""}


def _condense(brief: dict) -> str:
    """Ce qui part dans le PDF."""
    return "\n".join([
        brief.get("bloc1", {}).get("texte", ""),
        brief.get("bloc2", {}).get("texte", ""),
        brief.get("bloc3", {}).get("texte", ""),
        " ".join(e.get("texte", "") for e in brief.get("bloc4", {}).get("elements", [])),
        brief.get("bloc5", {}).get("texte", ""),
        " ".join(str(brief.get("bloc6", {}).get(k, ""))
                 for k in ("intro", "formulation", "gardefou")),
        brief.get("note_echeance", ""),
    ])


def _developpe(brief: dict) -> str:
    """Ce qui part dans le corps de l'email."""
    return "\n".join([
        brief.get("bloc1", {}).get("developpe", ""),
        brief.get("bloc2", {}).get("developpe", ""),
        brief.get("bloc3", {}).get("developpe", ""),
        " ".join(e.get("developpe", "") for e in brief.get("bloc4", {}).get("elements", [])),
        brief.get("bloc5", {}).get("developpe", ""),
        str(brief.get("bloc6", {}).get("developpe", "")),
    ])


def _texte_integral(brief: dict) -> str:
    """Les deux versions : la conformité s'applique identiquement aux deux."""
    return _condense(brief) + "\n" + _developpe(brief)


NOMBRE = re.compile(r"\d[\d\s  ]*(?:[.,]\d+)?")


def _nombres(texte: str) -> set[str]:
    """Nombres normalisés d'un texte, séparateurs de milliers retirés."""
    out = set()
    for brut in NOMBRE.findall(texte or ""):
        n = re.sub(r"[\s  ]", "", brut).replace(",", ".").rstrip(".")
        if n and len(n) <= 15:
            out.add(n)
    return out


def _cherche(motifs: list[str], texte: str) -> list[str]:
    trouves = []
    for m in motifs:
        for occ in re.finditer(m, texte, flags=re.IGNORECASE):
            debut = max(0, occ.start() - 40)
            trouves.append("…" + texte[debut:occ.end() + 40].replace("\n", " ") + "…")
    return trouves


def controler(brief: dict, collecte: Collecte) -> list[Constat]:
    constats: list[Constat] = []
    texte = _texte_integral(brief)

    # 1. Aucun chiffre là où la collecte n'a rien confirmé -------------------
    for point in collecte.manquants:
        alias = ALIAS_POINTS.get(point.cle, []) + [point.libelle.lower()]
        for tuile in brief.get("stats", []):
            label = tuile.get("label", "").lower()
            valeur = tuile.get("valeur", "").strip().lower()
            if any(a in label for a in alias) and valeur not in NC:
                constats.append(Constat(
                    Gravite.BLOQUANT, "chiffre non confirmé publié",
                    f"La tuile « {tuile.get('label')} » affiche « {tuile.get('valeur')} » "
                    f"alors que la collecte a rendu {point.libelle} en statut "
                    f"« {point.statut.value} » ({point.note.strip()})"))

    # 2. Sources : présence et qualité d'émetteur ---------------------------
    for nom in ("bloc1", "bloc2", "bloc3", "bloc4", "bloc5", "bloc6"):
        bloc = brief.get(nom, {})
        sources = bloc.get("sources", []) if isinstance(bloc, dict) else []
        if not sources:
            constats.append(Constat(
                Gravite.BLOQUANT, "bloc sans source",
                f"{nom} ne cite aucune URL d'émetteur."))
            continue
        for url in sources:
            hote = (urlparse(url).hostname or "").lower().removeprefix("www.")
            if not hote:
                constats.append(Constat(
                    Gravite.ALERTE, "source illisible",
                    f"{nom} : « {url} » n'est pas une URL exploitable."))
            elif not any(hote == d or hote.endswith("." + d)
                         for d in DOMAINES_EMETTEURS):
                constats.append(Constat(
                    Gravite.ALERTE, "source non émettrice",
                    f"{nom} cite {hote}, qui n'est pas dans la liste des "
                    f"émetteurs de référence — vérifier que ce n'est pas un "
                    f"article de presse."))

    # 3. Vocabulaire d'opportunité (interdit, bloc 3 en particulier) --------
    for extrait in _cherche(OPPORTUNITE, texte):
        constats.append(Constat(
            Gravite.BLOQUANT, "qualification d'opportunité de marché", extrait))

    # 4. Recommandation d'investissement ------------------------------------
    for extrait in _cherche(RECOMMANDATION, texte):
        constats.append(Constat(
            Gravite.BLOQUANT, "recommandation d'investissement", extrait))

    # 5. Projection à l'indicatif futur --------------------------------------
    for extrait in _cherche(PROJECTION, texte):
        constats.append(Constat(
            Gravite.ALERTE, "affirmation prospective non conditionnelle", extrait))

    # 6. Statuts réglementaires cohérents ------------------------------------
    for element in brief.get("bloc4", {}).get("elements", []):
        statut, corps = element.get("statut", ""), element.get("texte", "")
        if statut == "EN DISCUSSION" and not re.search(
                r"\b(?:serait|pourrait|devrait|envisag|conditionn|projet|"
                r"proposition|amendement|à ce stade)\w*", corps, re.IGNORECASE):
            constats.append(Constat(
                Gravite.BLOQUANT, "texte en discussion présenté comme acquis",
                f"« {corps[:110]}… » est classé EN DISCUSSION mais rédigé sans "
                f"conditionnel ni marqueur d'incertitude."))
        if statut == "VOTE NON APPLICABLE" and not re.search(
                r"\b(?:entr[ée]e? en vigueur|à compter du|applicable (?:à|au|en)|"
                r"exercices? clos)\b", corps, re.IGNORECASE):
            constats.append(Constat(
                Gravite.ALERTE, "date d'entrée en vigueur absente",
                f"« {corps[:110]}… » est classé VOTÉ NON APPLICABLE sans date "
                f"d'entrée en vigueur explicite."))

    # 7. Cohérence formulation / garde-fou du bloc 6 -------------------------
    b6 = brief.get("bloc6", {})
    if b6:
        formulation = b6.get("formulation", "").lower()
        gardefou = b6.get("gardefou", "").lower()
        for mot in re.findall(r"\b(?:per|pea|scpi|compte-titres|assurance vie|"
                              r"pel|cel|livret a|lep)\b", gardefou):
            if f"ne dit rien du {mot}" in gardefou or f"ne dit rien de {mot}" in gardefou:
                if mot in formulation:
                    constats.append(Constat(
                        Gravite.BLOQUANT, "formulation contredisant son garde-fou",
                        f"Le garde-fou exclut « {mot} », que la formulation "
                        f"prête à l'emploi mentionne pourtant."))

    # 8. Citation de clôture -------------------------------------------------
    cit = brief.get("citation", {})
    texte_cit = cit.get("texte", "").lower()
    attribution = cit.get("attribution", "").strip()
    if attribution:
        if not re.search(r"\d{4}", attribution):
            constats.append(Constat(
                Gravite.ALERTE, "citation sans date identifiable",
                f"« {attribution} » ne comporte pas d'année."))
        for fragment, auteur in CITATIONS_APOCRYPHES:
            if re.search(fragment, texte_cit) and auteur in attribution.lower():
                constats.append(Constat(
                    Gravite.BLOQUANT, "citation apocryphe",
                    f"Attribution contestée : « {attribution} »."))

    # 9. Cohérence entre les deux versions ------------------------------------
    # Le condensé est une réduction du développé : il ne peut pas porter un
    # chiffre que la version longue ignore.
    for nom in ("bloc1", "bloc2", "bloc3", "bloc5"):
        bloc = brief.get(nom, {})
        if not isinstance(bloc, dict) or not bloc.get("developpe"):
            continue
        orphelins = _nombres(bloc.get("texte", "")) - _nombres(bloc["developpe"])
        if orphelins:
            constats.append(Constat(
                Gravite.ALERTE, "chiffre présent dans le PDF mais absent du mail",
                f"{nom} : {', '.join(sorted(orphelins)[:5])} — le condensé doit "
                f"être une réduction de la version longue, pas une rédaction "
                f"parallèle."))

    for i, el in enumerate(brief.get("bloc4", {}).get("elements", []), start=1):
        if not el.get("developpe"):
            continue
        orphelins = _nombres(el.get("texte", "")) - _nombres(el["developpe"])
        if orphelins:
            constats.append(Constat(
                Gravite.ALERTE, "chiffre présent dans le PDF mais absent du mail",
                f"bloc4, élément {i} : {', '.join(sorted(orphelins)[:5])}."))

    # 10. Formats --------------------------------------------------------------
    mots_dev = len(_developpe(brief).split())
    mots_con = len(_condense(brief).split())

    if mots_dev == 0:
        constats.append(Constat(
            Gravite.BLOQUANT, "version longue absente",
            "Aucun bloc ne porte de version développée : l'email n'aurait rien "
            "de plus que le PDF."))
    elif not 1600 <= mots_dev <= 3000:
        constats.append(Constat(
            Gravite.ALERTE, "longueur du mail hors cible",
            f"{mots_dev} mots (cible 2 000 à 2 500)."))

    if not 700 <= mots_con <= 1600:
        constats.append(Constat(
            Gravite.ALERTE, "longueur du PDF hors cible",
            f"{mots_con} mots (cible 1 000 à 1 300)."))

    if mots_dev and mots_con and mots_con > mots_dev:
        constats.append(Constat(
            Gravite.ALERTE, "condensé plus long que le développé",
            f"{mots_con} mots contre {mots_dev} — les deux versions sont "
            f"probablement inversées."))

    if len(brief.get("stats", [])) != 8:
        constats.append(Constat(
            Gravite.ALERTE, "nombre de tuiles incorrect",
            f"{len(brief.get('stats', []))} tuiles au lieu de 8."))

    return constats


def resume(constats: list[Constat], collecte: Collecte) -> str:
    """En-tête de santé, affiché en tête d'email. Jamais masqué."""
    bloquants = [c for c in constats if c.gravite is Gravite.BLOQUANT]
    alertes = [c for c in constats if c.gravite is Gravite.ALERTE]
    lignes = [collecte.sante]
    if bloquants:
        lignes.append(f"{len(bloquants)} contrôle(s) bloquant(s) — à relire avant "
                      f"toute réutilisation en rendez-vous")
    if alertes:
        lignes.append(f"{len(alertes)} alerte(s)")
    if not constats:
        lignes.append("tous les contrôles automatiques passent")
    return " · ".join(lignes)
