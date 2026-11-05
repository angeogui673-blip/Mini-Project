# Le client-serveur dans un grand réseau Cisco

Ce guide construit dans Cisco Packet Tracer un réseau de deux sites reliés par deux routeurs, y fait passer l'échange TCP, puis le relie au vrai `serveur.py`. Il a été écrit pour Packet Tracer 8.2.2.

## Le réseau

```
      Réseau A : 192.168.10.0/24                   Réseau B : 192.168.20.0/24

PC1 ──┐                                                        ┌── PC3
      ├── Switch-A ── R1 ═══ 10.0.0.0/30 ═══ R2 ── Switch-B ───┼── Serveur-TCP
PC2 ──┘                                                        ├── Serveur-DNS
                                                               └── Serveur-DHCP
```

| Appareil | Interface | Adresse IP | Passerelle |
| --- | --- | --- | --- |
| R1 | G0/0, vers Switch-A | 192.168.10.1/24 | |
| R1 | G0/1, vers R2 | 10.0.0.1/30 | |
| R2 | G0/1, vers R1 | 10.0.0.2/30 | |
| R2 | G0/0, vers Switch-B | 192.168.20.1/24 | |
| Serveur-TCP | Fa0 | 192.168.20.10/24 | 192.168.20.1 |
| Serveur-DNS | Fa0 | 192.168.20.20/24 | 192.168.20.1 |
| Serveur-DHCP | Fa0 | 192.168.20.30/24 | 192.168.20.1 |
| PC1, PC2 | Fa0 | Automatique (DHCP) | 192.168.10.1 |
| PC3 | Fa0 | Automatique (DHCP) | 192.168.20.1 |

## Partie 1 : construire le réseau

### 1. Placer et relier les appareils

Placez 2 routeurs **2911**, 2 switchs **2960**, 3 **PC-PT** et 3 **Server-PT**, puis renommez-les selon le schéma.

- Utilisez un câble **Copper Straight-Through** entre les PC ou serveurs et les switchs, et entre les switchs et les routeurs.
- Utilisez un câble **Copper Cross-Over** entre R1 et R2, de G0/1 à G0/1.

Sur chaque routeur, à la question sur la configuration initiale, répondez `no`.

### 2. Configurer les routeurs

Ouvrez l'onglet **CLI** de R1 et collez :

```
enable
configure terminal
hostname R1
interface g0/0
 ip address 192.168.10.1 255.255.255.0
 ip helper-address 192.168.20.30
 no shutdown
exit
interface g0/1
 ip address 10.0.0.1 255.255.255.252
 no shutdown
exit
ip route 192.168.20.0 255.255.255.0 10.0.0.2
end
write memory
```

Puis l'onglet **CLI** de R2 :

```
enable
configure terminal
hostname R2
interface g0/0
 ip address 192.168.20.1 255.255.255.0
 no shutdown
exit
interface g0/1
 ip address 10.0.0.2 255.255.255.252
 no shutdown
exit
ip route 192.168.10.0 255.255.255.0 10.0.0.1
end
write memory
```

- **`ip route`** indique à chaque routeur par où joindre le réseau qu'il ne connaît pas.
- **`ip helper-address`** transmet les demandes DHCP du réseau A au serveur DHCP du réseau B. Sans elle, ces demandes s'arrêteraient au routeur, car elles sont envoyées en diffusion.

### 3. Configurer les serveurs

Sur chacun des trois serveurs, ouvrez **Desktop > IP Configuration**, choisissez **Static**, puis entrez son adresse et son masque `255.255.255.0`, la passerelle `192.168.20.1` et le DNS `192.168.20.20`.

**Serveur-DNS :** dans **Services > DNS**, activez le service (**On**), puis ajoutez le nom `serveur.local` avec l'adresse `192.168.20.10` et cliquez sur **Add**.

**Serveur-DHCP :** dans **Services > DHCP**, activez le service (**On**).

| Champ | Réseau B : modifiez `serverPool`, puis **Save** | Réseau A : nouveau nom, puis **Add** |
| --- | --- | --- |
| Pool Name | `serverPool` | `reseauA` |
| Default Gateway | `192.168.20.1` | `192.168.10.1` |
| DNS Server | `192.168.20.20` | `192.168.20.20` |
| Start IP Address | `192.168.20.100` | `192.168.10.100` |
| Subnet Mask | `255.255.255.0` | `255.255.255.0` |
| Maximum Number of Users | `50` | `50` |

### 4. Configurer les PC

Sur PC1, PC2 et PC3, ouvrez **Desktop > IP Configuration** et choisissez **DHCP**. Le message `DHCP request successful` doit apparaître, avec une adresse en `192.168.10.x` pour PC1 et PC2, et en `192.168.20.x` pour PC3.

### 5. Vérifier

Attendez que les points des câbles passent au vert ; le bouton d'avance rapide du temps accélère cette étape. Puis, dans **Desktop > Command Prompt** de PC1 :

| Commande | Ce qu'elle vérifie | Résultat attendu |
| --- | --- | --- |
| `ipconfig /all` | L'adresse reçue par DHCP | Adresse `192.168.10.x`, passerelle `192.168.10.1`, DNS `192.168.20.20` |
| `ping 192.168.10.1` | La passerelle | Réponses du routeur |
| `ping 192.168.20.10` | Le routage entre les réseaux | Réponses ; le tout premier ping peut échouer, le temps de la résolution ARP |
| `tracert 192.168.20.10` | Le chemin suivi | `192.168.10.1`, puis `10.0.0.2`, puis `192.168.20.10` |
| `nslookup serveur.local` | Le DNS | L'adresse `192.168.20.10` |

## Partie 2 : l'échange TCP dans le réseau simulé

1. Sur **Serveur-TCP**, ouvrez l'onglet **Programming**, cliquez sur **New**, nommez le projet `serveur`, choisissez un projet Python vide (**Empty - Python**) et collez `serveur_pt.py` dans `main.py`. Enregistrez, puis cliquez sur **Run**.
2. Sur **PC1**, faites de même avec `client_pt.py`.
3. Les réponses du serveur s'affichent dans la console, sous l'éditeur de PC1.

### Observer les paquets

1. Passez en mode **Simulation**, en bas à droite.
2. Dans **Edit Filters**, gardez seulement **TCP** et **ARP**.
3. Relancez le script de PC1, puis cliquez sur **Play** ou avancez avec **Capture / Forward**.
4. Cliquez sur une enveloppe pour voir ses couches, puis sur **Outbound PDU Details**.

Comparez le même paquet avant et après un routeur :

- **Les adresses IP ne changent pas :** du début à la fin, l'origine reste PC1 et la destination reste Serveur-TCP.
- **Les adresses MAC changent à chaque routeur :** elles ne servent qu'au tronçon en cours.

## Partie 3 : relier Packet Tracer au vrai serveur

La passerelle fait suivre les messages simulés vers le vrai `serveur.py` :

```
PC1 simulé ─► R1 ─► R2 ─► Serveur-TCP simulé ═ connexion réelle ═► serveur.py sur Windows
```

1. Dans Packet Tracer, ouvrez **Options > Preferences > Miscellaneous** et cochez **Enable External Network Access from Device Scripts**. Cette option autorise les scripts à accéder à votre vrai réseau : décochez-la après vos essais.
2. Dans un terminal Windows, dans le dossier `mini_3`, lancez `python serveur.py`.
3. Dans Wireshark, choisissez **Adapter for loopback traffic capture** avec le filtre `tcp.port == 5050`.
4. En mode **Realtime**, sur **Serveur-TCP**, arrêtez le script, remplacez son contenu par `passerelle_pt.py`, puis cliquez sur **Run**.
5. Relancez le script de PC1.

Le terminal de `serveur.py` doit afficher les messages de PC1, et Wireshark doit montrer la partie réelle du trajet. La réponse revient à PC1 par le même chemin.

Pour viser `serveur.py` sur un autre ordinateur, modifiez `IP_REELLE` dans la passerelle et lancez le serveur avec `--hote 0.0.0.0`.

## En cas de problème

| Symptôme | Cause probable |
| --- | --- |
| Un point de câble reste rouge | L'interface n'est pas activée : vérifiez `no shutdown`, ou le câble |
| `DHCP request failed` sur PC1 | `ip helper-address` manque sur R1, ou le pool `reseauA` n'a pas été ajouté |
| `ping` échoue vers l'autre réseau | Une route `ip route` manque, ou la passerelle du PC est fausse |
| `nslookup` échoue | Le service DNS est désactivé, ou l'entrée n'a pas été ajoutée |
| `Connexion impossible` sur PC1 | Le script du Serveur-TCP n'est pas lancé |
| Aucun message n'arrive à `serveur.py` | `serveur.py` n'est pas lancé, ou l'option d'accès au réseau externe n'est pas cochée |
