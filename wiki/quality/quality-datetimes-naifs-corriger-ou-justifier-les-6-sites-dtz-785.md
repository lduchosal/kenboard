---
id: 785
title: "QUALITY / Datetimes naïfs : corriger ou justifier les 6 sites DTZ"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-09T23:51:27
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #785 — QUALITY / Datetimes naïfs : corriger ou justifier les 6 sites DTZ

Chantier 2 du plan doc/code-quality.md (ken #783). 6 findings DTZ005/DTZ011 (datetime.now()/date.today() sans timezone). Examiner chaque site : passer en timezone-aware (UTC) là où la valeur est stockée/comparée en absolu ; poser un noqa argumenté là où la date locale est l'intention (ex. journal par jour). Vérifier la cohérence avec les colonnes MySQL — aucun changement de valeur affichée attendu.

---

## Résolution

### Modifications

**Vrai bug latent corrigé (2 sites)** — les tokens reset/verify écrivaient `expires_at` avec l'horloge Python (naïve, web2) mais le comparaient à `NOW()` MySQL (mysql2) : deux horloges différentes. L'expiration est désormais calculée côté DB, même horloge des deux côtés :
- `queries/password_reset.sql` — `prt_create` prend `:minutes`, écrit `NOW() + INTERVAL :minutes MINUTE`.
- `queries/email_verification.sql` — `evt_create` prend `:hours`, écrit `NOW() + INTERVAL :hours HOUR`.
- `auth_user.py` — les 2 call sites passent la durée au lieu d'un datetime ; import `datetime` retiré.
- `tests/unit/test_forgot_password.py`, `test_registration.py` — helpers adaptés (minutes=30 / hours=24).

**Date locale = intention, noqa argumenté (4 sites)** :
- `cli.py:241` (backfill burndown : jour calendaire opérateur), `models/task.py:63` (année courante pour le parsing dd.mm), `routes/pages.py` ×2 (fenêtre du chart taskers ; `now` du template admin_keys comparé à des DATETIME naïfs saisis en local).

### Comportements obtenus

- ruff --select DTZ : 0 finding. Expiration des tokens insensible à un écart d'horloge/TZ entre app et DB.
- Aucun changement de valeur affichée.

### Garde-fous

- black, ruff, flake8, mypy strict : verts.
- Suite complète hors e2e : 549 passed (dont les flows forgot-password et registration qui exercent les requêtes modifiées sur la DB de test).
---

[← retour à quality](index.md) · [voir log](../log/2026-06-09.md)
