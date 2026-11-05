"""Apparence : les couleurs, les polices et le style des éléments, inspirés d'un répertoire papier."""

import ctypes
from tkinter import font as tkfont
from tkinter import ttk

COUVERTURE = "#163A47"
PAGE = "#F5F8F7"
PAPIER = "#FFFFFF"
ENCRE = "#1C2B30"
ENCRE_DOUCE = "#55686F"
BORDURE = "#C9D6D8"
ONGLET = "#DDE8E8"
ONGLET_VIDE = "#94A6AB"
ACCENT = "#E8A917"
ACCENT_SURVOL = "#F4BC3A"
ERREUR = "#B00020"


def activer_nettete():
    """Sous Windows, dessine la fenêtre à la vraie résolution de l'écran pour éviter le flou."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):  # autre système que Windows, ou Windows trop ancien
        pass


def appliquer_theme(racine, px):
    """Applique le style à toute la fenêtre. `px` adapte une taille en pixels à l'échelle de l'écran."""
    racine.configure(background=PAGE)
    for nom in ("TkDefaultFont", "TkTextFont", "TkHeadingFont"):
        tkfont.nametofont(nom).configure(family="Segoe UI", size=10)

    style = ttk.Style(racine)
    style.theme_use("clam")  # le seul thème livré avec Tkinter dont on peut changer toutes les couleurs

    style.configure("TFrame", background=PAGE)
    style.configure("TLabel", background=PAGE, foreground=ENCRE)
    style.configure("Doux.TLabel", foreground=ENCRE_DOUCE)
    style.configure("Erreur.TLabel", foreground=ERREUR)
    style.configure("Titre.TLabel", font=("Segoe UI", 11, "bold"))
    style.configure("TSeparator", background=BORDURE)

    style.configure(
        "TEntry",
        fieldbackground=PAPIER,
        foreground=ENCRE,
        bordercolor=BORDURE,
        lightcolor=PAPIER,
        darkcolor=PAPIER,
        padding=px(5),
    )
    style.map("TEntry", bordercolor=[("focus", COUVERTURE)], lightcolor=[("focus", COUVERTURE)])

    style.configure(
        "Ajouter.TButton",
        background=ACCENT,
        foreground=ENCRE,
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        focuscolor=ENCRE,
        font=("Segoe UI", 10, "bold"),
        padding=(px(16), px(5)),
    )
    style.map("Ajouter.TButton", background=[("active", ACCENT_SURVOL)])

    style.configure(
        "Supprimer.TButton",
        background=PAGE,
        foreground=ERREUR,
        bordercolor=BORDURE,
        lightcolor=PAGE,
        darkcolor=PAGE,
        focuscolor=ERREUR,
        padding=(px(10), px(3)),
    )
    style.map(
        "Supprimer.TButton",
        background=[("active", PAPIER)],
        foreground=[("disabled", ONGLET_VIDE)],
    )

    style.configure(
        "Treeview",
        background=PAPIER,
        fieldbackground=PAPIER,
        foreground=ENCRE,
        bordercolor=BORDURE,
        lightcolor=PAPIER,
        darkcolor=PAPIER,
        rowheight=px(30),
    )
    style.map("Treeview", background=[("selected", COUVERTURE)], foreground=[("selected", PAPIER)])
    style.configure(
        "Treeview.Heading",
        background=ONGLET,
        foreground=ENCRE,
        bordercolor=BORDURE,
        lightcolor=ONGLET,
        darkcolor=ONGLET,
        relief="flat",
        font=("Segoe UI", 10, "bold"),
        padding=(0, px(5)),  # aligne les titres sur le texte des lignes
    )
    style.map("Treeview.Heading", background=[("active", ONGLET)])

    style.configure(
        "Vertical.TScrollbar",
        background=ONGLET,
        troughcolor=PAGE,
        bordercolor=PAGE,
        lightcolor=ONGLET,
        darkcolor=ONGLET,
        arrowcolor=ENCRE_DOUCE,
    )
