"""Logique : les règles d'un contact. Ce fichier ne connaît ni la fenêtre ni le fichier JSON.

Un contact est un dictionnaire : {"nom", "telephone"}.
"""

import re
import unicodedata

CHIFFRES_MIN = 3  # les numéros courts existent, comme le 112
CHIFFRES_MAX = 15  # la limite internationale
LETTRES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class ContactInvalide(ValueError):
    """Une saisie refusée. `champ` indique le champ à corriger : "nom" ou "telephone"."""

    def __init__(self, message, champ):
        super().__init__(message)
        self.champ = champ


def garder_chiffres(telephone):
    """Retourne seulement les chiffres : "06 12-34" donne "061234"."""
    return "".join(caractere for caractere in telephone if caractere in "0123456789")


def creer_contact(nom, telephone):
    """Nettoie et vérifie la saisie, puis retourne le contact."""
    nom = " ".join(nom.split())
    telephone = " ".join(telephone.split())

    if not nom:
        raise ContactInvalide("Saisissez un nom.", "nom")
    if not telephone:
        raise ContactInvalide("Saisissez un numéro de téléphone.", "telephone")
    if not re.fullmatch(r"\+?[0-9 .()-]+", telephone):
        raise ContactInvalide(
            "Le numéro ne peut contenir que des chiffres, des espaces et + . ( ) -", "telephone"
        )
    if not CHIFFRES_MIN <= len(garder_chiffres(telephone)) <= CHIFFRES_MAX:
        raise ContactInvalide(
            f"Le numéro doit contenir de {CHIFFRES_MIN} à {CHIFFRES_MAX} chiffres.", "telephone"
        )
    return {"nom": nom, "telephone": telephone}


def est_en_double(contacts, contact):
    """Vrai si le même nom existe déjà avec le même numéro, même écrit autrement."""
    return any(
        existant["nom"].casefold() == contact["nom"].casefold()
        and garder_chiffres(existant["telephone"]) == garder_chiffres(contact["telephone"])
        for existant in contacts
    )


def sans_accents(texte):
    """Retourne le texte en minuscules et sans accents : "Émile" donne "emile"."""
    decompose = unicodedata.normalize("NFD", texte.casefold())
    return "".join(caractere for caractere in decompose if not unicodedata.combining(caractere))


def cle_de_tri(contact):
    """Retourne la clé de l'ordre alphabétique, pour classer « Émile » avec les E et non après Z."""
    return sans_accents(contact["nom"])


def initiale(contact):
    """Retourne l'onglet du contact : sa première lettre, ou # si son nom commence autrement."""
    premier = sans_accents(contact["nom"])[:1].upper()
    return premier if premier in LETTRES else "#"


def initiales_presentes(contacts):
    """Retourne l'ensemble des onglets qui contiennent au moins un contact."""
    return {initiale(contact) for contact in contacts}


def contacts_de_lettre(contacts, lettre):
    """Retourne les contacts rangés sous cet onglet."""
    return [contact for contact in contacts if initiale(contact) == lettre]


def chercher_contacts(contacts, texte):
    """Retourne les contacts dont le nom contient le texte, ou le numéro si on cherche un numéro."""
    texte = " ".join(texte.split())
    if not texte:
        return list(contacts)

    if re.fullmatch(r"[0-9 +.()-]+", texte) and garder_chiffres(texte):
        chiffres = garder_chiffres(texte)
        return [c for c in contacts if chiffres in garder_chiffres(c["telephone"])]

    recherche = sans_accents(texte)
    return [c for c in contacts if recherche in sans_accents(c["nom"])]


def supprimer_contact(contacts, contact):
    """Retourne une nouvelle liste sans ce contact. `contacts` reste inchangée."""
    return [existant for existant in contacts if existant != contact]


def ajouter_contact(contacts, nom, telephone):
    """Retourne une nouvelle liste triée avec le contact en plus. `contacts` reste inchangée."""
    contact = creer_contact(nom, telephone)
    if est_en_double(contacts, contact):
        raise ContactInvalide("Ce contact existe déjà.", "nom")
    return sorted([*contacts, contact], key=cle_de_tri)
