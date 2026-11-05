"""Tests des trois couches : logique, données et interface."""

import json
import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from contacts import (
    ContactInvalide,
    ajouter_contact,
    chercher_contacts,
    cle_de_tri,
    contacts_de_lettre,
    creer_contact,
    garder_chiffres,
    initiale,
    initiales_presentes,
    supprimer_contact,
)
from interface import FenetreContacts, main
from stockage import FichierIllisible, charger_contacts, sauvegarder_contacts


class TestLogique(unittest.TestCase):
    def verifier_refus(self, nom, telephone, champ):
        with self.assertRaises(ContactInvalide) as refus:
            creer_contact(nom, telephone)
        self.assertEqual(refus.exception.champ, champ)

    def test_contact_valide(self):
        self.assertEqual(
            creer_contact("Awa Diallo", "06 12 34 56 78"),
            {"nom": "Awa Diallo", "telephone": "06 12 34 56 78"},
        )

    def test_espaces_en_trop_retires(self):
        contact = creer_contact("  Awa   Diallo ", " 06  12 34 ")
        self.assertEqual(contact, {"nom": "Awa Diallo", "telephone": "06 12 34"})

    def test_nom_vide_refuse(self):
        self.verifier_refus("   ", "0612345678", "nom")

    def test_telephone_vide_refuse(self):
        self.verifier_refus("Awa", "   ", "telephone")

    def test_lettres_refusees_dans_le_numero(self):
        self.verifier_refus("Awa", "06AB345678", "telephone")

    def test_chiffres_non_latins_refuses(self):
        self.verifier_refus("Awa", "٠٦١٢٣٤", "telephone")

    def test_plus_seulement_au_debut(self):
        creer_contact("Awa", "+33 6 12 34 56 78")
        self.verifier_refus("Awa", "33+612345678", "telephone")

    def test_longueur_du_numero(self):
        creer_contact("Urgences", "112")
        creer_contact("Awa", "1" * 15)
        self.verifier_refus("Awa", "12", "telephone")
        self.verifier_refus("Awa", "1" * 16, "telephone")
        self.verifier_refus("Awa", "+ . - ()", "telephone")

    def test_garder_chiffres(self):
        self.assertEqual(garder_chiffres("+33 (0)6.12-34"), "33061234")

    def test_ajout_ne_modifie_pas_la_liste_recue(self):
        contacts = []
        resultat = ajouter_contact(contacts, "Awa", "0612345678")
        self.assertEqual(contacts, [])
        self.assertEqual(len(resultat), 1)

    def test_doublon_refuse_meme_ecrit_autrement(self):
        contacts = ajouter_contact([], "Awa Diallo", "06 12 34 56 78")
        with self.assertRaises(ContactInvalide):
            ajouter_contact(contacts, "AWA DIALLO", "06.12.34.56.78")

    def test_meme_nom_avec_autre_numero_accepte(self):
        contacts = ajouter_contact([], "Awa", "0612345678")
        self.assertEqual(len(ajouter_contact(contacts, "Awa", "0700000000")), 2)

    def test_meme_numero_avec_autre_nom_accepte(self):
        contacts = ajouter_contact([], "Awa", "0612345678")
        self.assertEqual(len(ajouter_contact(contacts, "Moussa", "0612345678")), 2)

    def test_tri_sans_tenir_compte_des_accents_ni_de_la_casse(self):
        contacts = []
        for nom in ["Zoé", "Émile", "adam", "Eric"]:
            contacts = ajouter_contact(contacts, nom, "0612345678")
        self.assertEqual([c["nom"] for c in contacts], ["adam", "Émile", "Eric", "Zoé"])

    def test_cle_de_tri(self):
        self.assertEqual(cle_de_tri({"nom": "Émile"}), "emile")

    def test_initiale(self):
        self.assertEqual(initiale({"nom": "Émile"}), "E")
        self.assertEqual(initiale({"nom": "adam"}), "A")
        self.assertEqual(initiale({"nom": "3 Frères"}), "#")
        self.assertEqual(initiale({"nom": "Ñandú"}), "N")
        self.assertEqual(initiale({"nom": "Œuvre"}), "#")

    def test_contacts_de_lettre(self):
        contacts = [{"nom": "Émile", "telephone": "112"}, {"nom": "Zoé", "telephone": "113"}]
        self.assertEqual(contacts_de_lettre(contacts, "E"), contacts[:1])
        self.assertEqual(initiales_presentes(contacts), {"E", "Z"})

    def test_recherche(self):
        emile = {"nom": "Émile Kouassi", "telephone": "06 12 34"}
        awa = {"nom": "Awa 2", "telephone": "+225 07"}
        contacts = [awa, emile]
        self.assertEqual(chercher_contacts(contacts, ""), contacts)
        self.assertEqual(chercher_contacts(contacts, "   "), contacts)
        self.assertEqual(chercher_contacts(contacts, "emile"), [emile])
        self.assertEqual(chercher_contacts(contacts, "KOUA"), [emile])
        self.assertEqual(chercher_contacts(contacts, "émile  kouassi"), [emile])
        self.assertEqual(chercher_contacts(contacts, "06.12"), [emile])
        self.assertEqual(chercher_contacts(contacts, "2250"), [awa])
        self.assertEqual(chercher_contacts(contacts, "awa 2"), [awa])
        self.assertEqual(chercher_contacts(contacts, "xyz"), [])
        self.assertEqual(chercher_contacts(contacts, "+"), [])

    def test_suppression_ne_modifie_pas_la_liste_recue(self):
        awa = {"nom": "Awa", "telephone": "112"}
        zoe = {"nom": "Zoé", "telephone": "113"}
        contacts = [awa, zoe]
        self.assertEqual(supprimer_contact(contacts, awa), [zoe])
        self.assertEqual(contacts, [awa, zoe])


class TestDonnees(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "contacts.json"

    def test_fichier_absent_donne_une_liste_vide(self):
        self.assertEqual(charger_contacts(self.chemin), [])

    def test_aller_retour_avec_accents(self):
        contacts = [{"nom": "Hélène N'Guessan", "telephone": "+225 07 00"}]
        sauvegarder_contacts(contacts, self.chemin)
        self.assertEqual(charger_contacts(self.chemin), contacts)
        self.assertIn("Hélène", self.chemin.read_text(encoding="utf-8"))

    def test_pas_de_fichier_temporaire_restant(self):
        sauvegarder_contacts([], self.chemin)
        self.assertEqual(os.listdir(self.chemin.parent), ["contacts.json"])

    def test_echec_d_ecriture_garde_l_ancien_fichier(self):
        sauvegarder_contacts([{"nom": "Awa", "telephone": "112"}], self.chemin)
        with mock.patch("stockage.json.dump", side_effect=OSError("disque plein")):
            with self.assertRaises(OSError):
                sauvegarder_contacts([], self.chemin)
        self.assertEqual(charger_contacts(self.chemin), [{"nom": "Awa", "telephone": "112"}])

    def test_contenus_illisibles_refuses_et_non_modifies(self):
        contenus = [
            b"{pas du json",
            b"\xff\xfe\x00",
            b'{"nom": "Awa"}',
            b'["Awa"]',
            b'[{"nom": "Awa"}]',
            b'[{"nom": "Awa", "telephone": 112}]',
        ]
        for contenu in contenus:
            with self.subTest(contenu=contenu):
                self.chemin.write_bytes(contenu)
                with self.assertRaises(FichierIllisible):
                    charger_contacts(self.chemin)
                self.assertEqual(self.chemin.read_bytes(), contenu)


class TestInterface(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.chemin = Path(dossier.name) / "contacts.json"
        try:
            self.racine = tk.Tk()
        except tk.TclError as erreur:
            self.skipTest(f"Pas d'écran disponible : {erreur}")
        self.addCleanup(self.racine.destroy)
        self.racine.withdraw()
        self.fenetre = FenetreContacts(self.racine, [], self.chemin)

    def saisir(self, nom, telephone):
        self.fenetre.champ_nom.delete(0, "end")
        self.fenetre.champ_nom.insert(0, nom)
        self.fenetre.champ_telephone.delete(0, "end")
        self.fenetre.champ_telephone.insert(0, telephone)

    def lignes(self):
        liste = self.fenetre.liste
        return [tuple(map(str, liste.item(ligne, "values"))) for ligne in liste.get_children()]

    def test_liste_vide_au_depart(self):
        self.assertEqual(self.lignes(), [])
        self.assertEqual(self.fenetre.compteur.cget("text"), "Aucun contact")
        self.assertIn("premier contact", self.fenetre.indication.cget("text"))
        self.assertEqual(self.fenetre.onglets["A"].cget("state"), "disabled")

    def test_clic_ajoute_enregistre_et_vide_les_champs(self):
        self.saisir("Awa", "06 12 34 56 78")
        self.fenetre.bouton_ajouter.invoke()
        self.assertEqual(self.lignes(), [("Awa", "06 12 34 56 78")])
        self.assertEqual(self.fenetre.compteur.cget("text"), "1 contact")
        self.assertEqual(self.fenetre.champ_nom.get(), "")
        self.assertEqual(self.fenetre.champ_telephone.get(), "")
        self.assertEqual(
            json.loads(self.chemin.read_text(encoding="utf-8")),
            [{"nom": "Awa", "telephone": "06 12 34 56 78"}],
        )

    def test_touche_entree_ajoute(self):
        self.saisir("Awa", "0612345678")
        self.fenetre.quand_entree(None)
        self.assertEqual(self.lignes(), [("Awa", "0612345678")])

    def test_nouveau_contact_selectionne_a_sa_place(self):
        for nom in ["Zoé", "Adam"]:
            self.saisir(nom, "0612345678")
            self.fenetre.bouton_ajouter.invoke()
        self.assertEqual([ligne[0] for ligne in self.lignes()], ["Adam", "Zoé"])
        selection = self.fenetre.liste.selection()
        self.assertEqual(self.fenetre.liste.item(selection[0], "values")[0], "Adam")
        self.assertEqual(self.fenetre.compteur.cget("text"), "2 contacts")

    def test_saisie_refusee_garde_le_texte_et_affiche_l_erreur(self):
        self.saisir("Awa", "abc")
        self.fenetre.bouton_ajouter.invoke()
        self.assertEqual(self.lignes(), [])
        self.assertIn("chiffres", self.fenetre.message.cget("text"))
        self.assertEqual(self.fenetre.champ_nom.get(), "Awa")
        self.assertFalse(self.chemin.exists())

    def test_erreur_effacee_apres_un_ajout_reussi(self):
        self.saisir("", "0612345678")
        self.fenetre.bouton_ajouter.invoke()
        self.assertNotEqual(self.fenetre.message.cget("text"), "")
        self.saisir("Awa", "0612345678")
        self.fenetre.bouton_ajouter.invoke()
        self.assertEqual(self.fenetre.message.cget("text"), "")

    def test_echec_d_enregistrement_ne_perd_rien(self):
        self.saisir("Awa", "0612345678")
        with mock.patch("interface.sauvegarder_contacts", side_effect=OSError("disque plein")):
            self.fenetre.bouton_ajouter.invoke()
        self.assertEqual(self.lignes(), [])
        self.assertEqual(self.fenetre.champ_nom.get(), "Awa")
        self.assertIn("disque plein", self.fenetre.message.cget("text"))

        self.fenetre.bouton_ajouter.invoke()
        self.assertEqual(self.lignes(), [("Awa", "0612345678")])

    def remplir(self, *noms):
        for nom in noms:
            self.saisir(nom, "0612345678")
            self.fenetre.bouton_ajouter.invoke()

    def noms_affiches(self):
        return [ligne[0] for ligne in self.lignes()]

    def test_recherche_filtre_a_chaque_saisie(self):
        self.remplir("Awa", "Émile", "Zoé")
        self.fenetre.recherche.set("emi")
        self.assertEqual(self.noms_affiches(), ["Émile"])
        self.fenetre.quand_echap(None)
        self.assertEqual(self.noms_affiches(), ["Awa", "Émile", "Zoé"])

    def test_recherche_sans_resultat_le_dit(self):
        self.remplir("Awa")
        self.fenetre.recherche.set("xyz")
        self.assertEqual(self.noms_affiches(), [])
        self.assertIn("Aucun contact ne correspond", self.fenetre.indication.cget("text"))
        self.assertEqual(self.fenetre.compteur.cget("text"), "1 contact")

    def test_onglet_filtre_puis_second_clic_affiche_tout(self):
        self.remplir("Awa", "Émile", "Zoé")
        self.fenetre.onglets["E"].invoke()
        self.assertEqual(self.noms_affiches(), ["Émile"])
        self.assertIn("Lettre E", self.fenetre.indication.cget("text"))
        self.fenetre.onglets["E"].invoke()
        self.assertEqual(self.noms_affiches(), ["Awa", "Émile", "Zoé"])

    def test_onglet_vide_inactif(self):
        self.remplir("Awa")
        self.assertEqual(self.fenetre.onglets["A"].cget("state"), "normal")
        self.fenetre.onglets["B"].invoke()
        self.assertEqual(self.noms_affiches(), ["Awa"])

    def test_recherche_et_onglet_s_excluent(self):
        self.remplir("Awa", "Zoé")
        self.fenetre.recherche.set("zo")
        self.fenetre.onglets["A"].invoke()
        self.assertEqual(self.fenetre.recherche.get(), "")
        self.assertEqual(self.noms_affiches(), ["Awa"])
        self.fenetre.recherche.set("zo")
        self.assertIsNone(self.fenetre.lettre)
        self.assertEqual(self.noms_affiches(), ["Zoé"])

    def test_ajout_retire_les_filtres_pour_montrer_le_contact(self):
        self.remplir("Awa", "Zoé")
        self.fenetre.onglets["Z"].invoke()
        self.remplir("Adam")
        self.assertEqual(self.noms_affiches(), ["Adam", "Awa", "Zoé"])
        selection = self.fenetre.liste.selection()
        self.assertEqual(self.fenetre.liste.item(selection[0], "values")[0], "Adam")

    def selectionner(self, nom):
        liste = self.fenetre.liste
        for ligne in liste.get_children():
            if liste.item(ligne, "values")[0] == nom:
                liste.selection_set(ligne)
                self.fenetre.actualiser_bouton_supprimer()
                return
        self.fail(f"{nom} n'est pas affiché")

    def test_bouton_supprimer_actif_seulement_avec_une_selection(self):
        self.remplir("Awa")
        self.fenetre.liste.selection_set(())
        self.fenetre.actualiser_bouton_supprimer()
        self.assertTrue(self.fenetre.bouton_supprimer.instate(["disabled"]))
        self.selectionner("Awa")
        self.assertFalse(self.fenetre.bouton_supprimer.instate(["disabled"]))

    def test_suppression_confirmee(self):
        self.remplir("Awa", "Zoé")
        self.selectionner("Awa")
        with mock.patch("interface.messagebox.askyesno", return_value=True):
            self.fenetre.bouton_supprimer.invoke()
        self.assertEqual(self.noms_affiches(), ["Zoé"])
        self.assertEqual(charger_contacts(self.chemin), [{"nom": "Zoé", "telephone": "0612345678"}])
        self.assertEqual(self.fenetre.onglets["A"].cget("state"), "disabled")
        self.assertTrue(self.fenetre.bouton_supprimer.instate(["disabled"]))

    def test_suppression_refusee_ne_change_rien(self):
        self.remplir("Awa")
        self.selectionner("Awa")
        with mock.patch("interface.messagebox.askyesno", return_value=False):
            self.fenetre.quand_touche_suppr(None)
        self.assertEqual(self.noms_affiches(), ["Awa"])
        self.assertEqual(len(charger_contacts(self.chemin)), 1)

    def test_suppression_du_bon_contact_quand_la_liste_est_filtree(self):
        self.remplir("Awa", "Zoé")
        self.fenetre.recherche.set("zo")
        self.selectionner("Zoé")
        with mock.patch("interface.messagebox.askyesno", return_value=True):
            self.fenetre.supprimer()
        self.assertEqual(charger_contacts(self.chemin), [{"nom": "Awa", "telephone": "0612345678"}])

    def test_supprimer_le_dernier_de_l_onglet_affiche_tout(self):
        self.remplir("Awa", "Zoé")
        self.fenetre.onglets["Z"].invoke()
        self.selectionner("Zoé")
        with mock.patch("interface.messagebox.askyesno", return_value=True):
            self.fenetre.supprimer()
        self.assertIsNone(self.fenetre.lettre)
        self.assertEqual(self.noms_affiches(), ["Awa"])

    def test_echec_de_suppression_garde_le_contact(self):
        self.remplir("Awa")
        self.selectionner("Awa")
        with (
            mock.patch("interface.messagebox.askyesno", return_value=True),
            mock.patch("interface.sauvegarder_contacts", side_effect=OSError("disque plein")),
        ):
            self.fenetre.supprimer()
        self.assertEqual(self.noms_affiches(), ["Awa"])
        self.assertIn("disque plein", self.fenetre.message.cget("text"))

    def test_ajout_garde_ce_que_le_site_a_enregistre_entre_temps(self):
        self.remplir("Awa")
        site = [*charger_contacts(self.chemin), {"nom": "Site", "telephone": "0700000000"}]
        sauvegarder_contacts(site, self.chemin)
        self.remplir("Zoé")
        self.assertEqual(self.noms_affiches(), ["Awa", "Site", "Zoé"])
        self.assertEqual(len(charger_contacts(self.chemin)), 3)

    def test_suppression_garde_ce_que_le_site_a_enregistre_entre_temps(self):
        self.remplir("Awa")
        self.selectionner("Awa")
        sauvegarder_contacts(
            [*charger_contacts(self.chemin), {"nom": "Site", "telephone": "0700000000"}], self.chemin
        )
        with mock.patch("interface.messagebox.askyesno", return_value=True):
            self.fenetre.supprimer()
        self.assertEqual(self.noms_affiches(), ["Site"])

    def test_fichier_abime_pendant_l_utilisation_n_est_pas_ecrase(self):
        self.remplir("Awa")
        self.chemin.write_bytes(b"{abime")
        self.saisir("Zoé", "0612345678")
        self.fenetre.bouton_ajouter.invoke()
        self.assertEqual(self.chemin.read_bytes(), b"{abime")
        self.assertEqual(self.fenetre.champ_nom.get(), "Zoé")
        self.assertIn("impossible", self.fenetre.message.cget("text"))


class TestDemarrage(unittest.TestCase):
    def test_fichier_illisible_affiche_l_erreur_et_arrete(self):
        with (
            mock.patch("interface.tk.Tk"),
            mock.patch("interface.charger_contacts", side_effect=FichierIllisible("contacts.json")),
            mock.patch("interface.messagebox.showerror") as afficher_erreur,
            mock.patch("interface.FenetreContacts") as fenetre,
        ):
            with self.assertRaises(SystemExit) as arret:
                main()
        self.assertEqual(arret.exception.code, 1)
        afficher_erreur.assert_called_once()
        fenetre.assert_not_called()


if __name__ == "__main__":
    unittest.main()
