"""Interface web : le même carnet que la fenêtre Tkinter, présenté comme l'écran d'un téléphone.

Ce fichier reçoit les requêtes et répond. Les règles restent dans contacts.py, le fichier dans stockage.py
et le mot de passe dans acces.py.
"""

import argparse
import getpass
import socket
import sys
import threading
from datetime import timedelta

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from acces import (
    FICHIER_ACCES,
    LONGUEUR_MIN,
    AccesIllisible,
    GardeTentatives,
    charger_acces,
    enregistrer_mot_de_passe,
    mot_de_passe_correct,
)
from contacts import (
    ContactInvalide,
    ajouter_contact,
    chercher_contacts,
    creer_contact,
    initiale,
    supprimer_contact,
)
from stockage import FICHIER_CONTACTS, FichierIllisible, charger_contacts, sauvegarder_contacts

PORT = 5005


def vers_json(contact):
    """Ajoute au contact l'onglet sous lequel la page doit le ranger."""
    return {**contact, "initiale": initiale(contact)}


def lire_saisie():
    """Retourne le nom et le téléphone envoyés en JSON. Une requête mal formée est refusée plus loin."""
    donnees = request.get_json(silent=True)
    if not isinstance(donnees, dict):
        donnees = {}
    nom = donnees.get("nom")
    telephone = donnees.get("telephone")
    return (nom if isinstance(nom, str) else "", telephone if isinstance(telephone, str) else "")


def creer_app(chemin=FICHIER_CONTACTS, fichier_acces=FICHIER_ACCES):
    """Crée le site. Il demande un mot de passe dès que `fichier_acces` en contient un."""
    acces = charger_acces(fichier_acces)  # lève AccesIllisible plutôt que de démarrer sans protection

    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=16 * 1024,
        SESSION_COOKIE_SAMESITE="Lax",  # un autre site ne peut pas agir en utilisant votre connexion
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )
    if acces:
        app.secret_key = acces["cle_session"]  # signe le cookie de connexion : il ne peut pas être falsifié

    # Flask traite plusieurs requêtes en même temps : le verrou évite que deux écritures se mélangent.
    verrou = threading.Lock()
    garde = GardeTentatives()

    @app.before_request
    def exiger_connexion():
        """S'exécute avant chaque requête : sans connexion, seule la page du mot de passe est accessible."""
        if acces is None or session.get("connecte") or request.endpoint in ("connexion", "static"):
            return None
        if request.path.startswith("/api/"):
            return jsonify(erreur="Connexion requise."), 401
        return redirect(url_for("connexion"))

    @app.after_request
    def interdire_le_cache(reponse):
        """Empêche le navigateur de garder les contacts en mémoire, par exemple après un verrouillage."""
        if request.path.startswith("/api/"):
            reponse.headers["Cache-Control"] = "no-store"
        return reponse

    @app.errorhandler(ContactInvalide)
    def saisie_refusee(erreur):
        """Répond 400 avec le message et le champ à corriger."""
        return jsonify(erreur=str(erreur), champ=erreur.champ), 400

    @app.errorhandler(FichierIllisible)
    def fichier_illisible(_erreur):
        """Répond 500 sans toucher au fichier abîmé."""
        return jsonify(erreur="Le fichier de contacts est illisible : corrigez-le ou déplacez-le."), 500

    @app.errorhandler(OSError)
    def enregistrement_impossible(erreur):
        """Répond 500 si le fichier ne peut pas être lu ou écrit."""
        return jsonify(erreur=f"Enregistrement impossible : {erreur}"), 500

    @app.errorhandler(413)
    def saisie_trop_longue(_erreur):
        """Répond avec un message lisible si la requête dépasse la taille maximale."""
        return jsonify(erreur="Ce texte est trop long."), 413

    @app.route("/connexion", methods=["GET", "POST"])
    def connexion():
        """Affiche l'écran verrouillé et vérifie le mot de passe saisi."""
        if acces is None or session.get("connecte"):
            return redirect(url_for("accueil"))
        if request.method == "GET":
            return render_template("connexion.html")

        adresse = request.remote_addr
        if garde.est_bloque(adresse):
            erreur = "Trop d'essais. Réessayez dans quelques minutes."
            return render_template("connexion.html", erreur=erreur), 429
        if not mot_de_passe_correct(acces, request.form.get("mot_de_passe", "")):
            garde.noter_echec(adresse)
            return render_template("connexion.html", erreur="Mot de passe incorrect."), 401

        garde.oublier(adresse)
        session.clear()
        session["connecte"] = True
        session.permanent = True
        return redirect(url_for("accueil"))

    @app.post("/deconnexion")
    def deconnexion():
        """Verrouille le téléphone sur cet appareil."""
        session.clear()
        return redirect(url_for("connexion"))

    @app.get("/")
    def accueil():
        """Envoie la page du téléphone. Son script demande ensuite les contacts."""
        return render_template("index.html", protege=acces is not None)

    @app.get("/api/contacts")
    def lister():
        """Retourne les contacts qui correspondent à la recherche `q`, et le nombre total."""
        contacts = charger_contacts(chemin)
        resultats = chercher_contacts(contacts, request.args.get("q", ""))
        return jsonify(contacts=[vers_json(c) for c in resultats], total=len(contacts))

    @app.post("/api/contacts")
    def ajouter():
        """Ajoute un contact et le retourne, tel que la logique l'a nettoyé."""
        nom, telephone = lire_saisie()
        with verrou:
            contacts = ajouter_contact(charger_contacts(chemin), nom, telephone)
            sauvegarder_contacts(contacts, chemin)
        return jsonify(contact=vers_json(creer_contact(nom, telephone))), 201

    @app.post("/api/contacts/supprimer")
    def supprimer():
        """Supprime le contact indiqué. Répond 404 s'il n'existe plus."""
        nom, telephone = lire_saisie()
        contact = {"nom": nom, "telephone": telephone}
        with verrou:
            contacts = charger_contacts(chemin)
            if contact not in contacts:
                return jsonify(erreur="Ce contact n'existe plus."), 404
            sauvegarder_contacts(supprimer_contact(contacts, contact), chemin)
        return jsonify(ok=True)

    return app


def adresse_locale():
    """Retourne l'adresse de cet ordinateur sur le réseau. Connecter un socket UDP n'envoie aucun paquet."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sonde:
        try:
            sonde.connect(("10.255.255.255", 1))
            return sonde.getsockname()[0]
        except OSError:
            return None


def choisir_mot_de_passe():
    """Demande le mot de passe dans le terminal, sans l'afficher, puis l'enregistre. Retourne 0 si réussi."""
    print(f"Choisissez un mot de passe d'au moins {LONGUEUR_MIN} caractères. Il ne s'affiche pas quand vous tapez.")
    mot_de_passe = getpass.getpass("Mot de passe : ")
    if getpass.getpass("Confirmez : ") != mot_de_passe:
        print("Les deux saisies sont différentes : rien n'a été changé.")
        return 1
    try:
        enregistrer_mot_de_passe(mot_de_passe)
    except ValueError as erreur:
        print(erreur)
        return 1
    print("Mot de passe enregistré. Relancez le site s'il était ouvert : tous les appareils devront se reconnecter.")
    return 0


def lire_arguments(arguments):
    """Lit les options de la ligne de commande."""
    lecteur = argparse.ArgumentParser(description="Le carnet de contacts, présenté comme un téléphone.")
    lecteur.add_argument(
        "--mot-de-passe", action="store_true", help="choisir ou changer le mot de passe, puis quitter"
    )
    lecteur.add_argument(
        "--reseau", action="store_true", help="ouvrir le site aux appareils du réseau local (mot de passe obligatoire)"
    )
    return lecteur.parse_args(arguments)


def main(arguments=None):
    """Lance le site, ou s'arrête avec un message clair si les conditions ne sont pas réunies."""
    options = lire_arguments(arguments)
    if options.mot_de_passe:
        return choisir_mot_de_passe()

    try:
        acces = charger_acces()
        application = creer_app()
    except AccesIllisible as erreur:
        print(f"Le fichier du mot de passe est abîmé. Relancez avec --mot-de-passe.\n{erreur}")
        return 1

    if options.reseau and acces is None:
        print("Le mode réseau exige un mot de passe. Choisissez-le d'abord : python app.py --mot-de-passe")
        return 1

    if options.reseau:
        print(f"Sur votre téléphone, connecté au même Wi-Fi, ouvrez http://{adresse_locale()}:{PORT}")
        print("Attention : ce site n'est pas chiffré. Utilisez ce mode uniquement sur un Wi-Fi de confiance.")
        hote = "0.0.0.0"
    else:
        print(f"Ouvrez http://127.0.0.1:{PORT} dans votre navigateur.")
        hote = "127.0.0.1"
    print("Ctrl+C pour arrêter.")
    application.run(host=hote, port=PORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
