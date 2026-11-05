# Catalogue de la bibliothèque

Mini-application web locale pour une petite bibliothèque scolaire, dont le catalogue était difficile à tenir à jour dans un simple fichier. Le bibliothécaire peut ajouter, rechercher, modifier et retirer des livres, et suivre les prêts avec l'emprunteur, la date de retour et les retards.

Le catalogue peut se remplir avec un fonds de 95 livres réels, de Zola à *Dune*, répartis dans 12 catégories.

Notions pratiquées : routes et requêtes HTTP, SQL de base (CRUD), jointures entre tables, clés étrangères, gabarits HTML, formulaires, transitions CSS, tests du serveur.

## Lancement

Python 3.11 ou plus récent. Commandes pour Windows, à lancer dans ce dossier.

Installation, une seule fois :

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python charger_livres.py
```

La dernière commande crée la base `catalogue.db` et y ajoute les livres de `livres.json`. On peut la relancer sans risque : un livre déjà présent n'est ni dupliqué ni modifié.

Lancement :

```
.venv\Scripts\python app.py
```

Ouvrez ensuite <http://127.0.0.1:5000> dans le navigateur. Le site n'est accessible que depuis votre ordinateur. `Ctrl+C` arrête le serveur.

## Utilisation

- **Parcourir :** les livres sont présentés sur des étagères, rangés par catégorie. Un clic sur une couverture ouvre sa fiche.
- **Rechercher :** le champ de recherche cherche dans le titre, l'auteur et la cote, sans tenir compte des majuscules ni des accents. « moliere » trouve Molière et « P HUG » trouve *Les Contemplations*.
- **Prêter :** sur la fiche d'un livre disponible, indiquez l'emprunteur et la date de retour, proposée 21 jours plus tard.
- **Suivre les prêts :** la page « Prêts » liste les prêts en cours, les plus urgents d'abord, et signale les retards. Le nombre de prêts et de retards reste visible en haut de chaque page.
- **Enregistrer un retour :** le bouton se trouve sur la fiche et sur la page « Prêts ». Les anciens prêts restent dans l'historique du livre.
- **Ajouter et modifier :** le formulaire demande le titre, l'auteur, l'année, la catégorie, et en option un résumé et l'adresse d'une image de couverture. La cote se calcule toute seule.
- **Retirer :** le bouton de la fiche supprime le livre après confirmation. Un livre en prêt ne peut pas être retiré.

## Les cotes

La cote indique où ranger un livre sur les rayons. Elle réunit le code de la catégorie et les trois premières lettres du nom de l'auteur : *Germinal* d'Émile Zola devient `R ZOL`. Les documentaires utilisent la classification Dewey : `100` pour la philosophie, `500` pour les sciences et `900` pour l'histoire.

| Catégorie | Code | Catégorie | Code |
| --- | --- | --- | --- |
| Roman | `R` | Poésie | `P` |
| Policier | `RP` | Théâtre | `T` |
| Science-fiction | `SF` | Biographies | `B` |
| Fantasy | `FA` | Philosophie | `100` |
| Jeunesse | `J` | Sciences | `500` |
| Bande dessinée | `BD` | Histoire | `900` |

## Le fonds de livres

Dans `livres.json`, l'année est celle de la première publication de l'œuvre dans sa langue d'origine, y compris pour les livres traduits. Pour le théâtre, c'est l'année de la création sur scène. Pour une œuvre parue en plusieurs tomes, c'est l'année du premier.

Les couvertures de 64 livres sont des images chargées depuis [Open Library](https://openlibrary.org) : elles nécessitent une connexion internet et ne sont pas stockées dans ce dépôt. Sans image, ou sans connexion, le site dessine une couverture avec le titre et l'auteur.

## Routes

| Méthode | Adresse | Rôle |
| --- | --- | --- |
| GET | `/` | Tous les livres, rangés par catégorie |
| GET | `/categorie/<id>` | Livres d'une seule catégorie |
| GET | `/recherche?q=...` | Livres correspondant à la recherche |
| GET | `/livre/<id>` | Fiche d'un livre, avec son prêt et son historique |
| GET, POST | `/ajouter` | Affiche le formulaire, puis enregistre le livre |
| GET, POST | `/modifier/<id>` | Affiche le formulaire prérempli, puis enregistre les changements |
| POST | `/supprimer/<id>` | Retire le livre |
| GET | `/prets` | Prêts en cours et retards |
| POST | `/livre/<id>/preter` | Enregistre un prêt |
| POST | `/livre/<id>/rendre` | Enregistre un retour |

## Base de données

Trois tables : chaque livre appartient à une catégorie, et chaque prêt concerne un livre.

| Table `categories` | Contenu |
| --- | --- |
| `id` | Identifiant unique |
| `nom` | Nom de la catégorie |
| `code` | Début de la cote |

| Table `livres` | Contenu |
| --- | --- |
| `id` | Identifiant unique, jamais réutilisé |
| `titre` | Titre du livre |
| `auteur` | Auteur du livre |
| `annee` | Année de publication |
| `resume` | Résumé, facultatif |
| `couverture` | Adresse de l'image de couverture, facultative |
| `cote` | Cote calculée à partir de la catégorie et de l'auteur |
| `categorie_id` | Identifiant de la catégorie |

| Table `prets` | Contenu |
| --- | --- |
| `id` | Identifiant unique |
| `livre_id` | Identifiant du livre |
| `emprunteur` | Nom de l'emprunteur |
| `date_pret` | Date du prêt |
| `date_retour` | Date de retour prévue |
| `date_rendu` | Date du retour réel, vide tant que le prêt est en cours |

Un livre est disponible quand il n'a aucun prêt en cours. Un index unique empêche la base d'enregistrer deux prêts en cours pour le même livre.

Les noms des emprunteurs sont des données personnelles : ils restent dans `catalogue.db`, exclu du dépôt par `.gitignore`.

## Tests

```
.venv\Scripts\python -m unittest -v
```

Les tests utilisent une base temporaire et ne touchent jamais à `catalogue.db`.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `app.py` | Les routes Flask |
| `catalogue.py` | Les fonctions d'accès à la base : tout le SQL du projet |
| `livres.json` | Le fonds de livres réels |
| `charger_livres.py` | Ajoute les livres de `livres.json` au catalogue |
| `templates/base.html` | Structure commune aux pages |
| `templates/_couverture.html` | Affichage d'une couverture, réutilisé sur plusieurs pages |
| `templates/liste.html` | Étagères, catégories et recherche |
| `templates/fiche.html` | Fiche d'un livre, présentée comme un livre ouvert |
| `templates/prets.html` | Prêts en cours et retards |
| `templates/formulaire.html` | Formulaire d'ajout et de modification |
| `static/style.css` | Apparence des pages et transitions entre elles |
| `static/bibliotheque.svg` | Dessin de la salle de lecture |
| `test_catalogue.py` | Tests des fonctions SQL, des prêts et du fonds de livres |
| `test_app.py` | Tests des routes, avec le client de test de Flask |
| `requirements.txt` | Dépendance du projet (Flask) |
| `.gitignore` | Exclut du dépôt la base de données, l'environnement virtuel et les fichiers générés par Python |
