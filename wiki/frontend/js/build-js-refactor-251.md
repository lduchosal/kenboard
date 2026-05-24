---
id: 251
title: "BUILD / JS / refactor"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/js
section_title: "JS modules"
---

# #251 — BUILD / JS / refactor

## Décision (validée)

Stack JS retenue (CLAUDE.md mis à jour) :
- **Vite 6** pour bundler les modules ES en `src/dashboard/static/dist/app.js` (IIFE, fonctions publiques attachées à `globalThis` pour préserver les `onclick=\"\"` inline).
- **Vitest 2** pour les tests unitaires JS (jsdom).
- **Biome 1.9** pour lint + format.
- **TypeScript 5 via JSDoc + `// @ts-check`** pour le typecheck opt-in (api.js déjà typé, le reste s'ajoute progressivement).

## Résolution

### Modifications

#### Refactor JS

- `src/dashboard/static/app.js` (1046 lignes, monolithe) **supprimé**.
- `src/dashboard/static/js/` : 11 modules ES (~1200 lignes au total, plus aérés et commentés) :
  - `api.js` (apiCall, showError, fmtDate, API_BASE) — opt-in `// @ts-check`
  - `markdown.js` (renderMarkdown via marked + DOMPurify)
  - `modals.js` (dismissal générique Esc + click-outside)
  - `detail.js` (toggleDetail + URL hash sync `#ID-<id>`)
  - `fullscreen.js` (openFullscreen / closeFullscreen + backdrop click)
  - `tasks.js` (modal CRUD : open/save/delete/duplicate/confirm)
  - `categories.js` (CRUD catégories)
  - `projects.js` (CRUD projets + copyOnboardLink)
  - `dnd.js` (SortableJS wiring)
  - `keyboard.js` (raccourcis #249, sélection model, navigation 2D)
  - `main.js` (entry, bootstrap, expose les globals pour les inline onclick)
- `src/dashboard/static/js/keyboard.test.js` : 10 tests Vitest pour la sélection + navigation 2D (clamp, skip empty col, etc.).
- `src/dashboard/static/dist/app.js` : bundle Vite committed (~22 KB / 6 KB gzip), re-buildé à chaque release via publish.sh.

#### Toolchain

- `package.json` (devDeps : vite, vitest, @biomejs/biome, typescript, jsdom).
- `vite.config.js` (bundle IIFE, output unique, sourcemap, jsdom env pour vitest).
- `biome.json` (recommended + désactive noForEach + noParameterAssign + noExplicitAny).
- `jsconfig.json` (`checkJs: false` par défaut, opt-in via `// @ts-check`).
- `.gitignore` : ajoute `node_modules/`, exception `!src/dashboard/static/dist/`.

#### PDM scripts (pyproject.toml)

- Nouveau bloc *JS toolchain* : `js-install`, `js-lint`, `js-lint-fix`, `js-typecheck`, `js-test`, `js-build`.
- Composite `check` étendu : ajoute `js-lint`, `js-typecheck`, `js-test`, `js-build` entre `vulture` et `test-quick`.

#### Flask

- `src/dashboard/app.py` : route `/app.js` sert `dist/app.js` ; nouvelle route `/app.js.map` pour la sourcemap.
- `src/dashboard/templates/base.html` : inchangé (`<script src=\"{{ prefix }}app.js\">` continue de fonctionner).

#### publish.sh

- Compteurs d'étapes mis à jour (+5 : install, lint, typecheck, test, build).
- 5 nouvelles étapes JS placées après vulture, avant pytest, pour que le wheel embarque toujours un bundle frais.

#### CLAUDE.md

- Règle \"vanilla JS, no build step\" remplacée par la nouvelle architecture (modules ES, Vite, Biome, Vitest, JSDoc).
- Règle \"don't add a JS build step\" → \"don't add bundler plugins, CSS pipeline, or TS rewrite\" (cap explicite à la stack actuelle).
- Section *Layout* mise à jour avec `static/js/` + `static/dist/`.
- Note dans *When making changes* : `pdm run js-build` après chaque modif sous `static/js/`.

### Comportements obtenus

- Build : `npx vite build` → `dist/app.js` 21.81 KB / 6.13 KB gzip / sourcemap 70 KB.
- Lint Biome : 0 erreur sur 12 fichiers.
- Typecheck tsc : 0 erreur (api.js opt-in, autres en best-effort).
- Tests Vitest : 10 passed (sélection + nav 2D + clamp + skip empty col).
- Aucune régression e2e ni unit (52 e2e + 368 unit).

### Garde-fous

- `pdm run js-lint` : clean
- `pdm run js-typecheck` : clean
- `pdm run js-test` : 10 passed
- `pdm run js-build` : 22 KB bundle
- `pdm run check` (composite avec tous les gates Python + JS) : 378 passed
- `pdm run test-e2e` : 52 passed / 0 failed
- `pdm run lint` / `flake8` / `typecheck` : clean

## Folded in

- #250 (BUILD / JS / Validate) : couvert par js-lint + js-typecheck + js-build dans publish.sh.

## À faire dans des suivis

- Étendre `// @ts-check` aux autres modules au fur et à mesure des modifs (besoin d'un helper `dom.js` pour caster les `getElementById` vers les sous-types HTML).
- Corriger #248 (modal save submits stale fields) — bénéficie maintenant des tests Vitest pour reproduire en isolation.
- Migrer les `onclick=\"\"` inline vers `addEventListener` quand le coût d'inertie devient négatif (permettrait de retirer les exports vers `globalThis` dans main.js).
---

[← retour à frontend/js](index.md) · [voir log](../../log.md)
