---
id: 542
title: "EXTENSION / paintbrush - phase 1 schema + model + API (tasks.attachement)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T14:39:54
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/db
section_title: "Database (SQL + migrations)"
---

# #542 — EXTENSION / paintbrush - phase 1 schema + model + API (tasks.attachement)

Phase 1 (Epic #541) — schéma + modèle + API pour tasks.attachement.

---

## Résolution

### Modifications
- src/dashboard/migrations/0022.add_task_attachement.sql — migration idempotente (PREPARE/EXECUTE + INFORMATION_SCHEMA check, rollback no-op) ajoute tasks.attachement MEDIUMTEXT NULL. depends: 0021.create_task_wiki_classifications.
- tests/sql/schema.sql — tasks gagne la colonne (NULL par défaut).
- tests/conftest.py — back-fill idempotent pour DB de test héritées.
- src/dashboard/queries/tasks.sql :
  - 3 SELECT (task_get_by_project, task_get_by_category, task_get_by_id) retournent attachement.
  - task_create INSERT inclut attachement.
  - task_update UPDATE inclut attachement.
- src/dashboard/models/task.py :
  - ATTACHEMENT_MAX_BYTES = 16_777_215 (MEDIUMTEXT) + validateur byte-length \`_within_mediumtext_column\` (AfterValidator sur Annotated, même pattern que BoundedDescription #511).
  - Task / TaskCreate / TaskUpdate gagnent \`attachement: BoundedAttachement | None = None\`.
- src/dashboard/routes/tasks.py :
  - create_task passe data.attachement à task_create.
  - _has_field_updates teste data.attachement is not None.
  - _apply_field_updates passe attachement (existing.get() pour gérer les rows pré-migration en théorie).
- src/dashboard/app.py — _autocreate_error_task (#517) passe explicitement attachement=None.
- Tests unit/test_api.py : 3 nouveaux régressions Phase 1 (create avec attachement persiste+retourne ; create sans → null ; >MEDIUMTEXT → 422 propre).
- 10 call-sites task_create dans tests/* mis à jour pour passer attachement=None (script Python in-place).

### Garde-fous
- mypy clean (3 fichiers).
- TestTaskAPI : 12 passed (9 anciens + 3 #541).
- Suite complète : 502 passed.
- Migration suit les règles strictes CLAUDE.md (idempotente, une seule concern, rollback no-op).

### À suivre
Phase 2 (#543) : rendre attachement sur le modal détail de la tâche (sanitize via DOMPurify déjà chargé).
---

[← retour à backend/db](index.md) · [voir log](../../log.md)
