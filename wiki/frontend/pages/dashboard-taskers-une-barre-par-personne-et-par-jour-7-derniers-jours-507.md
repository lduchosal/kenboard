---
id: 507
title: "DASHBOARD / Taskers : une barre par personne et par jour (7 derniers jours)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T08:36:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #507 — DASHBOARD / Taskers : une barre par personne et par jour (7 derniers jours)

Évolution du composant « Classement des taskers » de la home (#492).

Au lieu d'une seule barre par personne (total sur 90 j), afficher un graphe en barres GROUPÉES : axe X = les 7 derniers jours ; pour chaque jour, une barre par personne (couleur de l'utilisateur).

- Métrique : COUNT(*) d'activités par (personne, jour).
- Attribution de l'auteur inchangée (token → propriétaire du token, sinon session) — réutiliser _resolve_activity_author (#492).
- Implique : nouvelle requête (GROUP BY DATE(occurred_at), user_name depuis :since=J-7), nouveau builder de géométrie + template (barres groupées, légende des personnes, axe = 7 jours), fenêtre = 7 jours au lieu de 90.
- Composant actuel : src/dashboard/templates/partials/activity_leaderboard.html + _build_author_leaderboard / activity_count_by_user.

---

## Résolution

### Modifications
- queries/activities.sql : activity_count_by_user → activity_daily_by_user (GROUP BY DATE(occurred_at), user_name depuis :since).
- routes/pages.py : _build_author_leaderboard → _build_taskers_daily_chart (résout les principals, bucket par (jour, personne), barres groupées : par jour, une barre par personne active ; ordre des personnes stable = total desc, partagé entre les jours). Constante LEADERBOARD_WINDOW_DAYS(90) → TASKERS_WINDOW_DAYS(7). Labels d'axe = jour FR abrégé + n° (ex. « ven 29 »). _resolve_activity_author inchangé.
- templates/partials/ : activity_leaderboard.html → activity_taskers.html (barres SVG groupées + axe 7 jours + légende personnes). Include index.html mis à jour.
- static/style.css : .leaderboard-* → .taskers-* (axe = colonnes égales, légende couleur→nom).
- Tests : test_taskers_chart.py (helpers : groupement, fusion session+token/jour, hors-fenêtre, vide), test_activity.py (requête activity_daily_by_user), test_page_routes.py (rendu / : titre « Taskers (7 derniers jours) », propriétaire affiché, principal brut absent).

### Comportements obtenus
- 7 groupes (jours), chaque groupe = une barre par personne active ce jour, couleur utilisateur.
- Légende couleur→personne (les noms ne tiennent pas sous chaque barre groupée) ; axe = libellés des 7 jours.
- Activité token attribuée au propriétaire ; session+token d'une personne fusionnés par jour ; jours hors fenêtre / principals non-attribuables ignorés.
- SVG inline côté serveur, aucune lib de chart, aucun changement JS.

### Garde-fous
- pdm run check : 491 passed (mypy strict, interrogate 100%, ruff, flake8, refurb, vulture, js-build, test-quick). Aucune réf résiduelle 'leaderboard'.
- Rendu vérifié via test GET / (titre + nom propriétaire ; principal brut absent). Pas de session navigateur live.
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-29.md)
