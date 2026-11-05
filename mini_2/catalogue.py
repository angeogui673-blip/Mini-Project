"""Accès aux données du catalogue : tout le SQL du projet est dans ce fichier."""

import sqlite3
import unicodedata
from datetime import date
from pathlib import Path

FICHIER_BASE = Path(__file__).parent / "catalogue.db"

CREATION_TABLES = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS livres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titre TEXT NOT NULL,
    auteur TEXT NOT NULL,
    annee INTEGER NOT NULL,
    resume TEXT NOT NULL DEFAULT '',
    cote TEXT NOT NULL,
    disponible INTEGER NOT NULL DEFAULT 1 CHECK (disponible IN (0, 1)),
    categorie_id INTEGER NOT NULL REFERENCES categories (id)
);
"""

# Le code commence la cote du livre, comme sur l'étiquette collée au dos.
# Les documentaires utilisent la classification Dewey, comme dans une vraie bibliothèque.
CATEGORIES = [
    ("Roman", "R"),
    ("Policier", "RP"),
    ("Science-fiction", "SF"),
    ("Fantasy", "FA"),
    ("Jeunesse", "J"),
    ("Bande dessinée", "BD"),
    ("Poésie", "P"),
    ("Théâtre", "T"),
    ("Biographies", "B"),
    ("Philosophie", "100"),
    ("Sciences", "500"),
    ("Histoire", "900"),
]

# Ces mots font partie du nom de famille : « Le Clézio » donne LEC, « La Fontaine » donne LAF.
PARTICULES = {"le", "la", "du"}

# Une ligne de livre, avec le nom de sa catégorie grâce à la jointure entre les deux tables.
SELECT_LIVRES = """
    SELECT livres.*, categories.nom AS categorie
    FROM livres
    JOIN categories ON categories.id = livres.categorie_id
"""
TRI_LIVRES = "ORDER BY sans_accents(categories.nom), livres.cote, sans_accents(livres.titre), livres.id"


def sans_accents(texte):
    """Retourne le texte en minuscules, sans accents : « Cœur Émile » donne « coeur emile »."""
    decompose = unicodedata.normalize("NFD", texte)
    lettres = "".join(c for c in decompose if not unicodedata.combining(c))
    return lettres.casefold().replace("œ", "oe").replace("æ", "ae")


def connecter(chemin=FICHIER_BASE):
    """Ouvre la base, crée les tables et les catégories si besoin, et retourne la connexion."""
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row  # permet d'écrire livre["titre"]
    connexion.create_function("sans_accents", 1, sans_accents, deterministic=True)
    connexion.execute("PRAGMA foreign_keys = ON")  # SQLite ne les vérifie pas sans cette ligne
    connexion.executescript(CREATION_TABLES)

    if connexion.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        with connexion:
            connexion.executemany("INSERT INTO categories (nom, code) VALUES (?, ?)", CATEGORIES)
    return connexion


# --- Catégories ---

def lister_categories(connexion):
    """Retourne les catégories par ordre alphabétique, avec le nombre de livres de chacune."""
    # LEFT JOIN garde aussi les catégories qui n'ont encore aucun livre.
    return connexion.execute(
        """
        SELECT categories.*, COUNT(livres.id) AS nb
        FROM categories
        LEFT JOIN livres ON livres.categorie_id = categories.id
        GROUP BY categories.id
        ORDER BY sans_accents(categories.nom)
        """
    ).fetchall()


def trouver_categorie(connexion, categorie_id):
    """Retourne la catégorie portant cet id, ou None si elle n'existe pas."""
    return connexion.execute(
        "SELECT * FROM categories WHERE id = ?", (categorie_id,)
    ).fetchone()


# --- Validation ---

def calculer_cote(code, auteur):
    """Retourne la cote : le code de la catégorie et les 3 premières lettres du nom de l'auteur."""
    mots = auteur.split(" et ")[0].split()  # s'il y a deux auteurs, on classe au premier
    nom = mots[-1]
    if len(mots) >= 2 and mots[-2].casefold() in PARTICULES:
        nom = mots[-2] + nom
    lettres = "".join(lettre for lettre in sans_accents(nom) if lettre.isalpha())
    return f"{code} {lettres[:3].upper()}"


def valider_livre(connexion, titre, auteur, annee, categorie_id, resume, disponible):
    """Nettoie les valeurs d'un livre et les retourne. Lève ValueError si l'une est invalide."""
    titre = titre.strip()
    auteur = auteur.strip()
    if not titre:
        raise ValueError("Le titre ne peut pas être vide.")
    if not auteur:
        raise ValueError("L'auteur ne peut pas être vide.")

    try:
        annee = int(annee)
    except (TypeError, ValueError):
        raise ValueError("L'année doit être un nombre, par exemple 1885.")

    annee_maximale = date.today().year + 1
    if not 1 <= annee <= annee_maximale:
        raise ValueError(f"L'année doit être comprise entre 1 et {annee_maximale}.")

    try:
        categorie = trouver_categorie(connexion, int(categorie_id))
    except (TypeError, ValueError):
        categorie = None
    if categorie is None:
        raise ValueError("Choisissez une catégorie dans la liste.")

    return {
        "titre": titre,
        "auteur": auteur,
        "annee": annee,
        "resume": resume.strip(),
        "cote": calculer_cote(categorie["code"], auteur),
        "disponible": int(bool(disponible)),
        "categorie_id": categorie["id"],
    }


# --- Les quatre opérations de base (CRUD) ---
# Les « ? » et les « :nom » laissent SQLite insérer les valeurs :
# une saisie ne peut jamais devenir du SQL.

def ajouter_livre(connexion, titre, auteur, annee, categorie_id, resume="", disponible=True):
    """Create : ajoute un livre et retourne son id."""
    valeurs = valider_livre(connexion, titre, auteur, annee, categorie_id, resume, disponible)
    with connexion:  # valide l'écriture si tout va bien, l'annule en cas d'erreur
        curseur = connexion.execute(
            """
            INSERT INTO livres (titre, auteur, annee, resume, cote, disponible, categorie_id)
            VALUES (:titre, :auteur, :annee, :resume, :cote, :disponible, :categorie_id)
            """,
            valeurs,
        )
    return curseur.lastrowid


def lister_livres(connexion, categorie_id=None):
    """Read : retourne les livres rangés par catégorie puis par cote, éventuellement d'une seule catégorie."""
    if categorie_id is None:
        return connexion.execute(f"{SELECT_LIVRES} {TRI_LIVRES}").fetchall()
    return connexion.execute(
        f"{SELECT_LIVRES} WHERE livres.categorie_id = ? {TRI_LIVRES}", (categorie_id,)
    ).fetchall()


def rechercher_livres(connexion, terme):
    """Read : retourne les livres dont le titre, l'auteur ou la cote contient le terme."""
    # Dans LIKE, % et _ sont des jokers : on les protège pour les chercher tels quels.
    terme = sans_accents(terme)
    terme = terme.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    motif = f"%{terme}%"
    return connexion.execute(
        f"""
        {SELECT_LIVRES}
        WHERE sans_accents(livres.titre) LIKE ? ESCAPE '\\'
           OR sans_accents(livres.auteur) LIKE ? ESCAPE '\\'
           OR sans_accents(livres.cote) LIKE ? ESCAPE '\\'
        {TRI_LIVRES}
        """,
        (motif, motif, motif),
    ).fetchall()


def trouver_livre(connexion, id_livre):
    """Read : retourne le livre portant cet id, ou None s'il n'existe pas."""
    return connexion.execute(f"{SELECT_LIVRES} WHERE livres.id = ?", (id_livre,)).fetchone()


def modifier_livre(connexion, id_livre, titre, auteur, annee, categorie_id, resume="", disponible=True):
    """Update : remplace les valeurs d'un livre. Retourne False si l'id n'existe pas."""
    valeurs = valider_livre(connexion, titre, auteur, annee, categorie_id, resume, disponible)
    with connexion:
        curseur = connexion.execute(
            """
            UPDATE livres
            SET titre = :titre, auteur = :auteur, annee = :annee, resume = :resume,
                cote = :cote, disponible = :disponible, categorie_id = :categorie_id
            WHERE id = :id
            """,
            {**valeurs, "id": id_livre},
        )
    return curseur.rowcount > 0


def changer_disponibilite(connexion, id_livre):
    """Update : un livre disponible devient emprunté, et inversement. Retourne False si l'id n'existe pas."""
    with connexion:
        curseur = connexion.execute(
            "UPDATE livres SET disponible = 1 - disponible WHERE id = ?", (id_livre,)
        )
    return curseur.rowcount > 0


def supprimer_livre(connexion, id_livre):
    """Delete : retire un livre. Retourne False si l'id n'existe pas."""
    with connexion:
        curseur = connexion.execute("DELETE FROM livres WHERE id = ?", (id_livre,))
    return curseur.rowcount > 0
