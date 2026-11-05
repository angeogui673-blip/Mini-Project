package contacts;

import javafx.collections.FXCollections;
import javafx.collections.ObservableList;

/** Modèle : la liste des contacts et ses règles. Cette classe ne connaît pas la fenêtre. */
public class CarnetContacts {

    private static final int CHIFFRES_MIN = 3;
    private static final int CHIFFRES_MAX = 15;

    // Une liste observable prévient automatiquement ceux qui l'affichent quand elle change.
    private final ObservableList<Contact> contacts = FXCollections.observableArrayList();

    public ObservableList<Contact> getContacts() {
        return contacts;
    }

    /** Vérifie la saisie et ajoute le contact, ou lance une exception avec le message à afficher. */
    public void ajouter(String nom, String telephone) {
        Contact contact = new Contact(nettoyer(nom), nettoyer(telephone));

        if (contact.nom().isEmpty()) {
            throw new IllegalArgumentException("Saisissez un nom.");
        }
        if (contact.telephone().isEmpty()) {
            throw new IllegalArgumentException("Saisissez un numéro de téléphone.");
        }
        if (!contact.telephone().matches("\\+?[0-9 .()-]+")) {
            throw new IllegalArgumentException(
                    "Le numéro ne peut contenir que des chiffres, des espaces et + . ( ) -");
        }
        long chiffres = contact.telephone().chars().filter(c -> c >= '0' && c <= '9').count();
        if (chiffres < CHIFFRES_MIN || chiffres > CHIFFRES_MAX) {
            throw new IllegalArgumentException(
                    "Le numéro doit contenir de " + CHIFFRES_MIN + " à " + CHIFFRES_MAX + " chiffres.");
        }
        if (contacts.contains(contact)) {
            throw new IllegalArgumentException("Ce contact existe déjà.");
        }

        contacts.add(contact);
    }

    /** Retire les espaces au début et à la fin, et réduit les espaces répétés à un seul. */
    private static String nettoyer(String texte) {
        return texte.trim().replaceAll("\\s+", " ");
    }
}
