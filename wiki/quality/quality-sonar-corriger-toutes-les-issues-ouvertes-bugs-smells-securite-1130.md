---
id: 1130
title: "QUALITY / Sonar : corriger toutes les issues ouvertes (bugs, smells, sécurité)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-10-02T14:39:21
classified_at: 2026-09-30T15:26:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1130 — QUALITY / Sonar : corriger toutes les issues ouvertes (bugs, smells, sécurité)

**TL;DR** — La gate Sonar bloquait la release et le log de publish.sh était pollué → 111 issues Sonar corrigées sans NOSONAR, 0 vulnérabilité npm, 0 warning, et publish.sh réécrit (1 ligne par commande, logs par étape, stop on error) ; releases 0.4.3 → 0.4.6 publiées.

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



## Suite — publish.sh propre (0.4.5 → 0.4.6)

### Modifications

- `package.json` / `package-lock.json` — vitest 5, @vitest/coverage-v8 5, vite 8, esbuild 0.28, jsdom 30 : `npm audit` 11 vulnérabilités (2 critiques) → 0 ; `engines` Node ≥ 22.22.2 + `.npmrc` engine-strict + `.nvmrc` ; `setup-node` 22 dans `.github/workflows/publish.yml`.
- `publish.sh` — sortie compacte : « [NN/MM] étape » puis « ✓ description — résumé (durée) » par commande, détail dans `logs/publish/<étape>-<n>.log`, warnings remontés (⚠), tout échec affiche la fin du log et arrête le run (y compris zip, .vsix, release GitHub, signature Firefox, avec commande de reprise) ; étape « JS Security Audit » bloquante ; verrou `.publish.lock` contre deux runs concurrents (cause du mélange 0.4.3/0.4.4).
- `pyproject.toml` — `ignore_package_warnings = ["oidc-provider-mock"]` ; pytest `filterwarnings = ["error", …]` (3 dépréciations amont ignorées) ; `js-install` en `npm ci --no-fund --no-audit --prefer-offline` (un npm ci réseau avait bloqué 1 h) ; `js-audit`.
- `src/dashboard/logging.py` — `_reset_handlers` ferme l'ancien WatchedFileHandler (fuite de descripteur révélée par les warnings) ; 4 tests ferment leurs réponses de fichiers statiques.
- Formateurs qui se battaient (black reformatait 3 fichiers à chaque run) : JS des tests e2e sorti des `page.evaluate`, concaténation implicite fusionnée (`test_wiki`), import `__future__` dans `test_queries`.
- `scripts/sign-firefox-extension.sh` — secret AMO passé par `WEB_EXT_API_KEY/SECRET` au lieu de l'argv (visible dans la liste des processus).

### Garde-fous

- `sh publish.sh --quality` : 25 étapes, aucune ligne ⚠, 664 unit + 52 E2E sans warning.
- Release 0.4.6 via le nouveau publish.sh : PyPI, tag, release GitHub (zip + .vsix) ; la signature Firefox a expiré côté réseau après 42 min (`fetch failed`) — dépôt AMO 0.4.6 en attente de validation, .xpi à joindre à la main.
---

[← retour à quality](index.md) · [voir log](../log/2026-09-30.md)
