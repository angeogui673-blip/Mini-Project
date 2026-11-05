package contacts;

/** Modèle : un contact. Un record crée seul le constructeur, les accesseurs et equals. */
public record Contact(String nom, String telephone) {

    /** Le texte affiché par la liste de la fenêtre. */
    @Override
    public String toString() {
        return nom + " : " + telephone;
    }
}
