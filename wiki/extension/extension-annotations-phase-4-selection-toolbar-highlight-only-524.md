---
id: 524
title: "EXTENSION / annotations - phase 4 selection toolbar (highlight only)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:37:03
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #524 — EXTENSION / annotations - phase 4 selection toolbar (highlight only)

Phase 4 (selection toolbar)

---

**Source (epic):** #520

## Résolution — document.addEventListener('selectionchange', onSelectionChange). Debounce 200 ms, ignore sélection < 2 chars, ignore si la sélection vit dans notre shadow ou dans un input[type=password]/contenteditable. showAdder(range) positionne l'adder près de la fin de sélection, clampé au viewport (W=180, H=32). Un seul bouton 🖍 Surligner (notes phase 2 / post-MVP).



## Garde-fous (partagés)

- pdm run build-extension : OK (bundle 113 KB IIFE).
- node --check sur le bundle : OK.
- web-ext lint : 0 erreur, 0 warning.
- pdm run js-test : 68 passed (63 existants + 5 nouveaux buildMarkdown).
- pdm run js-lint (Biome, scope src/dashboard) : clean.
- NON testé en navigateur ici (impossible d.exécuter MV3 dans cet environnement). À valider end-to-end sur Firefox release après reload de l.extension : Alt+K active, surligner persiste, push crée bien une tâche avec [citer](URL#:~:text=…).
---

[← retour à extension](index.md) · [voir log](../log.md)
