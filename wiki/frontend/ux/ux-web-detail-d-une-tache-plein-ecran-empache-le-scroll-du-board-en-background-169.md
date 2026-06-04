---
id: 169
title: "UX / WEB / Detail d'une tâche plein écran empâche le scroll du board en background"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:49
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #169 — UX / WEB / Detail d'une tâche plein écran empâche le scroll du board en background

Detail d'une tâche plein écran empêche le scroll du board en background

---

## Résolution

- **`app.js`** — `openFullscreen()` ajoute `document.body.style.overflow = 'hidden'` à l'ouverture de la modale. `closeFullscreen()` restaure avec `document.body.style.overflow = ''`. Le scroll du board en arrière-plan est bloqué tant que la modale est affichée.

### Garde-fous

- 269 tests verts
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)
