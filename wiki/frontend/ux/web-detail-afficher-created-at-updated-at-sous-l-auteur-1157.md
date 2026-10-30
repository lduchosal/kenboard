---
id: 1157
title: "WEB / DETAIL / Afficher created at / updated at sous l'auteur"
status: done
who: "Claude"
due_date: 
updated_at: 2026-10-30T10:05:35
classified_at: 2026-10-30T10:04:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #1157 — WEB / DETAIL / Afficher created at / updated at sous l'auteur

**TL;DR** — La vue détail (plein écran) n'affichait pas quand la carte avait été créée / modifiée → ajout d'une ligne « created at …, updated at … » sous le nom de l'auteur, alimentée par `created_at` / `updated_at` déjà renvoyés par l'API.

Dans le header du détail d'une carte, ajouter en dessous du nom de l'auteur : « created at xxxx, updated at xxxx » (dates de création et de dernière mise à jour de la tâche).

## Résolution

### Modifications
- `src/dashboard/static/js/api.js` — nouveau helper `fmtDateTime(iso)` → `dd.mm.yyyy HH:MM`, par découpage de chaîne (les timestamps serveur sont naïfs : passer par `Date` les décalerait de l'offset UTC du navigateur).
- `src/dashboard/static/js/fullscreen.js` — `openFullscreen` transmet `created`/`updated` ; `populateFullscreen` remplit `#fs-dates`.
- `src/dashboard/templates/modals/task_fullscreen.html` — `<div id="fs-dates">` sous `.fullscreen-meta`.
- `src/dashboard/static/style.css` — `.fullscreen-dates` (11px, dimmed, aligné sous le nom à droite de l'avatar).
- `src/dashboard/static/js/api.test.js` — 4 tests `fmtDateTime`.
- `src/dashboard/static/dist/app.js(.map)` — bundle régénéré par `pdm run js-build`.

### Comportements obtenus
- Ouverture plein écran : sous l'avatar + nom, `created at 30.10.2026 10:02, updated at 30.10.2026 10:02`.
- Pendant le chargement API (placeholder `...`), la ligne reste vide ; une date absente est simplement omise.

### Garde-fous
- `pdm run js-lint`, `js-typecheck`, `js-test` (81 passed), `js-build` : OK.
- `pdm run test-unit` : 654 passed.
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-10-30.md)
