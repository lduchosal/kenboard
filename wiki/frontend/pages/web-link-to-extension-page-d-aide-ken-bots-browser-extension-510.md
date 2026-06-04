---
id: 510
title: "WEB / Link to extension — page d'aide (ken bots + browser extension)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T10:19:00
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #510 — WEB / Link to extension — page d'aide (ken bots + browser extension)

Dans le kenboard web, ajouter une page dans le menu pour l'aide sur l'utilisation du kenboard. Deux sections : (1) le ken pour les bots (CLI/agents), (2) le ken pour le browser extension (install + usage). Réf AMO (dev, privé) : https://addons.mozilla.org/fr/developers/addon/225c8265ea3946a0a74a/edit

---

## Résolution

### Modifications
- src/dashboard/routes/pages.py — nouvelle route GET /aide (@login_required), miroir d'admin_board : charge catégories/projets/users filtrés par scope, _build_context, rend aide.html.
- src/dashboard/templates/aide.html — page d'aide, 2 cartes : "Le ken pour les agents" (install pip, .ken / Copy onboard link, commandes ken, workflow) et "Le ken pour le navigateur" (télécharger depuis les releases GitHub, install Chrome/Firefox, config via Onboarding link collé, raccourci Ctrl/Cmd+Shift+K).
- src/dashboard/templates/base.html — ajout d'un {% block head %} (vide par défaut, sans effet sur les autres pages) pour injecter le style scopé de la page.
- src/dashboard/templates/partials/header.html — lien "Aide" dans le dropdown avatar, visible par tous les utilisateurs (hors bloc admin).
- tests/unit/test_page_routes.py — TestAidePage : /aide renvoie 200 et contient les deux sections.

### Décision sur le lien extension
L'URL AMO fournie est la console développeur (privée). L'add-on est *unlisted* → pas de page publique AMO. La page d'aide pointe donc vers les releases GitHub (github.com/lduchosal/kenboard/releases) pour le zip, et documente le .xpi signé pour Firefox persistant.

### Garde-fous
- Suite complète unit+integration : 495 passed (493 + 2 nouveaux), aucune régression (le {% block head %} de base.html n'affecte pas les pages existantes).
- mypy OK ; flake8 (src/) clean ; interrogate 100%.
- NON vérifié visuellement en navigateur ici : rendu confirmé via le client de test Flask (200, deux sections présentes, pas d'erreur Jinja). À jeter un œil sur /aide une fois déployé.
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-29.md)
