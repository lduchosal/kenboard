---
id: 232
title: "USER / Onboarding a new user"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:55
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #232 — USER / Onboarding a new user

Permettre a un nouvel utilisateur de creer son compte depuis la page de login avec validation par email.

---

## Resolution

### Modifications

- `src/dashboard/config.py` — Ajout REGISTER_ALLOWED_DOMAIN (vide = inscription desactivee)
- `src/dashboard/auth_user.py` — 3 nouvelles routes :
  - GET/POST /register : formulaire email+password, valide domaine, envoie email verification
  - GET /verify-email/<token> : verifie le token, cree user + categorie Users + projet personnel + scopes
  - Helper _get_or_create_users_category() pour la categorie partagee
- `src/dashboard/migrations/0019.create_email_verification_tokens.sql` — Table (id, email, password_hash, token_hash, expires_at, used_at)
- `src/dashboard/queries/email_verification.sql` (nouveau) — CRUD tokens
- `src/dashboard/templates/register.html` (nouveau) — Formulaire inscription avec domaine affiche
- `src/dashboard/templates/email/verify_email.html` (nouveau) — Template email HTML
- `src/dashboard/templates/login.html` — Lien 'Creer un compte' (visible si REGISTER_ALLOWED_DOMAIN)
- `tests/conftest.py` — Table email_verification_tokens dans le test DB

### Flux

1. User ouvre /register, saisit email@domaine + mot de passe
2. Validation : domaine autorise, email unique, zxcvbn
3. Token + password_hash stockes en DB, email de verification envoye
4. User clique le lien → /verify-email/<token>
5. Creation : user (is_admin=0) + categorie 'Users' (ou reutilisee) + projet 'user@email' + scope read+write
6. Redirect vers /login avec message 'Compte active'

### Garde-fous

- pytest unit : 343 passed
- mypy : 0 issues
- flake8 : clean
- interrogate : 100%
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
