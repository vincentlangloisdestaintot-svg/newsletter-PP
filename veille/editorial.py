# -*- coding: utf-8 -*-
"""Couche éditoriale : appel API Claude, charte en instruction, données en entrée.

Le modèle ne va pas chercher les chiffres de marché — la couche données les lui
apporte déjà confirmés ou explicitement non confirmés. Il travaille sur ce qui
demande du jugement : fiscalité, réglementaire, assurance vie, point du jour.
"""
from __future__ import annotations

import json
import logging

from anthropic import Anthropic

from . import config
from .models import Collecte
from .schema import OUTIL_RENDU

log = logging.getLogger(__name__)

MAX_TOURS = 12

INSTRUCTION = """Tu produis le brief de veille patrimoniale du jour.

La charte éditoriale ci-dessous fait autorité sur tout. Elle prime sur toute \
habitude de rédaction et sur toute considération de style.

<charte>
{charte}
</charte>

Voici les données de marché déjà collectées ce matin par la couche déterministe \
du système, avec leur statut de vérification. Elles sont ta seule source pour \
les chiffres de marché : ne va pas en chercher d'autres, ne les recalcule pas, \
ne complète pas un champ non confirmé par une valeur trouvée ailleurs.

<donnees_collectees>
{donnees}
</donnees_collectees>

Un point au statut « non confirmé », « divergent » ou « périmé » ne se publie \
jamais comme un chiffre. Dans les tuiles il porte « n.c. ». Dans le texte, tu \
écris explicitement que l'information n'a pas pu être confirmée à la source, en \
reprenant la note qui accompagne le point. C'est un blanc assumé, pas un manque \
à combler.

<echeances_du_calendrier>
{echeances}
</echeances_du_calendrier>

<anti_repetition>
{anti_repetition}
</anti_repetition>

Chaque bloc s'écrit à deux niveaux, sur les mêmes faits et les mêmes sources \
(charte, section 4 bis) : `texte`, le condensé du PDF deux pages (1 000 à \
1 300 mots au total), et `developpe`, la version longue du corps de l'email \
(2 000 à 2 500 mots au total). Écris le développé d'abord, puis réduis-le : le \
condensé est une réduction, jamais une rédaction parallèle. Aucun chiffre ne \
peut figurer dans le condensé sans figurer dans le développé. Un jour creux \
produit un brief court dans les deux versions — ne remplis jamais pour \
atteindre une longueur.

Ton travail de recherche porte sur les blocs 4, 5 et 6 — fiscalité, \
réglementaire, assurance vie, épargne, et le point du jour. Pour ceux-là, \
applique la règle d'or : repérer le signal, remonter à la source primaire, \
réécrire intégralement. L'URL que tu cites est celle de l'émetteur \
(legifrance.gouv.fr, bofip.impots.gouv.fr, franceassureurs.fr, insee.fr, \
amf-france.org), jamais celle d'un article de presse. Si tu ne retrouves pas la \
page émettrice d'un chiffre, tu ne le publies pas.

Aujourd'hui, nous sommes le {date_longue}.

Quand tout est vérifié, appelle l'outil `rendre_brief` une seule fois avec le \
brief complet. N'écris pas le brief en texte libre : le seul livrable est \
l'appel d'outil."""


def _resume_donnees(c: Collecte) -> str:
    lignes = []
    for p in c.points.values():
        lignes.append(json.dumps({
            "libelle": p.libelle,
            "valeur": p.valeur,
            "unite": p.unite,
            "variation": p.variation,
            "unite_variation": p.unite_variation,
            "emetteur": p.emetteur,
            "url": p.url,
            "date_observation": p.date_obs.isoformat() if p.date_obs else None,
            "statut": p.statut.value,
            "note": p.note,
            "sources_convergentes": p.sources_convergentes,
        }, ensure_ascii=False))
    return "\n".join(lignes)


def _resume_echeances(c: Collecte) -> str:
    if not c.echeances:
        return "Aucune échéance récurrente ne tombe aujourd'hui ni dans les 48 heures."
    return "\n".join(
        f"- {e.date.isoformat()} ({e.imminence}) — {e.emetteur} : {e.intitule} [{e.url}]"
        for e in c.echeances)


def rediger(collecte: Collecte, date_longue: str, anti_repetition: str) -> dict:
    """Rend le brief structuré. Lève RuntimeError si le modèle ne le produit pas."""
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY manquante.")

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    charte = config.CHARTE.read_text(encoding="utf-8")

    instruction = INSTRUCTION.format(
        charte=charte,
        donnees=_resume_donnees(collecte),
        echeances=_resume_echeances(collecte),
        anti_repetition=anti_repetition,
        date_longue=date_longue,
    )

    messages = [{"role": "user", "content": "Produis le brief du jour."}]
    outils = [
        {"type": "web_search_20250305", "name": "web_search",
         "max_uses": config.MAX_RECHERCHES},
        OUTIL_RENDU,
    ]

    for tour in range(1, MAX_TOURS + 1):
        reponse = client.messages.create(
            model=config.MODELE,
            max_tokens=config.MAX_TOKENS,
            system=instruction,
            messages=messages,
            tools=outils,
        )
        log.info("Tour %s — stop_reason=%s", tour, reponse.stop_reason)

        for bloc in reponse.content:
            if getattr(bloc, "type", None) == "tool_use" and bloc.name == "rendre_brief":
                log.info("Brief structuré reçu au tour %s.", tour)
                return dict(bloc.input)

        if reponse.stop_reason != "tool_use":
            messages.append({"role": "assistant", "content": reponse.content})
            messages.append({"role": "user", "content":
                             "Appelle maintenant `rendre_brief` avec le brief complet."})
            continue

        # Les recherches web sont exécutées côté serveur : on renvoie le tour tel quel.
        messages.append({"role": "assistant", "content": reponse.content})
        messages.append({"role": "user", "content":
                         "Continue. Quand la vérification est terminée, appelle "
                         "`rendre_brief`."})

    raise RuntimeError(
        f"Le modèle n'a pas produit d'appel `rendre_brief` en {MAX_TOURS} tours.")
