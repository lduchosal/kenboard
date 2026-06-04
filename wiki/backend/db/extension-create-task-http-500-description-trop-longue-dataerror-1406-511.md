---
id: 511
title: "EXTENSION / create task — HTTP 500 (description trop longue, DataError 1406)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-29T10:12:36
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/db
section_title: "Database (SQL + migrations)"
---

# #511 — EXTENSION / create task — HTTP 500 (description trop longue, DataError 1406)

POST /api/v1/tasks via l'extension renvoie 500 Internal server error : pymysql DataError(1406, "Data too long for column 'description' at row 1"). error_id observé: E-6a1947af-3464.

---

## Résolution (révisée après discussion produit)

### Décision
On ne stocke PAS de binaire (PNG base64) dans la base. La piste « élargir la colonne en MEDIUMTEXT » a été abandonnée (revert) : c'était traiter le symptôme. L'extension passera à une capture **textuelle structurée** (tâche séparée). #511 se limite donc à : ne plus jamais 500 sur une description trop longue, colonne `TEXT` conservée.

### Modifications
- src/dashboard/models/task.py — DESCRIPTION_MAX_BYTES = 65_535 (capacité MySQL TEXT en utf8mb4) + validateur `_within_text_column` (AfterValidator sur un type Annotated `BoundedDescription`) appliqué à TaskCreate.description et TaskUpdate.description. La validation compte les **octets** encodés (pas les caractères), car c'est ce que limite la colonne. Au-delà → ValidationError → 422 propre (handler global app.py:158), jamais 500.
- (revert) migration 0022 supprimée ; tests/sql/schema.sql et tests/conftest.py reviennent à `description TEXT`.
- tests/unit/test_api.py — 2 régressions : description 50 KB → 201 ; description > 65 535 octets → 422.

### Comportements obtenus
- Plus aucun 500 sur description trop longue : 422 propre.
- Colonne inchangée (TEXT), pas de blob binaire en base.
- (À venir, tâche séparée) l'extension enverra une capture textuelle structurée au lieu du PNG, ce qui supprime la cause initiale du dépassement.

### Garde-fous
- mypy OK ; suite complète unit+integration : 495 passed.
- Aucune migration à appliquer en prod (revert) — fix purement applicatif (validation).
---

[← retour à backend/db](index.md) · [voir log](../../log.md)
