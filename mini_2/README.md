# Catalogue de livres

Mini-application web locale pour une petite bibliothèque scolaire, dont le catalogue était difficile à tenir à jour dans un simple fichier. Le bibliothécaire peut ajouter, rechercher, modifier, prêter et retirer des livres depuis son navigateur. Les livres sont rangés par catégorie et portent une cote, comme dans une vraie bibliothèque.

Le catalogue peut se remplir avec un fonds de 95 livres réels, de Zola à *Dune*, répartis dans 12 catégories.

Notions pratiquées : routes et requêtes HTTP, SQL de base (CRUD), jointures entre tables, clé étrangère, gabarits HTML, formulaires, tests du serveur.

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

- **Parcourir :** chaque tiroir du meuble ouvre une catégorie. « Tous les livres » affiche tous les rayons.
- **Rechercher :** le champ de recherche cherche dans le titre, l'auteur et la cote, sans tenir compte des majuscules ni des accents. « moliere » trouve Molière et « P HUG » trouve *Les Contemplations*.
- **Prêter et rendre :** un clic sur une fiche change le tampon « Disponible » ou « Emprunté ».
- **Ajouter et modifier :** le formulaire demande le titre, l'auteur, l'année, la catégorie et un résumé facultatif. La cote se calcule toute seule.
- **Retirer :** le bouton « Retirer » supprime le livre après confirmation.

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

## Routes

| Méthode | Adresse | Rôle |
| --- | --- | --- |
| GET | `/` | Tous les livres, rangés par catégorie |
| GET | `/categorie/<id>` | Livres d'une seule catégorie |
| GET | `/recherche?q=...` | Livres correspondant à la recherche |
| GET, POST | `/ajouter` | Affiche le formulaire, puis enregistre le livre |
| GET, POST | `/modifier/<id>` | Affiche le formulaire prérempli, puis enregistre les changements |
| POST | `/pret/<id>` | Prête le livre, ou le rend s'il est emprunté |
| POST | `/supprimer/<id>` | Retire le livre |

## Base de données

Deux tables, reliées par une clé étrangère : chaque livre appartient à une catégorie.

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
| `cote` | Cote calculée à partir de la catégorie et de l'auteur |
| `disponible` | 1 si le livre est disponible, 0 s'il est emprunté |
| `categorie_id` | Identifiant de la catégorie |

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
| `templates/liste.html` | Page de la liste, des catégories et de la recherche |
| `templates/formulaire.html` | Formulaire d'ajout et de modification |
| `static/style.css` | Apparence des pages |
| `test_catalogue.py` | Tests des fonctions SQL et du fonds de livres |
| `test_app.py` | Tests des routes, avec le client de test de Flask |
| `requirements.txt` | Dépendance du projet (Flask) |
| `.gitignore` | Exclut du dépôt la base de données, l'environnement virtuel et les fichiers générés par Python |
