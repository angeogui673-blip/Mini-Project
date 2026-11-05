// Affiche la vraie heure et la vraie date dans les éléments prévus pour.

function afficherHeure() {
  const maintenant = new Date();
  const heure = maintenant.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  const date = maintenant.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });

  for (const noeud of document.querySelectorAll("[data-heure]")) noeud.textContent = heure;
  for (const noeud of document.querySelectorAll("[data-date]")) noeud.textContent = date;
}

afficherHeure();
setInterval(afficherHeure, 20000);
