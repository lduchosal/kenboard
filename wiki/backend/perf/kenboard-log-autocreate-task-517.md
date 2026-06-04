---
id: 517
title: "KENBOARD / Log / autocreate task"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T22:53:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #517 — KENBOARD / Log / autocreate task

Une erreur dans le kenboard devrait créer automatiquement un tâche dans le BOARD par default configuré dans le env du kenboard avec les informations nécessaires.é debugger, reproduire, tester et corriger.

---

**Source:** https://www.kenboard.2113.ch/cat/0ee51b6f-81b8-4da0-9efc-0bd9e01f9e4f.html

---

## Résolution

### Modifications
- src/dashboard/config.py — `KENBOARD_ERROR_PROJECT_ID` (str, défaut ""), `KENBOARD_ERROR_WHO` (défaut "kenboard"). Vide = feature OFF.
- src/dashboard/queries/tasks.sql — `task_find_open_by_title^` : retrouve une tâche non-done d'un projet par titre exact (pour la dédup).
- src/dashboard/app.py — helper module-level `_autocreate_error_task(error_id, error_class, original, route)` ; appelé dans `handle_internal_server_error` juste après `log.error("unhandled_error", …)`. Imports : `traceback`, `datetime/timezone`.
- tests/unit/test_fatal_error.py — 2 tests : (a) configuré → une tâche créée + dédup au second hit ; (b) non configuré → aucune création.

### Comportement
- **OFF par défaut** : sans `KENBOARD_ERROR_PROJECT_ID`, comportement inchangé (no-op).
- Quand configuré, un 500 :
  - logge `unhandled_error` (inchangé) ;
  - crée une tâche `todo` dans le projet cible, titre `BUG / 500 <ExcType> @ <rule>`, who=`KENBOARD_ERROR_WHO`, description markdown : error_id, méthode+path+rule, type+message, timestamp UTC, **traceback complet** (tronqué à 60K chars), checklist Reproduire/Test/Corriger.
- **Garde-fous** :
  - anti-boucle : skip si `request.path` commence par `/api/v1/tasks` (sinon une erreur sur la création de tâche déclencherait sa propre création) ;
  - dédup : si une tâche non-`done` existe déjà avec le même titre-signature (ExcType @ rule), on ne recrée pas — pas de spam même si la route boucle ;
  - jamais d'exception remontée : tout est enveloppé dans `try/except` qui logge un warning ; un échec de création ne masque jamais le 500 retourné au caller ;
  - insert DB direct (pas de POST HTTP sur soi-même → pas d'auth ni de récursion) ;
  - route signature = `request.url_rule` (groupe par endpoint, pas par id concret), fallback path ;
  - titre tronqué à 250, description à 60K chars (évite tout dépassement TEXT, cf. #511).

### Garde-fous tests
- Suite complète : 498 passed (+2). mypy clean ; flake8 src clean ; interrogate 100%.

### Activation prod
Définir dans `.env` du kenboard :
```
KENBOARD_ERROR_PROJECT_ID=<UUID du projet "Bugs/erreurs">
KENBOARD_ERROR_WHO=kenboard   # optionnel, défaut "kenboard"
```
puis redémarrer le service. Avant le redémarrage : zéro changement de comportement.
---

[← retour à backend/perf](index.md) · [voir log](../../log/2026-05-29.md)
