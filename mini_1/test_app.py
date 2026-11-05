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

    def tache(self, id_tache=1, titre="Réviser", echeance="2999-12-31", etat=t.A_FAIRE, description="", rappel=None):
        return {
            "id": id_tache,
            "titre": titre,
            "description": description,
            "echeance": echeance,
            "rappel": rappel,
            "etat": etat,
        }

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

    def test_le_titre_de_la_page_invite_a_creer_des_taches(self):
        self.assertIn("Créez vos tâches ici", self.page())

    def test_ajouter_enregistre_la_description_et_le_rappel(self):
        self.client.post(
            "/ajouter",
            data={
                "titre": "Réviser",
                "description": "Chapitres 3 et 4",
                "echeance": "2999-12-31",
                "rappel": "2999-12-30T08:00",
            },
        )
        tache = t.charger_taches(self.chemin)[0]
        self.assertEqual(tache["description"], "Chapitres 3 et 4")
        self.assertEqual(tache["rappel"], "2999-12-30T08:00")

        html = self.page()
        self.assertIn("Chapitres 3 et 4", html)
        self.assertIn("30/12/2999 à 08:00", html)

    def test_rappel_invalide_refuse_et_saisie_conservee(self):
        reponse = self.client.post(
            "/ajouter",
            data={"titre": "Réviser", "description": "Chapitre 3", "echeance": "2999-12-31", "rappel": "bientôt"},
        )
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Le rappel doit être", html)
        self.assertIn(">Chapitre 3</textarea>", html)
        self.assertEqual(t.charger_taches(self.chemin), [])

    def test_rappel_atteint_affiche_lalerte_et_change_le_titre_de_longlet(self):
        self.enregistrer(self.tache(rappel="2000-01-01T08:00"))
        html = self.page()
        self.assertIn('class="message rappels"', html)
        self.assertIn("<title>(1) Rappel : Mes tâches</title>", html)
        self.assertNotIn("data-rappel", html)

    def test_rappel_a_venir_sans_alerte_mais_surveille_par_la_page(self):
        self.enregistrer(self.tache(rappel="2999-12-30T08:00"))
        html = self.page()
        self.assertNotIn('class="message rappels"', html)
        self.assertIn('data-rappel="2999-12-30T08:00"', html)

    def test_tache_terminee_ne_declenche_plus_son_rappel(self):
        self.enregistrer(self.tache(rappel="2000-01-01T08:00", etat=t.TERMINEE))
        html = self.page()
        self.assertNotIn('class="message rappels"', html)
        self.assertNotIn("data-rappel", html)
        self.assertNotIn("01/01/2000", html)

    def test_le_html_dans_une_description_est_neutralise(self):
        self.enregistrer(self.tache(description="<script>alert(1)</script>"))
        self.assertNotIn("<script>alert(1)", self.page())

    def test_le_bloc_notes_souvre_seulement_a_larrivee(self):
        self.assertIn('class="couverture"', self.page())

        reponse = self.client.post(
            "/ajouter", data={"titre": "Réviser", "echeance": "2999-12-31"}
        )
        self.assertIn("ouvert=1", reponse.headers["Location"])
        apres_action = self.client.get(reponse.headers["Location"]).get_data(as_text=True)
        self.assertNotIn('class="couverture"', apres_action)

        erreur = self.client.post("/ajouter", data={"titre": "", "echeance": ""})
        self.assertNotIn('class="couverture"', erreur.get_data(as_text=True))

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
