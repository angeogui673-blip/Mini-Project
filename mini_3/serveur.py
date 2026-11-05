"""Serveur TCP : attend des clients, lit leurs messages et leur répond.

Lancement sur cet ordinateur seulement : python serveur.py
Lancement ouvert au réseau local :       python serveur.py --hote 0.0.0.0
"""

import argparse
import socket
import threading

HOTE_PAR_DEFAUT = "127.0.0.1"
PORT_PAR_DEFAUT = 5050
TAILLE_MAX_MESSAGE = 4096
ATTENTE_MAXIMALE = 5  # nombre de connexions qui peuvent patienter avant d'être acceptées


def preparer_reponse(message):
    """Retourne la réponse du serveur à un message."""
    return f"Reçu : {message}"


def traiter_client(connexion, adresse):
    """Lit les messages d'un client et répond à chacun, jusqu'à ce qu'il se déconnecte."""
    nom_client = f"{adresse[0]}:{adresse[1]}"
    print(f"[connexion] {nom_client}")

    try:
        # TCP envoie un flux d'octets, sans notion de message : un message se termine ici par \n.
        # makefile permet de lire ligne par ligne, et appelle recv pour nous.
        with connexion, connexion.makefile("r", encoding="utf-8", errors="replace", newline="\n") as flux:
            while True:
                ligne = flux.readline(TAILLE_MAX_MESSAGE)
                if not ligne:  # une lecture vide signifie que le client a fermé la connexion
                    break
                message = ligne.rstrip("\r\n")
                print(f"[{nom_client}] {message}")
                connexion.sendall(f"{preparer_reponse(message)}\n".encode("utf-8"))
    except OSError as erreur:  # par exemple si le client est coupé brutalement
        print(f"[erreur] {nom_client} : {erreur}")

    print(f"[déconnexion] {nom_client}")


def creer_serveur(hote=HOTE_PAR_DEFAUT, port=PORT_PAR_DEFAUT):
    """Crée le socket du serveur et commence à écouter sur l'adresse et le port demandés."""
    serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4 et TCP
    try:
        serveur.bind((hote, port))
        serveur.listen(ATTENTE_MAXIMALE)
    except OSError:
        serveur.close()
        raise
    # Sous Windows, accept bloquerait Ctrl+C : on lui fait vérifier régulièrement s'il doit s'arrêter.
    serveur.settimeout(0.5)
    return serveur


def lancer_serveur(serveur, arret=None):
    """Accepte les clients jusqu'à l'arrêt, chacun dans son propre thread."""
    arret = arret or threading.Event()
    while not arret.is_set():
        try:
            connexion, adresse = serveur.accept()
        except socket.timeout:
            continue
        except OSError:  # le socket du serveur a été fermé
            break
        connexion.settimeout(None)
        # daemon=True : ces threads ne retiennent pas le programme quand on l'arrête.
        threading.Thread(target=traiter_client, args=(connexion, adresse), daemon=True).start()


def lire_arguments():
    analyseur = argparse.ArgumentParser(description="Serveur TCP du mini-projet 3.")
    analyseur.add_argument("--hote", default=HOTE_PAR_DEFAUT,
                           help="adresse d'écoute : 127.0.0.1 pour cet ordinateur, 0.0.0.0 pour le réseau local")
    analyseur.add_argument("--port", type=int, default=PORT_PAR_DEFAUT, help="port d'écoute")
    return analyseur.parse_args()


def main():
    arguments = lire_arguments()
    try:
        serveur = creer_serveur(arguments.hote, arguments.port)
    except OSError as erreur:
        print(f"Impossible d'écouter sur {arguments.hote}:{arguments.port} : {erreur}")
        print("Le port est peut-être déjà utilisé. Essayez un autre port avec --port.")
        return

    print(f"Serveur à l'écoute sur {arguments.hote}:{arguments.port}. Ctrl+C pour arrêter.")
    with serveur:
        try:
            lancer_serveur(serveur)
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")


if __name__ == "__main__":
    main()
