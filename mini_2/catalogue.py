"""Accès aux données du catalogue : tout le SQL du projet est dans ce fichier."""

import sqlite3
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

FICHIER_BASE = Path(__file__).parent / "catalogue.db"
DUREE_PRET_JOURS = 21

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
    couverture TEXT NOT NULL DEFAULT '',
    cote TEXT NOT NULL,
    categorie_id INTEGER NOT NULL REFERENCES categories (id)
);

-- Un prêt est en cours tant que date_rendu est vide. Les anciens prêts forment l'historique.
CREATE TABLE IF NOT EXISTS prets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    livre_id INTEGER NOT NULL REFERENCES livres (id) ON DELETE CASCADE,
    emprunteur TEXT NOT NULL,
    date_pret TEXT NOT NULL,
    date_retour TEXT NOT NULL,
    date_rendu TEXT
);

-- La base elle-même refuse deux prêts en cours pour le même livre.
CREATE UNIQUE INDEX IF NOT EXISTS un_seul_pret_en_cours
    ON prets (livre_id) WHERE date_rendu IS NULL;
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

# Une ligne de livre, avec sa catégorie et son prêt en cours.
# LEFT JOIN garde les livres sans prêt : emprunteur et date_retour sont alors vides.
SELECT_LIVRES = """
    SELECT livres.*, categories.nom AS categorie, prets.emprunteur, prets.date_retour
    FROM livres
    JOIN categories ON categories.id = livres.categorie_id
    LEFT JOIN prets ON prets.livre_id = livres.id AND prets.date_rendu IS NULL
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


def valider_livre(connexion, titre, auteur, annee, categorie_id, resume, couverture):
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

    couverture = couverture.strip()
    adresse = urlsplit(couverture)
    if couverture and (adresse.scheme not in ("http", "https") or not adresse.netloc):
        raise ValueError("L'adresse de la couverture doit commencer par https://.")

    return {
        "titre": titre,
        "auteur": auteur,
        "annee": annee,
        "resume": resume.strip(),
        "couverture": couverture,
        "cote": calculer_cote(categorie["code"], auteur),
        "categorie_id": categorie["id"],
    }


# --- Les quatre opérations de base (CRUD) ---
# Les « ? » et les « :nom » laissent SQLite insérer les valeurs :
# une saisie ne peut jamais devenir du SQL.

def ajouter_livre(connexion, titre, auteur, annee, categorie_id, resume="", couverture=""):
    """Create : ajoute un livre et retourne son id."""
    valeurs = valider_livre(connexion, titre, auteur, annee, categorie_id, resume, couverture)
    with connexion:  # valide l'écriture si tout va bien, l'annule en cas d'erreur
        curseur = connexion.execute(
            """
            INSERT INTO livres (titre, auteur, annee, resume, couverture, cote, categorie_id)
            VALUES (:titre, :auteur, :annee, :resume, :couverture, :cote, :categorie_id)
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


def modifier_livre(connexion, id_livre, titre, auteur, annee, categorie_id, resume="", couverture=""):
    """Update : remplace les valeurs d'un livre. Retourne False si l'id n'existe pas."""
    valeurs = valider_livre(connexion, titre, auteur, annee, categorie_id, resume, couverture)
    with connexion:
        curseur = connexion.execute(
            """
            UPDATE livres
            SET titre = :titre, auteur = :auteur, annee = :annee, resume = :resume,
                couverture = :couverture, cote = :cote, categorie_id = :categorie_id
            WHERE id = :id
            """,
            {**valeurs, "id": id_livre},
        )
    return curseur.rowcount > 0


def supprimer_livre(connexion, id_livre):
    """Delete : retire un livre et son historique. Retourne False si l'id n'existe pas.

    Lève ValueError si le livre est encore en prêt.
    """
    livre = trouver_livre(connexion, id_livre)
    if livre is None:
        return False
    if livre["emprunteur"] is not None:
        raise ValueError("Ce livre est en prêt : enregistrez son retour avant de le retirer.")
    with connexion:
        connexion.execute("DELETE FROM livres WHERE id = ?", (id_livre,))
    return True


# --- Les prêts ---

def date_retour_par_defaut(aujourdhui=None):
    """Retourne la date de retour proposée pour un nouveau prêt."""
    return (aujourdhui or date.today()) + timedelta(days=DUREE_PRET_JOURS)


def jours_de_retard(date_retour, aujourdhui=None):
    """Retourne le nombre de jours de retard d'une date de retour, ou 0 si elle n'est pas dépassée."""
    retard = (aujourdhui or date.today()) - date.fromisoformat(date_retour)
    return max(retard.days, 0)


def preter_livre(connexion, id_livre, emprunteur, date_retour, aujourdhui=None):
    """Enregistre un prêt et retourne son id. Lève ValueError si le prêt n'est pas possible."""
    aujourdhui = aujourdhui or date.today()
    emprunteur = emprunteur.strip()
    if not emprunteur:
        raise ValueError("Indiquez le nom de l'emprunteur.")

    try:
        retour = date.fromisoformat(date_retour.strip())
    except ValueError:
        raise ValueError("La date de retour doit être une date valide.")
    if retour < aujourdhui:
        raise ValueError("La date de retour ne peut pas être déjà passée.")

    if trouver_livre(connexion, id_livre) is None:
        raise ValueError("Ce livre n'existe pas.")

    try:
        with connexion:
            curseur = connexion.execute(
                "INSERT INTO prets (livre_id, emprunteur, date_pret, date_retour) VALUES (?, ?, ?, ?)",
                (id_livre, emprunteur, aujourdhui.isoformat(), retour.isoformat()),
            )
    except sqlite3.IntegrityError:  # refusé par l'index un_seul_pret_en_cours
        raise ValueError("Ce livre est déjà en prêt.")
    return curseur.lastrowid


def rendre_livre(connexion, id_livre, aujourdhui=None):
    """Enregistre le retour du livre. Retourne False s'il n'était pas en prêt."""
    aujourdhui = aujourdhui or date.today()
    with connexion:
        curseur = connexion.execute(
            "UPDATE prets SET date_rendu = ? WHERE livre_id = ? AND date_rendu IS NULL",
            (aujourdhui.isoformat(), id_livre),
        )
    return curseur.rowcount > 0


def lister_prets_en_cours(connexion):
    """Retourne les prêts en cours, les retours les plus urgents en premier."""
    return connexion.execute(
        """
        SELECT prets.*, livres.id AS id_livre, livres.titre, livres.auteur, livres.cote, livres.couverture
        FROM prets
        JOIN livres ON livres.id = prets.livre_id
        WHERE prets.date_rendu IS NULL
        ORDER BY prets.date_retour, sans_accents(livres.titre)
        """
    ).fetchall()


def compter_prets(connexion, aujourdhui=None):
    """Retourne le nombre de prêts en cours et le nombre de prêts en retard."""
    aujourdhui = aujourdhui or date.today()
    ligne = connexion.execute(
        """
        SELECT COUNT(*) AS en_cours, COALESCE(SUM(date_retour < ?), 0) AS en_retard
        FROM prets
        WHERE date_rendu IS NULL
        """,
        (aujourdhui.isoformat(),),
    ).fetchone()
    return {"en_cours": ligne["en_cours"], "en_retard": ligne["en_retard"]}


def historique_prets(connexion, id_livre, limite=5):
    """Retourne les derniers prêts terminés d'un livre, du plus récent au plus ancien."""
    return connexion.execute(
        """
        SELECT * FROM prets
        WHERE livre_id = ? AND date_rendu IS NOT NULL
        ORDER BY date_rendu DESC, id DESC
        LIMIT ?
        """,
        (id_livre, limite),
    ).fetchall()
