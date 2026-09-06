# -*- coding: utf-8 -*-
"""Configuration centrale. Aucun secret en dur : tout vient de l'environnement."""
from __future__ import annotations

import os
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CHARTE = RACINE / "charte" / "charte-editoriale.md"
ARCHIVE = RACINE / "archive"
CALENDRIER = RACINE / "calendrier.yml"

# --- Éditorial -------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODELE = os.environ.get("VEILLE_MODELE", "claude-sonnet-4-5-20250929")
MAX_TOKENS = int(os.environ.get("VEILLE_MAX_TOKENS", "8000"))
MAX_RECHERCHES = int(os.environ.get("VEILLE_MAX_RECHERCHES", "12"))

# --- Livraison -------------------------------------------------------------
CANAL = os.environ.get("VEILLE_CANAL", "resend")        # "resend" | "smtp" | "aucun"
DESTINATAIRE = os.environ.get("VEILLE_DESTINATAIRE", "")
EXPEDITEUR = os.environ.get("VEILLE_EXPEDITEUR", "")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

SMTP_HOTE = os.environ.get("SMTP_HOTE", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_UTILISATEUR = os.environ.get("SMTP_UTILISATEUR", "")
SMTP_MOT_DE_PASSE = os.environ.get("SMTP_MOT_DE_PASSE", "")

# --- Garde-fous ------------------------------------------------------------
# Fraîcheur maximale tolérée par famille de données, en jours.
FRAICHEUR = {
    "taux": 5,
    "indices": 5,
    "politique_monetaire": 45,
    "change": 5,
}

# Seuils de matérialité du bloc 3 (charte, section 4).
SEUIL_OAT_PB = 5
SEUIL_SPREAD_PB = 3

# Anti-répétition (charte, section 11).
FENETRE_CITATION_JOURS = 90
FENETRE_ANGLE_JOURS = 15
MAX_FORMATS_CONSECUTIFS = 3


def verifier(strict: bool = True) -> list[str]:
    """Rend la liste des problèmes de configuration bloquants."""
    problemes = []
    if not ANTHROPIC_API_KEY:
        problemes.append("ANTHROPIC_API_KEY manquante — la couche éditoriale ne peut pas tourner.")
    if not CHARTE.exists():
        problemes.append(f"Charte introuvable : {CHARTE}")
    if strict and CANAL != "aucun":
        if not DESTINATAIRE:
            problemes.append("VEILLE_DESTINATAIRE manquant.")
        if CANAL == "resend" and not RESEND_API_KEY:
            problemes.append("RESEND_API_KEY manquante alors que VEILLE_CANAL=resend.")
        if CANAL == "smtp" and not (SMTP_UTILISATEUR and SMTP_MOT_DE_PASSE):
            problemes.append("Identifiants SMTP manquants alors que VEILLE_CANAL=smtp.")
    return problemes
