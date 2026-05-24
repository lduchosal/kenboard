---
id: 231
title: "USER / Changement de mot de passe"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:55
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #231 — USER / Changement de mot de passe

Un utilisateur doit pouvoir changer son mot de passe via une procedure standard.

---

## Resolution

### Modifications

- `src/dashboard/config.py` — 7 variables SMTP (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS, SMTP_ENABLED)
- `src/dashboard/email.py` (nouveau) — Module d'envoi d'email via smtplib, templates Jinja2. init_email(app) + send_email(to, subject, template, **ctx).
- `src/dashboard/auth_user.py` — 4 nouvelles routes : GET/POST /forgot-password, GET/POST /reset-password/<token>. Rate limit 3/heure sur forgot-password.
- `src/dashboard/migrations/0018.create_password_reset_tokens.sql` — Table password_reset_tokens (id, user_id, token_hash SHA256, expires_at, used_at)
- `src/dashboard/queries/password_reset.sql` (nouveau) — CRUD tokens (create, get by hash, mark used, cleanup)
- `src/dashboard/templates/forgot_password.html` (nouveau) — Formulaire email
- `src/dashboard/templates/reset_password.html` (nouveau) — Formulaire nouveau mot de passe
- `src/dashboard/templates/email/password_reset.html` (nouveau) — Template email HTML
- `src/dashboard/templates/login.html` — Lien 'Mot de passe oublie' + support message de succes
- `src/dashboard/app.py` — Branchement init_email(app)
- `tests/conftest.py` — Table password_reset_tokens dans le test DB

### Securite

- Token hashe SHA256 en DB (jamais en clair)
- Expiration 30 min
- Usage unique (used_at)
- Rate limit 3/h sur /forgot-password
- Pas de leak d'existence d'email (reponse identique)
- Validation zxcvbn sur le nouveau mot de passe
- Invalidation de toutes les sessions apres reset (rotation nonce)

### Garde-fous

- pytest unit : 343 passed
- mypy : 0 issues
- flake8 : clean
- interrogate : 100%
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
