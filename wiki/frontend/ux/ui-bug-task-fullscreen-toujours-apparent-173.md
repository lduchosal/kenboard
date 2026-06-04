---
id: 173
title: "UI / BUG / task-fullscreen toujours apparent"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:52
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #173 — UI / BUG / task-fullscreen toujours apparent

Le task-fullscreen est toujours apparent en bas de la page

---

## Résolution

Le dialog natif HTML est visible par defaut. Ajout display:none sur .fullscreen-modal et display:flex sur .fullscreen-modal[open]. 269 tests verts.
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)
