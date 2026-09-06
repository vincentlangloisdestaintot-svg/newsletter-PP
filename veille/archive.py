# -*- coding: utf-8 -*-
"""Archive des éditions.

Deux fonctions : constituer le corpus réutilisable en book, et alimenter
l'anti-répétition mécanique de la charte (section 11). Sans archive, les
citations et les angles se répètent au bout de quelques semaines et rien ne le
détecte.

Arborescence : archive/AAAA/AAAA-MM-JJ.{json,md,pdf}
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import shutil
from pathlib import Path

from .config import (ARCHIVE, FENETRE_ANGLE_JOURS, FENETRE_CITATION_JOURS,
                     MAX_FORMATS_CONSECUTIFS)

log = logging.getLogger(__name__)


def _dossier(jour: dt.date) -> Path:
    d = ARCHIVE / f"{jour.year}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def enregistrer(jour: dt.date, brief: dict, collecte: dict, markdown: str,
                pdf: Path | None, constats: list[str]) -> dict[str, Path]:
    d = _dossier(jour)
    base = jour.isoformat()
    ecrits: dict[str, Path] = {}

    chemin_json = d / f"{base}.json"
    chemin_json.write_text(json.dumps({
        "date": base,
        "brief": brief,
        "collecte": collecte,
        "constats": constats,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    ecrits["json"] = chemin_json

    chemin_md = d / f"{base}.md"
    chemin_md.write_text(markdown, encoding="utf-8")
    ecrits["markdown"] = chemin_md

    if pdf and pdf.exists():
        chemin_pdf = d / f"{base}.pdf"
        shutil.copy2(pdf, chemin_pdf)
        ecrits["pdf"] = chemin_pdf

    log.info("Édition archivée : %s", ", ".join(str(p) for p in ecrits.values()))
    return ecrits


def _editions(depuis: dt.date) -> list[tuple[dt.date, dict]]:
    out: list[tuple[dt.date, dict]] = []
    if not ARCHIVE.exists():
        return out
    for f in sorted(ARCHIVE.rglob("*.json")):
        try:
            jour = dt.date.fromisoformat(f.stem)
        except ValueError:
            continue
        if jour < depuis:
            continue
        try:
            out.append((jour, json.loads(f.read_text(encoding="utf-8"))))
        except (ValueError, OSError):
            continue
    return sorted(out, key=lambda x: x[0])


def contraintes(aujourdhui: dt.date | None = None) -> str:
    """Texte injecté dans l'instruction éditoriale : ce qu'il ne faut pas refaire."""
    j = aujourdhui or dt.date.today()

    citations = [
        (e["brief"].get("citation") or {}).get("texte", "").strip()
        for _, e in _editions(j - dt.timedelta(days=FENETRE_CITATION_JOURS))
    ]
    citations = [c for c in citations if c]

    recents = _editions(j - dt.timedelta(days=FENETRE_ANGLE_JOURS))
    angles = [(e["brief"].get("bloc6") or {}).get("angle", "").strip()
              for _, e in recents]
    angles = [a for a in angles if a]

    formats = [(e["brief"].get("bloc6") or {}).get("format", "")
               for _, e in _editions(j - dt.timedelta(days=30))]

    lignes: list[str] = []
    if citations:
        lignes.append(
            f"Citations déjà utilisées ces {FENETRE_CITATION_JOURS} derniers jours "
            f"— à ne pas reprendre :\n" + "\n".join(f"  - {c}" for c in citations[-25:]))
    if angles:
        lignes.append(
            f"Angles du bloc 6 des {FENETRE_ANGLE_JOURS} derniers jours "
            f"— à ne pas refaire :\n" + "\n".join(f"  - {a}" for a in angles))

    if len(formats) >= MAX_FORMATS_CONSECUTIFS:
        derniers = formats[-MAX_FORMATS_CONSECUTIFS:]
        if len(set(derniers)) == 1:
            impose = "ARGUMENT" if derniers[0] == "TECHNIQUE" else "TECHNIQUE"
            lignes.append(
                f"Les {MAX_FORMATS_CONSECUTIFS} dernières éditions sont au format "
                f"{derniers[0]}. Le bloc 6 doit aujourd'hui être au format {impose}.")

    if not lignes:
        return ("Aucune édition archivée exploitable : pas de contrainte "
                "d'anti-répétition ce matin.")
    return "\n\n".join(lignes)
