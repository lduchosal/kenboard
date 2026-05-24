---
id: 155
title: "WEB / Kenboard / Tâche en plein écran"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:39
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #155 — WEB / Kenboard / Tâche en plein écran

Ajouter un bouton <-> pour voir la tâche en plein écran dans une popup modale

---

## Résolution

### Modifications

- **`src/dashboard/templates/modals/task_fullscreen.html`** (nouveau) — modale plein écran avec : header (#id + badge status), titre en grand (22px), métadonnées (avatar coloré + nom + date), description rendue en markdown via `marked.parse()` + sanitizée par `DOMPurify`, boutons Editer + Fermer.
- **`src/dashboard/templates/partials/task_card.html`** — ajout du bouton `⤢` dans `.task-actions` (visible en mode détail, à côté de "Editer"). Appelle `openFullscreen()`.
- **`src/dashboard/templates/base.html`** — include de `modals/task_fullscreen.html`.
- **`src/dashboard/static/app.js`** — fonctions `openFullscreen()` et `closeFullscreen()`. Peuple la modale avec les données de la tâche, rend la description en markdown. Le bouton "Editer" dans la modale ferme le fullscreen et ouvre le modal d'édition existant. Fermeture via backdrop click, bouton ×, ou touche Escape.
- **`src/dashboard/static/style.css`** — `.fullscreen-modal` (overlay fixe, z-index 200, fond semi-transparent), `.fullscreen-card` (90vw / max 860px, padding 32px, border-radius 10px, overflow-y auto), styles pour le markdown rendu (pre, code, h1-h3, ul/ol). Breakpoint responsive à 640px (card 98vw, padding 20px).

### Comportements obtenus

- Clic simple sur une tâche → mode détail (existant, inchangé)
- Clic sur `⤢` en mode détail → modale plein écran avec description markdown
- Bouton "Editer" dans la modale → ferme le fullscreen, ouvre le modal d'édition
- Escape / clic backdrop / bouton × → ferme la modale
- Sur mobile (< 640px) la modale prend 98% du viewport

### Garde-fous

- 269 tests verts, `pdm run check` OK
- Aucun changement d'API, aucune migration DB
- La description est sanitizée via `DOMPurify.sanitize()` avant injection dans le DOM (même pipeline que le rendu markdown existant dans les cartes)
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
