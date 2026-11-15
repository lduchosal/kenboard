---
id: 1195
title: "SEC / Durcissement post-audit"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:12
classified_at: 2026-11-15T18:45:29
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1195 — SEC / Durcissement post-audit

**TL;DR** — Lot de durcissement issu de l'audit : comparaison de la clé admin à temps constant, garde admin dans les routes, DOMPurify fail-closed, validation `color`/`who`, anti-énumération au login, limite de taille de requête.

---

Issu de l'audit #1183 (section Durcissement) : comparaison de la clé admin à temps constant, contrôle admin dans les routes users/keys (pas seulement le middleware), DOMPurify fail-closed, validation color/who, énumération d'utilisateurs au login et à l'inscription, limite de taille de requête.

---

## Résolution

### Modifications

- `src/dashboard/auth.py` — clé admin comparée avec `hmac.compare_digest`.
- `src/dashboard/routes/users.py`, `src/dashboard/routes/keys.py` — `before_request` de blueprint appelant `api_admin_required()` (exception : changement de mot de passe self-service).
- `src/dashboard/static/js/markdown.js`, `fullscreen.js` (+ bundle `static/dist/app.js`) — sans DOMPurify, la description reste du texte au lieu d'être injectée non assainie.
- `src/dashboard/models/user.py` — `color` soumis à `COLOR_PATTERN` (création et mise à jour).
- `src/dashboard/models/task.py` — `who` limité à 100 caractères (taille de la colonne) : 422 au lieu d'une 500.
- `src/dashboard/auth_login.py` — vérification argon2 factice quand le compte n'existe pas.
- `src/dashboard/app.py` — `MAX_CONTENT_LENGTH` à 20 Mo.
- `tests/unit/test_sec_audit.py::TestHardening` (9 tests), `static/js/markdown.test.js` (1 test).

### Comportements obtenus

- Avec la table de préfixes du middleware vidée, `/api/v1/users` et `/api/v1/keys` répondent toujours 403 à un non-admin.
- Un login sur un nom inconnu coûte une vérification de hash, comme un vrai compte.
- Une requête au-delà de la limite reçoit 413 sans être analysée.
- L'énumération à l'inscription est traitée dans #1194.

### Non traité (demande un arbitrage ou un chantier dédié)

- CSP `script-src 'unsafe-inline'` : les templates reposent sur des `onclick` et des `<script>` en ligne ; la retirer est un refactor du front.
- Rate limit en mémoire par worker (stockage partagé type Redis à décider) et absence de verrouillage par compte.
- Envoi SMTP synchrone sur `/forgot-password` (oracle de timing résiduel).
- Traceback complète dans les tâches 500 auto-créées (comportement voulu par #517).
- Extension navigateur (token en `storage.local`, content script sur `<all_urls>`).

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
