---
id: 523
title: "EXTENSION / annotations - phase 3 activation Alt+K / ESC + badge"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T00:37:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #523 — EXTENSION / annotations - phase 3 activation Alt+K / ESC + badge

Phase 3 (activation Alt+K + ESC + badge)

---

**Source (epic):** #520

## Résolution — onKeyDown (capture phase) : Alt+K toggle activate()/deactivate() ; ESC dégomme adder > drawer > mode (cascade). Badge top-right kb·N rendu via buildBadge()/renderBadge() ; visible quand mode=on. chrome.runtime.onMessage écoute 'kb-annotate-start' pour qu'un futur bouton popup puisse activer le mode.



## Garde-fous (partagés)

- pdm run build-extension : OK (bundle 113 KB IIFE).
- node --check sur le bundle : OK.
- web-ext lint : 0 erreur, 0 warning.
- pdm run js-test : 68 passed (63 existants + 5 nouveaux buildMarkdown).
- pdm run js-lint (Biome, scope src/dashboard) : clean.
- NON testé en navigateur ici (impossible d.exécuter MV3 dans cet environnement). À valider end-to-end sur Firefox release après reload de l.extension : Alt+K active, surligner persiste, push crée bien une tâche avec [citer](URL#:~:text=…).
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
