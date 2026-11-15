---
id: 1193
title: "SEC / Clés API : durée de vie (user supprimé, tokens d'onboarding)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:10
classified_at: 2026-11-15T18:45:22
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1193 — SEC / Clés API : durée de vie (user supprimé, tokens d'onboarding)

**TL;DR** — Les clés API survivaient à la suppression de leur utilisateur et les liens d'onboarding restaient des clés `write` valides indéfiniment → révocation à la suppression, et échéance de 7 jours pour un lien jamais utilisé.

---

Issu de l'audit #1183 (M5). Les clés survivent à la suppression de leur utilisateur (FK SET NULL) ; les tokens d'onboarding sont write, sans expiration, même jamais utilisés.

---

## Résolution

### Modifications

- `src/dashboard/queries/api_keys.sql` — `key_revoke_for_user!`, `key_expire_in_days!`, `key_promote_onboarding!`.
- `src/dashboard/routes/users.py` — `delete_user` révoque les clés du user avant suppression.
- `src/dashboard/routes/keys.py` — `ONBOARDING_TOKEN_DAYS = 7` appliqué à la création du token (échéance calculée côté base).
- `src/dashboard/auth_api_key.py` — la promotion `onboarding → onboarded` au premier usage lève l'échéance.
- `doc/api-keys.md` — comportement documenté.
- `tests/unit/test_sec_audit.py::TestApiKeyLifetime` — 4 tests.

### Comportements obtenus

- La clé d'un utilisateur supprimé répond 401 ; les autres clés sont intactes.
- Un lien d'onboarding neuf expire à J+7 ; utilisé une fois, il devient la clé permanente de l'agent (comportement inchangé pour les agents déjà onboardés).

### Non traité ici

- Le token circule toujours en query string (`/onboard/…?token=`) et apparaît donc dans les logs d'accès nginx envoyés à logstash : à exclure côté vhost. `ken init -` (URL sur stdin) existe déjà pour l'historique shell.
- Les tokens `onboarding` déjà émis et jamais utilisés gardent `expires_at = NULL` : à révoquer depuis `/admin/keys` si besoin.

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
