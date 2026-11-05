"""Tests des routes du site, avec le client de test de Flask."""

import json
import tempfile
import unittest
from pathlib import Path

import taches as t
from app import app


class TestSite(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "taches.json"

        # Les tests écrivent dans un dossier temporaire, jamais dans les vraies tâches.
        ancien_chemin = app.config["FICHIER_TACHES"]
        app.config["FICHIER_TACHES"] = self.chemin
        self.addCleanup(app.config.__setitem__, "FICHIER_TACHES", ancien_chemin)

        self.client = app.test_client()

    def enregistrer(self, *taches):
        t.sauvegarder_taches(list(taches), self.chemin)

    def tache(self, id_tache=1, titre="Réviser", echeance="2999-12-31", etat=t.A_FAIRE):
        return {"id": id_tache, "titre": titre, "echeance": echeance, "etat": etat}

    def page(self):
        return self.client.get("/").get_data(as_text=True)

    def test_page_vide_invite_a_ajouter(self):
        self.assertIn("Aucune tâche", self.page())

    def test_ajouter_enregistre_puis_redirige(self):
        reponse = self.client.post(
            "/ajouter", data={"titre": "Réviser", "echeance": "2026-12-15"}
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(t.charger_taches(self.chemin)[0]["titre"], "Réviser")
        self.assertIn("15/12/2026", self.page())

    def test_saisie_invalide_affiche_lerreur_et_garde_le_texte(self):
        reponse = self.client.post(
            "/ajouter", data={"titre": "Réviser", "echeance": "demain"}
        )
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("date valide", html)
        self.assertIn('value="Réviser"', html)
        self.assertEqual(t.charger_taches(self.chemin), [])

    def test_terminer(self):
        self.enregistrer(self.tache())
        self.assertEqual(self.client.post("/terminer/1").status_code, 302)
        self.assertEqual(t.charger_taches(self.chemin)[0]["etat"], t.TERMINEE)
        self.assertIn("Terminée", self.page())

    def test_supprimer(self):
        self.enregistrer(self.tache())
        self.assertEqual(self.client.post("/supprimer/1").status_code, 302)
        self.assertEqual(t.charger_taches(self.chemin), [])

    def test_id_inconnu_donne_404(self):
        self.assertEqual(self.client.post("/terminer/99").status_code, 404)
        self.assertEqual(self.client.post("/supprimer/99").status_code, 404)

    def test_un_simple_lien_ne_peut_pas_supprimer(self):
        self.enregistrer(self.tache())
        self.assertEqual(self.client.get("/supprimer/1").status_code, 405)
        self.assertEqual(len(t.charger_taches(self.chemin)), 1)

    def test_retard_signale_seulement_si_echeance_depassee(self):
        self.enregistrer(self.tache(echeance="2999-12-31"))
        self.assertNotIn("En retard", self.page())
        self.enregistrer(self.tache(echeance="2000-01-01"))
        self.assertIn("En retard", self.page())

    def test_le_html_dans_un_titre_est_neutralise(self):
        self.enregistrer(self.tache(titre="<script>alert(1)</script>"))
        html = self.page()
        self.assertNotIn("<script>alert(1)", html)
        self.assertIn("&lt;script&gt;", html)

    def test_fichier_corrompu_affiche_un_message_sans_lecraser(self):
        self.chemin.write_text("{ pas du json", encoding="utf-8")
        for reponse in (
            self.client.get("/"),
            self.client.post("/ajouter", data={"titre": "A", "echeance": "2026-12-15"}),
        ):
            self.assertEqual(reponse.status_code, 500)
            self.assertIn("illisible", reponse.get_data(as_text=True))
        self.assertEqual(self.chemin.read_text(encoding="utf-8"), "{ pas du json")
        with self.assertRaises(json.JSONDecodeError):
            t.charger_taches(self.chemin)


if __name__ == "__main__":
    unittest.main()
