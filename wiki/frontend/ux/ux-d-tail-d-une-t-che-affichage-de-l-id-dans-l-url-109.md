---
id: 109
title: "UX / Détail d'une tâche / Affichage de l'ID dans l'URL"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:22
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #109 — UX / Détail d'une tâche / Affichage de l'ID dans l'URL

Le détail d'une tâche dépend de l'URL: cat/123-123-123.html#ID-75
Quand on demande le détail d'une tâche on change l'url
Les tâches se mettent en mode détail quand leur ID est présent dans l'URL
Ca permet de faire des liens depuis la page Kenboard directement vers la tâche.
Quand la page se rafraichit, on ne perd pas le détail de la tâche en cours

---

## Résolution

### Modifications

- **`src/dashboard/static/app.js`** — `toggleDetail` synchronise `window.location.hash` (`#ID-<id>`) via `history.replaceState` (pas de pollution d'historique). Nouveau bloc `_applyTaskHash` qui restaure le mode détail au chargement et sur `hashchange`. Le scroll vers la carte est explicite (`scrollIntoView`) — on utilise `data-task-id` et non un vrai `id` DOM, donc pas de saut de scroll natif du navigateur.
- **`src/dashboard/templates/index.html`** — les cartes de l'overview "En cours" pointent vers `cat/<cat>.html#ID-<task>` au lieu du seul ancrage projet. Un clic depuis la racine ouvre directement la tâche en mode détail dans sa catégorie.
- **`src/dashboard/templates/category.html`** — l'IIFE qui met à jour le titre reconnaît `#ID-<id>` et résout le projet via la `.section` parente de la carte, donc le titre reste cohérent en mode détail.

### Comportements obtenus

- L'auto-refresh 60s (`location.reload()`) préserve désormais le détail ouvert.
- Les liens partagés `…/cat/X.html#ID-75` ouvrent la tâche directement.
- Le préfixe `ID-` désambiguïse proprement avec l'ancrage projet existant (UUIDs), donc rien ne casse côté navigation projet.
- Fermeture du détail (clic sur la même carte) → le fragment est nettoyé via `replaceState`.
- Bascule d'une tâche à une autre → le fragment suit.

### Garde-fous

- `pdm run lint` : OK.
- Tests unitaires (hors `test_api_keys` lié au WIP de la tâche #110) : 182 passed.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
