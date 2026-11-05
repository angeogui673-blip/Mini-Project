"""Client TCP : se connecte au serveur, envoie du texte et affiche les réponses.

Lancement sur le même ordinateur que le serveur : python client.py
Lancement depuis un autre ordinateur :            python client.py 192.168.1.20
"""

import argparse
import socket

HOTE_PAR_DEFAUT = "127.0.0.1"
PORT_PAR_DEFAUT = 5050
DELAI_SECONDES = 5
MOT_QUITTER = "quitter"


def se_connecter(hote=HOTE_PAR_DEFAUT, port=PORT_PAR_DEFAUT):
    """Ouvre une connexion TCP vers le serveur : c'est ici qu'a lieu la poignée de main."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # IPv4 et TCP
    client.settimeout(DELAI_SECONDES)  # évite d'attendre sans fin un serveur qui ne répond pas
    try:
        client.connect((hote, port))
    except OSError:
        client.close()
        raise
    return client


def echanger(connexion, flux, message):
    """Envoie un message et retourne la réponse du serveur."""
    connexion.sendall(f"{message}\n".encode("utf-8"))  # \n marque la fin du message
    reponse = flux.readline()
    if not reponse:
        raise ConnectionError("le serveur a fermé la connexion")
    return reponse.rstrip("\r\n")


def discuter(connexion):
    """Demande des messages au clavier et affiche les réponses, jusqu'à « quitter »."""
    print(f"Tapez un message, ou « {MOT_QUITTER} » pour terminer.")
    with connexion.makefile("r", encoding="utf-8", errors="replace", newline="\n") as flux:
        while True:
            message = input("Vous : ").strip()
            if message == MOT_QUITTER:
                return
            if message:
                print(f"Serveur : {echanger(connexion, flux, message)}")


def lire_arguments():
    analyseur = argparse.ArgumentParser(description="Client TCP du mini-projet 3.")
    analyseur.add_argument("hote", nargs="?", default=HOTE_PAR_DEFAUT, help="adresse IP du serveur")
    analyseur.add_argument("port", nargs="?", type=int, default=PORT_PAR_DEFAUT, help="port du serveur")
    return analyseur.parse_args()


def main():
    arguments = lire_arguments()
    try:
        connexion = se_connecter(arguments.hote, arguments.port)
    except OSError as erreur:
        print(f"Connexion impossible à {arguments.hote}:{arguments.port} : {erreur}")
        print("Vérifiez que le serveur est lancé, ainsi que l'adresse IP, le port et le pare-feu.")
        return

    ip_locale, port_local = connexion.getsockname()
    print(f"Connecté à {arguments.hote}:{arguments.port} depuis {ip_locale}:{port_local}.")

    with connexion:
        try:
            discuter(connexion)
        except (OSError, ConnectionError) as erreur:
            print(f"Connexion perdue : {erreur}")
        except (KeyboardInterrupt, EOFError):
            print()
    print("Connexion fermée.")


if __name__ == "__main__":
    main()
