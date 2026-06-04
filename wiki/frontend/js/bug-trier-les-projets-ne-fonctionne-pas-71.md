---
id: 71
title: "BUG / Trier les projets ne fonctionne pas"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:19
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/js
section_title: "JS modules"
---

# #71 — BUG / Trier les projets ne fonctionne pas

**Sévérité: bug fonctionnel**

## Cause racine

Le frontend (`app.js` `saveCat` et `saveProject`) envoyait `projectOrder` (camelCase) dans le body JSON. Les modèles Pydantic `CategoryUpdate` / `ProjectUpdate` exposent `project_order` (snake_case). Pydantic v2 ignore silencieusement les champs inconnus → `data.project_order is None` → la branche de réordonnancement (`if data.project_order:`) est skippée → les nouvelles positions ne sont jamais persistées. Aucune erreur visible côté client.

## Fix

`src/dashboard/static/app.js`:
- `saveCat` ligne 141-144: `projectOrder` → `project_order`
- `saveProject` ligne 218-219: `projectOrder` → `project_order`
- Commentaires inline pour pin la convention snake_case et éviter la régression

## Tests

`tests/unit/test_api.py`:
- `TestProjectAPI::test_patch_project_reorders_siblings` — PATCH /projects/<id> avec project_order rewrite les positions ✓
- `TestCategoryProjectReorder::test_patch_category_reorders_its_projects` — PATCH /categories/<id> idem ✓
- `TestCategoryProjectReorder::test_patch_category_ignores_camelcase_alias` — **test de non-régression**: envoie le legacy camelCase `projectOrder` et vérifie que l'ordre reste inchangé. C'est le mode d'échec exact que ce ticket fixe.

## Vérification

- `pdm run test-quick` → 208 passed (3 nouveaux + 205 existants)
- `pdm run check` → vert
---

[← retour à frontend/js](index.md) · [voir log](../../log/2026-05-24.md)
