"""Tests du client et du serveur, avec de vraies connexions TCP sur cet ordinateur."""

import contextlib
import io
import os
import socket
import struct
import threading
import unittest

import client as c
import serveur as s


class TestPreparerReponse(unittest.TestCase):
    def test_reponse(self):
        self.assertEqual(s.preparer_reponse("Bonjour"), "Reçu : Bonjour")


class ServeurDeTest(unittest.TestCase):
    """Démarre un vrai serveur pour chaque test, sur un port libre choisi par le système."""

    def setUp(self):
        self.serveur = s.creer_serveur("127.0.0.1", 0)  # le port 0 demande un port libre
        self.addCleanup(self.serveur.close)
        self.port = self.serveur.getsockname()[1]

        # Les messages affichés par le serveur ne doivent pas encombrer le résultat des tests.
        sortie = contextlib.redirect_stdout(io.StringIO())
        sortie.__enter__()
        self.addCleanup(sortie.__exit__, None, None, None)

        self.arret = threading.Event()
        fil = threading.Thread(target=s.lancer_serveur, args=(self.serveur, self.arret), daemon=True)
        fil.start()

        def arreter():
            self.arret.set()
            fil.join(timeout=3)

        self.addCleanup(arreter)

    def nouveau_client(self):
        """Retourne une connexion et son flux de lecture, fermés à la fin du test."""
        connexion = c.se_connecter("127.0.0.1", self.port)
        self.addCleanup(connexion.close)
        flux = connexion.makefile("r", encoding="utf-8", newline="\n")
        self.addCleanup(flux.close)
        return connexion, flux


class TestEchanges(ServeurDeTest):
    def test_message_et_reponse(self):
        connexion, flux = self.nouveau_client()
        self.assertEqual(c.echanger(connexion, flux, "Bonjour"), "Reçu : Bonjour")

    def test_accents_et_caracteres_speciaux(self):
        connexion, flux = self.nouveau_client()
        for message in ("Été à la bibliothèque", "cœur", "日本語", "✓"):
            with self.subTest(message=message):
                self.assertEqual(c.echanger(connexion, flux, message), f"Reçu : {message}")

    def test_plusieurs_messages_sur_la_meme_connexion(self):
        connexion, flux = self.nouveau_client()
        for numero in range(20):
            self.assertEqual(c.echanger(connexion, flux, f"message {numero}"), f"Reçu : message {numero}")

    def test_un_message_coupe_en_deux_envois_reste_un_seul_message(self):
        # TCP est un flux d'octets : un message peut arriver en plusieurs morceaux.
        connexion, flux = self.nouveau_client()
        connexion.sendall("Bon".encode("utf-8"))
        connexion.sendall("jour\n".encode("utf-8"))
        self.assertEqual(flux.readline(), "Reçu : Bonjour\n")

    def test_un_accent_coupe_en_deux_morceaux_reste_lisible(self):
        connexion, flux = self.nouveau_client()
        octets = "é\n".encode("utf-8")
        connexion.sendall(octets[:1])
        connexion.sendall(octets[1:])
        self.assertEqual(flux.readline(), "Reçu : é\n")

    def test_deux_messages_dans_un_seul_envoi_recoivent_deux_reponses(self):
        connexion, flux = self.nouveau_client()
        connexion.sendall(b"un\ndeux\n")
        self.assertEqual(flux.readline(), "Reçu : un\n")
        self.assertEqual(flux.readline(), "Reçu : deux\n")

    def test_octets_invalides_ne_font_pas_tomber_le_serveur(self):
        connexion, flux = self.nouveau_client()
        connexion.sendall(b"\xff\xfe\n")
        self.assertTrue(flux.readline().startswith("Reçu : "))
        self.assertEqual(c.echanger(connexion, flux, "encore là"), "Reçu : encore là")


class TestPlusieursClients(ServeurDeTest):
    def test_deux_clients_connectes_en_meme_temps(self):
        connexion_a, flux_a = self.nouveau_client()
        connexion_b, flux_b = self.nouveau_client()
        # Le client B reçoit sa réponse alors que le client A reste connecté sans rien envoyer.
        self.assertEqual(c.echanger(connexion_b, flux_b, "je suis B"), "Reçu : je suis B")
        self.assertEqual(c.echanger(connexion_a, flux_a, "je suis A"), "Reçu : je suis A")
        self.assertEqual(c.echanger(connexion_b, flux_b, "encore B"), "Reçu : encore B")

    def test_chaque_client_a_son_propre_port(self):
        connexion_a, _ = self.nouveau_client()
        connexion_b, _ = self.nouveau_client()
        self.assertNotEqual(connexion_a.getsockname()[1], connexion_b.getsockname()[1])

    def test_le_serveur_survit_au_depart_dun_client(self):
        connexion, _ = self.nouveau_client()
        connexion.close()
        autre, flux = self.nouveau_client()
        self.assertEqual(c.echanger(autre, flux, "toujours là"), "Reçu : toujours là")

    def test_le_serveur_survit_a_une_coupure_brutale(self):
        connexion, _ = self.nouveau_client()
        # SO_LINGER à 0 : la fermeture envoie un RST au lieu du FIN habituel.
        format_linger = "hh" if os.name == "nt" else "ii"  # la structure diffère entre Windows et Linux
        connexion.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack(format_linger, 1, 0))
        connexion.close()
        autre, flux = self.nouveau_client()
        self.assertEqual(c.echanger(autre, flux, "toujours là"), "Reçu : toujours là")


class TestErreurs(unittest.TestCase):
    def test_connexion_refusee_si_aucun_serveur_ne_tourne(self):
        # On réserve un port libre, puis on le libère : personne n'y écoute.
        temporaire = socket.socket()
        temporaire.bind(("127.0.0.1", 0))
        port = temporaire.getsockname()[1]
        temporaire.close()
        with self.assertRaises(OSError):
            c.se_connecter("127.0.0.1", port)

    def test_deux_serveurs_ne_peuvent_pas_ecouter_sur_le_meme_port(self):
        premier = s.creer_serveur("127.0.0.1", 0)
        self.addCleanup(premier.close)
        with self.assertRaises(OSError):
            s.creer_serveur("127.0.0.1", premier.getsockname()[1])

    def test_le_client_signale_un_serveur_qui_ferme(self):
        # Un faux serveur qui accepte la connexion puis ferme sans répondre.
        faux = socket.socket()
        self.addCleanup(faux.close)
        faux.bind(("127.0.0.1", 0))
        faux.listen(1)
        connexion = c.se_connecter("127.0.0.1", faux.getsockname()[1])
        self.addCleanup(connexion.close)
        accepte, _ = faux.accept()
        accepte.close()
        with connexion.makefile("r", encoding="utf-8", newline="\n") as flux:
            with self.assertRaises(OSError):  # ConnectionError est une sorte d'OSError
                c.echanger(connexion, flux, "Bonjour")


if __name__ == "__main__":
    unittest.main()
