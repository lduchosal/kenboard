---
id: 18
title: "TEST / Tests units && E2E"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:12
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #18 — TEST / Tests units && E2E

Des tests unitaires couvrent-ils les nouvelles fonctionnalités ?
Des tests e2e playwright couvrent-ils les nouvelles fonctionnalités ?

## Couverture ajoutée (3 tests e2e)

Dans `tests/e2e/test_dashboard.py::TestTaskCRUD` :

1. **`test_edit_modal_status_reflects_dragged_position`** — régression #11. Simule un drag&drop sans reload (déplacement DOM + PATCH), ouvre le modal d'édition, vérifie que le dropdown reflète la nouvelle colonne, sauve sans rien toucher, vérifie la persistance.

2. **`test_task_description_renders_markdown`** — couvre #15. Crée une tâche avec markdown (`**bold**`, listes, code inline), reload, vérifie que `.task-desc.innerHTML` contient `<strong>`, `<em>`, `<ul>/<li>`, `<code>`. Vérifie aussi que la textarea du modal d'édition récupère bien le markdown source (round-trip), pas l'HTML rendu.

3. **`test_auto_refresh_skips_when_modal_open`** — couvre #14. Vérifie que `shouldSkipRefresh()` retourne `false` au repos, puis `true` quand on a ouvert le modal de création de tâche (la condition critique : ne pas perdre la saisie du user).

## État global

- 64 unit tests + 26 e2e tests = **90 tests verts**
- Tous les checks qualité passent : ruff, mypy, black, isort, flake8, vulture, refurb, interrogate (100%)
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
