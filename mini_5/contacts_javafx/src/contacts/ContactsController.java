package contacts;

import javafx.fxml.FXML;
import javafx.scene.control.Label;
import javafx.scene.control.ListView;
import javafx.scene.control.TextField;

/** Contrôleur : relie la vue au modèle et réagit aux actions de l'utilisateur. */
public class ContactsController {

    // @FXML : JavaFX remplit ces champs avec les éléments de même fx:id dans contacts.fxml.
    @FXML private TextField champNom;
    @FXML private TextField champTelephone;
    @FXML private ListView<Contact> listeContacts;
    @FXML private Label message;

    private final CarnetContacts carnet = new CarnetContacts();

    /** Appelée par JavaFX une fois la vue chargée : la liste affichera les contacts du modèle. */
    @FXML
    private void initialize() {
        listeContacts.setItems(carnet.getContacts());
    }

    /** Appelée par le bouton ou la touche Entrée : transmet la saisie au modèle. */
    @FXML
    private void ajouter() {
        try {
            carnet.ajouter(champNom.getText(), champTelephone.getText());
        } catch (IllegalArgumentException erreur) {
            message.setText(erreur.getMessage());
            return;
        }

        message.setText("");
        champNom.clear();
        champTelephone.clear();
        champNom.requestFocus();
    }
}
