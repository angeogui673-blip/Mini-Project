"""Site web du catalogue : les routes Flask, qui appellent les fonctions de catalogue.py."""

from itertools import groupby
from urllib.parse import urlsplit

from flask import Flask, abort, g, redirect, render_template, request, url_for

import catalogue as c

app = Flask(__name__)
app.config["BASE"] = c.FICHIER_BASE


def base():
    """Retourne la connexion de la requête en cours, en l'ouvrant au premier appel."""
    if "base" not in g:
        g.base = c.connecter(app.config["BASE"])
    return g.base


@app.teardown_appcontext
def fermer_base(_erreur):
    """Ferme la connexion à la fin de chaque requête."""
    connexion = g.pop("base", None)
    if connexion is not None:
        connexion.close()


def lire_formulaire():
    """Retourne les valeurs envoyées par le formulaire. Une case décochée n'est pas envoyée."""
    return {
        "titre": request.form.get("titre", ""),
        "auteur": request.form.get("auteur", ""),
        "annee": request.form.get("annee", ""),
        "categorie_id": request.form.get("categorie_id", ""),
        "resume": request.form.get("resume", ""),
        "disponible": "disponible" in request.form,
    }


def afficher_liste(livres, recherche="", categorie=None):
    """Retourne la page de liste, avec le meuble à tiroirs des catégories."""
    categories = c.lister_categories(base())
    # SQL a déjà trié les livres par catégorie : on regroupe ceux qui se suivent.
    rayons = [
        (nom, list(livres_du_rayon))
        for nom, livres_du_rayon in groupby(livres, key=lambda livre: livre["categorie"])
    ]
    return render_template(
        "liste.html",
        livres=livres,
        rayons=rayons,
        categories=categories,
        total=sum(ligne["nb"] for ligne in categories),
        recherche=recherche,
        categorie=categorie,
    )


def afficher_formulaire(livre, modification, erreur=None):
    """Retourne la page du formulaire, avec le code 400 si la saisie a été refusée."""
    page = render_template(
        "formulaire.html",
        livre=livre,
        categories=c.lister_categories(base()),
        modification=modification,
        erreur=erreur,
    )
    return page, 400 if erreur else 200


def page_precedente():
    """Retourne l'adresse de la page d'où vient la requête, si elle appartient à ce site."""
    precedente = urlsplit(request.referrer or "")
    if precedente.netloc != request.host:
        return url_for("accueil")
    return precedente.path + (f"?{precedente.query}" if precedente.query else "")


@app.get("/")
def accueil():
    return afficher_liste(c.lister_livres(base()))


@app.get("/categorie/<int:categorie_id>")
def categorie(categorie_id):
    categorie_choisie = c.trouver_categorie(base(), categorie_id)
    if categorie_choisie is None:
        abort(404)
    return afficher_liste(c.lister_livres(base(), categorie_id), categorie=categorie_choisie)


@app.get("/recherche")
def recherche():
    terme = request.args.get("q", "").strip()
    if not terme:
        return redirect(url_for("accueil"))
    return afficher_liste(c.rechercher_livres(base(), terme), recherche=terme)


@app.route("/ajouter", methods=["GET", "POST"])
def ajouter():
    if request.method == "GET":
        return afficher_formulaire({"disponible": True}, modification=False)

    saisie = lire_formulaire()
    try:
        id_livre = c.ajouter_livre(base(), **saisie)
    except ValueError as erreur:
        return afficher_formulaire(saisie, modification=False, erreur=erreur)
    return redirect(url_for("accueil", _anchor=f"livre-{id_livre}"))


@app.route("/modifier/<int:id_livre>", methods=["GET", "POST"])
def modifier(id_livre):
    livre = c.trouver_livre(base(), id_livre)
    if livre is None:
        abort(404)

    if request.method == "GET":
        return afficher_formulaire(livre, modification=True)

    saisie = lire_formulaire()
    try:
        c.modifier_livre(base(), id_livre, **saisie)
    except ValueError as erreur:
        return afficher_formulaire(saisie, modification=True, erreur=erreur)
    return redirect(url_for("accueil", _anchor=f"livre-{id_livre}"))


@app.post("/pret/<int:id_livre>")
def pret(id_livre):
    if not c.changer_disponibilite(base(), id_livre):
        abort(404)
    return redirect(f"{page_precedente()}#livre-{id_livre}")


@app.post("/supprimer/<int:id_livre>")
def supprimer(id_livre):
    if not c.supprimer_livre(base(), id_livre):
        abort(404)
    return redirect(page_precedente())


if __name__ == "__main__":
    app.run()
