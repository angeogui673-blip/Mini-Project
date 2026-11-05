# Passerelle entre Packet Tracer et le vrai reseau. A coller a la place de serveur_pt.py sur le Serveur-TCP.
#
# Trajet d'un message :
#   PC1 simule -> routeurs simules -> Serveur-TCP simule -> connexion reelle -> serveur.py sur Windows
#
# Prerequis dans Packet Tracer : Options > Preferences > Miscellaneous,
# cocher "Enable External Network Access from Device Scripts".
# serveur.py doit etre lance sur Windows avant de demarrer ce script.

from tcp import *
from realtcp import *
from time import *

PORT_SIMULE = 5050
IP_REELLE = "127.0.0.1"  # ou l'adresse IP du second ordinateur, si serveur.py tourne dessus
PORT_REEL = 5050

serveur = TCPServer()
connexions_reelles = []  # garde les connexions reelles actives pendant tout le programme


def quand_nouveau_client(client):
    print("Client simule : " + client.remoteIP())
    reelle = RealTCPClient()
    connexions_reelles.append(reelle)

    def quand_message_simule(donnees):
        print("Vers le vrai serveur : " + donnees)
        reelle.send(donnees + "\n")  # serveur.py attend un \n a la fin de chaque message

    def quand_reponse_reelle(donnees):
        print("Du vrai serveur : " + donnees)
        client.send(donnees.strip())

    client.onReceive(quand_message_simule)
    reelle.onReceive(quand_reponse_reelle)
    reelle.connect(IP_REELLE, PORT_REEL)


def main():
    serveur.onNewClient(quand_nouveau_client)
    serveur.listen(PORT_SIMULE)
    print("Passerelle prete vers " + IP_REELLE + ":" + str(PORT_REEL))
    while True:
        sleep(3600)


if __name__ == "__main__":
    main()
