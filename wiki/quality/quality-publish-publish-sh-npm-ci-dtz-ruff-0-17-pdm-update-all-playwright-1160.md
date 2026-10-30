---
id: 1160
title: "QUALITY / PUBLISH / publish.sh : npm ci, DTZ ruff 0.17, pdm update-all, playwright"
status: done
who: "Claude"
due_date: 
updated_at: 2026-10-30T10:20:36
classified_at: 2026-10-30T10:20:35
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1160 — QUALITY / PUBLISH / publish.sh : npm ci, DTZ ruff 0.17, pdm update-all, playwright

**TL;DR** — `publish.sh` cassait en cascade (npm ci, noqa DTZ effacés, pytest, E2E, push rejeté) → lockfile réaligné, DTZ relisté pour ruff 0.17, `pdm update --update-all`, config pytest-asyncio/pdm, install des navigateurs Playwright, `.pdm-python` ignoré ; toutes les étapes qualité passent.

publish.sh échoue à l'étape 16 (npm ci) puis aux suivantes ; tout corriger jusqu'au push.

## Résolution

### Modifications
- `package-lock.json` — régénéré (`npm install` + `npm audit fix`) : `a144cb6` (#1158) n'embarquait que `package.json`, le lockfile mis à jour ayant été écrasé par un `git checkout` avant le commit → `npm ci` refusait (rolldown 1.2.11 vs 1.2.16).
- `pyproject.toml` — `DTZ` en `extend-select` : ruff 0.17 ne garde que DTZ002/003/004 par défaut, RUF100 supprimait les `noqa: DTZ005/011` argumentés de #785 au `ruff --fix`.
- `publish.sh` — `pdm update --update-all` : la stratégie reuse bumpait pytest 9.2 en laissant anyio 4.13 (plugin pytest important `CallSpec2` → `PytestRemovedIn10Warning` sous `filterwarnings = error`).
- `pyproject.toml` — `asyncio_default_fixture_loop_scope = "function"` (pytest-asyncio 1.4) ; `ignore_package_warnings` += `deprecated`, `pyee` (dernières majeures Python ≥ 3.12, prod en 3.11).
- `publish.sh` — `playwright install chromium firefox` avant les E2E (build navigateur manquant après bump playwright ; firefox pour le test autofill-leak).
- `.gitignore` — `.pdm-python`, committé par le `git add .` de la release CI 0.4.7 (chemin `/home/runner/...`), retiré de l'index.

### Comportements obtenus
- publish.sh : étapes 1–27 vertes (unit 664, E2E 52, metrics gate PASS, wiki sync/build), npm audit 0 vulnérabilité.
- Push rejeté (release CI 0.4.7 entre-temps) → commits rejoués sur `origin/main` et poussés.

### Garde-fous
- `pdm run test-unit` 654 → 664 passed, `pdm run test-e2e` 52 passed, ruff clean, `npm ci` OK.
- Reste ouvert : `git add .` (publish.sh:342) embarque tout le working tree dans le commit de release — c'est lui qui a committé `.pdm-python` en CI, et il avalerait un WIP local non committé.
---

[← retour à quality](index.md) · [voir log](../log/2026-10-30.md)
