"""Tests du site : les routes Flask, sur un fichier temporaire."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from acces import (
    DUREE_BLOCAGE,
    ESSAIS_MAX,
    AccesIllisible,
    GardeTentatives,
    charger_acces,
    enregistrer_mot_de_passe,
    mot_de_passe_correct,
)
from app import creer_app, main
from stockage import charger_contacts, sauvegarder_contacts


class TestSite(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "contacts.json"
        self.client = creer_app(self.chemin, Path(dossier.name) / "acces.json").test_client()

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


MOT_DE_PASSE = "un mot de passe"


class TestMotDePasse(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.fichier = Path(dossier.name) / "acces.json"

    def test_aucun_mot_de_passe_au_depart(self):
        self.assertIsNone(charger_acces(self.fichier))

    def test_le_mot_de_passe_n_est_jamais_enregistre_en_clair(self):
        enregistrer_mot_de_passe(MOT_DE_PASSE, self.fichier)
        self.assertNotIn(MOT_DE_PASSE, self.fichier.read_text(encoding="utf-8"))

    def test_verification(self):
        enregistrer_mot_de_passe(MOT_DE_PASSE, self.fichier)
        acces = charger_acces(self.fichier)
        self.assertTrue(mot_de_passe_correct(acces, MOT_DE_PASSE))
        self.assertFalse(mot_de_passe_correct(acces, "autre chose"))
        self.assertFalse(mot_de_passe_correct(acces, ""))

    def test_mot_de_passe_trop_court_refuse(self):
        with self.assertRaises(ValueError):
            enregistrer_mot_de_passe("court", self.fichier)
        self.assertFalse(self.fichier.exists())

    def test_fichier_abime_refuse(self):
        for contenu in (b"{abime", b"[]", b'{"empreinte": "x"}', b'{"empreinte": "", "cle_session": "y"}'):
            with self.subTest(contenu=contenu):
                self.fichier.write_bytes(contenu)
                with self.assertRaises(AccesIllisible):
                    charger_acces(self.fichier)
                with self.assertRaises(AccesIllisible):
                    creer_app(self.fichier.with_name("contacts.json"), self.fichier)

    def test_garde_bloque_puis_libere(self):
        temps = [100.0]
        garde = GardeTentatives(horloge=lambda: temps[0])
        for _ in range(ESSAIS_MAX - 1):
            garde.noter_echec("1.1.1.1")
        self.assertFalse(garde.est_bloque("1.1.1.1"))
        garde.noter_echec("1.1.1.1")
        self.assertTrue(garde.est_bloque("1.1.1.1"))
        self.assertFalse(garde.est_bloque("2.2.2.2"))
        temps[0] += DUREE_BLOCAGE + 1
        self.assertFalse(garde.est_bloque("1.1.1.1"))
        garde.noter_echec("1.1.1.1")
        self.assertFalse(garde.est_bloque("1.1.1.1"))


class TestSiteProtege(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.contacts = Path(dossier.name) / "contacts.json"
        self.fichier = Path(dossier.name) / "acces.json"
        enregistrer_mot_de_passe(MOT_DE_PASSE, self.fichier)
        sauvegarder_contacts([{"nom": "Awa", "telephone": "112"}], self.contacts)
        self.app = creer_app(self.contacts, self.fichier)
        self.client = self.app.test_client()

    def connecter(self, mot_de_passe=MOT_DE_PASSE, client=None):
        return (client or self.client).post("/connexion", data={"mot_de_passe": mot_de_passe})

    def test_sans_connexion_la_page_renvoie_vers_le_verrou(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(reponse.location.endswith("/connexion"))

    def test_sans_connexion_les_contacts_restent_inaccessibles(self):
        lecture = self.client.get("/api/contacts")
        self.assertEqual(lecture.status_code, 401)
        self.assertNotIn("Awa", lecture.get_data(as_text=True))

        ajout = self.client.post("/api/contacts", json={"nom": "Zoé", "telephone": "113"})
        suppression = self.client.post("/api/contacts/supprimer", json={"nom": "Awa", "telephone": "112"})
        self.assertEqual((ajout.status_code, suppression.status_code), (401, 401))
        self.assertEqual(charger_contacts(self.contacts), [{"nom": "Awa", "telephone": "112"}])

    def test_ecran_verrouille_et_fichiers_statiques_accessibles(self):
        page = self.client.get("/connexion")
        self.assertEqual(page.status_code, 200)
        self.assertIn('type="password"', page.get_data(as_text=True))
        for fichier in ("telephone.css", "heure.js"):
            with self.client.get(f"/static/{fichier}") as reponse:
                self.assertEqual(reponse.status_code, 200)

    def test_mauvais_mot_de_passe(self):
        reponse = self.connecter("autre chose")
        self.assertEqual(reponse.status_code, 401)
        self.assertIn("incorrect", reponse.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/contacts").status_code, 401)

    def test_formulaire_vide(self):
        self.assertEqual(self.client.post("/connexion").status_code, 401)

    def test_bon_mot_de_passe_ouvre_tout(self):
        reponse = self.connecter()
        self.assertEqual(reponse.status_code, 302)
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn('aria-label="Verrouiller"', page.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/contacts").get_json()["total"], 1)
        self.assertEqual(self.client.get("/connexion").status_code, 302)

    def test_cookie_protege(self):
        cookie = self.connecter().headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)

    def test_contacts_jamais_gardes_en_cache(self):
        self.connecter()
        self.assertEqual(self.client.get("/api/contacts").headers["Cache-Control"], "no-store")

    def test_verrouiller_coupe_l_acces(self):
        self.connecter()
        self.assertEqual(self.client.post("/deconnexion").status_code, 302)
        self.assertEqual(self.client.get("/api/contacts").status_code, 401)

    def test_cookie_falsifie_refuse(self):
        self.client.set_cookie("session", "eyJjb25uZWN0ZSI6dHJ1ZX0.AAAAAA.fausse-signature")
        self.assertEqual(self.client.get("/api/contacts").status_code, 401)

    def test_trop_d_essais_bloquent_meme_le_bon_mot_de_passe(self):
        for _ in range(ESSAIS_MAX):
            self.assertEqual(self.connecter("autre chose").status_code, 401)
        reponse = self.connecter()
        self.assertEqual(reponse.status_code, 429)
        self.assertIn("Trop d", reponse.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/contacts").status_code, 401)

    def test_le_blocage_ne_touche_que_cet_appareil(self):
        for _ in range(ESSAIS_MAX):
            self.connecter("autre chose")
        autre = self.app.test_client()
        reponse = autre.post(
            "/connexion",
            data={"mot_de_passe": MOT_DE_PASSE},
            environ_base={"REMOTE_ADDR": "192.168.1.50"},
        )
        self.assertEqual(reponse.status_code, 302)

    def test_une_connexion_reussie_remet_le_compteur_a_zero(self):
        for _ in range(ESSAIS_MAX - 1):
            self.connecter("autre chose")
        self.connecter()
        self.client.post("/deconnexion")
        self.assertEqual(self.connecter("autre chose").status_code, 401)
        self.assertEqual(self.connecter().status_code, 302)

    def test_changer_le_mot_de_passe_deconnecte_les_appareils(self):
        self.connecter()
        cookie = self.client.get_cookie("session").value
        enregistrer_mot_de_passe("un tout autre mot", self.fichier)
        nouveau = creer_app(self.contacts, self.fichier).test_client()
        nouveau.set_cookie("session", cookie)
        self.assertEqual(nouveau.get("/api/contacts").status_code, 401)


class TestLancement(unittest.TestCase):
    ACCES = {"empreinte": "x", "cle_session": "y"}

    def lancer(self, arguments, acces):
        with (
            mock.patch("app.charger_acces", return_value=acces),
            mock.patch("app.creer_app") as creer,
            mock.patch("builtins.print") as afficher,
        ):
            code = main(arguments)
        texte = " ".join(str(appel.args[0]) for appel in afficher.call_args_list if appel.args)
        return code, creer.return_value.run, texte

    def test_mode_reseau_refuse_sans_mot_de_passe(self):
        code, lancer_site, texte = self.lancer(["--reseau"], None)
        self.assertEqual(code, 1)
        lancer_site.assert_not_called()
        self.assertIn("--mot-de-passe", texte)

    def test_mode_reseau_avec_mot_de_passe(self):
        code, lancer_site, texte = self.lancer(["--reseau"], self.ACCES)
        self.assertEqual(code, 0)
        self.assertEqual(lancer_site.call_args.kwargs["host"], "0.0.0.0")
        self.assertIn("pas chiffré", texte)

    def test_par_defaut_le_site_reste_sur_cet_ordinateur(self):
        for acces in (None, self.ACCES):
            with self.subTest(acces=acces):
                code, lancer_site, _texte = self.lancer([], acces)
                self.assertEqual(code, 0)
                self.assertEqual(lancer_site.call_args.kwargs["host"], "127.0.0.1")

    def test_fichier_d_acces_abime_empeche_de_demarrer(self):
        with (
            mock.patch("app.charger_acces", side_effect=AccesIllisible("abimé")),
            mock.patch("app.creer_app") as creer,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(main(["--reseau"]), 1)
        creer.return_value.run.assert_not_called()

    def test_choix_du_mot_de_passe(self):
        with (
            mock.patch("app.getpass.getpass", side_effect=[MOT_DE_PASSE, MOT_DE_PASSE]),
            mock.patch("app.enregistrer_mot_de_passe") as enregistrer,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(main(["--mot-de-passe"]), 0)
        enregistrer.assert_called_once_with(MOT_DE_PASSE)

    def test_saisies_differentes_ne_changent_rien(self):
        with (
            mock.patch("app.getpass.getpass", side_effect=[MOT_DE_PASSE, "autre"]),
            mock.patch("app.enregistrer_mot_de_passe") as enregistrer,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(main(["--mot-de-passe"]), 1)
        enregistrer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
