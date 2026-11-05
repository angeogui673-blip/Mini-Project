package contacts;

import java.io.IOException;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.stage.Stage;

/** Le point de départ : charge la vue, qui crée son contrôleur, puis ouvre la fenêtre. */
public class App extends Application {

    @Override
    public void start(Stage fenetre) throws IOException {
        Parent racine = FXMLLoader.load(App.class.getResource("contacts.fxml"));
        fenetre.setTitle("Mes contacts");
        fenetre.setScene(new Scene(racine, 420, 460));
        fenetre.show();
    }

    public static void main(String[] args) {
        launch(args);
    }
}
