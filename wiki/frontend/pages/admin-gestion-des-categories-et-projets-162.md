---
id: 162
title: "ADMIN / Gestion des catégories et projets"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:43
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #162 — ADMIN / Gestion des catégories et projets

Dans le menu ajouter un lien vers une page d'admin pour gérer les catégories et les projets
Un seule page avec la liste de toutes les catégories et tous les projets:

Catégorie 1
  Projet 1
  Projet 2
  Projet 3

Catégorie 1
  Projet 1
  Projet 2
  Projet 3

On peut drag / drop  les projets et les catégories pour réordonner
Un bouton Edit pernet d'editer le projet ou la catégorie
On réutilise tout ce qu'on peut
formulaires html
api
etc

---

## Résolution

### Modifications

- **`src/dashboard/routes/pages.py`** — nouvelle route `GET /admin/board` (`@login_required` + `admin_required()`). Charge toutes les catégories et projets via `_load_all_data()`.
- **`src/dashboard/templates/admin_board.html`** (nouveau) — page admin tree view :
  - Chaque catégorie avec pastille couleur, nom, bouton "+ Projet" (style discret, collé au nom), bouton "Editer" (aligné à droite)
  - Projets indentés sous leur catégorie : handle ☰, acronyme, nom, statut (archived en rouge), bouton "Editer"
  - Bouton "+ Catégorie" à côté du titre "Gestion du board"
- **`src/dashboard/templates/partials/header.html`** — lien "Board" ajouté dans le dropdown avatar admin (avant "Utilisateurs")
- **`src/dashboard/static/style.css`** — section "Admin board" : `.board-admin-list`, `.board-cat`, `.board-cat-header`, `.board-cat-color`, `.board-drag-handle`, `.board-projects`, `.board-project`, `.board-project-acronym/name/status`

### Drag-and-drop

- **Catégories** : SortableJS avec handle `.board-drag-handle` → appelle `POST /api/v1/categories/reorder` (API existante)
- **Projets** : SortableJS avec group `board-projects` (drag entre catégories) → appelle `PATCH /api/v1/projects/<id>` avec `cat` + `project_order` (API existante)

### Réutilisation

- Modals existants : `modals/category.html` (`editCat()`) et `modals/project.html` (`editProject()`)
- APIs existantes : `/api/v1/categories/reorder`, `PATCH /api/v1/projects/<id>`, `POST /api/v1/categories`, `POST /api/v1/projects`
- Aucune nouvelle API créée

### Bugs corrigés pendant l'implémentation

- `p.cat` → `p.cat_id` (le champ DB s'appelle `cat_id`, pas `cat`)
- `editCategory()` → `editCat()` (nom de la fonction JS)

### Garde-fous

- 269 tests verts, `pdm run check` OK
- Aucun changement d'API
- Aucune migration DB
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-24.md)
