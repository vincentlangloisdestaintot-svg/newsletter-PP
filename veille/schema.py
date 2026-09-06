# -*- coding: utf-8 -*-
"""Schéma unique du brief, à deux niveaux de lecture.

Chaque bloc porte deux écritures des mêmes faits :

    texte      condensé — ce qui part dans le PDF deux pages.
    developpe  version longue — ce qui part dans le corps de l'email.

Les deux sortent du même JSON, écrites au même moment, sur les mêmes sources.
C'est ce qui garantit qu'elles ne divergent pas : le condensé est une réduction
du développé, jamais une rédaction parallèle.
"""

STATUTS_REGLEMENTAIRES = ["EN VIGUEUR", "VOTE NON APPLICABLE", "EN DISCUSSION"]

TUILE = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "description": "Intitulé court, en majuscules."},
        "valeur": {"type": "string", "description": "Valeur formatée, ou « n.c. » si non confirmée."},
        "contexte": {"type": "string", "description": "Variation, date de séance, émetteur — très court."},
    },
    "required": ["label", "valeur", "contexte"],
}

SOURCES = {"type": "array", "items": {"type": "string"},
           "description": "URL(s) de l'émetteur, jamais un article de presse."}


def _bloc(nom: str, condense: str, developpe: str, extra: dict | None = None) -> dict:
    props = {
        "texte": {"type": "string", "description": condense},
        "developpe": {"type": "string", "description": developpe},
        "sources": SOURCES,
    }
    if extra:
        props.update(extra)
    return {
        "type": "object",
        "description": nom,
        "properties": props,
        "required": list(props),
    }


BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "date_titre": {
            "type": "string",
            "description": "Ex. « JEUDI 3 SEPT. 2026 ». Majuscules, mois abrégé.",
        },

        "bloc1": _bloc(
            "Le chiffre du jour : un seul chiffre, celui qui structure la journée.",
            "Condensé, 3 à 5 lignes : émetteur, date, statut provisoire ou définitif "
            "avec la date du définitif, variation, et ce que ça déclenche.",
            "Version longue, 150 à 250 mots : d'où vient ce chiffre, comment il se "
            "compare aux périodes précédentes, ce qu'il mesure exactement et ce "
            "qu'il ne mesure pas, et ce qu'il déclenche dans la journée.",
            {"valeur": {"type": "string", "description": "Le chiffre seul, ex. « 3,3 % »."}},
        ),

        "bloc2": _bloc(
            "Marchés actions et matières premières. Finit par la lecture patrimoniale.",
            "Condensé, 3 à 5 lignes.",
            "Version longue, 250 à 400 mots : niveaux, mouvements et ce qui les "
            "explique, divergences entre sources le cas échéant, puis la lecture "
            "patrimoniale développée.",
        ),

        "bloc3": _bloc(
            "Taux et obligataire. Seuil de matérialité appliqué. Aucune "
            "qualification d'opportunité, dans aucune des deux versions.",
            "Condensé, 5 à 8 lignes.",
            "Version longue, 350 à 500 mots : niveaux et variations, forme de "
            "courbe, politique monétaire et prochaines échéances, adjudications, "
            "notation. Ce que le seuil de matérialité fait écarter est dit en une "
            "ligne plutôt que développé.",
        ),

        "bloc4": {
            "type": "object",
            "description": "Fiscalité et réglementaire. Chaque élément porte l'un des trois statuts.",
            "properties": {
                "elements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "statut": {"type": "string", "enum": STATUTS_REGLEMENTAIRES},
                            "texte": {"type": "string", "description": "Condensé : référence exacte, date, et en une phrase ce que ça change."},
                            "developpe": {"type": "string", "description": "Version longue : le mécanisme, le périmètre exact, ce qui reste incertain, et l'effet concret pour un client type."},
                        },
                        "required": ["statut", "texte", "developpe"],
                    },
                },
                "sources": SOURCES,
            },
            "required": ["elements", "sources"],
        },

        "bloc5": _bloc(
            "Assurance vie, retraite, épargne. Un encours n'est pas un flux.",
            "Condensé, 6 à 10 lignes, terminé par l'angle d'usage.",
            "Version longue, 350 à 500 mots : les agrégats et ce que chacun mesure "
            "réellement, les données qui vont en sens inverse, puis l'angle d'usage "
            "développé — ce que ces chiffres permettent de dire ou de désamorcer en "
            "rendez-vous, sans recommander de support.",
            {"tuiles": {"type": "array", "items": TUILE, "maxItems": 4}},
        ),

        "bloc6": {
            "type": "object",
            "description": "Le point du jour. La formulation ne doit rien affirmer que le garde-fou interdise.",
            "properties": {
                "format": {"type": "string", "enum": ["ARGUMENT", "TECHNIQUE"]},
                "angle": {"type": "string", "description": "Résumé de l'angle en 5 mots max, pour l'anti-répétition."},
                "intro": {"type": "string", "description": "Condensé de la mise en situation, pour le PDF."},
                "formulation": {"type": "string", "description": "Formulation prête à l'emploi, entre guillemets. Identique dans les deux versions."},
                "gardefou": {"type": "string", "description": "Condensé du garde-fou, pour le PDF."},
                "developpe": {"type": "string", "description": "Version longue, 400 à 600 mots : le raisonnement complet, la référence exacte, les cas où il ne s'applique pas, et le garde-fou détaillé."},
                "sources": SOURCES,
            },
            "required": ["format", "angle", "intro", "formulation", "gardefou",
                         "developpe", "sources"],
        },

        "stats": {
            "type": "array",
            "description": "Exactement 8 tuiles de chiffres clés. Toute donnée non confirmée porte « n.c. » en valeur.",
            "items": TUILE,
            "minItems": 8,
            "maxItems": 8,
        },
        "note_echeance": {
            "type": "string",
            "description": "Échéance du calendrier tombant aujourd'hui ou sous 48 h, plus le garde-fou du bloc taux.",
        },
        "citation": {
            "type": "object",
            "properties": {
                "texte": {"type": "string"},
                "attribution": {"type": "string", "description": "Auteur, ouvrage ou discours, date. Vide si phrase originale."},
            },
            "required": ["texte", "attribution"],
        },
        "chiffres_non_confirmes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Liste explicite de ce qui n'a pas pu être confirmé à la source ce matin.",
        },
    },
    "required": ["date_titre", "bloc1", "bloc2", "bloc3", "bloc4", "bloc5",
                 "bloc6", "stats", "note_echeance", "citation",
                 "chiffres_non_confirmes"],
}

OUTIL_RENDU = {
    "name": "rendre_brief",
    "description": ("Rend le brief du jour, complet et vérifié, dans ses deux "
                    "niveaux de lecture. À appeler une seule fois, en dernier, "
                    "après toutes les recherches."),
    "input_schema": BRIEF_SCHEMA,
}
