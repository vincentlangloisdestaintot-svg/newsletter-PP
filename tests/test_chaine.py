# -*- coding: utf-8 -*-
"""Tests de la chaîne hors appel API : contrôles qualité et rendus.

Le point critique testé ici : les contrôles doivent attraper un brief piégé.
Un contrôle qui ne détecte rien sur un texte fautif ne protège de rien.

    python -m tests.test_chaine
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from veille import dates_fr, render_pdf, render_text, validate          # noqa: E402
from veille.models import Collecte, DataPoint, Statut                   # noqa: E402

OK, KO = "\033[32mOK\033[0m", "\033[31mÉCHEC\033[0m"
resultats: list[bool] = []


def verifier(intitule: str, condition: bool, detail: str = "") -> None:
    resultats.append(condition)
    print(f"  [{OK if condition else KO}] {intitule}{'  — ' + detail if detail else ''}")


# --------------------------------------------------------------------------
def collecte_test() -> Collecte:
    """Collecte où l'OAT n'a PAS été confirmée — le piège du brief fautif."""
    points = {
        "oat_10a": DataPoint(
            cle="oat_10a", libelle="OAT 10 ans", unite="%",
            statut=Statut.NON_CONFIRME,
            note="Aucune source émettrice n'a répondu."),
        "bce_depot": DataPoint(
            cle="bce_depot", libelle="BCE — taux de facilité de dépôt",
            valeur=2.25, unite="%", emetteur="BCE",
            url="https://data.ecb.europa.eu/data/datasets/FM/FM.D.U2.EUR.4F.KR.DFR.LEV",
            date_obs=dt.date.today(), statut=Statut.CONFIRME),
        "cac40": DataPoint(
            cle="cac40", libelle="CAC 40", valeur=8301.85, unite="points",
            emetteur="Euronext Paris", date_obs=dt.date.today(),
            statut=Statut.CONFIRME, sources_convergentes=["Stooq", "Yahoo Finance"]),
    }
    return Collecte(date_run=dt.datetime.now(), points=points)


def _remplissage(mots: int, graine: str) -> str:
    """Texte neutre servant à atteindre une longueur, sans chiffre parasite."""
    base = (f"{graine} Le mécanisme est détaillé ici sans ajouter de donnée "
            "nouvelle, en précisant ce que l'agrégat mesure et ce qu'il ne "
            "mesure pas, ainsi que les réserves à conserver. ")
    sortie = base
    while len(sortie.split()) < mots:
        sortie += base
    return sortie


def brief_propre() -> dict:
    return {
        "date_titre": dates_fr.titre(dt.date.today()),
        "bloc1": {"valeur": "3,3 %",
                  "texte": "Indice des prix, estimation provisoire, définitif le 17 du mois.",
                  "developpe": "Indice des prix, estimation provisoire, définitif le 17 du mois. "
                               + _remplissage(200, "Sur le chiffre du jour."),
                  "sources": ["https://www.insee.fr/fr/statistiques"]},
        "bloc2": {"texte": "Le CAC 40 recule de 0,39 % sur la séance.",
                  "developpe": "Le CAC 40 recule de 0,39 % sur la séance. "
                               + _remplissage(300, "Sur les marchés actions."),
                  "sources": ["https://www.insee.fr/fr/statistiques"]},
        "bloc3": {"texte": "Le niveau de l'OAT 10 ans n'a pas pu être confirmé à la source ce matin.",
                  "developpe": "Le niveau de l'OAT 10 ans n'a pas pu être confirmé à la source ce matin. "
                               + _remplissage(400, "Sur les taux."),
                  "sources": ["https://www.aft.gouv.fr/fr"]},
        "bloc4": {"elements": [
            {"statut": "EN VIGUEUR",
             "texte": "Article 12 de la LFSS, publié et applicable depuis le 1er janvier.",
             "developpe": "Article 12 de la LFSS, publié et applicable depuis le 1er janvier. "
                          + _remplissage(200, "Sur ce texte en vigueur.")},
            {"statut": "EN DISCUSSION",
             "texte": "Le dépôt du projet serait prévu fin septembre ; aucune mesure arrêtée à ce stade.",
             "developpe": "Le dépôt du projet serait prévu fin septembre ; aucune mesure "
                          "arrêtée à ce stade. "
                          + _remplissage(200, "Sur ce texte en discussion, qui pourrait évoluer.")},
        ], "sources": ["https://www.legifrance.gouv.fr"]},
        "bloc5": {"tuiles": [{"label": "COLLECTE NETTE", "valeur": "4,7 Md€",
                              "contexte": "mois précédent"}],
                  "texte": "Le cumul reste supérieur à l'an passé. Angle d'usage : "
                           "situer le mois dans le cumul, sans extrapoler.",
                  "developpe": "Le cumul reste supérieur à l'an passé. Angle d'usage : "
                               "situer le mois dans le cumul, sans extrapoler. "
                               + _remplissage(400, "Sur l'épargne."),
                  "sources": ["https://www.franceassureurs.fr"]},
        "bloc6": {"format": "TECHNIQUE", "angle": "CSG 2026 par enveloppe",
                  "intro": "Répartition de la hausse de CSG selon l'enveloppe.",
                  "formulation": "« Les produits de ce contrat restent taxés à 17,2 % à ce jour. »",
                  "gardefou": "Ne dit rien du PER, non confirmé. Ne recommande aucun arbitrage.",
                  "developpe": "Répartition de la hausse de CSG selon l'enveloppe. "
                               + _remplissage(500, "Sur le point du jour."),
                  "sources": ["https://bofip.impots.gouv.fr"]},
        "stats": [{"label": "OAT 10 ANS", "valeur": "n.c.", "contexte": "non confirmé"},
                  {"label": "BCE DÉPÔT", "valeur": "2,25 %", "contexte": "inchangé"},
                  {"label": "CAC 40", "valeur": "8 301,85", "contexte": "-0,39 %"},
                  {"label": "DAX", "valeur": "n.c.", "contexte": "non confirmé"},
                  {"label": "SPREAD", "valeur": "n.c.", "contexte": "jambe manquante"},
                  {"label": "BRENT", "valeur": "n.c.", "contexte": "hors périmètre"},
                  {"label": "FED FUNDS", "valeur": "n.c.", "contexte": "non confirmé"},
                  {"label": "NOTE FRANCE", "valeur": "n.c.", "contexte": "non confirmé"}],
        "note_echeance": "Aucune échéance sous 48 heures.",
        "citation": {"texte": "« Le risque vient de ne pas savoir ce que l'on fait. »",
                     "attribution": "Warren Buffett, lettre aux actionnaires, 1993"},
        "chiffres_non_confirmes": ["OAT 10 ans", "Spread OAT/Bund"],
    }


def brief_piege() -> dict:
    b = brief_propre()
    # 1. publie un chiffre que la collecte n'a pas confirmé
    b["stats"][0] = {"label": "OAT 10 ANS", "valeur": "4,19 %", "contexte": "AFT"}
    # 2. qualification d'opportunité dans le bloc taux
    b["bloc3"]["texte"] = ("L'OAT à 4,19 % ouvre une fenêtre intéressante et "
                           "un point d'entrée à saisir.")
    # 3. recommandation d'investissement
    b["bloc5"]["texte"] = "Privilégiez les fonds en euros, il faut investir maintenant."
    # 4. texte en discussion rédigé comme acquis
    b["bloc4"]["elements"][1] = {"statut": "EN DISCUSSION",
                                 "texte": "Le PLF 2027 supprime l'abattement au 1er janvier."}
    # 5. source de presse au lieu de l'émetteur
    b["bloc2"]["sources"] = ["https://www.lesechos.fr/marches/article"]
    # 6. citation apocryphe
    b["citation"] = {"texte": "« Sois le changement que tu veux voir dans le monde. »",
                     "attribution": "Gandhi, 1913"}
    # 7. projection à l'indicatif futur
    b["bloc1"]["texte"] = "L'inflation continuera de progresser dans les prochains mois."
    # 8. chiffre présent dans le PDF mais absent de la version longue
    b["bloc5"]["texte"] = ("Collecte nette de 4,7 Md€ et encours de 2 174 Md€. "
                           + b["bloc5"]["texte"])
    b["bloc5"]["developpe"] = _remplissage(400, "Sur l'épargne, sans chiffre.")
    return b


def brief_sans_version_longue() -> dict:
    b = brief_propre()
    for nom in ("bloc1", "bloc2", "bloc3", "bloc5", "bloc6"):
        b[nom].pop("developpe", None)
    for el in b["bloc4"]["elements"]:
        el.pop("developpe", None)
    return b


# --------------------------------------------------------------------------
def main() -> int:
    c = collecte_test()

    print("\n1. Dates françaises sans locale système")
    verifier("format long", dates_fr.longue(dt.date(2026, 9, 3)) == "jeudi 3 septembre 2026",
             dates_fr.longue(dt.date(2026, 9, 3)))
    verifier("« 1er » uniquement le premier du mois",
             dates_fr.longue(dt.date(2026, 9, 1)).startswith("mardi 1er"))
    verifier("titre abrégé en majuscules",
             dates_fr.titre(dt.date(2026, 9, 3)) == "JEUDI 3 SEPT. 2026",
             dates_fr.titre(dt.date(2026, 9, 3)))

    print("\n2. Modèle de données")
    verifier("un point non confirmé n'est jamais publiable",
             not c.points["oat_10a"].publiable)
    verifier("rendu explicite du blanc assumé",
             c.points["oat_10a"].rendu() == "non confirmé à la source")
    verifier("en-tête de santé compté correctement",
             c.sante.startswith("2/3"), c.sante)

    print("\n3. Contrôles sur un brief conforme")
    constats = validate.controler(brief_propre(), c)
    bloquants = [x for x in constats if x.gravite is validate.Gravite.BLOQUANT]
    for x in constats:
        print(f"      · {x}")
    verifier("aucun constat bloquant", not bloquants, f"{len(bloquants)} bloquant(s)")

    print("\n4. Contrôles sur un brief piégé — chaque piège doit être attrapé")
    constats = validate.controler(brief_piege(), c)
    regles = {x.regle for x in constats}
    for x in constats:
        print(f"      · {x}")
    verifier("chiffre non confirmé publié", "chiffre non confirmé publié" in regles)
    verifier("qualification d'opportunité", "qualification d'opportunité de marché" in regles)
    verifier("recommandation d'investissement", "recommandation d'investissement" in regles)
    verifier("texte en discussion présenté comme acquis",
             "texte en discussion présenté comme acquis" in regles)
    verifier("source non émettrice", "source non émettrice" in regles)
    verifier("citation apocryphe", "citation apocryphe" in regles)
    verifier("projection non conditionnelle",
             "affirmation prospective non conditionnelle" in regles)
    verifier("chiffre du PDF absent du mail",
             "chiffre présent dans le PDF mais absent du mail" in regles)

    print("\n5. Cohérence des deux niveaux de lecture")
    regles_sans = {x.regle for x in validate.controler(brief_sans_version_longue(), c)}
    verifier("version longue absente détectée", "version longue absente" in regles_sans)

    b_ok = brief_propre()
    mots_dev = len(validate._developpe(b_ok).split())
    mots_con = len(validate._condense(b_ok).split())
    verifier("le mail est plus long que le PDF", mots_dev > mots_con,
             f"{mots_dev} mots contre {mots_con}")

    print("\n5 bis. Rendus")
    b, sante = brief_propre(), validate.resume([], c)
    md = render_text.markdown(b, sante, [])
    verifier("markdown : six blocs présents",
             all(f"## {i}." in md for i in range(1, 7)))
    verifier("markdown : blanc assumé visible",
             "non confirmé à la source" in md.lower())
    verifier("markdown : rend bien la version longue",
             "Sur les taux." in md)

    html = render_text.email_html(b, sante, ["contrôle de démonstration"])
    verifier("html : document complet", html.strip().startswith("<!doctype html>"))
    verifier("html : bandeau de contrôle affiché", "contrôle de démonstration" in html)
    html_plat = " ".join(html.lower().split())
    verifier("html : mention de conformité en pied",
             "ne constitue ni une recommandation" in html_plat)

    sortie = Path("/tmp/test_veille.pdf")
    try:
        render_pdf.construire(b, sante, ["contrôle de démonstration"], sortie)
        taille = sortie.stat().st_size
        verifier("pdf : fichier produit", taille > 5000, f"{taille} octets")
    except Exception as exc:                                   # noqa: BLE001
        verifier("pdf : fichier produit", False, repr(exc))

    print("\n6. Échappement du texte modèle dans le PDF")
    dangereux = {"date_titre": "TEST", **b,
                 "bloc2": {"texte": "Écart & <balise> \"guillemets\"",
                           "sources": ["https://www.insee.fr"]}}
    try:
        render_pdf.construire(dangereux, sante, [], Path("/tmp/test_echap.pdf"))
        verifier("caractères spéciaux sans casse", True)
    except Exception as exc:                                   # noqa: BLE001
        verifier("caractères spéciaux sans casse", False, repr(exc))

    total, reussis = len(resultats), sum(resultats)
    print(f"\n=== {reussis}/{total} vérifications passent ===\n")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
