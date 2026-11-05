# Client-serveur TCP

Deux petits programmes Python échangent du texte sur un réseau local, pour rendre visibles les bases de la communication réseau. Un serveur attend des connexions, et un client s'y connecte, envoie un message et affiche la réponse. Wireshark permet d'observer les paquets échangés.

Notions pratiquées : adresse IP, port, modèle client/serveur, poignée de main TCP, lecture d'une capture de paquets.

## Lancement sur un seul ordinateur

Python 3, sans dépendance à installer. Ouvrez deux terminaux dans ce dossier.

Dans le premier, lancez le serveur :

```
python serveur.py
```

Dans le second, lancez le client :

```
python client.py
```

Tapez un message, ou `quitter` pour terminer. `Ctrl+C` arrête le serveur.

```
Connecté à 127.0.0.1:5050 depuis 127.0.0.1:64020.
Tapez un message, ou « quitter » pour terminer.
Vous : Bonjour
Serveur : Reçu : Bonjour
```

Le serveur accepte plusieurs clients en même temps.

## Lancement sur deux ordinateurs

Les deux ordinateurs doivent être sur le même réseau. Le second n'a besoin que de Python et du fichier `client.py`.

Sur l'ordinateur serveur, lancez le serveur en l'ouvrant au réseau local, et cherchez son adresse IPv4 avec `ipconfig` :

```
python serveur.py --hote 0.0.0.0
```

Sur l'autre ordinateur, indiquez cette adresse :

```
python client.py 192.168.1.20
```

Le pare-feu de Windows peut demander d'autoriser Python : autorisez-le sur les réseaux privés uniquement. Tout appareil du réseau local peut joindre le serveur tant qu'il tourne en mode `0.0.0.0` : arrêtez-le après vos essais.

## Adresse IP et port

- **L'adresse IP désigne la machine.** `127.0.0.1` est l'adresse de boucle locale : elle désigne l'ordinateur lui-même, et le trafic ne sort pas sur le réseau.
- **Le port désigne le programme sur cette machine.** Le serveur utilise un port fixe, `5050`, pour que les clients sachent où le joindre. Le client reçoit un port temporaire choisi par le système, par exemple `64020`, ce qui permet à deux clients de coexister.
- **`0.0.0.0` n'est pas une adresse à joindre.** Pour le serveur, elle signifie « écouter sur toutes les cartes réseau de cet ordinateur ».

## L'échange observé

Capture réelle de ce programme, pour l'envoi d'un message suivi de `quitter` :

| Paquet | De | Vers | Drapeaux | Données | Rôle |
| --- | --- | --- | --- | --- | --- |
| 1 | client | serveur | SYN | | Poignée de main : le client demande à se connecter |
| 2 | serveur | client | SYN, ACK | | Le serveur accepte |
| 3 | client | serveur | ACK | | Le client confirme : la connexion est établie |
| 4 | client | serveur | PSH, ACK | `Bonjour\n` | Le client envoie son message (8 octets) |
| 5 | serveur | client | ACK | | Le serveur confirme la réception |
| 6 | serveur | client | PSH, ACK | `Reçu : Bonjour\n` | Le serveur envoie sa réponse (16 octets) |
| 7 | client | serveur | ACK | | Le client confirme la réception |
| 8 | client | serveur | FIN, ACK | | Le client ferme son côté de la connexion |
| 9 | serveur | client | ACK | | Le serveur en prend acte |
| 10 | serveur | client | FIN, ACK | | Le serveur ferme à son tour |
| 11 | client | serveur | ACK | | La connexion est terminée |

Deux observations :

- **TCP confirme ce qu'il reçoit.** Après le paquet 4 (8 octets), le serveur annonce dans le paquet 5 qu'il attend l'octet numéro 9.
- **Le message circule en clair.** `Bonjour` se lit directement dans la capture, car rien n'est chiffré. Quiconque capte ce trafic peut le lire, et il ne faut donc pas envoyer de données sensibles par ce programme.

## Observer l'échange avec Wireshark

1. Ouvrez Wireshark et choisissez l'interface :
   - **Adapter for loopback traffic capture** si le client et le serveur sont sur le même ordinateur ;
   - **Wi-Fi** ou **Ethernet** si le client est sur un autre ordinateur.
2. Entrez le filtre d'affichage `tcp.port == 5050`.
3. Lancez le serveur, puis le client, envoyez un message et tapez `quitter`.
4. Faites un clic droit sur un paquet, puis **Suivre > Flux TCP** pour lire la conversation.

## Dans un grand réseau Cisco

Le dossier [`packet_tracer`](packet_tracer/GUIDE.md) reproduit l'échange dans Cisco Packet Tracer : un réseau de deux sites, avec deux routeurs, DHCP et DNS. Une passerelle relie ensuite le réseau simulé au vrai `serveur.py`.

## Tests

```
python -m unittest -v
```

Les tests ouvrent de vraies connexions TCP sur cet ordinateur, sur un port libre choisi par le système. Ils vérifient notamment les accents, plusieurs clients simultanés, un message reçu en plusieurs morceaux et la coupure brutale d'un client.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `serveur.py` | Le serveur TCP |
| `client.py` | Le client TCP |
| `test_reseau.py` | Les tests |
| `packet_tracer/GUIDE.md` | Construction du réseau Cisco, étape par étape |
| `packet_tracer/serveur_pt.py` | Serveur à coller dans Packet Tracer |
| `packet_tracer/client_pt.py` | Client à coller dans Packet Tracer |
| `packet_tracer/passerelle_pt.py` | Relie le réseau simulé au vrai `serveur.py` |
| `.gitignore` | Exclut du dépôt les fichiers générés par Python |
