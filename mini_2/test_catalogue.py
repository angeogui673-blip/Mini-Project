"""Tests des fonctions du catalogue, des prêts et du fonds de livres, sur une base temporaire."""

import json
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import catalogue as c
from charger_livres import FICHIER_LIVRES, charger_livres

AUJOURDHUI = date(2026, 6, 15)


class BaseTemporaire(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "test.db"
        self.base = c.connecter(self.chemin)
        self.addCleanup(self.base.close)  # à fermer avant le dossier, sinon Windows refuse de l'effacer
        self.base.execute("PRAGMA synchronous = OFF")  # accélère les tests : pas besoin d'écrire sur le disque à chaque fois
        self.roman = self.categorie("Roman")
        self.bd = self.categorie("Bande dessinée")

    def categorie(self, nom):
        return self.base.execute("SELECT id FROM categories WHERE nom = ?", (nom,)).fetchone()["id"]


class TestAjouter(BaseTemporaire):
    def test_ajoute_et_nettoie_les_valeurs(self):
        id_livre = c.ajouter_livre(
            self.base, "  Germinal ", " Émile Zola ", " 1885 ", self.roman, " Une grève. ", " https://exemple.org/g.jpg "
        )
        self.assertEqual(
            dict(c.trouver_livre(self.base, id_livre)),
            {
                "id": id_livre,
                "titre": "Germinal",
                "auteur": "Émile Zola",
                "annee": 1885,
                "resume": "Une grève.",
                "couverture": "https://exemple.org/g.jpg",
                "cote": "R ZOL",
                "categorie_id": self.roman,
                "categorie": "Roman",
                "emprunteur": None,
                "date_retour": None,
            },
        )

    def test_livre_conserve_apres_fermeture_de_la_base(self):
        id_livre = c.ajouter_livre(self.base, "Germinal", "Émile Zola", 1885, self.roman)
        self.base.close()
        self.base = c.connecter(self.chemin)
        self.addCleanup(self.base.close)
        self.assertEqual(c.trouver_livre(self.base, id_livre)["titre"], "Germinal")

    def test_valeurs_invalides_refusees(self):
        annee_suivante = date.today().year + 1
        cas = [
            ("   ", "Zola", 1885, self.roman),
            ("Germinal", "   ", 1885, self.roman),
            ("Germinal", "Zola", "", self.roman),
            ("Germinal", "Zola", "ancien", self.roman),
            ("Germinal", "Zola", None, self.roman),
            ("Germinal", "Zola", 0, self.roman),
            ("Germinal", "Zola", annee_suivante + 1, self.roman),
            ("Germinal", "Zola", 1885, ""),
            ("Germinal", "Zola", 1885, "roman"),
            ("Germinal", "Zola", 1885, 9999),
        ]
        for titre, auteur, annee, categorie in cas:
            with self.subTest(titre=titre, auteur=auteur, annee=annee, categorie=categorie):
                with self.assertRaises(ValueError):
                    c.ajouter_livre(self.base, titre, auteur, annee, categorie)
        self.assertEqual(c.lister_livres(self.base), [])

    def test_adresse_de_couverture_invalide_refusee(self):
        for adresse in ("image.jpg", "javascript:alert(1)", "ftp://exemple.org/a.jpg", "https://"):
            with self.subTest(adresse=adresse):
                with self.assertRaises(ValueError):
                    c.ajouter_livre(self.base, "A", "B", 2000, self.roman, couverture=adresse)
        self.assertEqual(c.lister_livres(self.base), [])

    def test_annee_suivante_acceptee_pour_un_livre_a_paraitre(self):
        id_livre = c.ajouter_livre(self.base, "À paraître", "Auteur", date.today().year + 1, self.roman)
        self.assertIsNotNone(c.trouver_livre(self.base, id_livre))

    def test_la_base_refuse_elle_meme_une_categorie_inconnue(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.base.execute(
                "INSERT INTO livres (titre, auteur, annee, cote, categorie_id)"
                " VALUES ('A', 'B', 2000, 'R B', 9999)"
            )


class TestCote(unittest.TestCase):
    def test_exemples(self):
        cas = [
            ("R", "Émile Zola", "R ZOL"),
            ("R", "Stendhal", "R STE"),
            ("R", "Mariama Bâ", "R BA"),
            ("J", "Antoine de Saint-Exupéry", "J SAI"),
            ("R", "J.-M. G. Le Clézio", "R LEC"),
            ("P", "Jean de La Fontaine", "P LAF"),
            ("FA", "Ursula K. Le Guin", "FA LEG"),
            ("BD", "René Goscinny et Albert Uderzo", "BD GOS"),
            ("BD", "Eiichirō Oda", "BD ODA"),
            ("100", "René Descartes", "100 DES"),
        ]
        for code, auteur, attendu in cas:
            with self.subTest(auteur=auteur):
                self.assertEqual(c.calculer_cote(code, auteur), attendu)


class TestCategories(BaseTemporaire):
    def test_les_categories_sont_creees_une_seule_fois(self):
        self.assertEqual(len(c.lister_categories(self.base)), len(c.CATEGORIES))
        seconde = c.connecter(self.chemin)
        self.addCleanup(seconde.close)
        self.assertEqual(len(c.lister_categories(seconde)), len(c.CATEGORIES))

    def test_compte_les_livres_et_garde_les_categories_vides(self):
        c.ajouter_livre(self.base, "Germinal", "Émile Zola", 1885, self.roman)
        c.ajouter_livre(self.base, "Nana", "Émile Zola", 1880, self.roman)
        nombres = {ligne["nom"]: ligne["nb"] for ligne in c.lister_categories(self.base)}
        self.assertEqual(nombres["Roman"], 2)
        self.assertEqual(nombres["Théâtre"], 0)

    def test_ordre_alphabetique_en_ignorant_les_accents(self):
        noms = [ligne["nom"] for ligne in c.lister_categories(self.base)]
        self.assertEqual(noms, sorted(noms, key=c.sans_accents))


class TestListerEtRechercher(BaseTemporaire):
    def setUp(self):
        super().setUp()
        c.ajouter_livre(self.base, "Zazie dans le métro", "Raymond Queneau", 1959, self.roman)
        c.ajouter_livre(self.base, "Germinal", "Émile Zola", 1885, self.roman)
        c.ajouter_livre(self.base, "Étoile errante", "J.-M. G. Le Clézio", 1992, self.roman)
        c.ajouter_livre(self.base, "Le Cœur cousu", "Carole Martinez", 2007, self.roman)
        c.ajouter_livre(self.base, "100% maths", "Collectif", 2020, self.categorie("Sciences"))
        c.ajouter_livre(self.base, "Tintin au Tibet", "Hergé", 1960, self.bd)

    def titres(self, terme):
        return [livre["titre"] for livre in c.rechercher_livres(self.base, terme)]

    def test_range_par_categorie_puis_par_cote(self):
        titres = [livre["titre"] for livre in c.lister_livres(self.base)]
        self.assertEqual(
            titres,
            [
                "Tintin au Tibet",  # Bande dessinée
                "Étoile errante",  # Roman : R LEC
                "Le Cœur cousu",  # R MAR
                "Zazie dans le métro",  # R QUE
                "Germinal",  # R ZOL
                "100% maths",  # Sciences
            ],
        )

    def test_lister_une_seule_categorie(self):
        self.assertEqual([livre["titre"] for livre in c.lister_livres(self.base, self.bd)], ["Tintin au Tibet"])

    def test_chaque_livre_connait_le_nom_de_sa_categorie(self):
        self.assertEqual(c.lister_livres(self.base, self.bd)[0]["categorie"], "Bande dessinée")

    def test_recherche_dans_le_titre_lauteur_et_la_cote(self):
        self.assertEqual(self.titres("germ"), ["Germinal"])
        self.assertEqual(self.titres("queneau"), ["Zazie dans le métro"])
        self.assertEqual(self.titres("r zol"), ["Germinal"])

    def test_recherche_sans_tenir_compte_des_accents_ni_des_majuscules(self):
        self.assertEqual(self.titres("EMILE"), ["Germinal"])
        self.assertEqual(self.titres("étoile"), ["Étoile errante"])
        self.assertEqual(self.titres("metro"), ["Zazie dans le métro"])

    def test_recherche_avec_les_lettres_liees(self):
        self.assertEqual(self.titres("coeur"), ["Le Cœur cousu"])
        self.assertEqual(self.titres("CŒUR"), ["Le Cœur cousu"])

    def test_les_jokers_sql_sont_cherches_comme_du_texte(self):
        self.assertEqual(self.titres("%"), ["100% maths"])
        self.assertEqual(self.titres("_"), [])

    def test_sans_resultat(self):
        self.assertEqual(self.titres("introuvable"), [])

    def test_injection_sql_sans_effet(self):
        self.assertEqual(self.titres("' OR 1=1 --"), [])
        self.assertEqual(len(c.lister_livres(self.base)), 6)


class TestInjection(BaseTemporaire):
    def test_un_titre_malveillant_est_enregistre_comme_du_texte(self):
        titre = "'); DROP TABLE livres; --"
        id_livre = c.ajouter_livre(self.base, titre, "Auteur", 2000, self.roman)
        self.assertEqual(c.trouver_livre(self.base, id_livre)["titre"], titre)
        self.assertEqual(len(c.lister_livres(self.base)), 1)

    def test_un_nom_demprunteur_malveillant_est_enregistre_comme_du_texte(self):
        id_livre = c.ajouter_livre(self.base, "A", "B", 2000, self.roman)
        nom = "'); DROP TABLE prets; --"
        c.preter_livre(self.base, id_livre, nom, "2999-01-01")
        self.assertEqual(c.trouver_livre(self.base, id_livre)["emprunteur"], nom)


class TestModifierEtSupprimer(BaseTemporaire):
    def setUp(self):
        super().setUp()
        self.id_livre = c.ajouter_livre(self.base, "Germinal", "Émile Zola", 1885, self.roman)
        self.autre = c.ajouter_livre(self.base, "Nana", "Émile Zola", 1880, self.roman)

    def test_modifier_ne_change_que_ce_livre(self):
        self.assertTrue(
            c.modifier_livre(self.base, self.id_livre, "Germinal", "Zola", 1885, self.roman, "Une grève.", "https://a.org/g.jpg")
        )
        livre = c.trouver_livre(self.base, self.id_livre)
        self.assertEqual(livre["auteur"], "Zola")
        self.assertEqual(livre["resume"], "Une grève.")
        self.assertEqual(livre["couverture"], "https://a.org/g.jpg")
        self.assertEqual(c.trouver_livre(self.base, self.autre)["auteur"], "Émile Zola")

    def test_changer_de_categorie_ou_dauteur_recalcule_la_cote(self):
        c.modifier_livre(self.base, self.id_livre, "Germinal", "Émile Zola", 1885, self.bd)
        self.assertEqual(c.trouver_livre(self.base, self.id_livre)["cote"], "BD ZOL")
        c.modifier_livre(self.base, self.id_livre, "Germinal", "Victor Hugo", 1885, self.bd)
        self.assertEqual(c.trouver_livre(self.base, self.id_livre)["cote"], "BD HUG")

    def test_modifier_avec_valeurs_invalides_ne_change_rien(self):
        with self.assertRaises(ValueError):
            c.modifier_livre(self.base, self.id_livre, "", "Zola", 1885, self.roman)
        self.assertEqual(c.trouver_livre(self.base, self.id_livre)["titre"], "Germinal")

    def test_modifier_id_inconnu(self):
        self.assertFalse(c.modifier_livre(self.base, 99, "A", "B", 2000, self.roman))

    def test_supprimer_ne_retire_que_ce_livre(self):
        self.assertTrue(c.supprimer_livre(self.base, self.id_livre))
        self.assertIsNone(c.trouver_livre(self.base, self.id_livre))
        self.assertIsNotNone(c.trouver_livre(self.base, self.autre))

    def test_supprimer_id_inconnu(self):
        self.assertFalse(c.supprimer_livre(self.base, 99))

    def test_un_id_retire_nest_jamais_reutilise(self):
        c.supprimer_livre(self.base, self.autre)
        nouveau = c.ajouter_livre(self.base, "Thérèse Raquin", "Émile Zola", 1867, self.roman)
        self.assertGreater(nouveau, self.autre)


class TestPrets(BaseTemporaire):
    def setUp(self):
        super().setUp()
        self.id_livre = c.ajouter_livre(self.base, "Germinal", "Émile Zola", 1885, self.roman)
        self.autre = c.ajouter_livre(self.base, "Nana", "Émile Zola", 1880, self.roman)

    def preter(self, id_livre=None, emprunteur="Awa Diop", date_retour="2026-07-06"):
        return c.preter_livre(self.base, id_livre or self.id_livre, emprunteur, date_retour, AUJOURDHUI)

    def test_un_livre_sans_pret_est_disponible(self):
        self.assertIsNone(c.trouver_livre(self.base, self.id_livre)["emprunteur"])

    def test_preter_enregistre_lemprunteur_et_les_dates(self):
        self.preter(emprunteur="  Awa Diop ")
        livre = c.trouver_livre(self.base, self.id_livre)
        self.assertEqual(livre["emprunteur"], "Awa Diop")
        self.assertEqual(livre["date_retour"], "2026-07-06")
        pret = c.lister_prets_en_cours(self.base)[0]
        self.assertEqual(pret["date_pret"], "2026-06-15")
        self.assertIsNone(pret["date_rendu"])

    def test_un_pret_ne_concerne_que_ce_livre(self):
        self.preter()
        self.assertIsNone(c.trouver_livre(self.base, self.autre)["emprunteur"])

    def test_preter_un_livre_deja_prete_est_refuse(self):
        self.preter()
        with self.assertRaisesRegex(ValueError, "déjà en prêt"):
            self.preter(emprunteur="Marc")
        self.assertEqual(c.trouver_livre(self.base, self.id_livre)["emprunteur"], "Awa Diop")

    def test_la_base_refuse_elle_meme_deux_prets_en_cours(self):
        self.preter()
        with self.assertRaises(sqlite3.IntegrityError):
            self.base.execute(
                "INSERT INTO prets (livre_id, emprunteur, date_pret, date_retour)"
                " VALUES (?, 'Marc', '2026-01-01', '2026-02-01')",
                (self.id_livre,),
            )

    def test_saisies_de_pret_invalides_refusees(self):
        cas = [
            ("   ", "2026-07-06"),
            ("Awa", ""),
            ("Awa", "bientôt"),
            ("Awa", "2026-02-30"),
            ("Awa", "2026-06-14"),  # hier
        ]
        for emprunteur, date_retour in cas:
            with self.subTest(emprunteur=emprunteur, date_retour=date_retour):
                with self.assertRaises(ValueError):
                    self.preter(emprunteur=emprunteur, date_retour=date_retour)
        self.assertEqual(c.lister_prets_en_cours(self.base), [])

    def test_retour_prevu_aujourdhui_accepte(self):
        self.preter(date_retour="2026-06-15")
        self.assertEqual(len(c.lister_prets_en_cours(self.base)), 1)

    def test_preter_un_livre_inconnu_est_refuse(self):
        with self.assertRaisesRegex(ValueError, "n'existe pas"):
            self.preter(id_livre=99)

    def test_rendre_rend_le_livre_disponible_et_garde_lhistorique(self):
        self.preter()
        self.assertTrue(c.rendre_livre(self.base, self.id_livre, date(2026, 6, 20)))
        self.assertIsNone(c.trouver_livre(self.base, self.id_livre)["emprunteur"])
        self.assertEqual(c.lister_prets_en_cours(self.base), [])
        historique = c.historique_prets(self.base, self.id_livre)
        self.assertEqual(historique[0]["emprunteur"], "Awa Diop")
        self.assertEqual(historique[0]["date_rendu"], "2026-06-20")

    def test_rendre_un_livre_qui_nest_pas_en_pret(self):
        self.assertFalse(c.rendre_livre(self.base, self.id_livre))

    def test_rendre_deux_fois_ne_change_pas_la_date(self):
        self.preter()
        c.rendre_livre(self.base, self.id_livre, date(2026, 6, 20))
        self.assertFalse(c.rendre_livre(self.base, self.id_livre, date(2026, 6, 25)))
        self.assertEqual(c.historique_prets(self.base, self.id_livre)[0]["date_rendu"], "2026-06-20")

    def test_un_livre_rendu_peut_etre_prete_de_nouveau(self):
        self.preter()
        c.rendre_livre(self.base, self.id_livre, AUJOURDHUI)
        self.preter(emprunteur="Marc")
        self.assertEqual(c.trouver_livre(self.base, self.id_livre)["emprunteur"], "Marc")
        self.assertEqual(len(c.historique_prets(self.base, self.id_livre)), 1)

    def test_historique_du_plus_recent_au_plus_ancien_et_limite(self):
        for numero in range(7):
            self.preter(emprunteur=f"Lecteur {numero}")
            c.rendre_livre(self.base, self.id_livre, AUJOURDHUI + timedelta(days=numero))
        noms = [pret["emprunteur"] for pret in c.historique_prets(self.base, self.id_livre)]
        self.assertEqual(noms, ["Lecteur 6", "Lecteur 5", "Lecteur 4", "Lecteur 3", "Lecteur 2"])

    def test_prets_tries_du_plus_urgent_au_moins_urgent(self):
        self.preter(date_retour="2026-08-01")
        self.preter(id_livre=self.autre, date_retour="2026-07-01")
        titres = [pret["titre"] for pret in c.lister_prets_en_cours(self.base)]
        self.assertEqual(titres, ["Nana", "Germinal"])

    def test_jours_de_retard(self):
        self.assertEqual(c.jours_de_retard("2026-06-16", AUJOURDHUI), 0)
        self.assertEqual(c.jours_de_retard("2026-06-15", AUJOURDHUI), 0)
        self.assertEqual(c.jours_de_retard("2026-06-14", AUJOURDHUI), 1)
        self.assertEqual(c.jours_de_retard("2026-05-15", AUJOURDHUI), 31)

    def test_compter_prets_en_cours_et_en_retard(self):
        self.assertEqual(c.compter_prets(self.base, AUJOURDHUI), {"en_cours": 0, "en_retard": 0})
        self.preter(date_retour="2026-06-15")
        self.preter(id_livre=self.autre, date_retour="2026-06-20")
        self.assertEqual(c.compter_prets(self.base, AUJOURDHUI), {"en_cours": 2, "en_retard": 0})
        self.assertEqual(c.compter_prets(self.base, date(2026, 6, 16)), {"en_cours": 2, "en_retard": 1})
        self.assertEqual(c.compter_prets(self.base, date(2026, 7, 1)), {"en_cours": 2, "en_retard": 2})

    def test_un_livre_rendu_nest_plus_compte(self):
        self.preter(date_retour="2026-06-20")
        c.rendre_livre(self.base, self.id_livre, AUJOURDHUI)
        self.assertEqual(c.compter_prets(self.base, date(2026, 7, 1)), {"en_cours": 0, "en_retard": 0})

    def test_date_de_retour_par_defaut(self):
        self.assertEqual(c.date_retour_par_defaut(AUJOURDHUI), date(2026, 7, 6))

    def test_un_livre_en_pret_ne_peut_pas_etre_retire(self):
        self.preter()
        with self.assertRaisesRegex(ValueError, "en prêt"):
            c.supprimer_livre(self.base, self.id_livre)
        self.assertIsNotNone(c.trouver_livre(self.base, self.id_livre))

    def test_retirer_un_livre_efface_aussi_son_historique(self):
        self.preter()
        c.rendre_livre(self.base, self.id_livre, AUJOURDHUI)
        self.assertTrue(c.supprimer_livre(self.base, self.id_livre))
        self.assertEqual(self.base.execute("SELECT COUNT(*) FROM prets").fetchone()[0], 0)

    def test_modifier_un_livre_garde_son_pret(self):
        self.preter()
        c.modifier_livre(self.base, self.id_livre, "Germinal (édition révisée)", "Émile Zola", 1885, self.roman)
        self.assertEqual(c.trouver_livre(self.base, self.id_livre)["emprunteur"], "Awa Diop")


class TestFondsDeLivres(BaseTemporaire):
    def setUp(self):
        super().setUp()
        with open(FICHIER_LIVRES, encoding="utf-8") as fichier:
            self.fonds = json.load(fichier)

    def test_tout_le_fonds_se_charge(self):
        self.assertEqual(charger_livres(self.base), len(self.fonds))
        self.assertEqual(len(c.lister_livres(self.base)), len(self.fonds))

    def test_relancer_le_chargement_ne_cree_pas_de_doublons(self):
        charger_livres(self.base)
        self.assertEqual(charger_livres(self.base), 0)
        self.assertEqual(len(c.lister_livres(self.base)), len(self.fonds))

    def test_relancer_le_chargement_garde_les_modifications_du_bibliothecaire(self):
        charger_livres(self.base)
        livre = c.rechercher_livres(self.base, "Germinal")[0]
        c.preter_livre(self.base, livre["id"], "Awa", "2999-01-01")
        charger_livres(self.base)
        self.assertEqual(c.trouver_livre(self.base, livre["id"])["emprunteur"], "Awa")

    def test_chaque_categorie_contient_des_livres(self):
        charger_livres(self.base)
        for ligne in c.lister_categories(self.base):
            with self.subTest(categorie=ligne["nom"]):
                self.assertGreater(ligne["nb"], 0)

    def test_chaque_livre_a_un_resume_et_un_auteur_unique_par_titre(self):
        self.assertTrue(all(livre["resume"].strip() for livre in self.fonds))
        paires = [(livre["titre"], livre["auteur"]) for livre in self.fonds]
        self.assertEqual(len(paires), len(set(paires)))

    def test_les_couvertures_viennent_dopen_library_et_sont_toutes_differentes(self):
        adresses = [livre["couverture"] for livre in self.fonds if "couverture" in livre]
        self.assertTrue(adresses)
        self.assertEqual(len(adresses), len(set(adresses)))
        for adresse in adresses:
            self.assertRegex(adresse, r"^https://covers\.openlibrary\.org/b/id/\d+-M\.jpg\?default=false$")

    def test_exemples_de_cotes_du_fonds(self):
        charger_livres(self.base)
        attendues = {
            "Germinal": "R ZOL",
            "Tintin au Tibet": "BD HER",
            "Discours de la méthode": "100 DES",
            "Désert": "R LEC",
            "Fables": "P LAF",
        }
        for titre, cote in attendues.items():
            with self.subTest(titre=titre):
                self.assertEqual(c.rechercher_livres(self.base, titre)[0]["cote"], cote)


if __name__ == "__main__":
    unittest.main()
