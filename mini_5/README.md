# Carnet de contacts : Tkinter, site web et JavaFX MVC

Une petite application pour ajouter, chercher, afficher et supprimer des contacts (nom et téléphone). Elle sert à pratiquer la programmation événementielle et la séparation entre interface, logique et données.

- **Tkinter (Python) :** une fenêtre de bureau présentée comme un répertoire, avec ses onglets A à Z.
- **Site web (Python, Flask) :** le même carnet, présenté comme un téléphone. Il utilise les mêmes règles et le même fichier de contacts que la fenêtre.
- **JavaFX (Java) :** une fenêtre minimale organisée selon le modèle MVC. Ses contacts restent en mémoire et disparaissent à la fermeture.

## Lancer la fenêtre Tkinter

Python 3, sans dépendance à installer. Sous Linux, Tkinter s'installe parfois à part (`sudo apt install python3-tk`).

```
cd contacts_python
python interface.py
```

- Un clic sur une lettre affiche ses contacts. Un second clic affiche de nouveau tout le carnet.
- `Entrée` ajoute le contact saisi, `Suppr` supprime le contact sélectionné et `Échap` efface la recherche.

## Lancer le site web

La première fois, créez un environnement Python et installez Flask :

```
cd contacts_python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Puis lancez le site, et ouvrez `http://127.0.0.1:5005` dans votre navigateur :

```
python app.py
```

Sur une fenêtre large, l'application s'affiche dans un téléphone dessiné. Sur un écran de téléphone, le dessin disparaît et elle prend tout l'écran.

Les boutons **Appeler** et **Message** ouvrent des liens `tel:` et `sms:`. Ils ouvrent l'application de téléphone ou de messages de l'appareil, si celui-ci en a une : sur un ordinateur, il peut donc ne rien se passer. Le site n'appelle jamais lui-même.

Le site n'écoute que sur cet ordinateur et n'a pas de mot de passe. Ne l'ouvrez pas au réseau tel quel : toute personne connectée pourrait lire et supprimer vos contacts.

## Les contacts enregistrés

Les contacts sont dans `contacts_python/contacts.json`, qui reste hors du dépôt. Si ce fichier est abîmé, l'application l'indique sans l'écraser.

La fenêtre et le site peuvent être ouverts en même temps : chacun relit le fichier avant d'écrire. Pour voir dans la fenêtre un contact ajouté sur le site, relancez-la.

## Une logique, deux interfaces

| Couche | Fichier | Rôle |
| --- | --- | --- |
| Interface de bureau | `interface.py`, `theme.py` | Afficher la fenêtre et réagir aux événements |
| Interface web | `app.py`, `templates/`, `static/` | Répondre aux requêtes et afficher le téléphone |
| Logique | `contacts.py` | Vérifier une saisie, refuser les doublons, trier, chercher |
| Données | `stockage.py` | Lire et écrire le fichier JSON |

`contacts.py` et `stockage.py` ne connaissent aucune des deux interfaces. C'est ce qui a permis d'ajouter le site sans réécrire les règles.

Ajouter un contact suit le même chemin dans les deux cas :

1. L'interface reçoit l'événement : un clic dans la fenêtre, ou une requête `POST /api/contacts` pour le site.
2. `charger_contacts` relit le fichier.
3. `ajouter_contact` vérifie la saisie et retourne une nouvelle liste, ou un refus avec le champ à corriger.
4. `sauvegarder_contacts` écrit la liste.
5. L'interface affiche le résultat, ou le message d'erreur.

## Tests

```
cd contacts_python
.venv\Scripts\activate
python -m unittest -v
```

Les tests couvrent la logique, les données, la fenêtre et les routes du site. Ceux de la fenêtre ouvrent une vraie fenêtre Tkinter masquée et cliquent sur les vrais boutons. Tous utilisent un dossier temporaire et ne touchent pas à vos contacts.

## JavaFX et le modèle MVC

MVC répartit le programme en trois rôles :

```
                1. clic sur « Ajouter »
Utilisateur ─────────────────────────────► VUE : contacts.fxml
     ▲                                        │
     │                                        │ 2. appelle ajouter()
     │                                        ▼
     │                                     CONTRÔLEUR : ContactsController
     │                                        │
     │ 5. voit le nouveau contact             │ 3. carnet.ajouter(nom, téléphone)
     │                                        ▼
    VUE : listeContacts ◄─────────────────  MODÈLE : CarnetContacts, Contact
                  4. la liste observable prévient la vue
```

| Rôle | Ce qu'il fait | Dans JavaFX | Dans le site web |
| --- | --- | --- | --- |
| Modèle | Détient les contacts et leurs règles | `Contact.java`, `CarnetContacts.java` | `contacts.py`, `stockage.py` |
| Vue | Montre l'interface | `contacts.fxml` | `index.html`, `telephone.css` |
| Contrôleur | Réagit aux actions | `ContactsController.java` | `app.py`, `telephone.js` |

Dans la fenêtre Tkinter, la classe `FenetreContacts` joue à la fois la vue et le contrôleur. JavaFX les sépare vraiment : on pourrait redessiner `contacts.fxml` sans modifier une ligne de Java, tant que les `fx:id` et `onAction` restent les mêmes.

`CarnetContacts` dépend tout de même de JavaFX pour sa liste observable. C'est ce qui permet à la vue de se mettre à jour sans que le modèle la connaisse.

### Lancer la version JavaFX

> **État :** ce code n'a pas encore été compilé ni lancé, faute de Java sur l'ordinateur où il a été écrit.

Il faut un JDK 21 qui inclut JavaFX, par exemple **Azul Zulu**, avec le paquet **JDK FX**. Vérifiez l'installation :

```
java --list-modules | findstr javafx
```

La commande doit lister `javafx.controls` et `javafx.fxml`. Depuis `contacts_javafx`, dans PowerShell :

```
javac -d out src\contacts\*.java
java -cp "out;src" contacts.App
```

Sous Linux, remplacez le `;` par `:` et les `\` par `/`.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `contacts_python/contacts.py` | Les règles des contacts |
| `contacts_python/stockage.py` | La lecture et l'écriture du fichier JSON |
| `contacts_python/interface.py` | La fenêtre Tkinter |
| `contacts_python/theme.py` | Les couleurs et le style de la fenêtre |
| `contacts_python/app.py` | Le site Flask et ses routes |
| `contacts_python/templates/index.html` | La structure de la page du téléphone |
| `contacts_python/static/telephone.css` | L'apparence du téléphone |
| `contacts_python/static/telephone.js` | Les réactions de la page aux gestes |
| `contacts_python/test_contacts.py` | Les tests de la logique, des données et de la fenêtre |
| `contacts_python/test_app.py` | Les tests du site |
| `contacts_python/requirements.txt` | La version de Flask à installer |
| `contacts_javafx/src/contacts/App.java` | Le point de départ JavaFX |
| `contacts_javafx/src/contacts/contacts.fxml` | La vue |
| `contacts_javafx/src/contacts/ContactsController.java` | Le contrôleur |
| `contacts_javafx/src/contacts/CarnetContacts.java` | Le modèle : la liste et ses règles |
| `contacts_javafx/src/contacts/Contact.java` | Le modèle : un contact |
| `.gitignore` | Exclut du dépôt les contacts et les fichiers générés |
