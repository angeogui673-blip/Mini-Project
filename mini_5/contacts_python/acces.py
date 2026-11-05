"""Accès : le mot de passe du site. Ce fichier ne connaît ni les contacts ni les pages.

Le mot de passe n'est jamais enregistré : seule son empreinte l'est, et on ne peut pas la retransformer en mot de passe.
"""

import json
import os
import secrets
import time
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

FICHIER_ACCES = Path(__file__).parent / "acces.json"
LONGUEUR_MIN = 8
ESSAIS_MAX = 5
DUREE_BLOCAGE = 5 * 60  # en secondes


class AccesIllisible(Exception):
    """Le fichier d'accès existe mais il est abîmé. Le site refuse alors de démarrer sans protection."""


def charger_acces(chemin=FICHIER_ACCES):
    """Retourne l'empreinte et la clé de session, ou None si aucun mot de passe n'a été choisi."""
    try:
        with open(chemin, encoding="utf-8") as fichier:
            acces = json.load(fichier)
    except FileNotFoundError:
        return None
    except ValueError as erreur:
        raise AccesIllisible(f"{chemin} : {erreur}") from erreur

    champs = ("empreinte", "cle_session")
    if not isinstance(acces, dict) or not all(isinstance(acces.get(c), str) and acces[c] for c in champs):
        raise AccesIllisible(f"{chemin} : ce n'est pas un fichier d'accès valide.")
    return acces


def enregistrer_mot_de_passe(mot_de_passe, chemin=FICHIER_ACCES):
    """Enregistre l'empreinte du mot de passe, avec une nouvelle clé qui déconnecte tous les appareils."""
    if len(mot_de_passe) < LONGUEUR_MIN:
        raise ValueError(f"Le mot de passe doit contenir au moins {LONGUEUR_MIN} caractères.")

    acces = {
        "empreinte": generate_password_hash(mot_de_passe),
        "cle_session": secrets.token_hex(32),
    }
    temporaire = f"{chemin}.tmp"
    with open(temporaire, "w", encoding="utf-8") as fichier:
        json.dump(acces, fichier)
    os.replace(temporaire, chemin)


def mot_de_passe_correct(acces, mot_de_passe):
    """Vrai si le mot de passe correspond à l'empreinte enregistrée."""
    return check_password_hash(acces["empreinte"], mot_de_passe)


class GardeTentatives:
    """Bloque quelques minutes un appareil qui se trompe trop souvent, pour empêcher d'essayer au hasard."""

    def __init__(self, horloge=time.monotonic):
        self.horloge = horloge
        self.echecs = {}  # adresse IP -> nombre d'échecs
        self.blocages = {}  # adresse IP -> moment de fin du blocage

    def est_bloque(self, adresse):
        """Vrai si cet appareil doit encore attendre. Un blocage terminé remet son compteur à zéro."""
        fin = self.blocages.get(adresse)
        if fin is None:
            return False
        if self.horloge() < fin:
            return True
        self.oublier(adresse)
        return False

    def noter_echec(self, adresse):
        """Compte un échec, et bloque l'appareil s'il a atteint la limite."""
        self.echecs[adresse] = self.echecs.get(adresse, 0) + 1
        if self.echecs[adresse] >= ESSAIS_MAX:
            self.blocages[adresse] = self.horloge() + DUREE_BLOCAGE

    def oublier(self, adresse):
        """Efface l'historique de cet appareil, par exemple après une connexion réussie."""
        self.echecs.pop(adresse, None)
        self.blocages.pop(adresse, None)
