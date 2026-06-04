---
id: 527
title: "EXTENSION / annotations - phase 7 tests + docs"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:37:08
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #527 — EXTENSION / annotations - phase 7 tests + docs

Phase 7 (tests + docs)

---

**Source (epic):** #520

## Résolution — extension/content/buildMarkdown.js : module pur extrait pour la testabilité (importé par annotate.src.js). buildMarkdown.test.js : 5 tests vitest (header+source+quote, séparateur ---, omission [citer] sans textFragmentUrl, fallback URL si titre vide, header seul si zéro annotation). vite.config.js : include étendu à extension/content/**/*.test.js (coverage reste exclusive à src/dashboard). extension/README.md : section 'Annotate a page (#520)' avec Alt+K activation, ESC cascade, modèle de persistance par URL canonique, note Shadow DOM.



## Garde-fous (partagés)

- pdm run build-extension : OK (bundle 113 KB IIFE).
- node --check sur le bundle : OK.
- web-ext lint : 0 erreur, 0 warning.
- pdm run js-test : 68 passed (63 existants + 5 nouveaux buildMarkdown).
- pdm run js-lint (Biome, scope src/dashboard) : clean.
- NON testé en navigateur ici (impossible d.exécuter MV3 dans cet environnement). À valider end-to-end sur Firefox release après reload de l.extension : Alt+K active, surligner persiste, push crée bien une tâche avec [citer](URL#:~:text=…).
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
