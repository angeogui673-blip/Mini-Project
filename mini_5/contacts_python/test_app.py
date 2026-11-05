"""Tests du site : les routes Flask, sur un fichier temporaire."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import creer_app
from stockage import charger_contacts, sauvegarder_contacts


class TestSite(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "contacts.json"
        self.client = creer_app(self.chemin).test_client()

    def ajouter(self, nom="Awa", telephone="06 12 34 56 78"):
        return self.client.post("/api/contacts", json={"nom": nom, "telephone": telephone})

    def test_page_du_telephone(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 200)
        page = reponse.get_data(as_text=True)
        self.assertIn('class="telephone"', page)
        self.assertIn("telephone.js", page)

    def test_fichiers_statiques_servis(self):
        for fichier in ("telephone.css", "telephone.js"):
            with self.client.get(f"/static/{fichier}") as reponse:
                self.assertEqual(reponse.status_code, 200)

    def test_carnet_vide(self):
        reponse = self.client.get("/api/contacts")
        self.assertEqual(reponse.get_json(), {"contacts": [], "total": 0})

    def test_ajout_retourne_le_contact_nettoye_et_enregistre(self):
        reponse = self.ajouter("  Émile   Kouassi ", " 06  12 ")
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(
            reponse.get_json()["contact"],
            {"nom": "Émile Kouassi", "telephone": "06 12", "initiale": "E"},
        )
        self.assertEqual(charger_contacts(self.chemin), [{"nom": "Émile Kouassi", "telephone": "06 12"}])

    def test_saisie_refusee_indique_le_champ(self):
        cas = [("", "0612345678", "nom"), ("Awa", "", "telephone"), ("Awa", "abc", "telephone")]
        for nom, telephone, champ in cas:
            with self.subTest(nom=nom, telephone=telephone):
                reponse = self.ajouter(nom, telephone)
                self.assertEqual(reponse.status_code, 400)
                self.assertEqual(reponse.get_json()["champ"], champ)
        self.assertFalse(self.chemin.exists())

    def test_doublon_refuse(self):
        self.ajouter()
        self.assertEqual(self.ajouter("AWA", "06.12.34.56.78").status_code, 400)
        self.assertEqual(len(charger_contacts(self.chemin)), 1)

    def test_requetes_mal_formees_refusees(self):
        cas = [
            {"data": "nom=Awa", "content_type": "text/plain"},
            {"data": "{pas du json", "content_type": "application/json"},
            {"json": ["Awa", "112"]},
            {"json": {"nom": 12, "telephone": ["112"]}},
        ]
        for options in cas:
            with self.subTest(options=options):
                self.assertEqual(self.client.post("/api/contacts", **options).status_code, 400)

    def test_requete_trop_grosse_refusee(self):
        reponse = self.ajouter("A" * 20000, "112")
        self.assertEqual(reponse.status_code, 413)
        self.assertIn("trop long", reponse.get_json()["erreur"])
        self.assertFalse(self.chemin.exists())

    def test_recherche_utilise_la_logique_commune(self):
        self.ajouter("Émile", "06 12")
        self.ajouter("Zoé", "07 99")
        recherches = {"emile": ["Émile"], "07.9": ["Zoé"], "xyz": []}
        for texte, attendus in recherches.items():
            with self.subTest(texte=texte):
                donnees = self.client.get("/api/contacts", query_string={"q": texte}).get_json()
                self.assertEqual([c["nom"] for c in donnees["contacts"]], attendus)
                self.assertEqual(donnees["total"], 2)

    def test_liste_triee_avec_initiales(self):
        for nom in ["Zoé", "Émile", "3 Frères"]:
            self.ajouter(nom, "0612345678")
        contacts = self.client.get("/api/contacts").get_json()["contacts"]
        self.assertEqual(
            [(c["nom"], c["initiale"]) for c in contacts],
            [("3 Frères", "#"), ("Émile", "E"), ("Zoé", "Z")],
        )

    def test_suppression(self):
        self.ajouter("Awa", "112")
        self.ajouter("Zoé", "113")
        reponse = self.client.post("/api/contacts/supprimer", json={"nom": "Awa", "telephone": "112"})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(charger_contacts(self.chemin), [{"nom": "Zoé", "telephone": "113"}])

    def test_suppression_d_un_contact_absent(self):
        self.ajouter("Awa", "112")
        reponse = self.client.post("/api/contacts/supprimer", json={"nom": "Awa", "telephone": "999"})
        self.assertEqual(reponse.status_code, 404)
        self.assertEqual(len(charger_contacts(self.chemin)), 1)

    def test_fichier_abime_ni_lu_ni_ecrase(self):
        self.chemin.write_bytes(b"{abime")
        self.assertEqual(self.client.get("/api/contacts").status_code, 500)
        reponse = self.ajouter()
        self.assertEqual(reponse.status_code, 500)
        self.assertIn("illisible", reponse.get_json()["erreur"])
        self.assertEqual(self.chemin.read_bytes(), b"{abime")

    def test_echec_d_ecriture(self):
        self.ajouter("Awa", "112")
        with mock.patch("app.sauvegarder_contacts", side_effect=OSError("disque plein")):
            reponse = self.ajouter("Zoé", "113")
        self.assertEqual(reponse.status_code, 500)
        self.assertIn("disque plein", reponse.get_json()["erreur"])
        self.assertEqual(len(charger_contacts(self.chemin)), 1)

    def test_le_site_voit_ce_que_la_fenetre_a_enregistre(self):
        sauvegarder_contacts([{"nom": "Fenêtre", "telephone": "112"}], self.chemin)
        contacts = self.client.get("/api/contacts").get_json()["contacts"]
        self.assertEqual(contacts[0]["nom"], "Fenêtre")


if __name__ == "__main__":
    unittest.main()
