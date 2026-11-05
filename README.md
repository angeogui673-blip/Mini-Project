# Gestionnaire de tâches

Petite application pour suivre ses tâches et ne pas oublier leurs échéances : ajouter, lister, terminer et supprimer des tâches. Chaque tâche peut avoir une description et un rappel à une date et une heure choisies. L'application s'utilise en ligne de commande ou depuis un mini site web local présenté comme un bloc-notes. Les deux versions partagent les mêmes fonctions et le même fichier JSON.

Notions pratiquées : fonctions, listes et dictionnaires, lecture/écriture de fichiers, dates et heures, tests unitaires, commits Git. Pour le site : routes Flask, formulaires, gabarits HTML, CSS et animation.

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
Description (Entrée pour passer) : Chapitres 3 et 4
Échéance (AAAA-MM-JJ) : 2026-12-15
Rappel (AAAA-MM-JJ HH:MM, Entrée pour passer) : 2026-11-01 08:00
Tâche 1 ajoutée.

1. Ajouter  2. Lister  3. Terminer  4. Supprimer  5. Quitter
Votre choix : 1
Titre : Rendre le TP Python
Description (Entrée pour passer) :
Échéance (AAAA-MM-JJ) : 2026-12-20
Rappel (AAAA-MM-JJ HH:MM, Entrée pour passer) : 2026-12-18 18:30
Tâche 2 ajoutée.

1. Ajouter  2. Lister  3. Terminer  4. Supprimer  5. Quitter
Votre choix : 2
  1. [ ] 2026-12-15  Réviser les réseaux
       Chapitres 3 et 4
       Rappel : 2026-11-01 à 08:00  (RAPPEL ATTEINT)
  2. [ ] 2026-12-20  Rendre le TP Python
       Rappel : 2026-12-18 à 18:30
```

La liste affiche d'abord les tâches à faire, de l'échéance la plus proche à la plus lointaine, puis les tâches terminées. Une tâche à faire dont l'échéance est dépassée est signalée `(EN RETARD)`.

## Fonctionnement des rappels

Un rappel atteint reste affiché jusqu'à ce que la tâche soit terminée ou supprimée.

- **Sur le site :** une alerte apparaît en haut de la page et le titre de l'onglet change. Si la page reste ouverte, elle se recharge seule quand l'heure arrive, sauf si le formulaire contient une saisie : l'alerte apparaît alors à l'envoi ou quand le formulaire est vidé.
- **En ligne de commande :** les rappels atteints s'affichent au lancement du programme et dans la liste.

Aucun programme ne tourne en arrière-plan : si le site et le menu sont fermés, le rappel s'affiche à la prochaine ouverture.

## Format des données

Chaque tâche est un dictionnaire, et la liste est sauvegardée dans `taches.json`, à côté du programme. La description et le rappel sont facultatifs :

```json
[
  {
    "id": 1,
    "titre": "Réviser les réseaux",
    "description": "Chapitres 3 et 4",
    "echeance": "2026-12-15",
    "rappel": "2026-11-01T08:00",
    "etat": "à faire"
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
| `static/style.css` | Apparence de la page et animation d'ouverture du bloc-notes |
| `static/rappels.js` | Recharge la page quand l'heure d'un rappel arrive |
| `test_taches.py` | Tests unitaires des fonctions |
| `test_app.py` | Tests des routes du site |
| `requirements.txt` | Dépendance du site (Flask) |
| `.gitignore` | Exclut du dépôt les tâches personnelles (`taches.json`), l'environnement virtuel et les fichiers générés par Python |
