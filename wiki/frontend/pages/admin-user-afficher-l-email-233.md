---
id: 233
title: "ADMIN / USER / Afficher l'email"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:56
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #233 — ADMIN / USER / Afficher l'email

Dans la gestion des users, afficher l'adresse email des utilisateurs.

---

## Resolution

Ajout d'une colonne Email dans le tableau /admin/users entre Nom et Couleur. Affiche u.email en lecture seule (pas editable). Vide si l'email n'est pas renseigne.

### Garde-fous

- pytest unit : 343 passed
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-24.md)
