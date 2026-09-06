# -*- coding: utf-8 -*-
"""Aperçu de la mise en page, sans appel API.

Toutes les valeurs sont fictives et signalées comme telles : cet aperçu sert à
juger la maquette, jamais à être lu comme une veille. Aucun chiffre n'y est
présenté comme réel.

    python -m tests.apercu_mise_en_page
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from veille import dates_fr, render_pdf, render_text                    # noqa: E402

FICTIF = "valeur fictive"

BRIEF = {
    "date_titre": dates_fr.titre(dt.date.today()),
    "bloc1": {
        "valeur": "0,0 %",
        "texte": ("APERÇU DE MISE EN PAGE — toutes les valeurs de ce document "
                  "sont fictives. Dans une édition réelle, ce bloc porte un seul "
                  "chiffre, son émetteur, sa date, son statut provisoire ou "
                  "définitif avec la date du définitif, et en une phrase ce que "
                  "ce chiffre déclenche dans la journée."),
        "sources": ["https://www.insee.fr/fr/statistiques"],
    },
    "bloc2": {
        "texte": ("Emplacement du commentaire actions et matières premières : "
                  "indices européens à la clôture, indices américains à leur "
                  "clôture de la veille, change et matières premières si "
                  "mouvement significatif. Le bloc se termine toujours par la "
                  "lecture patrimoniale, jamais par le commentaire boursier."),
        "sources": ["https://www.insee.fr/fr/statistiques"],
    },
    "bloc3": {
        "texte": ("Emplacement du bloc taux : OAT 10 ans, spread OAT/Bund et "
                  "position dans la fourchette annuelle, forme de courbe, Bund "
                  "et Treasury, taux directeurs et dates des prochaines "
                  "réunions, notation souveraine, adjudications de la semaine. "
                  "Le seuil de matérialité s'applique : sous 5 pb sur l'OAT et "
                  "3 pb sur le spread, une ligne de niveau et on passe. Ce bloc "
                  "décrit des niveaux, il ne qualifie aucun moment de marché."),
        "sources": ["https://www.aft.gouv.fr/fr"],
    },
    "bloc4": {
        "elements": [
            {"statut": "EN VIGUEUR",
             "texte": "Emplacement d'un texte publié et applicable : référence "
                      "exacte, date, et en une phrase ce que ça change."},
            {"statut": "VOTE NON APPLICABLE",
             "texte": "Emplacement d'un texte voté dont l'entrée en vigueur est "
                      "différée : la date d'application est obligatoire, à "
                      "compter du 31 décembre de l'exercice concerné."},
            {"statut": "EN DISCUSSION",
             "texte": "Emplacement d'un texte en cours de navette : le "
                      "conditionnel serait obligatoire et aucune mesure ne "
                      "pourrait être présentée comme arrêtée à ce stade."},
        ],
        "sources": ["https://www.legifrance.gouv.fr"],
    },
    "bloc5": {
        "tuiles": [
            {"label": "COTISATIONS", "valeur": "n.c.", "contexte": FICTIF},
            {"label": "COLLECTE NETTE", "valeur": "n.c.", "contexte": FICTIF},
            {"label": "CUMUL ANNUEL", "valeur": "n.c.", "contexte": FICTIF},
            {"label": "ENCOURS", "valeur": "n.c.", "contexte": "stock, pas un flux"},
        ],
        "texte": ("Emplacement du bloc épargne : collecte, encours, taux servis, "
                  "épargne réglementée. Un encours n'est pas un flux et des "
                  "cotisations ne sont pas une collecte nette : la grandeur "
                  "citée est celle qui mesure réellement le mouvement commenté. "
                  "Angle d'usage : ce que le chiffre permet de dire ou de "
                  "désamorcer en rendez-vous, sans recommander de support."),
        "sources": ["https://www.franceassureurs.fr"],
    },
    "bloc6": {
        "format": "TECHNIQUE",
        "angle": "aperçu de maquette",
        "intro": ("Emplacement du point du jour. En format technique : un point "
                  "de mécanique fiscale, réglementaire ou produit, avec sa "
                  "référence exacte. En format argument : un raisonnement "
                  "utilisable en rendez-vous, avec sa source opposable."),
        "formulation": ("« Emplacement de la formulation prête à l'emploi, qui "
                        "n'affirme jamais ce que le garde-fou placé juste après "
                        "vient interdire. »"),
        "gardefou": ("Garde-fou : ce que la formulation ne dit pas, ce qu'elle "
                     "ne couvre pas, et le rappel qu'aucun arbitrage n'est "
                     "recommandé."),
        "sources": ["https://bofip.impots.gouv.fr"],
    },
    "stats": [
        {"label": "OAT 10 ANS", "valeur": "n.c.", "contexte": FICTIF},
        {"label": "SPREAD OAT/BUND", "valeur": "n.c.", "contexte": FICTIF},
        {"label": "BUND 10 ANS", "valeur": "n.c.", "contexte": FICTIF},
        {"label": "TREASURY 10 ANS", "valeur": "n.c.", "contexte": FICTIF},
        {"label": "CAC 40", "valeur": "n.c.", "contexte": FICTIF},
        {"label": "S&P 500", "valeur": "n.c.", "contexte": FICTIF},
        {"label": "BCE DÉPÔT", "valeur": "n.c.", "contexte": FICTIF},
        {"label": "FED FUNDS", "valeur": "n.c.", "contexte": FICTIF},
    ],
    "note_echeance": ("Emplacement de l'échéance du calendrier tombant "
                      "aujourd'hui ou dans les 48 heures, suivie du garde-fou "
                      "du bloc taux."),
    "citation": {
        "texte": "« Emplacement de la ligne de clôture : une seule phrase. »",
        "attribution": "Citation vérifiée et datée, ou phrase originale",
    },
    "chiffres_non_confirmes": [
        "Aperçu de maquette : aucune donnée réelle n'a été collectée."],
}

SANTE = "aperçu de mise en page — 0/8 chiffres confirmés, par construction"
CONSTATS = ["Document de démonstration : toutes les valeurs sont fictives et "
            "aucun chiffre n'y est publié."]

RALLONGE = (
    "\n\nDans une édition réelle, c'est ici que la version longue se distingue "
    "du PDF : elle développe le mécanisme derrière le chiffre, précise ce que "
    "l'agrégat mesure et ce qu'il ne mesure pas, mentionne les données qui vont "
    "en sens inverse, et détaille le périmètre exact des textes cités."
    "\n\nLe PDF joint reprend les mêmes faits et les mêmes sources, réduits à "
    "l'essentiel sur deux pages. Aucun chiffre ne peut figurer dans le PDF sans "
    "figurer ici — c'est vérifié mécaniquement avant chaque envoi.")


def _poser_versions_longues(brief: dict) -> dict:
    """L'aperçu montre les deux niveaux : on dérive le développé du condensé."""
    for nom in ("bloc1", "bloc2", "bloc3", "bloc5"):
        brief[nom]["developpe"] = brief[nom]["texte"] + RALLONGE
    for el in brief["bloc4"]["elements"]:
        el["developpe"] = el["texte"] + RALLONGE
    brief["bloc6"]["developpe"] = brief["bloc6"]["intro"] + RALLONGE
    return brief


def main() -> int:
    _poser_versions_longues(BRIEF)
    sortie = Path("/tmp")
    pdf = render_pdf.construire(BRIEF, SANTE, CONSTATS,
                                sortie / "apercu_veille_patrimoniale.pdf")
    html = render_text.email_html(BRIEF, SANTE, CONSTATS)
    (sortie / "apercu_email.html").write_text(html, encoding="utf-8")
    md = render_text.markdown(BRIEF, SANTE, CONSTATS)
    (sortie / "apercu_brief.md").write_text(md, encoding="utf-8")
    print(f"PDF      : {pdf}")
    print(f"Email    : {sortie / 'apercu_email.html'}")
    print(f"Markdown : {sortie / 'apercu_brief.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
