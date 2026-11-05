"""Remplit le catalogue avec les livres de livres.json. Lancement : python charger_livres.py

On peut le relancer sans risque : un livre déjà présent n'est ni dupliqué ni modifié.
"""

import json
from pathlib import Path

import catalogue as c

FICHIER_LIVRES = Path(__file__).parent / "livres.json"


def charger_livres(connexion, chemin=FICHIER_LIVRES):
    """Ajoute les livres absents du catalogue et retourne le nombre de livres ajoutés."""
    with open(chemin, encoding="utf-8") as fichier:
        livres = json.load(fichier)

    categories = {categorie["nom"]: categorie["id"] for categorie in c.lister_categories(connexion)}
    ajoutes = 0
    for livre in livres:
        deja_present = connexion.execute(
            "SELECT 1 FROM livres WHERE titre = ? AND auteur = ?",
            (livre["titre"], livre["auteur"]),
        ).fetchone()
        if deja_present:
            continue
        c.ajouter_livre(
            connexion,
            livre["titre"],
            livre["auteur"],
            livre["annee"],
            categories[livre["categorie"]],
            livre["resume"],
            livre.get("couverture", ""),
        )
        ajoutes += 1
    return ajoutes


def main():
    connexion = c.connecter()
    ajoutes = charger_livres(connexion)
    total = len(c.lister_livres(connexion))
    connexion.close()
    print(f"{ajoutes} livre(s) ajouté(s). Le catalogue en contient maintenant {total}.")


if __name__ == "__main__":
    main()
