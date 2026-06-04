---
id: 546
title: "EXTENSION / paintbrush - phase 5 outil texte"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T16:11:20
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #546 — EXTENSION / paintbrush - phase 5 outil texte

Phase 5 — outil texte

---

**Source (epic):** #541

## Résolution — Tool text : pointerdown ouvre un composer rouge 12px aux coords client. Enter commit, ESC annule. Au commit : si un rectangle est proche (dist < hypot(w,h), nearestRectTo), la note est attachée au shape rect (s.note). Sinon texte autonome {type:'text', x, y, content}. Raccourcis R/T pour switcher rapidement entre les outils.



## Garde-fous partagés

- pdm run build-extension : OK (bundle 27 KB IIFE, divise par 4 vs #520 puisque dom-anchor-text-* ne sont plus importés).
- node --check bundle : OK.
- web-ext lint : 0/0.
- vitest buildMarkdown : 6/6 (+1 pour la note attachee a un rectangle).
- mypy + suite complete Python : 502 passed, clean.
- NON teste en navigateur ici (a valider apres reload de l extension).
---

[← retour à extension](index.md) · [voir log](../log.md)
