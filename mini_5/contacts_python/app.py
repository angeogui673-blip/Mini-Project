"""Interface web : le même carnet que la fenêtre Tkinter, présenté comme l'écran d'un téléphone.

Ce fichier reçoit les requêtes et répond. Les règles restent dans contacts.py et le fichier dans stockage.py.
"""

import threading

from flask import Flask, jsonify, render_template, request

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


def creer_app(chemin=FICHIER_CONTACTS):
    """Crée le site. `chemin` permet aux tests de travailler sur un fichier temporaire."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
    # Flask traite plusieurs requêtes en même temps : le verrou évite que deux écritures se mélangent.
    verrou = threading.Lock()

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

    @app.get("/")
    def accueil():
        """Envoie la page du téléphone. Son script demande ensuite les contacts."""
        return render_template("index.html")

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


if __name__ == "__main__":
    print(f"Ouvrez http://127.0.0.1:{PORT} dans votre navigateur. Ctrl+C pour arrêter.")
    creer_app().run(port=PORT)
