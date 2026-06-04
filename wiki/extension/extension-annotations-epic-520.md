---
id: 520
title: "EXTENSION / annotations — epic"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:37:11
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #520 — EXTENSION / annotations — epic

EXTENSION / annotations — epic (#520)

Boucle d'annotation in-page : surligner du texte sur une page web, accumuler localement, pousser sur kenboard comme une tâche markdown — tout-texte (cohérent #511).

Approche C (validée par plan) : dom-anchor-text-quote/-position en deps + UI maison Shadow DOM. Découpé en 7 phases.

---

## Résolution

MVP livré en 7 phases (toutes en review) :
- #521 Phase 1 — scaffold build (package.json, esbuild, pdm alias, publish.sh)
- #522 Phase 2 — content_scripts dans manifest + Shadow DOM scaffold
- #523 Phase 3 — activation Alt+K + ESC cascade + badge top-right
- #524 Phase 4 — selection toolbar 🖍 Surligner avec debounce 200 ms
- #525 Phase 5 — wrap multi-text-node, anchor quote+position, storage par URL canonique, gestion SPA (pushState/popstate/replaceState)
- #526 Phase 6 — drawer slide-in droite, push markdown vers /api/v1/tasks avec text fragments
- #527 Phase 7 — vitest buildMarkdown (5 tests) + README section

### Fichiers livrés
- extension/content/annotate.src.js (~700 LOC) — content script complet
- extension/content/buildMarkdown.js — module pur testable
- extension/content/buildMarkdown.test.js — 5 tests vitest
- extension/content/annotate.bundle.js — IIFE 113 KB (committé)
- extension/manifest.json — content_scripts <all_urls>, document_idle
- extension/README.md — section "Annotate a page"
- package.json — deps dom-anchor-text-quote@^4.0.2, dom-anchor-text-position@^5.0.0, esbuild@^0.24.0 + script build-extension
- pyproject.toml — alias pdm build-extension
- publish.sh — rebuild bundle avant le zip de release
- vite.config.js — test include étendu à extension/content/

### Out of scope MVP (futures tâches)
- Notes attachées à un surlignage (composer inline).
- Mode brouillon multi-pages (annotations cumulées sur N onglets → 1 tâche).
- Side panel Chrome (chrome.sidePanel).
- Allowlist/denylist de domaines.
- Hover micro-actions sur le highlight (édit/delete in-place).
- Bouton popup "Annoter cette page" (envoi message kb-annotate-start est déjà câblé côté content script).

### Vérifications (gates passées)
- bundle build : 6-11 ms, 113 KB IIFE.
- node --check bundle : OK.
- web-ext lint : 0/0.
- pdm run js-test : 68 passed (63 existants + 5 nouveaux).
- pdm run js-lint (Biome, scope src/dashboard) : clean.

### À valider en navigateur (manuel)
- Alt+K active sur Firefox release (signé) + Chrome.
- Sélection → adder → clic Surligner → persiste après reload.
- SPA (ex. nav GitHub /issues → /issues/123) : badge survit, highlights de la nouvelle URL rechargés.
- Push : tâche créée avec markdown contenant [citer](#:~:text=…) cliquable.
- Pages privilégiées (chrome://, about:) : no-op silencieux.
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
