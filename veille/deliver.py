# -*- coding: utf-8 -*-
"""Livraison email : Resend (API) ou SMTP, au choix de VEILLE_CANAL."""
from __future__ import annotations

import base64
import logging
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

from . import config

log = logging.getLogger(__name__)

RESEND = "https://api.resend.com/emails"


def envoyer(sujet: str, corps_html: str, corps_texte: str,
            pieces: list[Path] | None = None) -> bool:
    pieces = [p for p in (pieces or []) if p and p.exists()]

    if config.CANAL == "aucun":
        log.info("VEILLE_CANAL=aucun — envoi ignoré.")
        return True
    if not config.DESTINATAIRE:
        log.error("VEILLE_DESTINATAIRE manquant — envoi impossible.")
        return False

    if config.CANAL == "resend":
        return _resend(sujet, corps_html, corps_texte, pieces)
    if config.CANAL == "smtp":
        return _smtp(sujet, corps_html, corps_texte, pieces)

    log.error("VEILLE_CANAL inconnu : %s", config.CANAL)
    return False


def _resend(sujet, html, texte, pieces) -> bool:
    if not config.RESEND_API_KEY:
        log.error("RESEND_API_KEY manquante.")
        return False
    charge = {
        "from": config.EXPEDITEUR or "Veille patrimoniale <onboarding@resend.dev>",
        "to": [d.strip() for d in config.DESTINATAIRE.split(",") if d.strip()],
        "subject": sujet,
        "html": html,
        "text": texte,
    }
    if pieces:
        charge["attachments"] = [{
            "filename": p.name,
            "content": base64.b64encode(p.read_bytes()).decode("ascii"),
        } for p in pieces]

    try:
        r = requests.post(
            RESEND, json=charge, timeout=45,
            headers={"Authorization": f"Bearer {config.RESEND_API_KEY}",
                     "Content-Type": "application/json"})
    except requests.RequestException as exc:
        log.error("Resend injoignable : %s", exc)
        return False

    if r.status_code in (200, 201):
        log.info("Email envoyé via Resend.")
        return True
    log.error("Resend a refusé l'envoi : HTTP %s — %s", r.status_code, r.text[:400])
    return False


def _smtp(sujet, html, texte, pieces) -> bool:
    if not (config.SMTP_UTILISATEUR and config.SMTP_MOT_DE_PASSE):
        log.error("Identifiants SMTP manquants.")
        return False

    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = config.EXPEDITEUR or config.SMTP_UTILISATEUR
    msg["To"] = config.DESTINATAIRE
    msg.set_content(texte)
    msg.add_alternative(html, subtype="html")

    for p in pieces:
        type_mime, _ = mimetypes.guess_type(p.name)
        maintype, _, subtype = (type_mime or "application/octet-stream").partition("/")
        msg.add_attachment(p.read_bytes(), maintype=maintype,
                           subtype=subtype, filename=p.name)

    try:
        with smtplib.SMTP(config.SMTP_HOTE, config.SMTP_PORT, timeout=45) as s:
            s.starttls()
            s.login(config.SMTP_UTILISATEUR, config.SMTP_MOT_DE_PASSE)
            s.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        log.error("Envoi SMTP échoué : %s", exc)
        return False

    log.info("Email envoyé via SMTP.")
    return True
