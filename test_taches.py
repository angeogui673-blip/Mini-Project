"""Tests unitaires du gestionnaire de tâches. Lancement : python -m unittest"""

import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import taches as t


class TestAjouter(unittest.TestCase):
    def test_cree_une_tache_a_faire_avec_id_1(self):
        liste = []
        tache = t.ajouter_tache(liste, "Réviser", "2026-12-01")
        self.assertEqual(
            tache,
            {
                "id": 1,
                "titre": "Réviser",
                "description": "",
                "echeance": "2026-12-01",
                "rappel": None,
                "etat": t.A_FAIRE,
            },
        )
        self.assertEqual(liste, [tache])

    def test_description_et_rappel_enregistres(self):
        tache = t.ajouter_tache([], "Réviser", "2026-12-15", "  Chapitre 3 ", "2026-12-10 08:00")
        self.assertEqual(tache["description"], "Chapitre 3")
        self.assertEqual(tache["rappel"], "2026-12-10T08:00")

    def test_format_du_navigateur_accepte_pour_le_rappel(self):
        tache = t.ajouter_tache([], "Réviser", "2026-12-15", rappel="2026-12-10T08:00")
        self.assertEqual(tache["rappel"], "2026-12-10T08:00")

    def test_rappel_invalide_refuse(self):
        for mauvais_rappel in ("bientôt", "10/12/2026 08:00", "2026-02-30 08:00", "2026-12-10 25:00"):
            with self.subTest(mauvais_rappel=mauvais_rappel):
                liste = []
                with self.assertRaises(ValueError):
                    t.ajouter_tache(liste, "Réviser", "2026-12-15", rappel=mauvais_rappel)
                self.assertEqual(liste, [])

    def test_rappel_avec_fuseau_horaire_ne_fait_pas_planter_la_comparaison(self):
        tache = t.ajouter_tache([], "Réviser", "2026-12-15", rappel="2000-01-01T08:00+01:00")
        self.assertTrue(t.rappel_est_atteint(tache))

    def test_les_id_ne_sont_pas_reutilises_apres_une_suppression_au_milieu(self):
        liste = []
        t.ajouter_tache(liste, "A", "2026-12-01")
        t.ajouter_tache(liste, "B", "2026-12-02")
        t.ajouter_tache(liste, "C", "2026-12-03")
        t.supprimer_tache(liste, 2)
        self.assertEqual(t.ajouter_tache(liste, "D", "2026-12-04")["id"], 4)

    def test_titre_vide_refuse(self):
        liste = []
        with self.assertRaises(ValueError):
            t.ajouter_tache(liste, "   ", "2026-12-01")
        self.assertEqual(liste, [])

    def test_date_invalide_refusee(self):
        for mauvaise_date in ("demain", "01/12/2026", "2026-02-30", ""):
            with self.subTest(mauvaise_date=mauvaise_date):
                liste = []
                with self.assertRaises(ValueError):
                    t.ajouter_tache(liste, "Réviser", mauvaise_date)
                self.assertEqual(liste, [])

    def test_date_sans_tirets_normalisee_pour_que_le_tri_reste_correct(self):
        tache = t.ajouter_tache([], "Réviser", "20261201")
        self.assertEqual(tache["echeance"], "2026-12-01")


class TestLister(unittest.TestCase):
    def test_tri_a_faire_dabord_puis_par_echeance(self):
        liste = []
        t.ajouter_tache(liste, "Lointaine", "2027-01-01")
        t.ajouter_tache(liste, "Proche", "2026-12-01")
        t.ajouter_tache(liste, "Déjà faite", "2026-01-01")
        t.terminer_tache(liste, 3)

        titres = [tache["titre"] for tache in t.lister_taches(liste)]

        self.assertEqual(titres, ["Proche", "Lointaine", "Déjà faite"])
        self.assertEqual(liste[0]["titre"], "Lointaine")  # l'ordre d'origine ne change pas


class TestFormater(unittest.TestCase):
    AUJOURDHUI = date(2026, 6, 15)
    MAINTENANT = datetime(2026, 6, 15, 12, 0)

    def ligne(self, echeance, etat=t.A_FAIRE, description="", rappel=None):
        tache = {
            "id": 1,
            "titre": "Réviser",
            "description": description,
            "echeance": echeance,
            "rappel": rappel,
            "etat": etat,
        }
        return t.formater_tache(tache, self.AUJOURDHUI, self.MAINTENANT)

    def test_description_et_rappel_affiches(self):
        ligne = self.ligne("2026-06-20", description="Chapitre 3", rappel="2026-06-18T08:00")
        self.assertIn("Chapitre 3", ligne)
        self.assertIn("Rappel : 2026-06-18 à 08:00", ligne)
        self.assertNotIn("RAPPEL ATTEINT", ligne)

    def test_rappel_atteint_signale(self):
        self.assertIn("RAPPEL ATTEINT", self.ligne("2026-06-20", rappel="2026-06-15T12:00"))

    def test_rappel_masque_quand_la_tache_est_terminee(self):
        self.assertNotIn("Rappel", self.ligne("2026-06-20", t.TERMINEE, rappel="2026-06-15T08:00"))

    def test_echeance_depassee_signalee(self):
        self.assertIn("EN RETARD", self.ligne("2026-06-14"))

    def test_echeance_aujourdhui_pas_en_retard(self):
        self.assertNotIn("EN RETARD", self.ligne("2026-06-15"))

    def test_tache_terminee_jamais_en_retard(self):
        ligne = self.ligne("2026-06-14", t.TERMINEE)
        self.assertNotIn("EN RETARD", ligne)
        self.assertIn("[x]", ligne)


class TestRappel(unittest.TestCase):
    MAINTENANT = datetime(2026, 6, 15, 12, 0)

    def est_atteint(self, rappel, etat=t.A_FAIRE):
        return t.rappel_est_atteint({"rappel": rappel, "etat": etat}, self.MAINTENANT)

    def test_sans_rappel(self):
        self.assertFalse(self.est_atteint(None))

    def test_avant_a_et_apres_lheure(self):
        self.assertFalse(self.est_atteint("2026-06-15T12:01"))
        self.assertTrue(self.est_atteint("2026-06-15T12:00"))
        self.assertTrue(self.est_atteint("2026-06-15T11:59"))

    def test_tache_terminee(self):
        self.assertFalse(self.est_atteint("2026-06-15T11:59", t.TERMINEE))


class TestTerminerEtSupprimer(unittest.TestCase):
    def setUp(self):
        self.liste = []
        t.ajouter_tache(self.liste, "A", "2026-12-01")

    def test_terminer(self):
        self.assertTrue(t.terminer_tache(self.liste, 1))
        self.assertEqual(self.liste[0]["etat"], t.TERMINEE)

    def test_terminer_id_inconnu(self):
        self.assertFalse(t.terminer_tache(self.liste, 99))
        self.assertEqual(self.liste[0]["etat"], t.A_FAIRE)

    def test_supprimer(self):
        self.assertTrue(t.supprimer_tache(self.liste, 1))
        self.assertEqual(self.liste, [])

    def test_supprimer_id_inconnu(self):
        self.assertFalse(t.supprimer_tache(self.liste, 99))
        self.assertEqual(len(self.liste), 1)


class TestFichierJson(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "taches.json"

    def test_fichier_absent_donne_une_liste_vide(self):
        self.assertEqual(t.charger_taches(self.chemin), [])

    def test_sauvegarde_puis_chargement_conserve_les_taches_et_les_accents(self):
        liste = []
        t.ajouter_tache(liste, "Préparer l'été", "2026-12-01")
        t.sauvegarder_taches(liste, self.chemin)
        self.assertEqual(t.charger_taches(self.chemin), liste)
        self.assertIn("Préparer l'été", self.chemin.read_text(encoding="utf-8"))

    def test_ancienne_tache_sans_description_ni_rappel_reste_lisible(self):
        ancienne = {"id": 1, "titre": "A", "echeance": "2026-12-01", "etat": t.A_FAIRE}
        self.chemin.write_text(json.dumps([ancienne]), encoding="utf-8")
        tache = t.charger_taches(self.chemin)[0]
        self.assertEqual(tache["description"], "")
        self.assertIsNone(tache["rappel"])
        self.assertIn("A", t.formater_tache(tache))

    def test_fichier_corrompu_leve_une_erreur_au_lieu_de_perdre_les_donnees(self):
        self.chemin.write_text("{ pas du json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            t.charger_taches(self.chemin)


if __name__ == "__main__":
    unittest.main()
