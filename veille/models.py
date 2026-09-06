# -*- coding: utf-8 -*-
"""Modèle de données : rien n'entre dans le brief sans émetteur, URL et statut."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Statut(str, Enum):
    """Statut de vérification d'une donnée.

    CONFIRME     : valeur obtenue chez son émetteur (ou deux sources convergentes).
    DIVERGENT    : sources contradictoires au-delà du seuil — non publiable tel quel.
    NON_CONFIRME : non récupérée. Le brief doit l'écrire, pas la combler.
    PERIME       : obtenue mais plus ancienne que la fraîcheur attendue.
    """

    CONFIRME = "confirmé"
    DIVERGENT = "divergent"
    NON_CONFIRME = "non confirmé"
    PERIME = "périmé"


@dataclass
class DataPoint:
    """Une donnée chiffrée et son dossier de preuve."""

    cle: str                      # identifiant interne stable, ex. "oat_10a"
    libelle: str                  # intitulé lisible, ex. "OAT 10 ans"
    valeur: float | None = None
    unite: str = ""               # "%", "pb", "points", "€"
    emetteur: str = ""            # qui publie le chiffre
    url: str = ""                 # page de l'émetteur, jamais un article de presse
    date_obs: dt.date | None = None
    statut: Statut = Statut.NON_CONFIRME
    provisoire: bool = False
    date_definitif: dt.date | None = None
    variation: float | None = None       # vs période précédente
    unite_variation: str = ""            # "%", "pb"
    sources_convergentes: list[str] = field(default_factory=list)
    note: str = ""                       # divergence, réserve, précision de méthode

    # --- Qualité -----------------------------------------------------------
    @property
    def publiable(self) -> bool:
        return self.statut is Statut.CONFIRME and self.valeur is not None

    @property
    def age_jours(self) -> int | None:
        if self.date_obs is None:
            return None
        return (dt.date.today() - self.date_obs).days

    def appliquer_fraicheur(self, max_jours: int) -> None:
        """Déclasse la donnée si elle est plus ancienne que la fraîcheur attendue."""
        age = self.age_jours
        if age is not None and age > max_jours and self.statut is Statut.CONFIRME:
            self.statut = Statut.PERIME
            self.note = (self.note + " " if self.note else "") + (
                f"Donnée de {age} jours, au-delà de la fraîcheur attendue "
                f"({max_jours} j) — signalée comme telle."
            )

    def rendu(self) -> str:
        """Texte court prêt à être affiché, ou mention explicite de blanc assumé."""
        if not self.publiable:
            return "non confirmé à la source"
        v = f"{self.valeur:,.2f}".replace(",", " ").replace(".", ",")
        if self.unite == "%":
            return f"{v} %"
        if self.unite == "pb":
            return f"{self.valeur:.0f} pb"
        return f"{v} {self.unite}".strip()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["statut"] = self.statut.value
        for k in ("date_obs", "date_definitif"):
            d[k] = d[k].isoformat() if d[k] else None
        return d


@dataclass
class Echeance:
    """Rendez-vous du calendrier récurrent tombant aujourd'hui ou sous 48 h."""

    date: dt.date
    emetteur: str
    intitule: str
    url: str = ""

    @property
    def imminence(self) -> str:
        delta = (self.date - dt.date.today()).days
        return {0: "aujourd'hui", 1: "demain"}.get(delta, f"dans {delta} jours")


@dataclass
class Collecte:
    """Sortie de la couche données : ce qui a été confirmé, et ce qui ne l'a pas été."""

    date_run: dt.datetime
    points: dict[str, DataPoint] = field(default_factory=dict)
    echeances: list[Echeance] = field(default_factory=list)

    def get(self, cle: str) -> DataPoint | None:
        return self.points.get(cle)

    @property
    def confirmes(self) -> list[DataPoint]:
        return [p for p in self.points.values() if p.publiable]

    @property
    def manquants(self) -> list[DataPoint]:
        return [p for p in self.points.values() if not p.publiable]

    @property
    def sante(self) -> str:
        return f"{len(self.confirmes)}/{len(self.points)} chiffres confirmés à la source"

    def to_dict(self) -> dict[str, Any]:
        return {
            "date_run": self.date_run.isoformat(),
            "sante": self.sante,
            "points": {k: v.to_dict() for k, v in self.points.items()},
            "echeances": [
                {"date": e.date.isoformat(), "emetteur": e.emetteur,
                 "intitule": e.intitule, "url": e.url}
                for e in self.echeances
            ],
        }
