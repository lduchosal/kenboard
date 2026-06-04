---
id: 261
title: "HOME / Dashboard / Engageement"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:55
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #261 — HOME / Dashboard / Engageement

## Demande

La page d'accueil a pour vocation d'être engageante pour les utilisateurs. On veut les attirer avec les statistiques. Actuellement, les stats bougent très peu et ne montrent pas l'evolution des tâche de manière globale. Seules une partie des tâches est comptée. La mise à jour ne se voit pas immediatement.

Approche retenue : enregistrer toutes les activités. Ajouter un middleware qui enregistre dans une table toutes les activités par board (créer / enregistrer / déplacer / supprimer une tâche). Aggréger dans un seul line graph par jour.

Choix middleware : helper explicite ``log_activity()`` appelé depuis chaque route handler, pas un Flask ``after_request`` (raisons : ``after_request`` ne voit pas le diff avant/après donc impossible de distinguer save vs move sans peeker dans le body ; pas d'accès à la connexion DB du handler ; couple le middleware à la forme des URLs).

---

## Résolution

### Migration + schéma

- `src/dashboard/migrations/0020.create_activities.sql` (idempotent, `-- rollback` no-op).
- Table `activities (id BIGINT PK, occurred_at, project_id FK→projects, user_name, action ENUM('create','save','move','delete'), target_type, target_id, details JSON, INDEX (project_id, occurred_at), INDEX (occurred_at))`.
- `tests/sql/schema.sql` : CREATE TABLE miroir + cleanup `DELETE FROM activities` ajouté dans `tests/conftest.py` + `tests/e2e/conftest.py`.

### Helper + queries

- `src/dashboard/activity.py` : `log_activity(conn, queries, *, project_id, action, target_id, target_type='task', details=None)` — résout user_name (session → API key → \"\"), serialise details en JSON, swallow les exceptions (avec warning log) pour ne jamais casser le write path.
- `src/dashboard/queries/activities.sql` : `activity_log!`, `activity_daily_total`, `activity_daily_counts` (par action, future use), `activity_recent_by_project`.

### Route handlers

- `src/dashboard/routes/tasks.py` :
  - POST → `create`
  - PATCH classifié sur le diff : status ou project changé → `move` (avec details `{from_status, to_status, from_project}`), sinon field-only update → `save`
  - DELETE → `delete`

### UI

- `src/dashboard/templates/partials/activity.html` : line graph SVG inline (même pattern que `burndown.html`, pas de lib de chart). 760×90, polygone d'aire à 12% d'opacité + polyline 1.5px.
- `src/dashboard/templates/index.html` : nouvelle section en haut.
- `src/dashboard/static/style.css` : `.activity-card`, `.activity-header`, `.activity-svg`, `.activity-axis`.
- `src/dashboard/routes/pages.py` : `index()` charge `activity_daily_total(days=30)` et build une série contiguë de 30 jours zero-filled pour que le SVG soit uniforme indépendamment de la densité d'activité.

### Tests (7 nouveaux dans `tests/unit/test_activity.py`)

1. `log_activity` écrit la bonne row
2. swallow DB-level failures sans raise (action hors ENUM)
3. `activity_daily_total` aggrège bien
4. POST /api/v1/tasks → `create`
5. PATCH avec status change → `move`
6. PATCH field-only → `save`
7. DELETE → `delete`

### Comportements obtenus

- Toute mutation de tâche depuis l'UI ou l'API passe par `log_activity` → row appended → visible dans le line graph au prochain chargement.
- Le line graph est zero-filled donc il s'affiche dès le premier jour, même sans activité.
- Le bandeau \"Activité (30 derniers jours)\" affiche la somme totale en gros chiffre + le SVG en dessous + l'axe \"date début → date fin\".
- Les `details` JSON capturent le contexte (status from→to pour les moves, title pour les creates) — base pour des graphes futurs (sparkline par catégorie, breakdown par action, etc.).

### Garde-fous

- `pdm run check` : 385 passed (378 + 7 nouveaux)
- `pdm run test-e2e` : 52 passed / 0 failed
- `pdm run js-test` / `js-lint` / `js-typecheck` / `js-build` : clean
- Migration idempotente respecte CLAUDE.md (PREPARE/EXECUTE pattern, `-- rollback` no-op, FK auto-index)

### Pistes futures (Tier 2/3 du brief initial)

- Activity card par catégorie (pas juste global)
- Sparkline par projet sur les `cat-card`
- Per-user contribution row (déjà capturé via `user_name`)
- Streak counter / personal best
- Optimistic UI sur task mutations pour que les counters bougent instantanément (au lieu d'attendre le reload)
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-24.md)
