"""Données : lecture et écriture du fichier JSON. Ce fichier ne connaît ni la fenêtre ni les règles."""

import json
import os
from pathlib import Path

FICHIER_CONTACTS = Path(__file__).parent / "contacts.json"


class FichierIllisible(Exception):
    """Le fichier existe mais son contenu n'est pas une liste de contacts."""


def est_un_contact(element):
    """Vrai si l'élément lu dans le fichier a bien la forme d'un contact."""
    return (
        isinstance(element, dict)
        and isinstance(element.get("nom"), str)
        and isinstance(element.get("telephone"), str)
    )


def charger_contacts(chemin=FICHIER_CONTACTS):
    """Retourne les contacts du fichier, ou une liste vide s'il n'existe pas encore."""
    try:
        with open(chemin, encoding="utf-8") as fichier:
            contacts = json.load(fichier)
    except FileNotFoundError:
        return []
    except ValueError as erreur:  # JSON invalide ou encodage incorrect
        raise FichierIllisible(f"{chemin} : {erreur}") from erreur

    if not isinstance(contacts, list) or not all(est_un_contact(c) for c in contacts):
        raise FichierIllisible(f"{chemin} : ce n'est pas une liste de contacts.")
    return contacts


def sauvegarder_contacts(contacts, chemin=FICHIER_CONTACTS):
    """Écrit d'abord un fichier temporaire, puis le met en place : une panne n'abîme pas l'ancien."""
    temporaire = f"{chemin}.tmp"
    with open(temporaire, "w", encoding="utf-8") as fichier:
        json.dump(contacts, fichier, ensure_ascii=False, indent=2)
    os.replace(temporaire, chemin)
