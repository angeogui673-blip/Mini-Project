"""Version web du gestionnaire de tâches.

Ce fichier ne contient que les routes : les actions restent dans taches.py,
et le site utilise le même fichier taches.json que le menu en ligne de commande.
"""

import json
from datetime import date, datetime

from flask import Flask, abort, redirect, render_template, request, url_for

import taches as t

app = Flask(__name__)
app.config["FICHIER_TACHES"] = t.FICHIER_TACHES


def charger():
    return t.charger_taches(app.config["FICHIER_TACHES"])


def sauvegarder(taches):
    t.sauvegarder_taches(taches, app.config["FICHIER_TACHES"])


def retour_accueil():
    """Revient à la page après une action, sans rejouer l'ouverture du bloc-notes."""
    return redirect(url_for("accueil", ouvert=1))


def preparer_ligne(tache):
    """Ajoute à une tâche ce que le gabarit HTML doit afficher."""
    rappel = tache["rappel"]
    return {
        **tache,
        "terminee": tache["etat"] == t.TERMINEE,
        "en_retard": t.est_en_retard(tache),
        "rappel_atteint": t.rappel_est_atteint(tache),
        "date_affichee": date.fromisoformat(tache["echeance"]).strftime("%d/%m/%Y"),
        "rappel_affiche": datetime.fromisoformat(rappel).strftime("%d/%m/%Y à %H:%M") if rappel else "",
    }


def afficher_page(taches, erreur=None, saisie=None, statut=200, ouverture=False):
    """Prépare les tâches pour le gabarit HTML et retourne la page."""
    lignes = [preparer_ligne(tache) for tache in t.lister_taches(taches)]
    page = render_template(
        "index.html",
        taches=lignes,
        rappels=[ligne for ligne in lignes if ligne["rappel_atteint"]],
        erreur=erreur,
        saisie=saisie or {},
        ouverture=ouverture,
    )
    return page, statut


@app.route("/")
def accueil():
    return afficher_page(charger(), ouverture="ouvert" not in request.args)


@app.post("/ajouter")
def ajouter():
    taches = charger()
    saisie = {
        champ: request.form.get(champ, "")
        for champ in ("titre", "description", "echeance", "rappel")
    }
    try:
        t.ajouter_tache(
            taches, saisie["titre"], saisie["echeance"], saisie["description"], saisie["rappel"]
        )
    except ValueError as erreur:
        return afficher_page(taches, str(erreur), saisie, statut=400)
    sauvegarder(taches)
    return retour_accueil()


@app.post("/terminer/<int:id_tache>")
def terminer(id_tache):
    taches = charger()
    if not t.terminer_tache(taches, id_tache):
        abort(404)
    sauvegarder(taches)
    return retour_accueil()


@app.post("/supprimer/<int:id_tache>")
def supprimer(id_tache):
    taches = charger()
    if not t.supprimer_tache(taches, id_tache):
        abort(404)
    sauvegarder(taches)
    return retour_accueil()


@app.errorhandler(json.JSONDecodeError)
def fichier_illisible(_erreur):
    # Comme dans le menu : on n'écrit rien, pour ne pas écraser les tâches récupérables.
    message = "Le fichier taches.json est illisible. Corrigez-le ou supprimez-le, puis rechargez la page."
    return afficher_page([], message, statut=500)


if __name__ == "__main__":
    app.run()
