---
id: 543
title: "EXTENSION / paintbrush - phase 2 affichage attachement sur la tâche"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T16:11:12
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #543 — EXTENSION / paintbrush - phase 2 affichage attachement sur la tâche

Phase 2 — affichage attachement sur la tâche

---

**Source (epic):** #541

## Résolution — templates/modals/task.html : nouveau div task-modal-attachement. tasks.js openEditTask vide + remplit via DOMPurify.sanitize(t.attachement, USE_PROFILES: svg). style.css : .task-modal-attachement avec damier transparent qui fait ressortir les rectangles rouges, max-height 240px scroll vertical.



## Garde-fous partagés

- pdm run build-extension : OK (bundle 27 KB IIFE, divise par 4 vs #520 puisque dom-anchor-text-* ne sont plus importés).
- node --check bundle : OK.
- web-ext lint : 0/0.
- vitest buildMarkdown : 6/6 (+1 pour la note attachee a un rectangle).
- mypy + suite complete Python : 502 passed, clean.
- NON teste en navigateur ici (a valider apres reload de l extension).
---

[← retour à extension](index.md) · [voir log](../log.md)
