---
id: 412
title: "WIKI / Schema + storage (#376a)"
status: review
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:24:21
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/db
section_title: "Database (SQL + migrations)"
---

# #412 — WIKI / Schema + storage (#376a)

Sous-tâche A de #376 (LLM Wiki pattern Karpathy, https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

---

## Résolution

### Modifications

- **src/dashboard/migrations/0021.create_task_wiki_classifications.sql** — table dédiée (option B), idempotente, -- rollback no-op. UNIQUE (task_id), INDEX (section_path), FK ON DELETE CASCADE.
- **tests/sql/schema.sql** : CREATE TABLE miroir + cleanup DELETE FROM task_wiki_classifications ajouté dans tests/conftest.py (before+after) et tests/e2e/conftest.py (clean_db).
- **src/dashboard/queries/wiki.sql** : 5 queries — wiki_classify! (upsert via ON DUPLICATE KEY), wiki_clear!, wiki_get_for_task^, wiki_get_all (join avec tasks pour récupérer title/etc.), wiki_get_unclassified_tasks (LEFT JOIN où classification est NULL).
- **src/dashboard/wiki.py** : dataclass Section (id, title, description, sub) avec .flatten() pour walk depth-first ; parse_architecture(path) qui extrait le frontmatter YAML d'ARCHITECTURE.md et reconstruit le tree ; section_paths(sections) qui flatten en liste de paths "parent/child".
- **pyproject.toml** : ajout pyyaml>=6.0 runtime dep (le types-PyYAML était déjà là côté dev).
- **tests/unit/test_wiki.py** : 16 tests couvrant tous les cas — parser (missing file, no frontmatter, empty frontmatter, no wiki key, flat, nested, missing id, fallback title) + section_paths (flat, nested) + queries (insert, upsert, clear, get_all join, unclassified filter, FK cascade).

### Comportements obtenus

- La DB peut désormais stocker une classification par tâche (mise à jour idempotente).
- Le helper sait parser un ARCHITECTURE.md avec frontmatter YAML, supporte la profondeur 2 niveaux validée par #376.
- Les queries fournissent toutes les primitives dont auront besoin les chunks B (groom) et C (sync).
- FK ON DELETE CASCADE : supprimer une tâche supprime aussi sa classification (pas d'orphelins).

### Hors scope (chunks suivants)

- Pas de commande CLI exposée (chunk B = ken wiki groom).
- Pas d'export MD (chunk C = ken wiki sync).
- Pas de rendu HTML (chunk D = ken wiki build).
- Pas de lint (chunk E = ken wiki lint).

### Garde-fous

- pdm run check : 418 passed (402 + 16 nouveaux)
- pdm run test-e2e : 52 passed / 0 failed
- mypy / ruff / flake8 / interrogate / vulture : clean
- Migration respecte CLAUDE.md (PREPARE/EXECUTE pattern, FK auto-index, -- rollback no-op)
---

[← retour à backend/db](index.md) · [voir log](../../log.md)
