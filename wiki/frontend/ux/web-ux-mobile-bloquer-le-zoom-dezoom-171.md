---
id: 171
title: "WEB / UX / MOBILE : bloquer le zoom dezoom"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:51
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #171 — WEB / UX / MOBILE : bloquer le zoom dezoom

Bloquer le pinch-to-zoom sur mobile

---

## Résolution

- Ajout de `maximum-scale=1, user-scalable=no` au viewport meta dans `base.html` et `login.html`
- Empêche le zoom/dezoom accidentel sur mobile qui casse le layout du kanban
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
