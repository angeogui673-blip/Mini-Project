// La page du téléphone : elle affiche ce que renvoie le serveur et réagit aux gestes.
// Aucune règle ici : la recherche, les vérifications et le tri restent dans contacts.py.

const LETTRES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ#";
const COULEURS = ["#163A47", "#2F6F73", "#7A4E8C", "#A4532B", "#3B6EA5", "#5C7A29", "#A63D57"];
const SERVEUR_MUET = "Le serveur ne répond pas. Vérifiez que app.py est lancé.";

const ecran = document.querySelector(".ecran");
const element = (id) => document.getElementById(id);

const etat = {
  ficheOuverte: null, // le contact affiché sur la fiche
  feuille: null, // la feuille ouverte
  retourFiche: null, // l'élément à qui rendre le focus en fermant la fiche
  retourFeuille: null, // l'élément à qui rendre le focus en fermant la feuille
  derniereDemande: 0,
};

// --- Petits outils ---

function creer(balise, classe, texte) {
  const noeud = document.createElement(balise);
  if (classe) noeud.className = classe;
  // textContent et jamais innerHTML : un nom contenant du HTML reste du simple texte.
  if (texte !== undefined) noeud.textContent = texte;
  return noeud;
}

async function envoyer(adresse, contact) {
  const reponse = await fetch(adresse, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(contact),
  });
  const donnees = await reponse.json().catch(() => ({}));
  return { statut: reponse.status, donnees };
}

function initiales(nom) {
  return nom
    .split(" ")
    .slice(0, 2)
    .map((mot) => Array.from(mot)[0].toUpperCase())
    .join("");
}

function couleurDe(nom) {
  const somme = Array.from(nom).reduce((total, lettre) => total + lettre.codePointAt(0), 0);
  return COULEURS[somme % COULEURS.length];
}

function remplirAvatar(avatar, nom) {
  avatar.textContent = initiales(nom);
  avatar.style.background = couleurDe(nom);
}

// --- La liste ---

function creerLigne(contact) {
  const ligne = creer("button", "ligne");
  ligne.type = "button";

  const avatar = creer("span", "avatar");
  avatar.setAttribute("aria-hidden", "true");
  remplirAvatar(avatar, contact.nom);

  const texte = creer("span", "ligne-texte");
  texte.append(creer("span", "ligne-nom", contact.nom), creer("span", "ligne-numero", contact.telephone));

  ligne.append(avatar, texte);
  ligne.addEventListener("click", () => ouvrirFiche(contact, ligne));
  return ligne;
}

function afficherVide(titre, texte) {
  const vide = creer("div", "vide");
  vide.append(creer("strong", "", titre), creer("span", "", texte));
  element("liste").replaceChildren(vide);
}

function afficherListe(contacts, total, recherche) {
  element("compteur").textContent =
    total === 0 ? "Aucun contact" : `${total} contact${total > 1 ? "s" : ""}`;

  const parLettre = new Map();
  for (const contact of contacts) {
    if (!parLettre.has(contact.initiale)) parLettre.set(contact.initiale, []);
    parLettre.get(contact.initiale).push(contact);
  }

  if (total === 0) {
    afficherVide("Votre carnet est vide", "Touchez + pour ajouter votre premier contact.");
  } else if (contacts.length === 0) {
    afficherVide("Aucun résultat", `Aucun contact ne correspond à « ${recherche} ».`);
  } else {
    const morceaux = [];
    for (const lettre of LETTRES) {
      if (!parLettre.has(lettre)) continue;
      const section = creer("section");
      section.dataset.lettre = lettre;
      section.append(creer("div", "lettre", lettre), ...parLettre.get(lettre).map(creerLigne));
      morceaux.push(section);
    }
    element("liste").replaceChildren(...morceaux);
  }

  actualiserIndex(parLettre, recherche);
}

function actualiserIndex(parLettre, recherche) {
  const index = element("index");
  index.hidden = Boolean(recherche);
  for (const bouton of index.children) {
    bouton.disabled = !parLettre.has(bouton.textContent);
  }
}

function construireIndex() {
  for (const lettre of LETTRES) {
    const bouton = creer("button", "", lettre);
    bouton.type = "button";
    bouton.tabIndex = -1; // au clavier, la recherche suffit : on évite 27 passages avec Tab
    bouton.addEventListener("click", () => allerALaLettre(lettre));
    element("index").append(bouton);
  }
}

function allerALaLettre(lettre) {
  const section = element("liste").querySelector(`[data-lettre="${lettre}"]`);
  if (section) element("liste").scrollTop = section.offsetTop;
}

async function chargerContacts() {
  // Une réponse lente ne doit pas remplacer celle d'une recherche plus récente.
  const demande = ++etat.derniereDemande;
  const recherche = element("champ-recherche").value.trim();

  try {
    const reponse = await fetch(`/api/contacts?q=${encodeURIComponent(recherche)}`);
    const donnees = await reponse.json();
    if (demande !== etat.derniereDemande) return;
    if (!reponse.ok) {
      afficherVide("Contacts indisponibles", donnees.erreur);
      return;
    }
    afficherListe(donnees.contacts, donnees.total, recherche);
  } catch {
    if (demande === etat.derniereDemande) afficherVide("Contacts indisponibles", SERVEUR_MUET);
  }
}

// --- Quelle partie de l'écran peut recevoir le clavier ---
// preventScroll : une feuille encore cachée sous l'écran ne doit pas faire défiler la zone.

function actualiserAcces() {
  element("vue-liste").inert = Boolean(etat.ficheOuverte || etat.feuille);
  element("vue-fiche").inert = !etat.ficheOuverte || Boolean(etat.feuille);
  for (const feuille of document.querySelectorAll(".feuille")) {
    feuille.inert = feuille !== etat.feuille;
  }
}

function rendreLeFocus(cible) {
  if (cible && cible.isConnected) cible.focus({ preventScroll: true });
  else element("champ-recherche").focus({ preventScroll: true });
}

// --- La fiche ---

function ouvrirFiche(contact, origine) {
  etat.ficheOuverte = contact;
  etat.retourFiche = origine;

  remplirAvatar(element("fiche-avatar"), contact.nom);
  element("fiche-nom").textContent = contact.nom;
  element("fiche-telephone").textContent = contact.telephone;

  const numero = contact.telephone.replace(/[^0-9+]/g, "");
  element("lien-appeler").href = `tel:${numero}`;
  element("lien-message").href = `sms:${numero}`;

  ecran.classList.add("fiche-ouverte");
  actualiserAcces();
  element("bouton-retour").focus({ preventScroll: true });
}

function fermerFiche() {
  etat.ficheOuverte = null;
  ecran.classList.remove("fiche-ouverte");
  actualiserAcces();
  rendreLeFocus(etat.retourFiche);
}

// --- Les feuilles ---

function ouvrirFeuille(feuille, premierChamp) {
  etat.feuille = feuille;
  etat.retourFeuille = document.activeElement;
  feuille.classList.add("ouverte");
  ecran.classList.add("feuille-ouverte");
  actualiserAcces();
  premierChamp.focus({ preventScroll: true });
}

function fermerFeuille() {
  etat.feuille.classList.remove("ouverte");
  etat.feuille = null;
  ecran.classList.remove("feuille-ouverte");
  actualiserAcces();
  rendreLeFocus(etat.retourFeuille);
}

function ouvrirAjout() {
  element("formulaire").reset();
  afficherErreurAjout("");
  ouvrirFeuille(element("feuille-ajout"), element("champ-nom"));
}

function afficherErreurAjout(texte, champ) {
  element("erreur-ajout").textContent = texte;
  for (const nom of ["nom", "telephone"]) {
    element(`champ-${nom}`).setAttribute("aria-invalid", String(nom === champ));
  }
  if (champ) element(`champ-${champ}`).focus({ preventScroll: true });
}

async function enregistrer(evenement) {
  evenement.preventDefault();
  const bouton = element("bouton-enregistrer");
  bouton.disabled = true; // évite un doublon en cas de double clic

  try {
    const { statut, donnees } = await envoyer("/api/contacts", {
      nom: element("champ-nom").value,
      telephone: element("champ-telephone").value,
    });
    if (statut === 201) {
      fermerFeuille();
      element("champ-recherche").value = ""; // sinon le nouveau contact pourrait rester caché
      await chargerContacts();
      ouvrirFiche(donnees.contact, element("champ-recherche"));
    } else {
      afficherErreurAjout(donnees.erreur || "L'enregistrement a échoué.", donnees.champ);
    }
  } catch {
    afficherErreurAjout(SERVEUR_MUET);
  } finally {
    bouton.disabled = false;
  }
}

function ouvrirSuppression() {
  const { nom, telephone } = etat.ficheOuverte;
  element("texte-suppression").textContent = `${nom} (${telephone}) sera supprimé définitivement.`;
  element("erreur-suppression").textContent = "";
  ouvrirFeuille(element("feuille-suppression"), element("bouton-garder"));
}

async function confirmerSuppression() {
  const bouton = element("bouton-confirmer");
  bouton.disabled = true;

  try {
    const { nom, telephone } = etat.ficheOuverte;
    const { statut, donnees } = await envoyer("/api/contacts/supprimer", { nom, telephone });
    // 404 : le contact a déjà disparu, le résultat voulu est atteint.
    if (statut === 200 || statut === 404) {
      fermerFeuille();
      fermerFiche();
      await chargerContacts();
    } else {
      element("erreur-suppression").textContent = donnees.erreur || "La suppression a échoué.";
    }
  } catch {
    element("erreur-suppression").textContent = SERVEUR_MUET;
  } finally {
    bouton.disabled = false;
  }
}

// --- L'heure de la barre du haut ---

function afficherHeure() {
  element("heure").textContent = new Date().toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// --- Le démarrage ---

function quandTouche(evenement) {
  if (evenement.key !== "Escape") return;
  if (etat.feuille) fermerFeuille();
  else if (etat.ficheOuverte) fermerFiche();
}

function demarrer() {
  construireIndex();
  element("champ-recherche").addEventListener("input", chargerContacts);
  element("bouton-nouveau").addEventListener("click", ouvrirAjout);
  element("bouton-retour").addEventListener("click", fermerFiche);
  element("bouton-annuler").addEventListener("click", fermerFeuille);
  element("formulaire").addEventListener("submit", enregistrer);
  element("bouton-supprimer").addEventListener("click", ouvrirSuppression);
  element("bouton-confirmer").addEventListener("click", confirmerSuppression);
  element("bouton-garder").addEventListener("click", fermerFeuille);
  element("voile").addEventListener("click", fermerFeuille);
  document.addEventListener("keydown", quandTouche);

  afficherHeure();
  setInterval(afficherHeure, 20000);
  chargerContacts();
}

demarrer();
