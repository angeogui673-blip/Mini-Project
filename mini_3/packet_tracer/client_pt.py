# Client TCP simule. A coller dans l'onglet Programming de PC1 dans Packet Tracer.
# Il envoie quelques messages au Serveur-TCP, situe dans l'autre reseau, deux routeurs plus loin.

from tcp import *
from time import *

IP_SERVEUR = "192.168.20.10"
PORT_SERVEUR = 5050
MESSAGES = ["Bonjour", "Ce message traverse deux routeurs", "Au revoir"]

client = TCPClient()


def quand_reponse(donnees):
    print("Serveur : " + donnees)


def attendre_connexion():
    for _ in range(10):
        if client.connected():
            return True
        sleep(1)
    return False


def main():
    client.onReceive(quand_reponse)
    print("Connexion a " + IP_SERVEUR + "...")
    client.connect(IP_SERVEUR, PORT_SERVEUR)

    if not attendre_connexion():
        print("Connexion impossible : verifiez le reseau et que le serveur est lance.")
        return

    print("Connecte depuis " + client.localIP() + ":" + str(client.localPort()))
    sleep(2)  # laisse le temps a la passerelle, si elle est utilisee, de joindre le vrai serveur

    for message in MESSAGES:
        print("Envoi : " + message)
        client.send(message)
        sleep(5)

    client.close()
    print("Connexion fermee.")


if __name__ == "__main__":
    main()
