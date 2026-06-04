---
id: 168
title: "UX / WEB / Open task refresh content with API call"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/js
section_title: "JS modules"
---

# #168 — UX / WEB / Open task refresh content with API call

Quand on ouvre une tâche, rafraichir le contenu de la tâche avec un call API

---

## Résolution

- **`src/dashboard/routes/tasks.py`** — nouveau endpoint `GET /api/v1/tasks/<id>` qui retourne une tâche unique par son id.
- **`src/dashboard/static/app.js`** — `openFullscreen()` est maintenant async : affiche d'abord les données du DOM (instantané), puis fait un `fetch /api/v1/tasks/<id>` pour rafraîchir avec le contenu à jour. Si l'API échoue, les données DOM restent affichées (graceful degradation). La logique de peuplement est extraite dans `_populateFullscreen()`.

### Garde-fous

- 269 tests verts
- Le nouvel endpoint hérite de l'auth middleware existant (cookie session ou bearer token)
---

[← retour à frontend/js](index.md) · [voir log](../../log/2026-05-24.md)
