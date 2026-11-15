---
id: 1192
title: "SEC / Login : open redirect via le paramètre next"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:10
classified_at: 2026-11-15T18:45:18
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1192 — SEC / Login : open redirect via le paramètre next

**TL;DR** — `next=/<TAB>/evil.example` passait `_is_safe_url` et donnait `Location: //evil.example` → caractères de contrôle, espaces et antislash refusés, cible validée après découpage.

---

Issu de l'audit #1183 (M4). _is_safe_url accepte '/<TAB>/evil.example' ; Werkzeug retire la tabulation et émet Location: //evil.example.

---

## Résolution

### Modifications

- `src/dashboard/auth_login.py` — `_is_safe_url()` : chemin local commençant par un seul `/`, sans caractère de contrôle / espace / antislash, sans schéma ni hôte après `urlsplit`.
- `tests/unit/test_sec_audit.py::TestLoginRedirect` — 11 cibles refusées, 3 acceptées.

### Comportements obtenus

- Toute cible hors site ou ambiguë redirige vers `/`.
- Un chemin local avec query et fragment est suivi tel quel.
- `next` contenant `\n` ne provoque plus de 500 (`Header values must not contain newline`).

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
