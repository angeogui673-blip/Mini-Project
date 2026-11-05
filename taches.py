"""Gestionnaire de tâches en ligne de commande.

Une tâche est un dictionnaire : {"id", "titre", "echeance", "etat"}.
La liste des tâches est sauvegardée dans un fichier JSON.
"""

import json
from datetime import date
from pathlib import Path

FICHIER_TACHES = Path(__file__).parent / "taches.json"
A_FAIRE = "à faire"
TERMINEE = "terminée"


# --- Lecture et écriture du fichier JSON ---

def charger_taches(chemin=FICHIER_TACHES):
    """Retourne la liste des tâches du fichier, ou une liste vide s'il n'existe pas."""
    try:
        with open(chemin, encoding="utf-8") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        return []


def sauvegarder_taches(taches, chemin=FICHIER_TACHES):
    """Écrit la liste des tâches dans le fichier JSON."""
    with open(chemin, "w", encoding="utf-8") as fichier:
        json.dump(taches, fichier, ensure_ascii=False, indent=2)


# --- Les actions sur les tâches ---

def ajouter_tache(taches, titre, echeance):
    """Ajoute une tâche à la liste et la retourne.

    Lève ValueError si le titre est vide ou si l'échéance n'est pas une vraie
    date au format AAAA-MM-JJ.
    """
    titre = titre.strip()
    if not titre:
        raise ValueError("Le titre ne peut pas être vide.")

    try:
        echeance = date.fromisoformat(echeance.strip()).isoformat()
    except ValueError:
        raise ValueError("L'échéance doit être une date valide au format AAAA-MM-JJ.")

    nouvel_id = max((tache["id"] for tache in taches), default=0) + 1
    tache = {"id": nouvel_id, "titre": titre, "echeance": echeance, "etat": A_FAIRE}
    taches.append(tache)
    return tache


def lister_taches(taches):
    """Retourne une copie triée : tâches à faire d'abord, échéance la plus proche en tête."""
    return sorted(taches, key=lambda tache: (tache["etat"] == TERMINEE, tache["echeance"]))


def trouver_tache(taches, id_tache):
    """Retourne la tâche portant cet id, ou None si elle n'existe pas."""
    for tache in taches:
        if tache["id"] == id_tache:
            return tache
    return None


def terminer_tache(taches, id_tache):
    """Marque la tâche comme terminée. Retourne False si l'id n'existe pas."""
    tache = trouver_tache(taches, id_tache)
    if tache is None:
        return False
    tache["etat"] = TERMINEE
    return True


def supprimer_tache(taches, id_tache):
    """Retire la tâche de la liste. Retourne False si l'id n'existe pas."""
    tache = trouver_tache(taches, id_tache)
    if tache is None:
        return False
    taches.remove(tache)
    return True


def est_en_retard(tache, aujourdhui=None):
    """Retourne True si la tâche n'est pas terminée et que son échéance est dépassée."""
    aujourdhui = aujourdhui or date.today()
    return tache["etat"] != TERMINEE and date.fromisoformat(tache["echeance"]) < aujourdhui


def formater_tache(tache, aujourdhui=None):
    """Retourne la ligne de texte qui affiche une tâche, avec une alerte si elle est en retard."""
    case = "[x]" if tache["etat"] == TERMINEE else "[ ]"
    ligne = f"{tache['id']:>3}. {case} {tache['echeance']}  {tache['titre']}"

    if est_en_retard(tache, aujourdhui):
        ligne += "  (EN RETARD)"
    return ligne


# --- Menu en ligne de commande ---

def afficher_taches(taches):
    """Affiche toutes les tâches à l'écran."""
    if not taches:
        print("Aucune tâche pour le moment.")
    for tache in lister_taches(taches):
        print(formater_tache(tache))


def lire_id():
    """Demande un numéro de tâche. Retourne None si la saisie n'est pas un nombre."""
    try:
        return int(input("Numéro de la tâche : "))
    except ValueError:
        print("Veuillez entrer un nombre.")
        return None


def boucle_menu(taches):
    """Affiche le menu et exécute les actions jusqu'à ce que l'utilisateur quitte."""
    while True:
        print("\n1. Ajouter  2. Lister  3. Terminer  4. Supprimer  5. Quitter")
        choix = input("Votre choix : ").strip()

        if choix == "1":
            titre = input("Titre : ")
            echeance = input("Échéance (AAAA-MM-JJ) : ")
            try:
                tache = ajouter_tache(taches, titre, echeance)
            except ValueError as erreur:
                print(erreur)
            else:
                sauvegarder_taches(taches)
                print(f"Tâche {tache['id']} ajoutée.")

        elif choix == "2":
            afficher_taches(taches)

        elif choix == "3":
            id_tache = lire_id()
            if id_tache is not None:
                if terminer_tache(taches, id_tache):
                    sauvegarder_taches(taches)
                    print(f"Tâche {id_tache} terminée.")
                else:
                    print(f"Aucune tâche avec le numéro {id_tache}.")

        elif choix == "4":
            id_tache = lire_id()
            if id_tache is not None:
                if supprimer_tache(taches, id_tache):
                    sauvegarder_taches(taches)
                    print(f"Tâche {id_tache} supprimée.")
                else:
                    print(f"Aucune tâche avec le numéro {id_tache}.")

        elif choix == "5":
            print("Au revoir !")
            return

        else:
            print("Choix invalide : entrez un chiffre de 1 à 5.")


def main():
    """Point d'entrée : charge les tâches puis lance le menu."""
    try:
        taches = charger_taches()
    except json.JSONDecodeError:
        # On s'arrête ici : repartir d'une liste vide écraserait le fichier à la prochaine sauvegarde.
        print(f"Le fichier {FICHIER_TACHES} est illisible. Corrigez-le ou supprimez-le, puis relancez.")
        return

    try:
        boucle_menu(taches)
    except (KeyboardInterrupt, EOFError):
        print("\nAu revoir !")


if __name__ == "__main__":
    main()
