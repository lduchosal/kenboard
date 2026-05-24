---
id: 230
title: "UX / Header / Liste des projets trop large"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:54
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #230 — UX / Header / Liste des projets trop large

Quand il y a beaucoup de categories, le header en mode Desktop est overcrowded et le menu admin n'est plus accessible.

---

## Resolution

### Modifications

- `src/dashboard/templates/partials/header.html` — Ajout classe `header-compact` sur le header quand `categories | length > 8`. Force le mode dropdown (categorie active + chevron) au lieu de la liste directe.
- `src/dashboard/static/style.css` — 2 regles CSS pour `.header-compact` : cache `header-badges`, affiche `header-badges-dropdown`.

### Comportement

- <= 8 categories : affichage normal (badges directs dans le header)
- > 8 categories : categorie active + menu deroulant. Le menu admin (avatar) reste toujours accessible.
- Le mecanisme de dropdown existait deja pour mobile (<=768px) — on le reutilise en desktop.

### Garde-fous

- pytest unit : 343 passed
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
