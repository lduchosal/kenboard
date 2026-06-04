---
id: 175
title: "UX / Création d'une catégorie, crée un projet"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:39
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #175 — UX / Création d'une catégorie, crée un projet

Quand on cree une nouvelle categorie dans le kenboard, un premier projet Project category name est cree automatiquement

---

## Resolution

Dans POST /api/v1/categories (routes/categories.py), apres le cat_create, ajout automatique d un proj_create avec name=Project category name, acronym=4 premieres lettres uppercase, status=active, position=0. Le board est immediatement utilisable apres creation d une categorie. 269 tests verts.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
