---
id: 248
title: "Fix e2e modal save: form submits stale field values"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:00
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/js
section_title: "JS modules"
---

# #248 — Fix e2e modal save: form submits stale field values

## Contexte

4 tests e2e dans `tests/e2e/test_dashboard.py::TestTaskCRUD` ont été supprimés
parce qu'ils échouaient systématiquement (même en isolation) :

- `test_edit_task`
- `test_move_task_via_status_select`
- `test_task_description_renders_markdown`
- `test_task_description_xss_is_sanitized`

## Symptôme

Tous les 4 partagent le même pattern : modifier un champ via `#task-modal`
(title / status / description), cliquer `.btn-save`, recharger, vérifier.

Le log Flask pour le PATCH montre l'**ancienne** valeur dans le body, pas celle
qu'on vient de taper. Exemple capturé pendant `test_edit_task` :

```
PATCH /api/v1/tasks/7553
body: {'title': 'Avant', 'description': 'Nouvelle description', ...}
```

→ `title='Avant'` alors que le test a fait `page.fill("#task-modal-title", "Apres")`.

## Suspects

Régressions probables introduites par les commits récents sur `app.js` :
- #221 (lazy-load des descriptions de tâches via API)
- #238 / #240 (nettoyages Sonarcloud)

Ces commits n'ont pas été détectés parce que `pdm run test-ci` exclut e2e.

## À faire

1. Reproduire localement (`pdm run test-e2e -k test_edit_task` après avoir
   restauré le test depuis le commit qui les supprime).
2. Identifier dans `app.js` le code qui lit les valeurs au moment du save —
   probablement il lit depuis le state in-memory plutôt que depuis le DOM.
3. Corriger.
4. Restaurer les 4 tests supprimés.
5. Envisager d'ajouter `test-e2e` au gate de publish (`publish.sh --quality`)
   pour ne pas reproduire le trou.
---

[← retour à frontend/js](index.md) · [voir log](../../log.md)
