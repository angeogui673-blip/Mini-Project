# Serveur TCP simule. A coller dans l'onglet Programming du Serveur-TCP de Packet Tracer.
# Packet Tracer n'utilise pas le module socket : le module tcp fonctionne par fonctions de rappel,
# appelees automatiquement quand un evenement arrive (nouveau client, message recu...).

from tcp import *
from time import *

PORT = 5050

serveur = TCPServer()


def quand_nouveau_client(client):
    print("Connexion de " + client.remoteIP())

    def quand_message(donnees):
        print("Recu de " + client.remoteIP() + " : " + donnees)
        client.send("Recu : " + donnees)

    client.onReceive(quand_message)


def main():
    serveur.onNewClient(quand_nouveau_client)
    serveur.listen(PORT)
    print("Serveur a l'ecoute sur le port " + str(PORT))
    while True:  # le programme doit rester actif pour continuer a recevoir
        sleep(3600)


if __name__ == "__main__":
    main()
