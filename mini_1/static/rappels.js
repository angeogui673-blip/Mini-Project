// Python décide quels rappels sont atteints. Ce script recharge seulement la page
// quand l'heure d'un rappel arrive alors qu'elle est restée ouverte.
const heures = [...document.querySelectorAll("[data-rappel]")].map(
  (tache) => new Date(tache.dataset.rappel)
);
const champs = [...document.querySelectorAll(".ajout input, .ajout textarea")];

setInterval(() => {
  const rappelArrive = heures.some((heure) => heure <= new Date());
  // On attend si quelqu'un est en train d'écrire, pour ne pas effacer sa saisie.
  const saisieEnCours = champs.some((champ) => champ.value);

  if (rappelArrive && !saisieEnCours) {
    location.assign("/?ouvert=1");
  }
}, 15000);
