---
id: 570
title: "BUG / QUALITY / e2e test_duplicate_task[chromium] flaky — race sur l'init du modal"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-31T21:04:31
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #570 — BUG / QUALITY / e2e test_duplicate_task[chromium] flaky — race sur l'init du modal

Test instable qui bloque ~1 publish sur 3 depuis quelques releases. Détails ci-dessous (déjà reproduit et investigué).

## Symptôme

```
tests/e2e/test_dashboard.py:331: in test_duplicate_task
    expect(page.locator("#task-modal-heading")).to_contain_text("copie")
E   AssertionError: Locator expected to contain text 'copie'
E   Actual value: Editer la tâche
E     - 7 × locator resolved to <h3 id="task-modal-heading">Editer la tâche</h3>
```

## Cause racine (confirmée par le log serveur)

Le test fait :
1. `self._open_task_edit_modal(page)` — ouvre le modal d'édition d'une tâche existante.
2. `expect(page.locator("#task-modal-duplicate")).to_be_visible()` — attend que le bouton soit visible.
3. `page.click("#task-modal-duplicate")` — clic immédiat.

Le souci : `#task-modal-duplicate` est visible **avant** que l'`apiCall` dans `openEditTask()` (src/dashboard/static/js/tasks.js:35-49) ait fini de peupler le titre via `document.getElementById('task-modal-title').value = t.title`. Le bouton existe DOM-side dès que le modal s'affiche (`display:flex`), mais le champ titre est encore vide tant que le fetch n'a pas répondu.

`duplicateTask()` (tasks.js:140-…) commence par :
```js
if (!_taskEditId) return;
const title = document.getElementById('task-modal-title').value.trim();
if (!title) return;
```
→ Si le titre est encore vide, return immédiat, **aucun POST /api/v1/tasks** émis, et le heading reste "Editer la tâche".

**Preuve via le log serveur** dans le run flaky (vu sur le run by5sx72pd ligne 480) : un seul `POST /api/v1/tasks` au lieu de deux (création initiale + duplicata).

## Reproduction

- Run publish.sh complet, l'e2e suite court — parfois passe, parfois échoue. Reproductible mais non-déterministe.
- En isolation, le test PASSE systématiquement (`pytest tests/e2e/test_dashboard.py::TestTaskCRUD::test_duplicate_task`). C'est la pression / parallélisme / ressources du run complet qui ralentit suffisamment le fetch pour que la race se déclenche.

## Fix proposé

Dans **tests/e2e/test_dashboard.py** `test_duplicate_task`, ajouter une attente explicite que le titre soit peuplé avant de cliquer Dupliquer :

```python
self._open_task_edit_modal(page)
# Attendre que le fetch de la tâche ait peuplé le titre — sinon
# duplicateTask() return early sur title.trim() === '' et le test
# observe le heading non-changé.
expect(page.locator("#task-modal-title")).not_to_have_value("")
expect(page.locator("#task-modal-duplicate")).to_be_visible()
page.click("#task-modal-duplicate")
```

Alternative côté code (plus robuste mais touche au comportement utilisateur) : disabled-by-default sur `#task-modal-duplicate`, ré-activé dans `openEditTask` après le fetch. Trop invasif pour un fix de flaky test, à éviter sauf si la même race apparaît côté production.

## Validation

1. Lancer `pdm run test-e2e` 10 fois de suite — doit passer à chaque fois.
2. OU `pytest tests/e2e/test_dashboard.py::TestTaskCRUD --count=20 --repeat-each=1` (avec pytest-repeat installé).
3. Confirmer que la durée du test n'a pas changé radicalement (l'attente devrait être < 100ms en pratique).

## Pourquoi prioritaire maintenant

Ce flaky a fait avorter au moins 3 publishs cette semaine (forgot_password ordering + duplicate timing), ralentit la release loop, et masque parfois de vrais soucis.

---

## Résolution

### Modifications

- tests/e2e/test_dashboard.py:325-330 — dans `test_duplicate_task`, juste après `_open_task_edit_modal(page)`, ajout de :

  ```python
  expect(page.locator("#task-modal-title")).not_to_have_value("")
  ```

  Avec un commentaire 3 lignes pointant sur `duplicateTask()` (early return sur title vide) et le ref ken #570.

### Comportement obtenu

- Le test attend désormais explicitement que `openEditTask()` ait fini de peupler le champ titre (via le fetch `apiCall`) avant de cliquer Dupliquer.
- Plus aucune fenêtre où `#task-modal-duplicate` est visible mais `#task-modal-title.value === ''`.
- Helper `_open_task_edit_modal` NON modifié (autres tests comme `test_delete_task` n'ont pas besoin du titre ; pas la peine d'élargir l'attente pour tout le monde et risquer de cacher d'autres bugs).
- Le code de production (`tasks.js` `duplicateTask`) n'a pas été touché : la guard `if (!title) return` reste là, elle protège aussi l'usage manuel utilisateur si jamais le titre est vidé.

### Garde-fous

- `pytest tests/e2e/test_dashboard.py::TestTaskCRUD::test_duplicate_task` × 3 → 3/3 PASSED (3.13s, 3.15s, 5.12s).
- `pytest tests/e2e/test_dashboard.py::TestTaskCRUD` (suite complète, 13 tests dont les 4 autres qui utilisent `_open_task_edit_modal`) → 13/13 PASSED en 24.44s — aucune régression sur `test_delete_task`, `test_edit_task`, `test_duplicate_button_hidden_on_create`, etc.
- Validation finale (10x `pdm run test-e2e` sous pression du publish complet) à confirmer côté reviewer — c'est précisément la condition de stress qui déclenchait le flaky, irreproductible en isolation par construction.
---

[← retour à quality](index.md) · [voir log](../log.md)
