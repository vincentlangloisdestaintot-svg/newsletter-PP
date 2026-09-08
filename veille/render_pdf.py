# -*- coding: utf-8 -*-
"""Rendu PDF — fiche flash, une page.

Le PDF n'est plus une réduction linéaire de l'édition email : c'est une fiche
de consultation. Chiffres, statuts, formulation du jour, blancs assumés. Le
raisonnement reste dans l'email.

Le texte affiché est dérivé mécaniquement du condensé (`texte`) du brief :
première ou deux premières phrases selon le bloc. Aucun champ nouveau n'est
attendu dans le JSON — si un brief porte un jour une clé `flash`, elle est
utilisée en priorité.

Le bloc RENDU (styles, couleurs) est figé : il ne doit pas bouger d'une
édition à l'autre.
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
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

# ============================================================================
# RENDU — identité visuelle. Ne pas modifier sans décision explicite.
# ============================================================================
C = {k: colors.HexColor(v) for k, v in dict(
    navy="#12213b", red="#c81e2c", ink="#1a1a2e", grey="#6b7280",
    tile="#f2f4f7", line="#dde1e8", green="#2f6f4f", amber="#a8781f",
    maroon="#7a3b3b", alert="#fdf2f2", alertline="#e6b8bb",
    pale="#41506b").items()}
C["white"] = colors.white

STATUS = {
    "EN VIGUEUR": (C["green"], "EN VIGUEUR"),
    "VOTE NON APPLICABLE": (C["amber"], "VOTÉ, NON APPLIC."),
    "EN DISCUSSION": (C["maroon"], "EN DISCUSSION"),
}


def S(name, **kw):
    kw.setdefault("fontName", "Helvetica")
    return ParagraphStyle(name, **kw)


ST = {
    "brand": S("brand", fontName="Helvetica-Bold", fontSize=17, textColor=C["white"], leading=19),
    "edition": S("edition", fontName="Helvetica-Bold", fontSize=8.2, textColor=C["white"], leading=10.5, alignment=TA_CENTER),
    "tagline": S("tagline", fontName="Helvetica-Oblique", fontSize=7.3, textColor=colors.HexColor("#c9cedb"), leading=9.4),
    "h2": S("h2", fontName="Helvetica-Bold", fontSize=9, textColor=C["navy"], spaceBefore=6, spaceAfter=2),
    "flash": S("flash", fontSize=8.2, leading=11, textColor=C["ink"], spaceAfter=2),
    "tl": S("tl", fontName="Helvetica-Bold", fontSize=6.4, textColor=C["grey"], leading=8),
    "tv": S("tv", fontName="Helvetica-Bold", fontSize=12.5, textColor=C["navy"], leading=14.5, spaceBefore=1),
    "tc": S("tc", fontSize=6.2, textColor=C["grey"], leading=7.6),
    "hl": S("hl", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#f5c6ca"), leading=10),
    "hv": S("hv", fontName="Helvetica-Bold", fontSize=26, textColor=C["white"], leading=28),
    "ht": S("ht", fontSize=8.2, textColor=C["white"], leading=11.2),
    "bb": S("bb", fontSize=8.2, textColor=C["ink"], leading=11),
    "ph": S("ph", fontName="Helvetica-Bold", fontSize=8.4, textColor=C["white"], leading=10.5),
    "pb": S("pb", fontSize=8, textColor=colors.HexColor("#c9cedb"), leading=11, spaceAfter=2),
    "pq": S("pq", fontName="Helvetica-BoldOblique", fontSize=9, textColor=colors.HexColor("#ffd9dc"), leading=12.5, spaceAfter=3),
    "qs": S("qs", fontName="Helvetica-BoldOblique", fontSize=11.5, textColor=C["red"], alignment=TA_CENTER, leading=15, spaceBefore=9, spaceAfter=3),
    "qa": S("qa", fontName="Helvetica-Bold", fontSize=7.4, textColor=C["navy"], alignment=TA_CENTER, leading=9.5),
    "sante": S("sante", fontName="Helvetica-Bold", fontSize=7.2, textColor=C["maroon"], leading=9.5),
    "santed": S("santed", fontSize=6.9, textColor=C["ink"], leading=9),
    "nc": S("nc", fontSize=7.2, leading=9.6, textColor=C["pale"]),
    "foot": S("foot", fontSize=6.3, leading=8.4, textColor=C["grey"], spaceBefore=7),
}

W = A4[0] - 24 * mm


def esc(txt: str) -> str:
    """Échappe le texte du modèle et applique les espaces insécables typographiques."""
    t = html.escape(str(txt or ""), quote=False)
    t = re.sub(r"\s+([%€:;!?»])", r"&nbsp;\1", t)
    t = t.replace("« ", "«&nbsp;")
    return t


# --- réduction mécanique du condensé --------------------------------------
_COUPE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÉÈÊÀÂÎÔÙÛÇ«])")


def phrases(texte: str) -> list[str]:
    """Découpe en phrases. Une coupure exige une majuscule derrière, ce qui
    évite de couper sur « n° 2026-103 du… » ou « art. L. 224-1 »."""
    brut = [p.strip() for p in _COUPE.split(str(texte or "").strip()) if p.strip()]
    out: list[str] = []
    for p in brut:
        # Une « phrase » très courte est un faux positif : on la recolle.
        if out and len(out[-1]) < 30:
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


def flash(bloc: dict, n: int = 2, cle: str = "texte") -> str:
    """Les n premières phrases du condensé, ou le champ `flash` s'il existe."""
    if not isinstance(bloc, dict):
        return ""
    if bloc.get("flash"):
        return str(bloc["flash"]).strip()
    return " ".join(phrases(bloc.get(cle, ""))[:n])


def _entete_nc(item: str) -> str:
    """« Bund 10 ans — aucune source… » -> « Bund 10 ans »."""
    return re.split(r"\s+[—–-]\s+", str(item), maxsplit=1)[0].strip()


# ============================================================================
def construire(brief: dict, sante: str, constats_bloquants: list[str],
               sortie: Path) -> Path:
    story: list = []

    band = Table([[Paragraph("VEILLE&nbsp;<font color='#c81e2c'>PATRIMONIALE</font>", ST["brand"]),
                   Paragraph(f"ÉDITION DU<br/>{esc(brief['date_titre'])}", ST["edition"])]],
                 colWidths=[W * 0.68, W * 0.32])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["navy"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (0, 0), 12)]))
    story.append(band)

    tagline = Table([[Paragraph(
        f"Fiche flash — chiffres, statuts et formulation du jour. "
        f"Contrôle automatique&nbsp;: {esc(sante)}. "
        f"Le raisonnement complet et les URL sources sont dans l'édition email.",
        ST["tagline"])]], colWidths=[W])
    tagline.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C["navy"]), ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 12)]))
    story.append(tagline)
    story.append(Spacer(1, 6))

    # Bandeau de santé : visible, jamais masqué.
    if constats_bloquants:
        lignes = [[Paragraph(f"CONTRÔLE BLOQUANT — {esc(sante)}", ST["sante"])]]
        for c in constats_bloquants[:5]:
            lignes.append([Paragraph("• " + esc(c), ST["santed"])])
        t = Table(lignes, colWidths=[W])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C["alert"]),
            ("BOX", (0, 0), (-1, -1), 0.7, C["alertline"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(t)
        story.append(Spacer(1, 7))

    # --- Le chiffre du jour ------------------------------------------------
    b1 = brief["bloc1"]
    story.append(_bar([[("LE CHIFFRE DU JOUR", ST["hl"])],
                       [(esc(b1["valeur"]), ST["hv"])],
                       [(esc(flash(b1, 2)), ST["ht"])]],
                      C["red"], [(7, 0), (0, 2), (2, 7)]))
    story.append(Spacer(1, 6))

    # --- Chiffres clés -----------------------------------------------------
    _titre(story, "CHIFFRES CLÉS")
    _grille(story, [(t["label"], t["valeur"], t["contexte"]) for t in brief["stats"]])
    tuiles5 = brief["bloc5"].get("tuiles") or []
    if tuiles5:
        _grille(story, [(t["label"], t["valeur"], t["contexte"]) for t in tuiles5])

    # --- Info flash --------------------------------------------------------
    _titre(story, "INFO FLASH")
    _puce(story, "TAUX", flash(brief["bloc3"], 2))
    _puce(story, "MARCHÉS", flash(brief["bloc2"], 2))
    _puce(story, "ÉPARGNE", flash(brief["bloc5"], 2))

    # --- Fiscalité et réglementaire ---------------------------------------
    _titre(story, "FISCALITÉ &amp; RÉGLEMENTAIRE")
    for el in brief["bloc4"]["elements"]:
        _statut(story, el["statut"], flash(el, 1))

    # --- Échéances ---------------------------------------------------------
    ech = " ".join(phrases(brief.get("note_echeance", ""))[:3])
    if ech:
        _titre(story, "À L'AGENDA")
        story.append(Paragraph(esc(ech), ST["flash"]))

    # --- Le point du jour --------------------------------------------------
    b6 = brief["bloc6"]
    story.append(Spacer(1, 4))
    story.append(KeepTogether([_bar([
        [(f"LE POINT DU JOUR — {esc(b6['format'])} · {esc(b6.get('angle', ''))}", ST["ph"])],
        [(esc(b6["formulation"]), ST["pq"])],
        [("<b>Garde-fou.</b> " + esc(flash(b6, 2, "gardefou")), ST["pb"])],
    ], C["navy"], [(8, 3), (2, 2), (2, 9)])]))

    # La fin — blancs assumés, citation, mentions — ne se coupe jamais.
    # Le blanc assumé apparaît dans les trois rendus, jamais dans deux sur trois.
    fin: list = []
    ncs = brief.get("chiffres_non_confirmes") or []
    if ncs:
        fin.append(Spacer(1, 6))
        fin.append(Paragraph(
            "<b>Non confirmé à la source ce matin —</b> "
            + esc(" · ".join(_entete_nc(x) for x in ncs))
            + ". Le motif de chaque blanc figure dans l'édition email.",
            ST["nc"]))

    cit = brief["citation"]
    fin.append(Paragraph(esc(cit["texte"]), ST["qs"]))
    if cit.get("attribution"):
        fin.append(Paragraph(esc(cit["attribution"]).upper(), ST["qa"]))
    story.append(KeepTogether(fin))

    story.append(Paragraph(
        "Document de veille à usage professionnel interne. Ne constitue ni une "
        "recommandation d'investissement, ni un conseil personnalisé. Les "
        "performances passées ne préjugent pas des performances futures. "
        "Chaque chiffre porte son émetteur et sa date&nbsp;; les URL sources "
        "figurent dans l'édition email.", ST["foot"]))

    sortie.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(sortie), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=0, bottomMargin=10 * mm,
        title=f"Veille patrimoniale — {brief['date_titre']}",
        author="Veille quotidienne")
    doc.build(story)
    return sortie


# --- primitives de mise en page (figées) -----------------------------------
def _titre(story, libelle):
    story.append(Paragraph(libelle, ST["h2"]))
    r = Table([[""]], colWidths=[W], rowHeights=[1.4])
    r.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C["navy"]),
                           ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story.append(r)
    story.append(Spacer(1, 4))


def _puce(story, kicker, texte):
    if not texte:
        return
    t = Table([[Paragraph(esc(kicker), ST["tl"]),
                Paragraph(esc(texte), ST["bb"])]],
              colWidths=[19 * mm, W - 19 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBEFORE", (0, 0), (0, 0), 1.6, C["red"]),
        ("LEFTPADDING", (0, 0), (0, 0), 6), ("LEFTPADDING", (1, 0), (1, 0), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(t)


def _bar(rows_styles, bg, pads):
    t = Table([[Paragraph(txt, st) for txt, st in row] for row in rows_styles],
              colWidths=[W])
    style = [("BACKGROUND", (0, 0), (-1, -1), bg),
             ("LEFTPADDING", (0, 0), (-1, -1), 12),
             ("RIGHTPADDING", (0, 0), (-1, -1), 12)]
    for i, (top, bot) in enumerate(pads):
        style += [("TOPPADDING", (0, i), (-1, i), top),
                  ("BOTTOMPADDING", (0, i), (-1, i), bot)]
    t.setStyle(TableStyle(style))
    return t


def _tuile(label, valeur, ctx):
    """Contenu seul : fond, cadre et hauteur sont portés par la grille."""
    t = Table([[Paragraph(esc(label), ST["tl"])],
               [Paragraph(esc(valeur), ST["tv"])],
               [Paragraph(esc(ctx), ST["tc"])]], colWidths=[W / 4 - 14])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _grille(story, data):
    """Un rang = une ligne de tableau : toutes les tuiles ont la même hauteur."""
    for i in range(0, len(data), 4):
        bloc = data[i:i + 4]
        row = [_tuile(*d) for d in bloc]
        while len(row) < 4:
            row.append(Paragraph("", ST["tc"]))
        rt = Table([row], colWidths=[W / 4] * 4)
        style = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for c in range(len(bloc)):
            style += [
                ("BACKGROUND", (c, 0), (c, 0), C["tile"]),
                ("BOX", (c, 0), (c, 0), 0.5, C["line"]),
                ("LINEABOVE", (c, 0), (c, 0), 1.4, C["navy"]),
            ]
        rt.setStyle(TableStyle(style))
        story.append(rt)
        story.append(Spacer(1, 2))


def _statut(story, statut, texte):
    color, label = STATUS.get(statut, (C["grey"], esc(statut)))
    puce = Table([[Paragraph(f"<font color='#ffffff'>{label}</font>", ST["tl"])]],
                 colWidths=[32 * mm])
    puce.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    t = Table([[puce, Paragraph(esc(texte), ST["bb"])]],
              colWidths=[34 * mm, W - 34 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(t)
