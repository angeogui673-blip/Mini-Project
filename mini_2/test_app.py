"""Tests des routes du site, avec le client de test de Flask."""

import tempfile
import unittest
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

    def ajouter_en_base(self, titre="Germinal", auteur="Émile Zola", annee=1885, categorie=None, resume="", disponible=True):
        base = c.connecter(self.chemin)
        id_livre = c.ajouter_livre(base, titre, auteur, annee, categorie or self.roman, resume, disponible)
        base.close()
        return id_livre

    def livres_en_base(self):
        base = c.connecter(self.chemin)
        livres = [dict(livre) for livre in c.lister_livres(base)]
        base.close()
        return livres

    def saisie(self, **valeurs):
        return {"titre": "Germinal", "auteur": "Émile Zola", "annee": "1885", "categorie_id": self.roman, **valeurs}

    def texte(self, url):
        return self.client.get(url).get_data(as_text=True)

    # --- Liste et catégories ---

    def test_catalogue_vide_invite_a_ajouter(self):
        self.assertIn("Le catalogue est vide", self.texte("/"))

    def test_liste_affiche_toutes_les_informations_de_la_fiche(self):
        self.ajouter_en_base(resume="Une grande grève.")
        self.ajouter_en_base("Nana", disponible=False)
        html = self.texte("/")
        self.assertIn("<h3>Germinal</h3>", html)
        self.assertIn("Émile Zola, 1885", html)
        self.assertIn("Une grande grève.", html)
        self.assertIn("R ZOL", html)
        self.assertIn('class="tampon"', html)
        self.assertIn('class="tampon emprunte"', html)

    def test_liste_range_les_livres_sous_le_nom_de_leur_categorie(self):
        self.ajouter_en_base("Germinal")
        self.ajouter_en_base("Tintin au Tibet", "Hergé", 1960, self.bd)
        html = self.texte("/")
        self.assertIn("<h2>Bande dessinée <small>1 livre</small></h2>", html)
        self.assertLess(html.index("<h2>Bande dessinée"), html.index("Tintin au Tibet"))
        self.assertLess(html.index("Tintin au Tibet"), html.index("<h2>Roman"))
        self.assertLess(html.index("<h2>Roman"), html.index("<h3>Germinal"))

    def test_les_rayons_suivent_lordre_alphabetique_malgre_les_accents(self):
        self.ajouter_en_base("Pietr le Letton", "Georges Simenon", 1931, self.id_categorie("Policier"))
        self.ajouter_en_base("Alcools", "Guillaume Apollinaire", 1913, self.id_categorie("Poésie"))
        html = self.texte("/")
        self.assertLess(html.index("<h2>Poésie"), html.index("<h2>Policier"))

    def test_le_meuble_affiche_les_categories_et_leur_nombre_de_livres(self):
        self.ajouter_en_base()
        html = self.texte("/")
        self.assertIn("Roman <small>1</small>", html)
        self.assertIn("Théâtre <small>0</small>", html)
        self.assertIn("Tous les livres <small>1</small>", html)

    def test_page_dune_categorie_ne_montre_que_ses_livres(self):
        self.ajouter_en_base("Germinal")
        self.ajouter_en_base("Tintin au Tibet", "Hergé", 1960, self.bd)
        html = self.texte(f"/categorie/{self.bd}")
        self.assertIn("<h3>Tintin au Tibet</h3>", html)
        self.assertNotIn("<h3>Germinal</h3>", html)
        self.assertIn("aria-current", html)

    def test_categorie_vide_le_dit(self):
        self.assertIn("Aucun livre dans cette catégorie", self.texte(f"/categorie/{self.bd}"))

    # --- Recherche ---

    def test_recherche_filtre_la_liste_et_garde_le_terme(self):
        self.ajouter_en_base("Germinal")
        self.ajouter_en_base("Nana")
        html = self.texte("/recherche?q=germ")
        self.assertIn("<h3>Germinal</h3>", html)
        self.assertNotIn("<h3>Nana</h3>", html)
        self.assertIn('value="germ"', html)
        self.assertIn("1 résultat pour", html)

    def test_recherche_sans_resultat_le_dit(self):
        self.ajouter_en_base()
        self.assertIn("Aucun livre ne correspond", self.texte("/recherche?q=introuvable"))

    def test_recherche_vide_revient_a_la_liste(self):
        reponse = self.client.get("/recherche?q=%20%20")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.headers["Location"], "/")

    # --- Ajout ---

    def test_formulaire_dajout_propose_les_categories_et_coche_disponible(self):
        html = self.texte("/ajouter")
        self.assertIn("Ajouter un livre", html)
        self.assertIn('type="checkbox" checked', html)
        self.assertIn(">Théâtre</option>", html)

    def test_ajouter_enregistre_puis_redirige_vers_la_fiche(self):
        reponse = self.client.post("/ajouter", data=self.saisie(disponible="on", resume="Une grève."))
        self.assertEqual(reponse.status_code, 302)
        livre = self.livres_en_base()[0]
        self.assertEqual(reponse.headers["Location"], f"/#livre-{livre['id']}")
        self.assertEqual(livre["titre"], "Germinal")
        self.assertEqual(livre["resume"], "Une grève.")
        self.assertEqual(livre["cote"], "R ZOL")
        self.assertEqual(livre["disponible"], 1)

    def test_case_decochee_enregistre_un_livre_emprunte(self):
        self.client.post("/ajouter", data=self.saisie())
        self.assertEqual(self.livres_en_base()[0]["disponible"], 0)

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
        id_livre = self.ajouter_en_base(categorie=self.bd, resume="Une grève.")
        html = self.texte(f"/modifier/{id_livre}")
        self.assertIn('value="Germinal"', html)
        self.assertIn('value="1885"', html)
        self.assertIn(">Une grève.</textarea>", html)
        self.assertRegex(html, rf'value="{self.bd}"\s+selected')
        self.assertIn("Enregistrer", html)

    def test_modifier_enregistre_et_recalcule_la_cote(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(f"/modifier/{id_livre}", data=self.saisie(categorie_id=self.bd))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.headers["Location"], f"/#livre-{id_livre}")
        livre = self.livres_en_base()[0]
        self.assertEqual(livre["categorie"], "Bande dessinée")
        self.assertEqual(livre["cote"], "BD ZOL")
        self.assertEqual(livre["disponible"], 0)

    def test_modification_invalide_ne_change_rien(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(f"/modifier/{id_livre}", data=self.saisie(titre="  "))
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(self.livres_en_base()[0]["titre"], "Germinal")

    # --- Prêt ---

    def test_preter_puis_rendre_en_un_clic(self):
        id_livre = self.ajouter_en_base()
        self.assertIn("Prêter : Germinal", self.texte("/"))

        self.assertEqual(self.client.post(f"/pret/{id_livre}").status_code, 302)
        self.assertEqual(self.livres_en_base()[0]["disponible"], 0)
        self.assertIn("Rendre : Germinal", self.texte("/"))

        self.client.post(f"/pret/{id_livre}")
        self.assertEqual(self.livres_en_base()[0]["disponible"], 1)

    def test_preter_revient_sur_la_page_de_categorie_a_la_bonne_fiche(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(
            f"/pret/{id_livre}", headers={"Referer": f"http://localhost/categorie/{self.roman}"}
        )
        self.assertEqual(reponse.headers["Location"], f"/categorie/{self.roman}#livre-{id_livre}")

    def test_preter_revient_sur_la_recherche_avec_le_terme(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(
            f"/pret/{id_livre}", headers={"Referer": "http://localhost/recherche?q=germ"}
        )
        self.assertEqual(reponse.headers["Location"], f"/recherche?q=germ#livre-{id_livre}")

    def test_une_page_precedente_externe_est_ignoree(self):
        id_livre = self.ajouter_en_base()
        reponse = self.client.post(
            f"/supprimer/{id_livre}", headers={"Referer": "https://exemple.org/ailleurs"}
        )
        self.assertEqual(reponse.headers["Location"], "/")

    # --- Suppression ---

    def test_supprimer_retire_le_livre(self):
        id_livre = self.ajouter_en_base()
        self.assertEqual(self.client.post(f"/supprimer/{id_livre}").status_code, 302)
        self.assertEqual(self.livres_en_base(), [])

    def test_un_simple_lien_ne_peut_ni_supprimer_ni_preter(self):
        id_livre = self.ajouter_en_base()
        self.assertEqual(self.client.get(f"/supprimer/{id_livre}").status_code, 405)
        self.assertEqual(self.client.get(f"/pret/{id_livre}").status_code, 405)
        livres = self.livres_en_base()
        self.assertEqual(len(livres), 1)
        self.assertEqual(livres[0]["disponible"], 1)

    # --- Cas particuliers ---

    def test_id_inconnu_donne_404(self):
        self.assertEqual(self.client.get("/modifier/99").status_code, 404)
        self.assertEqual(self.client.post("/modifier/99", data=self.saisie()).status_code, 404)
        self.assertEqual(self.client.post("/supprimer/99").status_code, 404)
        self.assertEqual(self.client.post("/pret/99").status_code, 404)
        self.assertEqual(self.client.get("/categorie/99").status_code, 404)

    def test_le_html_dans_un_livre_est_neutralise(self):
        self.ajouter_en_base("<script>alert(1)</script>", resume="<script>alert(2)</script>")
        html = self.texte("/")
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)

    def test_le_html_dans_une_recherche_est_neutralise(self):
        self.assertNotIn("<script>alert(1)", self.texte("/recherche?q=<script>alert(1)</script>"))


if __name__ == "__main__":
    unittest.main()
