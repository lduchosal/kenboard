---
id: 1165
title: "frontend / page à propos : projet, versions, dépendances, python (sections sensibles admin)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-01T10:16:07
classified_at: 2026-11-01T10:09:57
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #1165 — frontend / page à propos : projet, versions, dépendances, python (sections sensibles admin)

**TL;DR** — Il manquait une page « À propos » → nouvelle page `/about` (lien *À propos* dans le menu avatar). Tout utilisateur connecté y voit la présentation du projet, la version et les liens ; seuls les admins voient Python, la plateforme, les dépendances installées, la base et les migrations.

Ajouter une page « À propos » qui explique le projet et affiche les versions en cours (kenboard, Python, dépendances…). Les sections sensibles sont réservées à l'admin.

## Résolution

### Modifications
- `src/dashboard/about.py` (nouveau) — collecte des infos : `public_info()` (version, licence, liens repo/releases/PyPI), `runtime_info()` (Python, exécutable, venv, plateforme), `dependencies()` (`Requires-Dist` de kenboard + version installée, core puis extras), `database_info()` (version MySQL, base courante, migrations yoyo ; une erreur DB donne `None`, la page s'affiche quand même). Aucun secret lu.
- `src/dashboard/queries/about.sql` (nouveau) — `about_db_server` (`VERSION()`, `DATABASE()`), `about_migrations` (nombre + dernière ligne de `_yoyo_migration`).
- `src/dashboard/routes/pages.py` — route `GET /about` (`@login_required`). Les données admin ne sont **calculées** que si `is_admin`, pas seulement masquées dans le template.
- `src/dashboard/templates/about.html` (nouveau) — carte *Projet* (pour tous) + carte *Admin — Environnement d'exécution*.
- `src/dashboard/templates/partials/aide_styles.html` (nouveau) — styles des cartes, sortis de `aide.html` pour être partagés ; `aide.html` l'inclut.
- `src/dashboard/templates/partials/header.html` — lien *À propos* dans le menu avatar, sous *Aide*.
- `tests/unit/test_about.py` (nouveau, 11 tests) — parsing des requirements, liste des deps, rendu admin, non-admin connecté (pas de section admin), anonyme redirigé vers `/login`.

### Comportements obtenus
- Admin : Python 3.x + exécutable/venv, plateforme, MySQL + base, migrations (N appliquées, dernière, date), tableau des dépendances (requis / installé / extra ; extra non installé = *absent*).
- Non-admin : présentation, version, licence, liens. Rien sur le runtime.
- Base de test (schéma créé à la main, sans yoyo) : « aucune trace yoyo », pas d'erreur.

### Garde-fous
- `pdm run test-unit` : 685 passed.
- isort, black, docformatter, ruff, flake8, mypy, interrogate (100 %), vulture, refurb : verts.
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-11-01.md)
