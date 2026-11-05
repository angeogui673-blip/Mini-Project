# Gestionnaire de tâches

Petite application pour suivre ses tâches et ne pas oublier leurs échéances : ajouter, lister, terminer et supprimer des tâches. Elle s'utilise en ligne de commande ou depuis un mini site web local. Les deux versions partagent les mêmes fonctions et le même fichier JSON.

Notions pratiquées : fonctions, listes et dictionnaires, lecture/écriture de fichiers, tests unitaires, commits Git. Pour le site : routes Flask, formulaires, gabarits HTML et CSS.

## Lancement en ligne de commande

Python 3.11 ou plus récent, sans dépendance à installer.

```
python taches.py
```

## Lancement du site web

Installation, une seule fois (commandes pour Windows) :

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Lancement :

```
.venv\Scripts\python app.py
```

Ouvrez ensuite <http://127.0.0.1:5000> dans le navigateur. Le site n'est accessible que depuis votre ordinateur. `Ctrl+C` arrête le serveur.

## Exemple d'utilisation en ligne de commande

```
1. Ajouter  2. Lister  3. Terminer  4. Supprimer  5. Quitter
Votre choix : 1
Titre : Réviser les réseaux
Échéance (AAAA-MM-JJ) : 2026-12-15
Tâche 1 ajoutée.

1. Ajouter  2. Lister  3. Terminer  4. Supprimer  5. Quitter
Votre choix : 1
Titre : Rendre le TP Python
Échéance (AAAA-MM-JJ) : 2026-11-01
Tâche 2 ajoutée.

1. Ajouter  2. Lister  3. Terminer  4. Supprimer  5. Quitter
Votre choix : 3
Numéro de la tâche : 1
Tâche 1 terminée.

1. Ajouter  2. Lister  3. Terminer  4. Supprimer  5. Quitter
Votre choix : 2
  2. [ ] 2026-11-01  Rendre le TP Python  (EN RETARD)
  1. [x] 2026-12-15  Réviser les réseaux
```

La liste affiche d'abord les tâches à faire, de l'échéance la plus proche à la plus lointaine, puis les tâches terminées. Une tâche à faire dont l'échéance est dépassée est signalée `(EN RETARD)`.

## Format des données

Chaque tâche est un dictionnaire, et la liste est sauvegardée dans `taches.json`, à côté du programme :

```json
[
  {
    "id": 1,
    "titre": "Réviser les réseaux",
    "echeance": "2026-12-15",
    "etat": "terminée"
  }
]
```

## Tests

```
.venv\Scripts\python -m unittest -v
```

Sans l'installation de Flask, `python -m unittest test_taches -v` lance uniquement les tests de la version en ligne de commande.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `taches.py` | Programme principal : une fonction par action et le menu |
| `app.py` | Site web : les routes Flask, qui appellent les fonctions de `taches.py` |
| `templates/index.html` | Gabarit de la page |
| `static/style.css` | Apparence de la page |
| `test_taches.py` | Tests unitaires des fonctions |
| `test_app.py` | Tests des routes du site |
| `requirements.txt` | Dépendance du site (Flask) |
| `.gitignore` | Exclut du dépôt les tâches personnelles (`taches.json`), l'environnement virtuel et les fichiers générés par Python |
