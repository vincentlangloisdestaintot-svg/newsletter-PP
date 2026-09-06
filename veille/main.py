# -*- coding: utf-8 -*-
"""Point d'entrée.

Trois modes, selon la façon dont la partie éditoriale est produite :

    collecte     couche données seule → écrit donnees.json, schema.json, brief.md
                 (l'instruction de rédaction). Aucun appel modèle.

    finalise     reprend un brief.json rédigé ailleurs → contrôle, rendus, envoi,
                 archive. Aucun appel modèle.

    complet      collecte + rédaction par l'API Anthropic + finalisation, en un
                 seul processus. Nécessite ANTHROPIC_API_KEY, facturée à l'usage.

Le découpage collecte / finalise existe pour que la rédaction puisse être faite
par `anthropics/claude-code-action` avec un CLAUDE_CODE_OAUTH_TOKEN, c'est-à-dire
sur un abonnement Claude plutôt qu'en facturation API.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import archive, collect, config, dates_fr, deliver, render_pdf, render_text, validate
from .models import Collecte, DataPoint, Echeance, Statut
from .schema import BRIEF_SCHEMA

log = logging.getLogger("veille")

TRAVAIL = Path("/tmp/veille")


def _journalisation(verbeux: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbeux else logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
        datefmt="%H:%M:%S", stream=sys.stdout)


# ---------------------------------------------------------------------------
# Sérialisation de la collecte, pour la passer d'une étape à l'autre
# ---------------------------------------------------------------------------
def _recharger(donnees: dict) -> Collecte:
    import datetime as dt

    points: dict[str, DataPoint] = {}
    for cle, d in donnees.get("points", {}).items():
        p = DataPoint(cle=d["cle"], libelle=d["libelle"], valeur=d.get("valeur"),
                      unite=d.get("unite", ""), emetteur=d.get("emetteur", ""),
                      url=d.get("url", ""), statut=Statut(d["statut"]),
                      provisoire=d.get("provisoire", False),
                      variation=d.get("variation"),
                      unite_variation=d.get("unite_variation", ""),
                      sources_convergentes=d.get("sources_convergentes", []),
                      note=d.get("note", ""))
        if d.get("date_obs"):
            p.date_obs = dt.date.fromisoformat(d["date_obs"])
        points[cle] = p

    echeances = [Echeance(dt.date.fromisoformat(e["date"]), e["emetteur"],
                          e["intitule"], e.get("url", ""))
                 for e in donnees.get("echeances", [])]
    return Collecte(date_run=dt.datetime.fromisoformat(donnees["date_run"]),
                    points=points, echeances=echeances)


# ---------------------------------------------------------------------------
# Étape 1 — collecte
# ---------------------------------------------------------------------------
def etape_collecte(dossier: Path) -> int:
    jour = dates_fr.aujourdhui_paris()
    log.info("=== Collecte — %s ===", dates_fr.longue(jour))

    c = collect.collecter()
    dossier.mkdir(parents=True, exist_ok=True)

    (dossier / "donnees.json").write_text(
        json.dumps(c.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (dossier / "schema.json").write_text(
        json.dumps(BRIEF_SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8")

    instruction = _instruction(c, jour)
    (dossier / "instruction.md").write_text(instruction, encoding="utf-8")

    log.info("Écrits dans %s : donnees.json, schema.json, instruction.md", dossier)
    log.info("Santé de la collecte : %s", c.sante)
    return 0


def _instruction(c: Collecte, jour) -> str:
    """Instruction de rédaction, lisible par un agent comme par un humain."""
    ech = ("\n".join(f"- {e.date.isoformat()} ({e.imminence}) — {e.emetteur} : "
                     f"{e.intitule} [{e.url}]" for e in c.echeances)
           or "Aucune échéance récurrente aujourd'hui ni dans les 48 heures.")

    return f"""# Rédaction du brief — {dates_fr.longue(jour)}

## Ce que tu dois produire

Un fichier `brief.json` dans ce même dossier, strictement conforme à
`schema.json`. Rien d'autre. Pas de texte libre, pas de commentaire.

## Autorité éditoriale

`charte/charte-editoriale.md`, à la racine du dépôt. Lis-la intégralement
avant d'écrire. Elle prime sur toute habitude de rédaction.

## Données déjà collectées

`donnees.json`, dans ce dossier. Ce sont tes seules sources pour les chiffres
de marché. Ne va pas en chercher d'autres, ne les recalcule pas, ne complète
pas un champ non confirmé par une valeur trouvée ailleurs.

Un point au statut `non confirmé`, `divergent` ou `périmé` ne se publie jamais
comme un chiffre. Dans les tuiles il porte `n.c.`. Dans le texte, écris
explicitement que l'information n'a pas pu être confirmée à la source, en
reprenant la note du point. C'est un blanc assumé, pas un manque à combler.

État de la collecte : **{c.sante}**.

Non confirmés ce matin :
{chr(10).join(f"- {p.libelle} ({p.statut.value}) : {p.note.strip()}" for p in c.manquants) or "- aucun"}

## Échéances du calendrier

{ech}

## Anti-répétition

{archive.contraintes(jour)}

## Deux niveaux de lecture

Chaque bloc s'écrit deux fois, sur les mêmes faits et les mêmes sources
(charte, section 4 bis) :

- `texte` — le condensé, qui part dans le PDF deux pages. 1 000 à 1 300 mots
  au total sur l'ensemble des blocs.
- `developpe` — la version longue, qui part dans le corps de l'email. 2 000 à
  2 500 mots au total.

Le condensé est une **réduction** du développé, jamais une rédaction parallèle.
Écris le développé d'abord, puis réduis-le. Aucun chiffre ne peut figurer dans
le condensé sans figurer dans le développé — c'est vérifié mécaniquement avant
envoi.

Ce que le développé ajoute : le mécanisme derrière le chiffre, ce que l'agrégat
ne mesure pas, les données qui vont en sens inverse, le périmètre exact d'un
texte fiscal, les cas où un raisonnement ne s'applique pas. Du contenu, pas du
délayage. Un jour creux produit un brief court dans les deux versions : ne
remplis jamais pour atteindre une longueur.

## Ton travail de recherche

Il porte sur les blocs 4, 5 et 6 — fiscalité, réglementaire, assurance vie,
épargne, point du jour. Applique la règle d'or : repérer le signal, remonter à
la source primaire, réécrire intégralement. L'URL citée est celle de l'émetteur
(legifrance.gouv.fr, bofip.impots.gouv.fr, franceassureurs.fr, insee.fr,
amf-france.org), jamais celle d'un article de presse. Un chiffre dont tu n'as
pas retrouvé la page émettrice ne se publie pas.

Nous sommes le {dates_fr.longue(jour)}. Le champ `date_titre` vaut
`{dates_fr.titre(jour)}`.
"""


# ---------------------------------------------------------------------------
# Étape 2 — finalisation
# ---------------------------------------------------------------------------
def etape_finalise(dossier: Path, envoyer: bool) -> int:
    jour = dates_fr.aujourdhui_paris()

    chemin_brief = dossier / "brief.json"
    chemin_donnees = dossier / "donnees.json"
    for f in (chemin_brief, chemin_donnees):
        if not f.exists():
            log.error("Fichier manquant : %s", f)
            return 2

    try:
        brief = json.loads(chemin_brief.read_text(encoding="utf-8"))
    except ValueError as exc:
        log.error("brief.json illisible : %s", exc)
        return 3

    manquants = [c for c in BRIEF_SCHEMA["required"] if c not in brief]
    if manquants:
        log.error("brief.json incomplet, champs absents : %s", ", ".join(manquants))
        return 3

    collecte = _recharger(json.loads(chemin_donnees.read_text(encoding="utf-8")))
    brief.setdefault("date_titre", dates_fr.titre(jour))

    return _livrer(brief, collecte, jour, envoyer, dossier)


# ---------------------------------------------------------------------------
# Mode complet (API)
# ---------------------------------------------------------------------------
def etape_complet(envoyer: bool) -> int:
    from . import editorial

    problemes = config.verifier(strict=envoyer)
    if problemes:
        for p in problemes:
            log.error("Configuration : %s", p)
        return 2

    jour = dates_fr.aujourdhui_paris()
    log.info("=== Veille patrimoniale — %s ===", dates_fr.longue(jour))

    collecte = collect.collecter()
    try:
        brief = editorial.rediger(collecte, dates_fr.longue(jour),
                                  archive.contraintes(jour))
    except Exception as exc:                                   # noqa: BLE001
        log.exception("Rédaction impossible : %s", exc)
        return 3

    brief.setdefault("date_titre", dates_fr.titre(jour))
    return _livrer(brief, collecte, jour, envoyer, TRAVAIL)


# ---------------------------------------------------------------------------
def _livrer(brief: dict, collecte: Collecte, jour, envoyer: bool,
            dossier: Path) -> int:
    constats = validate.controler(brief, collecte)
    sante = validate.resume(constats, collecte)
    bloquants = [str(c) for c in constats if c.gravite is validate.Gravite.BLOQUANT]
    for c in constats:
        log.warning("Contrôle : %s", c)
    log.info("Santé : %s", sante)

    markdown = render_text.markdown(brief, sante, bloquants)
    html = render_text.email_html(brief, sante, bloquants)

    pdf: Path | None = None
    try:
        pdf = render_pdf.construire(
            brief, sante, bloquants,
            dossier / f"Veille_patrimoniale_{jour.isoformat()}.pdf")
        log.info("PDF produit : %s", pdf)
    except Exception as exc:                                   # noqa: BLE001
        log.exception("PDF non produit (%s) — l'email partira sans pièce jointe.", exc)

    envoi_ok = True
    if envoyer:
        marque = " ⚠" if bloquants else ""
        envoi_ok = deliver.envoyer(
            sujet=f"Veille patrimoniale — {dates_fr.titre(jour).title()}{marque}",
            corps_html=html, corps_texte=markdown, pieces=[pdf] if pdf else [])
    else:
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "apercu.html").write_text(html, encoding="utf-8")
        (dossier / "apercu.md").write_text(markdown, encoding="utf-8")
        log.info("Mode sans envoi — aperçus écrits dans %s", dossier)

    archive.enregistrer(jour, brief, collecte.to_dict(), markdown, pdf, bloquants)
    return 0 if envoi_ok else 4


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Veille patrimoniale quotidienne")
    ap.add_argument("etape", nargs="?", default="complet",
                    choices=["collecte", "finalise", "complet"])
    ap.add_argument("--dossier", default=str(TRAVAIL),
                    help="dossier de travail partagé entre les étapes")
    ap.add_argument("--sans-envoi", action="store_true")
    ap.add_argument("-v", "--verbeux", action="store_true")
    a = ap.parse_args()

    _journalisation(a.verbeux)
    dossier = Path(a.dossier)

    if a.etape == "collecte":
        return etape_collecte(dossier)
    if a.etape == "finalise":
        return etape_finalise(dossier, envoyer=not a.sans_envoi)
    return etape_complet(envoyer=not a.sans_envoi)


if __name__ == "__main__":
    raise SystemExit(main())
