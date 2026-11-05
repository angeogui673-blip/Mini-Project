"""Version web du gestionnaire de tâches.

Ce fichier ne contient que les routes : les actions restent dans taches.py,
et le site utilise le même fichier taches.json que le menu en ligne de commande.
"""

import json
from datetime import date

from flask import Flask, abort, redirect, render_template, request, url_for

import taches as t

app = Flask(__name__)
app.config["FICHIER_TACHES"] = t.FICHIER_TACHES


def charger():
    return t.charger_taches(app.config["FICHIER_TACHES"])


def sauvegarder(taches):
    t.sauvegarder_taches(taches, app.config["FICHIER_TACHES"])


def afficher_page(taches, erreur=None, titre="", echeance="", statut=200):
    """Prépare les tâches pour le gabarit HTML et retourne la page."""
    lignes = [
        {
            **tache,
            "terminee": tache["etat"] == t.TERMINEE,
            "en_retard": t.est_en_retard(tache),
            "date_affichee": date.fromisoformat(tache["echeance"]).strftime("%d/%m/%Y"),
        }
        for tache in t.lister_taches(taches)
    ]
    page = render_template(
        "index.html", taches=lignes, erreur=erreur, titre=titre, echeance=echeance
    )
    return page, statut


@app.route("/")
def accueil():
    return afficher_page(charger())


@app.post("/ajouter")
def ajouter():
    taches = charger()
    titre = request.form.get("titre", "")
    echeance = request.form.get("echeance", "")
    try:
        t.ajouter_tache(taches, titre, echeance)
    except ValueError as erreur:
        return afficher_page(taches, str(erreur), titre, echeance, statut=400)
    sauvegarder(taches)
    return redirect(url_for("accueil"))


@app.post("/terminer/<int:id_tache>")
def terminer(id_tache):
    taches = charger()
    if not t.terminer_tache(taches, id_tache):
        abort(404)
    sauvegarder(taches)
    return redirect(url_for("accueil"))


@app.post("/supprimer/<int:id_tache>")
def supprimer(id_tache):
    taches = charger()
    if not t.supprimer_tache(taches, id_tache):
        abort(404)
    sauvegarder(taches)
    return redirect(url_for("accueil"))


@app.errorhandler(json.JSONDecodeError)
def fichier_illisible(_erreur):
    # Comme dans le menu : on n'écrit rien, pour ne pas écraser les tâches récupérables.
    message = "Le fichier taches.json est illisible. Corrigez-le ou supprimez-le, puis rechargez la page."
    return afficher_page([], message, statut=500)


if __name__ == "__main__":
    app.run()
