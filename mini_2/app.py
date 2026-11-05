"""Site web du catalogue : les routes Flask, qui appellent les fonctions de catalogue.py."""

from datetime import date
from itertools import groupby
from urllib.parse import urlsplit

from flask import Flask, abort, g, redirect, render_template, request, url_for

import catalogue as c

app = Flask(__name__)
app.config["BASE"] = c.FICHIER_BASE

# Rend cette fonction utilisable directement dans les gabarits HTML.
app.add_template_global(c.jours_de_retard)


@app.template_filter("date_fr")
def date_fr(date_iso):
    """Dans un gabarit : {{ "2026-12-15"|date_fr }} affiche 15/12/2026."""
    return date.fromisoformat(date_iso).strftime("%d/%m/%Y")


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


@app.context_processor
def donnees_communes():
    """Donne à toutes les pages le nombre de prêts affiché dans la barre de navigation."""
    return {"nb_prets": c.compter_prets(base())}


def lire_formulaire():
    """Retourne les valeurs envoyées par le formulaire d'un livre."""
    return {
        champ: request.form.get(champ, "")
        for champ in ("titre", "auteur", "annee", "categorie_id", "resume", "couverture")
    }


def afficher_liste(livres, recherche="", categorie=None):
    """Retourne la page de liste, avec les étagères et la navigation entre les rayons."""
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


def afficher_fiche(id_livre, erreur=None, saisie=None, statut=200):
    """Retourne la page d'un livre : ses informations, son prêt et son historique."""
    livre = c.trouver_livre(base(), id_livre)
    if livre is None:
        abort(404)
    page = render_template(
        "fiche.html",
        livre=livre,
        historique=c.historique_prets(base(), id_livre),
        aujourdhui=date.today().isoformat(),
        retour_par_defaut=c.date_retour_par_defaut().isoformat(),
        erreur=erreur,
        saisie=saisie or {},
    )
    return page, statut


def page_precedente(par_defaut):
    """Retourne l'adresse de la page d'où vient la requête, si elle appartient à ce site."""
    precedente = urlsplit(request.referrer or "")
    if precedente.netloc != request.host:
        return par_defaut
    return precedente.path + (f"?{precedente.query}" if precedente.query else "")


# --- Parcourir le catalogue ---

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


@app.get("/livre/<int:id_livre>")
def fiche(id_livre):
    return afficher_fiche(id_livre)


# --- Gérer les livres ---

@app.route("/ajouter", methods=["GET", "POST"])
def ajouter():
    if request.method == "GET":
        return afficher_formulaire({}, modification=False)

    saisie = lire_formulaire()
    try:
        id_livre = c.ajouter_livre(base(), **saisie)
    except ValueError as erreur:
        return afficher_formulaire(saisie, modification=False, erreur=erreur)
    return redirect(url_for("fiche", id_livre=id_livre))


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
        return afficher_formulaire({**saisie, "id": id_livre}, modification=True, erreur=erreur)
    return redirect(url_for("fiche", id_livre=id_livre))


@app.post("/supprimer/<int:id_livre>")
def supprimer(id_livre):
    try:
        if not c.supprimer_livre(base(), id_livre):
            abort(404)
    except ValueError as erreur:
        return afficher_fiche(id_livre, erreur=erreur, statut=409)
    return redirect(url_for("accueil"))


# --- Prêts ---

@app.get("/prets")
def prets():
    return render_template("prets.html", prets=c.lister_prets_en_cours(base()))


@app.post("/livre/<int:id_livre>/preter")
def preter(id_livre):
    if c.trouver_livre(base(), id_livre) is None:
        abort(404)
    saisie = {
        "emprunteur": request.form.get("emprunteur", ""),
        "date_retour": request.form.get("date_retour", ""),
    }
    try:
        c.preter_livre(base(), id_livre, **saisie)
    except ValueError as erreur:
        return afficher_fiche(id_livre, erreur=erreur, saisie=saisie, statut=400)
    return redirect(url_for("fiche", id_livre=id_livre))


@app.post("/livre/<int:id_livre>/rendre")
def rendre(id_livre):
    if c.trouver_livre(base(), id_livre) is None:
        abort(404)
    c.rendre_livre(base(), id_livre)
    return redirect(page_precedente(url_for("fiche", id_livre=id_livre)))


if __name__ == "__main__":
    app.run()
