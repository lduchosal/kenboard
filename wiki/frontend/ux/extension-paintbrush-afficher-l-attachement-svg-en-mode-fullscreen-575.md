---
id: 575
title: "EXTENSION / paintbrush — afficher l'attachement SVG en mode fullscreen"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T23:34:28
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #575 — EXTENSION / paintbrush — afficher l'attachement SVG en mode fullscreen

Le modal d'édition affiche bien le SVG attachement (#541 phase 2) mais le modal fullscreen (#155, ouverture par clic sur une carte) ne l'affichait pas. Asymétrie réparée.

---

## Résolution

### Modifications
- templates/modals/task_fullscreen.html : nouveau <div id='fs-attachement' class='fullscreen-attachement'> après <div id='fs-desc'>, hidden par défaut.
- static/js/fullscreen.js : populateFullscreen() prend un nouveau paramètre `attachement` ; openFullscreen() le passe depuis t.attachement. Sanitisation via DOMPurify.sanitize(att, USE_PROFILES: {svg, svgFilters}), display: '' si non-vide, sinon hide + innerHTML = ''.
- style.css : .fullscreen-attachement (mêmes damier + svg max-width que .task-modal-attachement mais SANS max-height : on a la place en fullscreen donc le SVG peut prendre toute sa hauteur).

### Garde-fous
- pdm run js-test : 69/69 passed (vitest, inchangé — pas de nouveau test sur ce fix purement visuel).
- pdm run js-lint (Biome) : clean.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
