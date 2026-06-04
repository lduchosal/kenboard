---
id: 227
title: "TEST / Unit tests des page routes avant refactoring _load_all_data"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #227 — TEST / Unit tests des page routes avant refactoring _load_all_data

Ajouter des tests unitaires pour chaque page route (pages.py) avant de supprimer _load_all_data(). Ces tests serviront de filet de securite pour le refactoring.

---

## Resolution

### Modifications

- `tests/unit/test_page_routes.py` (nouveau) — 16 tests couvrant les 5 page routes :
  - `TestIndexPage` (4 tests) : status 200, contenu KEN, taches doing visibles, board vide
  - `TestCategoryPage` (5 tests) : status 200, nom categorie, taches du projet, 404 inconnue, isolation entre categories
  - `TestAdminBoardPage` (3 tests) : status 200, categories, projets
  - `TestAdminUsersPage` (2 tests) : status 200, users visibles
  - `TestAdminKeysPage` (2 tests) : status 200, cles API visibles

### Comportements verifies

- Chaque route retourne 200
- Les donnees attendues sont presentes dans le HTML rendu
- Les donnees d'autres categories ne leakent pas (test d'isolation)
- Le board vide ne crash pas
- La categorie inconnue retourne 404

### Garde-fous

- pytest unit : 343 passed (327 existants + 16 nouveaux)
- Fixture autouse _ensure_login_disabled pour isoler des tests auth qui togglent LOGIN_DISABLED
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
