---
id: 492
title: "KEN / Task / Author"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T07:48:07
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #492 — KEN / Task / Author

est-ce que l'auteur d'une task est connu dans la base ?

Sur la page d'accueil, en plus des activités sur les 30 derniers jours, ajouter en dessous un graphe en barres par semaine avec le nombre de tâches traitées par personne.

Définition de l'auteur :
- si la tâche a été créée avec un token, l'auteur est le propriétaire du token (son créateur) ;
- sinon, l'auteur est le créateur de la tâche.

---

## Résolution

### Réponse à la question
L'auteur n'est PAS sur la ligne `tasks` (seul `who` = l'assigné). Mais chaque mutation est tracée dans `activities.user_name` : nom d'affichage pour une session, principal `key:<id>:user:<owner>` pour un token (#110). Le propriétaire du token est donc récupérable (le principal embarque `user:<owner_id>` → `users.name`). Résolution à la LECTURE, pas de migration. Métrique : COUNT(*) de chaque mutation.

### Pivot de design (retour Luc, 2026-05-29)
Le spec initial demandait un graphe EMPILÉ par semaine. Remplacé par un CLASSEMENT (« concours du plus gros ken tasker ») : une barre par utilisateur = son total d'activité sur la fenêtre, trié du plus gros au plus petit. Plus de dimension hebdo ni d'empilement.

### Modifications
- queries/activities.sql : `activity_count_by_user` (COUNT(*) par principal depuis :since).
- routes/pages.py : `_resolve_activity_author` (principal → personne ; token→propriétaire, session→nom, sinon ignoré) + `_build_author_leaderboard` (résout, somme par personne, trie desc, géométrie SVG d'une barre/personne). Constante `LEADERBOARD_WINDOW_DAYS = 90`. Câblé dans `index()`.
- templates/partials/activity_leaderboard.html : nouveau partial (barres SVG + labels nom/total en HTML), inclus dans index.html sous l'activité 30j. (ancien activity_weekly.html supprimé.)
- static/style.css : styles .leaderboard-*.
- Tests : test_author_leaderboard.py (helpers purs), test_activity.py (requête activity_count_by_user), test_page_routes.py (rendu / : propriétaire du token affiché, pas le principal brut).

### Comportements obtenus
- Une barre par personne, classées du plus actif au moins actif (concours).
- Activité d'un token attribuée au propriétaire humain (pas à « Claude »).
- Session + token d'une même personne fusionnés.
- Tokens non-attribuables / anonymes ignorés.
- SVG inline côté serveur (labels en HTML car SVG étiré), aucune lib de chart, aucun changement JS. Fenêtre : 90 derniers jours.

### Garde-fous
- pdm run check : 490 passed (isort, black, docformatter, mypy strict, flake8, interrogate 100%, refurb, lint, vulture, test-quick + js-build). Aucune réf résiduelle 'weekly'.
- Rendu vérifié via test GET / (titre « Classement des taskers » + nom propriétaire ; principal brut absent). Pas de session navigateur live.
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-29.md)
