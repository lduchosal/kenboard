---
id: 522
title: "EXTENSION / annotations - phase 2 content script + Shadow DOM scaffold"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:36:59
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #522 — EXTENSION / annotations - phase 2 content script + Shadow DOM scaffold

Phase 2 (content_scripts + Shadow DOM)

---

**Source (epic):** #520

## Résolution — Manifest.json gagne content_scripts (<all_urls>, document_idle, js: content/annotate.bundle.js). annotate.src.js : ensureHost() attache un <div id=kb-annotate-root> à document.documentElement avec un Shadow DOM, SHADOW_CSS encapsulé pour badge/adder/drawer ; un style page-level séparé (id kb-annotate-page-style) injecté dans <head> pour les <span class=kb-hl> qui doivent overlay le DOM de la page. z-index 2147483647.



## Garde-fous (partagés)

- pdm run build-extension : OK (bundle 113 KB IIFE).
- node --check sur le bundle : OK.
- web-ext lint : 0 erreur, 0 warning.
- pdm run js-test : 68 passed (63 existants + 5 nouveaux buildMarkdown).
- pdm run js-lint (Biome, scope src/dashboard) : clean.
- NON testé en navigateur ici (impossible d.exécuter MV3 dans cet environnement). À valider end-to-end sur Firefox release après reload de l.extension : Alt+K active, surligner persiste, push crée bien une tâche avec [citer](URL#:~:text=…).
---

[← retour à extension](index.md) · [voir log](../log.md)
