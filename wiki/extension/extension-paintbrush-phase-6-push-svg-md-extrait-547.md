---
id: 547
title: "EXTENSION / paintbrush - phase 6 push (SVG + MD extrait)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T16:11:23
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #547 — EXTENSION / paintbrush - phase 6 push (SVG + MD extrait)

Phase 6 — push (SVG + MD)

---

**Source (epic):** #541

## Résolution — serialiseSvg : bbox des shapes + padding 16px, viewBox calculé, width capé à 900, XMLSerializer. pushToKenboard : récupère config, bâtit annotations (rect.capturedText + rect.note + textes autonomes), buildMarkdown pour description, POST /api/v1/tasks { project_id, title, description, attachement, status, who }. Sur succès : 'Tâche #N créée' + bouton 'Vider les annotations'.



## Garde-fous partagés

- pdm run build-extension : OK (bundle 27 KB IIFE, divise par 4 vs #520 puisque dom-anchor-text-* ne sont plus importés).
- node --check bundle : OK.
- web-ext lint : 0/0.
- vitest buildMarkdown : 6/6 (+1 pour la note attachee a un rectangle).
- mypy + suite complete Python : 502 passed, clean.
- NON teste en navigateur ici (a valider apres reload de l extension).
---

[← retour à extension](index.md) · [voir log](../log.md)
