---
id: 544
title: "EXTENSION / paintbrush - phase 3 scaffold overlay SVG + activation Alt+P"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T16:11:14
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #544 — EXTENSION / paintbrush - phase 3 scaffold overlay SVG + activation Alt+P

Phase 3 — scaffold paintbrush + activation Alt+P

---

**Source (epic):** #541

## Résolution — annotate.src.js réécrit (paintbrush remplace #520 quote). Shadow DOM (badge + palette + drawer + capture + composer) ; SVG overlay séparé (appendChild documentElement, position fixed, pointer-events none) avec viewBox = scroll/innerSize mis à jour sur scroll/resize. Activation Alt+P (e.code), ESC cascade composer → drawer → mode.



## Garde-fous partagés

- pdm run build-extension : OK (bundle 27 KB IIFE, divise par 4 vs #520 puisque dom-anchor-text-* ne sont plus importés).
- node --check bundle : OK.
- web-ext lint : 0/0.
- vitest buildMarkdown : 6/6 (+1 pour la note attachee a un rectangle).
- mypy + suite complete Python : 502 passed, clean.
- NON teste en navigateur ici (a valider apres reload de l extension).
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
