"""Tests des routes du site, avec le client de test de Flask."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import catalogue as c
from app import app


class TestSite(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "test.db"

        # Les tests écrivent dans un dossier temporaire, jamais dans le vrai catalogue.
        ancien_chemin = app.config["BASE"]
        app.config["BASE"] = self.chemin
        self.addCleanup(app.config.__setitem__, "BASE", ancien_chemin)

        self.client = app.test_client()
        self.roman = self.id_categorie("Roman")
        self.bd = self.id_categorie("Bande dessinée")

    def id_categorie(self, nom):
        base = c.connecter(self.chemin)
        id_categorie = base.execute("SELECT id FROM categories WHERE nom = ?", (nom,)).fetchone()["id"]
        base.close()
        return id_categorie

    def ajouter_en_base(self, titre="Germinal", auteur="Émile Zola", annee=1885, categorie=None, resume="", couverture=""):
        base = c.connecter(self.chemin)
        id_livre = c.ajouter_livre(base, titre, auteur, annee, categorie or self.roman, resume, couverture)
        base.close()
        return id_livre

    def preter_en_retard(self, id_livre, emprunteur="Awa Diop", jours=3):
        """Enregistre un prêt dont la date de retour est dépassée de quelques jours."""
        retour = date.today() - timedelta(days=jours)
        base = c.connecter(self.chemin)
        c.preter_livre(base, id_livre, emprunteur, retour.isoformat(), aujourdhui=retour)
        base.close()

    def livres_en_base(self):
        base = c.connecter(self.chemin)
        livres = [dict(livre) for livre in c.lister_livres(base)]
        base.close()
        return livres

    def saisie(self, **valeurs):
        return {"titre": "Germinal", "auteur": "Émile Zola", "annee": "1885", "categorie_id": self.roman, **valeurs}

    def demain(self):
        return (date.today() + timedelta(days=1)).isoformat()

    def texte(self, url):
        return self.client.get(url).get_data(as_text=True)

    # --- Liste et catégories ---

    def test_catalogue_vide_invite_a_ajouter(self):
        self.assertIn("Le catalogue est vide", self.texte("/"))

    def test_etagere_affiche_le_livre_et_sa_cote(self):
        self.ajouter_en_base()
        html = self.texte("/")
        self.assertIn("<b>Germinal</b>", html)
        self.assertIn("Émile Zola", html)
        self.assertIn("R ZOL", html)

    def test_liste_range_les_livres_sous_le_nom_de_leur_categorie(self):
        self.ajouter_en_base("Germinal")
        self.ajouter_en_base("Tintin au Tibet", "Hergé", 1960, self.bd)
        html = self.texte("/")
        self.assertIn("<h2>Bande dessinée <small>1 livre</small></h2>", html)
        self.assertLess(html.index("<h2>Bande dessinée"), html.index("<b>Tintin au Tibet"))
        self.assertLess(html.index("<b>Tintin au Tibet"), html.index("<h2>Roman"))
        self.assertLess(html.index("<h2>Roman"), html.index("<b>Germinal"))

    def test_les_rayons_suivent_lordre_alphabetique_malgre_les_accents(self):
        self.ajouter_en_base("Pietr le Letton", "Georges Simenon", 1931, self.id_categorie("Policier"))
        self.ajouter_en_base("Alcools", "Guillaume Apollinaire", 1913, self.id_categorie("Poésie"))
        html = self.texte("/")
        self.assertLess(html.index("<h2>Poésie"), html.index("<h2>Policier"))

    def test_la_navigation_affiche_les_categories_et_leur_nombre_de_livres(self):
        self.ajouter_en_base()
        html = self.texte("/")
        self.assertRegex(html, r"Roman <small>1</small>")
        self.assertRegex(html, r"Théâtre <small>0</small>")
        self.assertIn("Tous les livres <small>1</small>", html)

    def test_page_dune_categorie_ne_montre_que_ses_livres(self):
        self.ajouter_en_base("Germinal")
        self.ajouter_en_base("Tintin au Tibet", "Hergé", 1960, self.bd)
        html = self.texte(f"/categorie/{self.bd}")
        self.assertIn("<b>Tintin au Tibet</b>", html)
        self.assertNotIn("<b>Germinal</b>", html)
        self.assertIn('aria-current="page"', html)

    def test_categorie_vide_le_dit(self):
        self.assertIn("Aucun livre dans cette catégorie", self.texte(f"/categorie/{self.bd}"))

    # --- Couvertures ---

    def test_la_couverture_saffiche_avec_la_version_dessinee_en_secours(self):
        self.ajouter_en_base(couverture="https://exemple.org/g-M.jpg")
        html = self.texte("/")
        self.assertIn('src="https://exemple.org/g-M.jpg"', html)
        self.assertIn('class="couverture-dessinee"', html)
        self.assertIn('onerror="this.remove()"', html)

    def test_sans_image_seule_la_couverture_dessinee_saffiche(self):
        self.ajouter_en_base()
        html = self.texte("/")
        self.assertIn('class="couverture-dessinee"', html)
        self.assertNotIn("<img", html)

    def test_la_fiche_demande_la_grande_image(self):
        id_livre = self.ajouter_en_base(couverture="https://exemple.org/g-M.jpg")
        self.assertIn('src="https://exemple.org/g-L.jpg"', self.texte(f"/livre/{id_livre}"))

    def test_adresse_de_couverture_invalide_refusee(self):
        reponse = self.client.post("/ajouter", data=self.saisie(couverture="javascript:alert(1)"))
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(self.livres_en_base(), [])

    # --- Recherche ---

    def test_recherche_filtre_la_liste_et_garde_le_terme(self):
        self.ajouter_en_base("Germinal")
        self.ajouter_en_base("Nana")
        html = self.texte("/recherche?q=germ")
        self.assertIn("<b>Germinal</b>", html)
        self.assertNotIn("<b>Nana</b>", html)
        self.assertIn('value="germ"', html)
        self.assertIn("1 résultat pour", html)

    def test_recherche_sans_resultat_le_dit(self):
        self.ajouter_en_base()
        self.assertIn("Aucun livre ne correspond", self.texte("/recherche?q=introuvable"))

    def test_recherche_vide_revient_a_la_liste(self):
        reponse = self.client.get("/recherche?q=%20%20")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.headers["Location"], "/")

    # --- Fiche ---

    def test_fiche_affiche_toutes_les_informations(self):
        id_livre = self.ajouter_en_base(resume="Une grande grève.")
        html = self.texte(f"/livre/{id_livre}")
        self.assertIn("<h1>Germinal</h1>", html)
        self.assertIn("Émile Zola, 1885", html)
        self.assertIn("Une grande grève.", html)
        self.assertIn("R ZOL", html)
        self.assertIn("Roman", html)
        self.assertIn("Disponible", html)

    def test_fiche_propose_une_date_de_retour_par_defaut(self):
        id_livre = self.ajouter_en_base()
        attendue = c.date_retour_par_defaut().isoformat()
        self.assertIn(f'value="{attendue}"', self.texte(f"/livre/{id_livre}"))

    # --- Ajout ---

    def test_formulaire_dajout_propose_les_categories(self):
        html = self.texte("/ajouter")
        self.assertIn("Ajouter un livre", html)
        self.assertIn(">Théâtre</option>", html)

    def test_ajouter_enregistre_puis_ouvre_la_fiche(self):
        reponse = self.client.post("/ajouter", data=self.saisie(resume="Une grève."))
        self.assertEqual(reponse.status_code, 302)
        livre = self.livres_en_base()[0]
        self.assertEqual(reponse.headers["Location"], f"/livre/{livre['id']}")
        self.assertEqual(livre["titre"], "Germinal")
        self.assertEqual(livre["resume"], "Une grève.")
        self.assertEqual(livre["cote"], "R ZOL")

    def test_saisie_invalide_affiche_lerreur_et_garde_le_texte(self):
        reponse = self.client.post("/ajouter", data=self.saisie(annee="ancien", resume="Mon résumé"))
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("L&#39;année doit être un nombre", html)
        self.assertIn('value="Germinal"', html)
        self.assertIn(">Mon résumé</textarea>", html)
        self.assertRegex(html, rf'value="{self.roman}"\s+selected')
        self.assertEqual(self.livres_en_base(), [])

    def test_categorie_absente_ou_inconnue_refusee(self):
        for categorie in ("", "9999", "abc"):
            with self.subTest(categorie=categorie):
                reponse = self.client.post("/ajouter", data=self.saisie(categorie_id=categorie))
                self.assertEqual(reponse.status_code, 400)
                self.assertIn("Choisissez une catégorie", reponse.get_data(as_text=True))
        self.assertEqual(self.livres_en_base(), [])

    # --- Modification ---

    def test_formulaire_de_modification_prerempli(self):
        id_livre = self.ajouter_en_base(categorie=self.bd, resume="Une grève.", couverture="https://a.org/g.jpg")
        html = self.texte(f"/modifier/{id_livre}")
        self.assertIn('value="Germinal"', html)
        self.assertIn('value="1885"', html)
        self.assertIn('value="https://a.org/g.jpg"', html)
        self.assertIn(">Une grève.</textarea>", html)
        self.assertRegex(html, rf'value="{self.bd}"\s+selected')
        self.assertIn("Enregistrer", html)

    def test_modifier_enregistre_et_recalcule_la_cote(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(f"/modifier/{id_livre}", data=self.saisie(categorie_id=self.bd))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.headers["Location"], f"/livre/{id_livre}")
        livre = self.livres_en_base()[0]
        self.assertEqual(livre["categorie"], "Bande dessinée")
        self.assertEqual(livre["cote"], "BD ZOL")

    def test_modification_invalide_ne_change_rien(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(f"/modifier/{id_livre}", data=self.saisie(titre="  "))
        self.assertEqual(reponse.status_code, 400)
        self.assertIn(f'href="/livre/{id_livre}"', reponse.get_data(as_text=True))  # le lien Annuler reste correct
        self.assertEqual(self.livres_en_base()[0]["titre"], "Germinal")

    # --- Prêts ---

    def test_preter_enregistre_le_pret_et_revient_a_la_fiche(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(
            f"/livre/{id_livre}/preter", data={"emprunteur": "Awa Diop", "date_retour": self.demain()}
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.headers["Location"], f"/livre/{id_livre}")
        html = self.texte(f"/livre/{id_livre}")
        self.assertIn("Awa Diop", html)
        self.assertIn("Enregistrer le retour", html)
        self.assertNotIn('name="emprunteur"', html)
        self.assertNotIn("Retirer du catalogue", html)

    def test_pret_invalide_affiche_lerreur_et_garde_la_saisie(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(
            f"/livre/{id_livre}/preter", data={"emprunteur": "Awa Diop", "date_retour": "2000-01-01"}
        )
        html = reponse.get_data(as_text=True)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("déjà passée", html)
        self.assertIn('value="Awa Diop"', html)
        self.assertIsNone(self.livres_en_base()[0]["emprunteur"])

    def test_preter_un_livre_deja_prete_refuse(self):
        id_livre = self.ajouter_en_base()
        donnees = {"emprunteur": "Awa", "date_retour": self.demain()}
        self.client.post(f"/livre/{id_livre}/preter", data=donnees)
        reponse = self.client.post(f"/livre/{id_livre}/preter", data={**donnees, "emprunteur": "Marc"})
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(self.livres_en_base()[0]["emprunteur"], "Awa")

    def test_etagere_signale_un_livre_emprunte_sans_afficher_lemprunteur(self):
        id_livre = self.ajouter_en_base()
        self.client.post(f"/livre/{id_livre}/preter", data={"emprunteur": "Awa Diop", "date_retour": self.demain()})
        html = self.texte("/")
        self.assertIn('class="etat emprunte"', html)
        self.assertNotIn("Awa Diop", html)

    def test_retard_signale_sur_letagere_la_fiche_et_les_prets(self):
        id_livre = self.ajouter_en_base()
        self.preter_en_retard(id_livre, jours=3)
        self.assertIn('class="etat retard"', self.texte("/"))
        self.assertIn("En retard de 3 jours", self.texte(f"/livre/{id_livre}"))
        html = self.texte("/prets")
        self.assertIn("En retard de 3 jours", html)
        self.assertIn('class="ligne-retard"', html)

    def test_un_jour_de_retard_au_singulier(self):
        id_livre = self.ajouter_en_base()
        self.preter_en_retard(id_livre, jours=1)
        self.assertIn("En retard de 1 jour<", self.texte(f"/livre/{id_livre}"))

    def test_retour_prevu_aujourdhui_nest_pas_un_retard(self):
        id_livre = self.ajouter_en_base()
        self.preter_en_retard(id_livre, jours=0)
        self.assertNotIn("En retard", self.texte(f"/livre/{id_livre}"))

    def test_la_barre_de_navigation_compte_les_prets_et_les_retards(self):
        premier = self.ajouter_en_base()
        second = self.ajouter_en_base("Nana")
        self.client.post(f"/livre/{premier}/preter", data={"emprunteur": "Awa", "date_retour": self.demain()})
        self.preter_en_retard(second)
        html = self.texte("/")
        self.assertIn('<span class="compteur">2</span>', html)
        self.assertIn("1 en retard", html)

    def test_page_des_prets_vide_le_dit(self):
        self.assertIn("Aucun livre n'est en prêt", self.texte("/prets"))

    def test_page_des_prets_affiche_lemprunteur_et_la_date(self):
        id_livre = self.ajouter_en_base()
        retour = date.today() + timedelta(days=5)
        self.client.post(f"/livre/{id_livre}/preter", data={"emprunteur": "Awa Diop", "date_retour": retour.isoformat()})
        html = self.texte("/prets")
        self.assertIn("Awa Diop", html)
        self.assertIn(retour.strftime("%d/%m/%Y"), html)
        self.assertIn("Germinal", html)

    def test_rendre_termine_le_pret_et_garde_lhistorique(self):
        id_livre = self.ajouter_en_base()
        self.client.post(f"/livre/{id_livre}/preter", data={"emprunteur": "Awa Diop", "date_retour": self.demain()})
        reponse = self.client.post(f"/livre/{id_livre}/rendre")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.headers["Location"], f"/livre/{id_livre}")
        html = self.texte(f"/livre/{id_livre}")
        self.assertIn("Disponible", html)
        self.assertIn("Derniers prêts", html)
        self.assertIn("Awa Diop", html)
        self.assertIn("Aucun livre n", self.texte("/prets"))

    def test_rendre_depuis_la_page_des_prets_y_revient(self):
        id_livre = self.ajouter_en_base()
        self.client.post(f"/livre/{id_livre}/preter", data={"emprunteur": "Awa", "date_retour": self.demain()})
        reponse = self.client.post(f"/livre/{id_livre}/rendre", headers={"Referer": "http://localhost/prets"})
        self.assertEqual(reponse.headers["Location"], "/prets")

    def test_une_page_precedente_externe_est_ignoree(self):
        id_livre = self.ajouter_en_base()
        self.client.post(f"/livre/{id_livre}/preter", data={"emprunteur": "Awa", "date_retour": self.demain()})
        reponse = self.client.post(f"/livre/{id_livre}/rendre", headers={"Referer": "https://exemple.org/ailleurs"})
        self.assertEqual(reponse.headers["Location"], f"/livre/{id_livre}")

    # --- Suppression ---

    def test_supprimer_retire_le_livre(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(f"/supprimer/{id_livre}")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.headers["Location"], "/")
        self.assertEqual(self.livres_en_base(), [])

    def test_supprimer_un_livre_en_pret_est_refuse(self):
        id_livre = self.ajouter_en_base()
        self.preter_en_retard(id_livre)
        reponse = self.client.post(f"/supprimer/{id_livre}")
        self.assertEqual(reponse.status_code, 409)
        self.assertIn("enregistrez son retour", reponse.get_data(as_text=True))
        self.assertEqual(len(self.livres_en_base()), 1)

    def test_un_simple_lien_ne_peut_ni_supprimer_ni_preter_ni_rendre(self):
        id_livre = self.ajouter_en_base()
        self.assertEqual(self.client.get(f"/supprimer/{id_livre}").status_code, 405)
        self.assertEqual(self.client.get(f"/livre/{id_livre}/preter").status_code, 405)
        self.assertEqual(self.client.get(f"/livre/{id_livre}/rendre").status_code, 405)
        self.assertEqual(len(self.livres_en_base()), 1)

    # --- Cas particuliers ---

    def test_id_inconnu_donne_404(self):
        self.assertEqual(self.client.get("/livre/99").status_code, 404)
        self.assertEqual(self.client.get("/modifier/99").status_code, 404)
        self.assertEqual(self.client.post("/modifier/99", data=self.saisie()).status_code, 404)
        self.assertEqual(self.client.post("/supprimer/99").status_code, 404)
        self.assertEqual(self.client.post("/livre/99/preter", data={}).status_code, 404)
        self.assertEqual(self.client.post("/livre/99/rendre").status_code, 404)
        self.assertEqual(self.client.get("/categorie/99").status_code, 404)

    def test_le_html_dans_un_livre_est_neutralise(self):
        id_livre = self.ajouter_en_base("<script>alert(1)</script>", resume="<script>alert(2)</script>")
        for url in ("/", f"/livre/{id_livre}"):
            with self.subTest(url=url):
                html = self.texte(url)
                self.assertNotIn("<script>alert", html)
                self.assertIn("&lt;script&gt;", html)

    def test_le_html_dans_un_nom_demprunteur_est_neutralise(self):
        id_livre = self.ajouter_en_base()
        self.preter_en_retard(id_livre, emprunteur="<script>alert(3)</script>")
        for url in (f"/livre/{id_livre}", "/prets"):
            with self.subTest(url=url):
                self.assertNotIn("<script>alert", self.texte(url))

    def test_le_html_dans_une_recherche_est_neutralise(self):
        self.assertNotIn("<script>alert(1)", self.texte("/recherche?q=<script>alert(1)</script>"))

    def test_une_adresse_de_couverture_ne_peut_pas_sortir_de_lattribut(self):
        id_livre = self.ajouter_en_base(couverture='https://a.org/x"onload="alert(1)')
        self.assertNotIn('"onload="', self.texte(f"/livre/{id_livre}"))


if __name__ == "__main__":
    unittest.main()
