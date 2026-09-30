---
id: 1130
title: "QUALITY / Sonar : corriger toutes les issues ouvertes (bugs, smells, sécurité)"
status: review
who: "Claude"
due_date: 
updated_at: 2026-09-30T15:26:01
classified_at: 2026-09-30T15:26:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1130 — QUALITY / Sonar : corriger toutes les issues ouvertes (bugs, smells, sécurité)

**TL;DR** — La quality gate Sonar bloquait la release 0.4.3 → les 111 issues ouvertes sont corrigées (1 vulnérabilité, 6 bugs, 104 smells), sans suppression ni NOSONAR, gate locale verte.

La quality gate Sonar bloque la release (new_reliability_rating C, new_security_rating E). 111 issues ouvertes : 1 vulnérabilité (path traversal ken/config.py), 6 bugs (promesses flottantes JS, assertion tautologique), 104 code smells (décorateurs, assertions composites, monkeypatch, constantes, complexité, accessibilité des templates). Tout corriger puis relancer publish.sh --patch (release 0.4.3 : #1127 .vsix + #1129).

---

## Résolution

### Modifications

- `src/dashboard/ken/config.py` — `_persist_sync_dir` ajoute seulement la ligne `sync_dir=` en append, sans réécrire le contenu lu (pythonsecurity:S2083, BLOCKER) ; `_load_config` simplifié via `_existing_file` (S3776).
- `src/dashboard/static/js/{keyboard,detail,fullscreen}.js` — promesses flottantes marquées `void` (S9383 ×5) ; `populateFullscreen(task, avatarColor, btn)` au lieu de 8 paramètres (S107) ; `static/dist/` regénéré.
- `src/dashboard/auth_resolve.py`, `routes/wiki.py`, `ken/wiki_layout.py` — littéraux dupliqués → `_TASKS_PATH`, `_TASK_NOT_FOUND`, `_current_cls` (S1192).
- `src/dashboard/ken/wiki_groom.py` — plus de `except SystemExit` : `_try_request` renvoie `None` sur 404 (S5754).
- `src/dashboard/**` — `# noqa: CODE — raison` → raison sur la ligne au-dessus, `# noqa: CODE` seul (S7632, 10 occurrences harmonisées).
- Templates — `admin_keys.html`, `modals/project.html`, `modals/task.html` : selects étiquetés par `<label for>` `.sr-only` (nouvelle classe dans `style.css`) au lieu d'`aria-label` (Web:S7927) ; `autofocus` retiré de login / register / forgot / reset (Web:S9379) ; faux TODO de `partials/burndown.html` reformulé (S1135).
- Tests — `@pytest.fixture()` → `@pytest.fixture` (S9083) ; 2 fixtures `yield` sans teardown → `return` (S9100) ; assertions composites scindées (S9073) ; `test_perf` / `test_registration` via `monkeypatch` (S8997) ; `test_api_keys` : assertion tautologique → sha256 attendu (S5863).

### Comportements obtenus

- Aucune régression fonctionnelle ; les formulaires d'auth n'ont plus le focus automatique (choix d'accessibilité imposé par la règle).
- `ken wiki groom <id>` sans classification : même message « unclassified », sans passer par `SystemExit`.

### Garde-fous

- `sh publish.sh --quality` vert : ruff/mypy/flake8/interrogate/refurb/vulture, 664 unit + 52 E2E, JS 77, VS Code 14, metrics gate.
- Validation Sonar : au prochain `publish.sh --patch` (analyse du commit poussé).
---

[← retour à quality](index.md) · [voir log](../log/2026-09-30.md)
