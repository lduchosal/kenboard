---
id: 198
title: "USER / Password strength"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:45
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #198 — USER / Password strength

Password strenght is not enforced, user can set 123 as password and compromise board security. Any pip lib that enforce pass strength ?

---

## Résolution

Lib choisie : **zxcvbn** (4.5.0) — standard industrie, mesure l'entropie réelle.

### Politique

- Longueur min **8 caractères** (NIST)
- Score zxcvbn **≥ 3 / 4** ("safely unguessable")
- Double-gate : 8 chars seul ne suffit pas, il faut aussi l'entropie → passphrases ou mix lettres/chiffres/symboles de ~10+ chars

### Modifications

**Nouveau**
- `src/dashboard/password_strength.py` — module partagé `validate_password_strength()` avec `MIN_LENGTH=8`, `MIN_SCORE=3`. Messages d'erreur incluent le feedback zxcvbn.
- `tests/unit/test_password_strength.py` — 13 tests paramétrés (weak/strong, boundary, messages).

**Wiring**
- `src/dashboard/models/user.py` — `@field_validator` sur `UserCreate.password`, `PasswordChange.new_password`, `PasswordReset.new_password`.
- `src/dashboard/cli.py` — `kenboard set-password` appelle le validator.
- `pyproject.toml` — ajout `zxcvbn>=4.5.0`.

**UX — retour utilisateur actionnable**
- `src/dashboard/app.py` :
  - Nouveau `_extract_password_error()` qui détecte les erreurs de validation sur les champs password et retourne le message spécifique (incluant la guidance zxcvbn) au lieu du générique "Validation error".
  - Ajout de `field: "password"` dans la réponse pour que le frontend puisse cibler l'UX.
  - Bug pré-existant corrigé : `handle_validation_error` crashait en debug mode quand Pydantic incluait un `ValueError` non-sérialisable dans `ctx`. Ajout `_safe_pydantic_errors()`.
- `src/dashboard/templates/admin_users.html` — nouveau panneau informatif **en haut** de la page expliquant les critères et donnant des exemples (passphrase, mix caractères) AVANT que l'utilisateur tape son mot de passe. Frontend `apiCall()` inchangé : il utilisait déjà `parsed.error`, maintenant il affiche la raison précise.

**Tests mis à jour**
- `tests/unit/test_api.py`, `tests/unit/test_auth_user.py`, `tests/e2e/test_dashboard.py` — passwords faibles remplacés par des passwords passant zxcvbn.
- Ajout `test_weak_password_surfaces_specific_error` vérifiant que la réponse 422 porte bien le message zxcvbn avec `field: "password"`.

**Doc**
- `doc/authentication.md` — nouvelle section "Politique de mot de passe (#198)".

### Comportements obtenus

- **En amont** (avant saisie) : l'utilisateur voit les critères directement sur `/admin/users` (panneau dédié avec exemples).
- **En aval** (après rejet) : message précis dans la modale d'erreur, ex. `Password is too weak (strength 1/4, need 3/4). This is a very common password. Add another word or two.` au lieu de `Validation error`.
- Même politique partout : API `POST /users`, `POST /password`, `POST /reset-password`, CLI `set-password`.
- Exemples rejetés : `123`, `password`, `Password123`, `qwerty12`, `letmein!`, `adminadmin`
- Exemples acceptés : `correct horse battery staple`, `Xk9\$mQ2!vL`, `Tr0ub4dor&3-Captain!`

### Garde-fous

- `pdm run test-unit` → 297 passed (14 nouveaux tests #198)
- `pdm run test-integration` → 10 passed
- `pdm run test-e2e` → 53 passed
- `pdm run check` (isort + black + docformatter + mypy + flake8 + interrogate + refurb + lint + vulture + test-quick) → tout vert
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
