# -*- coding: utf-8 -*-
"""Rendu PDF — identité visuelle stable.

Le bloc RENDU (styles, couleurs, mise en page) est figé : il ne doit pas bouger
d'une édition à l'autre. Les données viennent du brief JSON, jamais de
constantes écrites à la main.

Écart assumé par rapport au gabarit d'origine : une section « Taux et
obligataire » a été ajoutée, parce que la charte définit six blocs et que le
gabarit n'en rendait que cinq — le bloc taux se retrouvait dilué dans les
tuiles. Texte et PDF rendent désormais la même structure.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ============================================================================
# RENDU — identité visuelle. Ne pas modifier sans décision explicite.
# ============================================================================
C = {k: colors.HexColor(v) for k, v in dict(
    navy="#12213b", red="#c81e2c", ink="#1a1a2e", grey="#6b7280",
    tile="#f2f4f7", line="#dde1e8", green="#2f6f4f", amber="#a8781f",
    maroon="#7a3b3b", alert="#fdf2f2", alertline="#e6b8bb").items()}
C["white"] = colors.white

STATUS = {
    "EN VIGUEUR": (C["green"], "EN<br/>VIGUEUR"),
    "VOTE NON APPLICABLE": (C["amber"], "VOTÉ<br/>NON APPLIC."),
    "EN DISCUSSION": (C["maroon"], "EN<br/>DISCUSSION"),
}


def S(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    return ParagraphStyle(name, **kw)


ST = {
    "brand": S("brand", fontName="Helvetica-Bold", fontSize=22, textColor=C["white"], leading=24),
    "edition": S("edition", fontName="Helvetica-Bold", fontSize=9, textColor=C["white"], leading=12, alignment=TA_CENTER),
    "tagline": S("tagline", fontName="Helvetica-Oblique", fontSize=8.3, textColor=colors.HexColor("#c9cedb"), leading=11),
    "h2": S("h2", fontName="Helvetica-Bold", fontSize=11, textColor=C["navy"], spaceBefore=12, spaceAfter=5),
    "body": S("body", fontSize=8.8, leading=12.5, textColor=C["ink"], spaceAfter=2),
    "src": S("src", fontName="Helvetica-Oblique", fontSize=7.4, leading=10, textColor=C["grey"], spaceBefore=3),
    "tl": S("tl", fontName="Helvetica-Bold", fontSize=6.9, textColor=C["grey"], leading=8.5),
    "tv": S("tv", fontName="Helvetica-Bold", fontSize=13.5, textColor=C["navy"], leading=15.5, spaceBefore=1),
    "tc": S("tc", fontSize=6.6, textColor=C["grey"], leading=8),
    "hl": S("hl", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#f5c6ca"), leading=11),
    "hv": S("hv", fontName="Helvetica-Bold", fontSize=30, textColor=C["white"], leading=32),
    "ht": S("ht", fontSize=8.6, textColor=C["white"], leading=12),
    "bh": S("bh", fontName="Helvetica-Bold", fontSize=7.6, textColor=C["white"], alignment=TA_CENTER, leading=9),
    "bb": S("bb", fontSize=8.4, textColor=C["ink"], leading=11.5),
    "ph": S("ph", fontName="Helvetica-Bold", fontSize=9.5, textColor=C["white"], leading=12),
    "pb": S("pb", fontSize=8.8, textColor=C["white"], leading=12.5, spaceAfter=4),
    "pq": S("pq", fontName="Helvetica-BoldOblique", fontSize=9.6, textColor=colors.HexColor("#ffd9dc"), leading=13, spaceAfter=4),
    "qs": S("qs", fontName="Helvetica-BoldOblique", fontSize=13, textColor=C["red"], alignment=TA_CENTER, leading=16, spaceBefore=10, spaceAfter=4),
    "qa": S("qa", fontName="Helvetica-Bold", fontSize=8, textColor=C["navy"], alignment=TA_CENTER, leading=10),
    "sante": S("sante", fontName="Helvetica-Bold", fontSize=7.6, textColor=C["maroon"], leading=10),
    "santed": S("santed", fontSize=7.2, textColor=C["ink"], leading=9.5),
}

W = A4[0] - 28 * mm


def esc(txt: str) -> str:
    """Échappe le texte du modèle et applique les espaces insécables typographiques."""
    t = html.escape(str(txt or ""), quote=False)
    t = re.sub(r"\s+([%€:;!?»])", r"&nbsp;\1", t)
    t = t.replace("« ", "«&nbsp;")
    return t


# ============================================================================
def construire(brief: dict, sante: str, constats_bloquants: list[str],
               sortie: Path) -> Path:
    story: list = []

    band = Table([[Paragraph("VEILLE&nbsp;<font color='#c81e2c'>PATRIMONIALE</font>", ST["brand"]),
                   Paragraph(f"ÉDITION DU<br/>{esc(brief['date_titre'])}", ST["edition"])]],
                 colWidths=[W * 0.68, W * 0.32])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["navy"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (0, 0), 12)]))
    story.append(band)

    tagline = Table([[Paragraph(
        "Marchés, taux, fiscalité et épargne — sourcé, opposable. "
        "Version condensée&nbsp;: le détail figure dans l'édition envoyée par email.",
        ST["tagline"])]], colWidths=[W])
    tagline.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["navy"]), ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10), ("LEFTPADDING", (0, 0), (-1, -1), 12)]))
    story.append(tagline)
    story.append(Spacer(1, 8))

    # Bandeau de santé : visible, jamais masqué.
    if constats_bloquants:
        lignes = [[Paragraph(f"CONTRÔLE AUTOMATIQUE — {esc(sante)}", ST["sante"])]]
        for c in constats_bloquants[:6]:
            lignes.append([Paragraph("• " + esc(c), ST["santed"])])
        t = Table(lignes, colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C["alert"]),
            ("BOX", (0, 0), (-1, -1), 0.7, C["alertline"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.append(t)
        story.append(Spacer(1, 8))

    # Chiffre du jour
    b1 = brief["bloc1"]
    story.append(_bar([[("LE CHIFFRE DU JOUR", ST["hl"])],
                       [(esc(b1["valeur"]), ST["hv"])],
                       [(esc(b1["texte"]), ST["ht"])]],
                      C["red"], [(10, 0), (0, 2), (2, 10)]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("STATS DU JOUR", ST["h2"]))
    _grille(story, [(t["label"], t["valeur"], t["contexte"]) for t in brief["stats"]])
    story.append(Spacer(1, 4))
    story.append(Paragraph(esc(brief["note_echeance"]), ST["body"]))
    story.append(Paragraph(_sources(b1["sources"]), ST["src"]))

    story.append(Paragraph("TAUX ET OBLIGATAIRE", ST["h2"]))
    story.append(Paragraph(esc(brief["bloc3"]["texte"]), ST["body"]))
    story.append(Paragraph(_sources(brief["bloc3"]["sources"]), ST["src"]))

    story.append(Paragraph("LECTURE PATRIMONIALE — MARCHÉS", ST["h2"]))
    story.append(Paragraph(esc(brief["bloc2"]["texte"]), ST["body"]))
    story.append(Paragraph(_sources(brief["bloc2"]["sources"]), ST["src"]))

    story.append(Paragraph("FISCALITÉ &amp; RÉGLEMENTAIRE", ST["h2"]))
    for el in brief["bloc4"]["elements"]:
        _statut(story, el["statut"], esc(el["texte"]))
    story.append(Paragraph(_sources(brief["bloc4"]["sources"]), ST["src"]))

    story.append(Paragraph("ASSURANCE VIE, RETRAITE, ÉPARGNE", ST["h2"]))
    tuiles = brief["bloc5"].get("tuiles") or []
    if tuiles:
        _grille(story, [(t["label"], t["valeur"], t["contexte"]) for t in tuiles])
        story.append(Spacer(1, 4))
    story.append(Paragraph(esc(brief["bloc5"]["texte"]), ST["body"]))
    story.append(Paragraph(_sources(brief["bloc5"]["sources"]), ST["src"]))
    story.append(Spacer(1, 6))

    b6 = brief["bloc6"]
    story.append(_bar([
        [(f"LE POINT DU JOUR — {esc(b6['format'])}", ST["ph"])],
        [(esc(b6["intro"]), ST["pb"])],
        [(esc(b6["formulation"]), ST["pq"])],
        [(esc(b6["gardefou"]), ST["pb"])],
    ], C["navy"], [(10, 4), (2, 2), (2, 2), (2, 10)]))

    # Le blanc assumé apparaît dans les trois rendus, jamais dans deux sur trois.
    if brief.get("chiffres_non_confirmes"):
        story.append(Paragraph("NON CONFIRMÉ À LA SOURCE CE MATIN", ST["h2"]))
        for x in brief["chiffres_non_confirmes"]:
            story.append(Paragraph("• " + esc(x), ST["body"]))

    cit = brief["citation"]
    story.append(Paragraph(esc(cit["texte"]), ST["qs"]))
    if cit.get("attribution"):
        story.append(Paragraph(esc(cit["attribution"]).upper(), ST["qa"]))

    sortie.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(sortie), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=0, bottomMargin=12 * mm,
        title=f"Veille patrimoniale — {brief['date_titre']}",
        author="Veille quotidienne")
    doc.build(story)
    return sortie


# --- primitives de mise en page (figées) -----------------------------------
def _bar(rows_styles, bg, pads):
    t = Table([[Paragraph(txt, st) for txt, st in row] for row in rows_styles],
              colWidths=[W])
    style = [("BACKGROUND", (0, 0), (-1, -1), bg),
             ("LEFTPADDING", (0, 0), (-1, -1), 14),
             ("RIGHTPADDING", (0, 0), (-1, -1), 14)]
    for i, (top, bot) in enumerate(pads):
        style += [("TOPPADDING", (0, i), (-1, i), top),
                  ("BOTTOMPADDING", (0, i), (-1, i), bot)]
    t.setStyle(TableStyle(style))
    return t


def _tuile(label, valeur, ctx):
    t = Table([[Paragraph(esc(label), ST["tl"])],
               [Paragraph(esc(valeur), ST["tv"])],
               [Paragraph(esc(ctx), ST["tc"])]], colWidths=[W / 4 - 3])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["tile"]),
        ("BOX", (0, 0), (-1, -1), 0.5, C["line"]),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    return t


def _grille(story, data):
    for i in range(0, len(data), 4):
        row = [_tuile(*d) for d in data[i:i + 4]]
        while len(row) < 4:
            row.append(Paragraph("", ST["tc"]))
        rt = Table([row], colWidths=[W / 4] * 4)
        rt.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(rt)


def _statut(story, statut, texte):
    color, label = STATUS.get(statut, (C["grey"], esc(statut)))
    t = Table([[Paragraph(label, ST["bh"]), Paragraph(texte, ST["bb"])]],
              colWidths=[28 * mm, W - 28 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), color),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fbfbfc")),
        ("BOX", (0, 0), (-1, -1), 0.5, C["line"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 9)]))
    story.append(t)
    story.append(Spacer(1, 3))


def _sources(urls: list[str]) -> str:
    if not urls:
        return "Source : non renseignée."
    return "Sources : " + esc(" · ".join(urls))
