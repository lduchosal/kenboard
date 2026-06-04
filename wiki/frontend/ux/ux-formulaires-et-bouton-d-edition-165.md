---
id: 165
title: "UX / Formulaires et bouton d'édition"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:46
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #165 — UX / Formulaires et bouton d'édition

Toute la gestion se fait dans la page Admin / Board
On peut retirer les boutons, formulaire et actions dans les pages 
- Liste des catégories
- Liste des projets
- Header

Les actions sont:
- Ajouter une catégorie
- Editer un catégorie
- Ajouter un projet 
- Edier un projet
- Reordre les catégorie
- Réordre les projets

Analyse l'impact avant la modification, ne pas casser la fonctionnalité Admin / Board que l'on vient de créer. Les API devraient rester identiques.

Nettoyer le JS, nettoyer les tests unit, etc..

---

## Résolution

### Analyse d'impact

Avant modification, un agent d'exploration a identifié 7 éléments UI présents en dehors de `/admin/board` qui dupliquaient les actions de gestion :

| Fichier | Élément retiré |
|---|---|
| `index.html` | `.cat-drag-handle` (drag catégories) |
| `index.html` | `.cat-edit-btn` (bouton Editer catégorie) |
| `index.html` | `.cat-card-add` ("Ajouter une catégorie") |
| `index.html` | Modals catégorie + projet + script `CAT_PROJECTS` |
| `category.html` | `.section-edit-btn` sur projets actifs et archivés |
| `category.html` | `.cat-card-add` ("Ajouter un projet") |
| `category.html` | Modal projet |
| `header.html` | `.header-add-project` ("+ Projet" dans le header) |

### Modifications

- **`src/dashboard/templates/index.html`** — retiré : drag handle catégorie, bouton Editer catégorie, bouton "Ajouter une catégorie", bloc modals (catégorie + projet + `CAT_PROJECTS`). La page index est maintenant en lecture seule (navigation vers les catégories uniquement).
- **`src/dashboard/templates/category.html`** — retiré : boutons `section-edit-btn` sur projets actifs et archivés, bouton "Ajouter un projet", modal projet. Conservé : bouton "Copy onboard link" (fonctionnalité agent, pas de gestion).
- **`src/dashboard/templates/partials/header.html`** — retiré : bouton "+ Projet" conditionnel.
- **`src/dashboard/static/app.js`** — retiré : `_initCatSortable()` + `_mobileCatMq` + `catGrid` + `_catSortable` (drag-drop catégories sur l'index page). Conservé : `editCat()`, `editProject()`, `saveCat()`, `saveProject()` (appelés par `admin_board.html`).
- **`src/dashboard/templates/admin_board.html`** — ajouté : `<script>const CAT_PROJECTS = {{ cat_projects | tojson }};</script>` (nécessaire pour que `editCat()` affiche la liste des projets dans le modal).

### Tests e2e adaptés

27 tests e2e cassés initialement → tous corrigés :
- Nouveau helper `_create_category_via_admin()` qui crée une catégorie via `/admin/board`
- Helper `_create_category_and_project()` réécrit pour passer par `/admin/board`
- `TestCategoryCRUD` (create/edit/delete) réécrit pour utiliser `/admin/board`
- `TestProjectCRUD` (edit/delete) réécrit pour utiliser `/admin/board`
- Tests `default_who` : naviguent vers `/admin/board` pour éditer le projet, puis reviennent sur la page catégorie pour vérifier le formulaire de tâche
- Sélecteur `.btn-edit:not(.section-onboard-btn)` pour distinguer "Editer" de "+ Projet" dans `.board-cat-header`

### Garde-fous

- 267 tests unitaires verts
- 53 tests e2e verts (0 failures)
- Aucune API modifiée
- Aucune migration DB
- Les fonctions JS globales (`editCat`, `editProject`, `saveCat`, `saveProject`) restent disponibles pour `admin_board.html`
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)
