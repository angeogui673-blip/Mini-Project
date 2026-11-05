"""Interface : la fenêtre Tkinter. Elle affiche et réagit aux événements, sans décider des règles."""

import sys
import tkinter as tk
from tkinter import messagebox, ttk

import theme
from contacts import (
    LETTRES,
    ContactInvalide,
    ajouter_contact,
    chercher_contacts,
    contacts_de_lettre,
    creer_contact,
    initiales_presentes,
    supprimer_contact,
)
from stockage import FICHIER_CONTACTS, FichierIllisible, charger_contacts, sauvegarder_contacts


class FenetreContacts:
    """Un répertoire : la recherche, la liste, les onglets A à Z et le formulaire d'ajout."""

    def __init__(self, racine, contacts, chemin=FICHIER_CONTACTS):
        self.racine = racine
        self.contacts = contacts
        self.chemin = chemin
        self.lettre = None  # l'onglet choisi, ou None pour tout afficher
        self.lignes = {}  # relie chaque ligne de la liste à son contact
        self.echelle = racine.winfo_fpixels("1i") / 96  # 1.5 sur un écran réglé à 150 %

        theme.appliquer_theme(racine, self.px)
        racine.title("Mes contacts")
        racine.geometry(f"{self.px(560)}x{self.px(590)}")
        racine.minsize(self.px(500), self.px(560))
        racine.columnconfigure(0, weight=1)
        racine.rowconfigure(1, weight=1)

        self.construire_entete()
        self.construire_onglets()
        page = ttk.Frame(racine, padding=self.px(14))
        page.grid(row=1, column=0, sticky="nsew")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        self.construire_recherche(page)
        self.construire_liste(page)
        self.construire_formulaire(page)

        self.afficher_contacts()
        self.champ_nom.focus_set()

    def px(self, taille):
        """Adapte une taille en pixels à l'échelle de l'écran."""
        return round(taille * self.echelle)

    def construire_entete(self):
        """Crée le bandeau du haut : le titre et le nombre de contacts."""
        entete = tk.Frame(self.racine, background=theme.COUVERTURE)
        entete.grid(row=0, column=0, columnspan=2, sticky="ew")
        entete.columnconfigure(0, weight=1)

        tk.Label(
            entete,
            text="Mes contacts",
            background=theme.COUVERTURE,
            foreground=theme.PAPIER,
            font=("Georgia", 18),
        ).grid(row=0, column=0, sticky="w", padx=self.px(14), pady=self.px(10))

        self.compteur = tk.Label(entete, background=theme.COUVERTURE, foreground=theme.ONGLET)
        self.compteur.grid(row=0, column=1, sticky="e", padx=self.px(14))

    def construire_onglets(self):
        """Crée les onglets du bord droit, comme sur un répertoire papier."""
        cadre = tk.Frame(self.racine, background=theme.COUVERTURE)
        cadre.grid(row=1, column=1, sticky="ns")

        self.onglets = {}
        for rang, lettre in enumerate(LETTRES + "#"):
            cadre.rowconfigure(rang, weight=1, uniform="onglet")
            bouton = tk.Button(
                cadre,
                text=lettre,
                width=3,
                relief="flat",
                borderwidth=0,
                padx=0,
                pady=0,
                takefocus=0,  # au clavier, la recherche suffit : on évite 27 passages avec Tab
                font=("Segoe UI", 8, "bold"),
                foreground=theme.ENCRE,
                activeforeground=theme.ENCRE,
                activebackground=theme.ACCENT_SURVOL,
                disabledforeground=theme.ONGLET_VIDE,
                # lettre=lettre : chaque bouton garde sa propre lettre
                command=lambda lettre=lettre: self.choisir_lettre(lettre),
            )
            bouton.grid(row=rang, column=0, sticky="nsew", pady=(0, 1))
            self.onglets[lettre] = bouton

    def construire_recherche(self, page):
        """Crée le champ de recherche. La liste se filtre à chaque caractère saisi."""
        cadre = ttk.Frame(page)
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, self.px(10)))
        cadre.columnconfigure(1, weight=1)

        ttk.Label(cadre, text="Rechercher").grid(row=0, column=0, padx=(0, self.px(8)))
        self.recherche = tk.StringVar()
        self.champ_recherche = ttk.Entry(cadre, textvariable=self.recherche)
        self.champ_recherche.grid(row=0, column=1, sticky="ew")

        self.recherche.trace_add("write", self.quand_recherche)
        self.champ_recherche.bind("<Escape>", self.quand_echap)

    def construire_liste(self, page):
        """Crée le tableau des contacts, sa barre de défilement et le bouton de suppression."""
        cadre = ttk.Frame(page)
        cadre.grid(row=1, column=0, sticky="nsew")
        cadre.columnconfigure(0, weight=1)
        cadre.rowconfigure(0, weight=1)

        self.liste = ttk.Treeview(
            cadre, columns=("nom", "telephone"), show="headings", selectmode="browse", height=6
        )
        self.liste.heading("nom", text="Nom", anchor="w")
        self.liste.heading("telephone", text="Téléphone", anchor="w")
        self.liste.column("nom", width=self.px(250), stretch=True)
        self.liste.column("telephone", width=self.px(170), stretch=False)
        self.liste.grid(row=0, column=0, sticky="nsew")

        defilement = ttk.Scrollbar(cadre, orient="vertical", command=self.liste.yview)
        defilement.grid(row=0, column=1, sticky="ns")
        self.liste.configure(yscrollcommand=defilement.set)

        self.liste.bind("<<TreeviewSelect>>", self.quand_selection)
        self.liste.bind("<Delete>", self.quand_touche_suppr)

        bas = ttk.Frame(cadre)
        bas.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(self.px(8), 0))
        bas.columnconfigure(0, weight=1)

        self.indication = ttk.Label(bas, style="Doux.TLabel", wraplength=self.px(330))
        self.indication.grid(row=0, column=0, sticky="w")
        self.bouton_supprimer = ttk.Button(
            bas, text="Supprimer", style="Supprimer.TButton", command=self.supprimer
        )
        self.bouton_supprimer.grid(row=0, column=1, sticky="e", padx=(self.px(8), 0))

    def construire_formulaire(self, page):
        """Crée le formulaire d'ajout et la zone d'erreur."""
        ttk.Separator(page).grid(row=2, column=0, sticky="ew", pady=self.px(12))

        cadre = ttk.Frame(page)
        cadre.grid(row=3, column=0, sticky="ew")
        cadre.columnconfigure(0, weight=3, uniform="champ")
        cadre.columnconfigure(1, weight=2, uniform="champ")

        ttk.Label(cadre, text="Nouveau contact", style="Titre.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, self.px(6))
        )
        ecart = (0, self.px(8))
        ttk.Label(cadre, text="Nom").grid(row=1, column=0, sticky="w")
        ttk.Label(cadre, text="Téléphone").grid(row=1, column=1, sticky="w")

        self.champ_nom = ttk.Entry(cadre)
        self.champ_nom.grid(row=2, column=0, sticky="ew", padx=ecart)
        self.champ_telephone = ttk.Entry(cadre)
        self.champ_telephone.grid(row=2, column=1, sticky="ew", padx=ecart)

        self.bouton_ajouter = ttk.Button(
            cadre, text="Ajouter", style="Ajouter.TButton", command=self.ajouter
        )
        self.bouton_ajouter.grid(row=2, column=2)

        self.message = ttk.Label(cadre, style="Erreur.TLabel", wraplength=self.px(470))
        self.message.grid(row=3, column=0, columnspan=3, sticky="w", pady=(self.px(6), 0))
        self.message.grid_remove()

        # La touche Entrée fait la même chose que le bouton.
        self.champ_nom.bind("<Return>", self.quand_entree)
        self.champ_telephone.bind("<Return>", self.quand_entree)

    def afficher_erreur(self, texte):
        """Affiche l'erreur sous le formulaire. La ligne disparaît quand il n'y a plus d'erreur."""
        self.message.configure(text=texte)
        if texte:
            self.message.grid()
        else:
            self.message.grid_remove()

    def contacts_visibles(self):
        """Retourne les contacts à montrer selon l'onglet choisi ou la recherche."""
        if self.lettre:
            return contacts_de_lettre(self.contacts, self.lettre)
        return chercher_contacts(self.contacts, self.recherche.get())

    def afficher_contacts(self, contact_a_montrer=None):
        """Redessine la liste, le compteur et les onglets à partir des données."""
        self.liste.delete(*self.liste.get_children())
        self.lignes = {}
        for contact in self.contacts_visibles():
            ligne = self.liste.insert("", "end", values=(contact["nom"], contact["telephone"]))
            self.lignes[ligne] = contact
            if contact == contact_a_montrer:
                self.liste.selection_set(ligne)
                self.liste.see(ligne)

        total = len(self.contacts)
        self.compteur.configure(
            text="Aucun contact" if total == 0 else f"{total} contact{'s' if total > 1 else ''}"
        )
        self.actualiser_onglets()
        self.actualiser_indication()
        self.actualiser_bouton_supprimer()

    def actualiser_onglets(self):
        """Grise les onglets vides et met en valeur l'onglet choisi."""
        presentes = initiales_presentes(self.contacts)
        for lettre, bouton in self.onglets.items():
            bouton.configure(
                state="normal" if lettre in presentes else "disabled",
                background=theme.ACCENT if lettre == self.lettre else theme.ONGLET,
            )

    def actualiser_indication(self):
        """Explique ce que montre la liste quand elle est vide ou filtrée."""
        if not self.contacts:
            texte = "Ajoutez votre premier contact ci-dessous."
        elif self.lettre:
            texte = f"Lettre {self.lettre}. Cliquez de nouveau dessus pour tout afficher."
        elif self.recherche.get().strip() and not self.lignes:
            texte = "Aucun contact ne correspond à cette recherche."
        else:
            texte = ""
        self.indication.configure(text=texte)

    def actualiser_bouton_supprimer(self):
        """N'active le bouton Supprimer que si un contact est sélectionné."""
        self.bouton_supprimer.state(["!disabled"] if self.liste.selection() else ["disabled"])

    def choisir_lettre(self, lettre):
        """Réagit au clic sur un onglet : filtre sur cette lettre, ou tout afficher si déjà choisie."""
        self.lettre = None if lettre == self.lettre else lettre
        self.recherche.set("")
        self.afficher_contacts()

    def quand_recherche(self, *_arguments):
        """Réagit à chaque changement dans le champ de recherche."""
        if self.recherche.get():
            self.lettre = None
        self.afficher_contacts()

    def quand_echap(self, _evenement):
        """Efface la recherche avec la touche Échap."""
        self.recherche.set("")

    def quand_selection(self, _evenement):
        """Réagit à la sélection d'une ligne."""
        self.actualiser_bouton_supprimer()

    def quand_touche_suppr(self, _evenement):
        """Réagit à la touche Suppr dans la liste."""
        self.supprimer()

    def ajouter(self):
        """Réagit au clic : demande à la logique, enregistre, puis met la fenêtre à jour."""
        nom = self.champ_nom.get()
        telephone = self.champ_telephone.get()

        try:
            # On relit le fichier : le site web a pu le modifier depuis l'ouverture de la fenêtre.
            contacts = ajouter_contact(charger_contacts(self.chemin), nom, telephone)
            sauvegarder_contacts(contacts, self.chemin)
        except ContactInvalide as erreur:
            self.afficher_erreur(str(erreur))
            champ = self.champ_nom if erreur.champ == "nom" else self.champ_telephone
            champ.focus_set()
            return
        except (OSError, FichierIllisible) as erreur:
            # Le contact reste dans les champs : rien n'est perdu et on peut réessayer.
            self.afficher_erreur(f"Enregistrement impossible : {erreur}")
            return

        self.contacts = contacts
        self.afficher_erreur("")
        self.champ_nom.delete(0, "end")
        self.champ_telephone.delete(0, "end")
        self.champ_nom.focus_set()
        # On retire les filtres, sinon le nouveau contact pourrait rester caché.
        self.lettre = None
        self.recherche.set("")
        self.afficher_contacts(creer_contact(nom, telephone))

    def supprimer(self):
        """Demande confirmation, retire le contact sélectionné, enregistre, puis met à jour."""
        selection = self.liste.selection()
        if not selection:
            return
        contact = self.lignes[selection[0]]

        if not messagebox.askyesno(
            "Supprimer ce contact ?",
            f"{contact['nom']} ({contact['telephone']}) sera supprimé définitivement.",
        ):
            return

        try:
            contacts = supprimer_contact(charger_contacts(self.chemin), contact)
            sauvegarder_contacts(contacts, self.chemin)
        except (OSError, FichierIllisible) as erreur:
            self.afficher_erreur(f"Enregistrement impossible : {erreur}")
            return

        self.contacts = contacts
        self.afficher_erreur("")
        if self.lettre not in initiales_presentes(contacts):
            self.lettre = None  # l'onglet choisi vient de se vider
        self.afficher_contacts()

    def quand_entree(self, _evenement):
        """Réagit à la touche Entrée dans un champ."""
        self.ajouter()


def main():
    """Charge les contacts et ouvre la fenêtre. Un fichier illisible n'est jamais écrasé."""
    theme.activer_nettete()  # doit être appelée avant la création de la fenêtre
    racine = tk.Tk()
    try:
        contacts = charger_contacts()
    except FichierIllisible as erreur:
        racine.withdraw()
        messagebox.showerror(
            "Contacts illisibles",
            f"Le fichier de contacts n'a pas pu être lu.\nCorrigez-le ou déplacez-le, puis relancez.\n\n{erreur}",
        )
        sys.exit(1)

    FenetreContacts(racine, contacts)
    racine.mainloop()


if __name__ == "__main__":
    main()
