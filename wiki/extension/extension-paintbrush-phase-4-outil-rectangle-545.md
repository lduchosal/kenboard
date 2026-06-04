---
id: 545
title: "EXTENSION / paintbrush - phase 4 outil rectangle"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T16:11:17
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #545 — EXTENSION / paintbrush - phase 4 outil rectangle

Phase 4 — outil rectangle

---

**Source (epic):** #541

## Résolution — Tool rect actif par défaut. Capture pane transparente écoute pointerdown/move/up + setPointerCapture. Coords client → page (clientX+scrollX). Preview rect dashé. Discard <8x8 px. captureUnderRect : 5 probes (centre + 4 coins) via document.elementsFromPoint, skip shadow/overlay/html/body, dedupe innerText, max 600 chars stockés sur le shape.



## Garde-fous partagés

- pdm run build-extension : OK (bundle 27 KB IIFE, divise par 4 vs #520 puisque dom-anchor-text-* ne sont plus importés).
- node --check bundle : OK.
- web-ext lint : 0/0.
- vitest buildMarkdown : 6/6 (+1 pour la note attachee a un rectangle).
- mypy + suite complete Python : 502 passed, clean.
- NON teste en navigateur ici (a valider apres reload de l extension).
---

[← retour à extension](index.md) · [voir log](../log/2026-05-30.md)
