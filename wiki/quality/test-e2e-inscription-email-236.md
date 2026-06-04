---
id: 236
title: "TEST / E2E / inscription email"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:57
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #236 — TEST / E2E / inscription email

Test end-to-end pour l'inscription par email.

---

## Resolution

`tests/e2e/test_email_flows.py` — Tests E2E Playwright avec serveur SMTP en memoire (aiosmtpd).

### TestRegistrationE2E (2 tests)

1. **test_full_registration_flow** — Parcours complet navigateur :
   - Login → clic 'Creer un compte' → formulaire register
   - Saisie email@test.com + mot de passe → submit
   - SMTP capture l'email → extraction du lien de verification
   - Playwright suit le lien → compte active
   - Login avec le nouveau compte → acces au board

2. **test_wrong_domain_rejected** — Mauvais domaine affiche erreur dans le navigateur

### Infrastructure

- `aiosmtpd` (dev dependency) — serveur SMTP en memoire qui capture les emails
- Serveur Flask dedie (port 5097) avec LOGIN_DISABLED=False + REGISTER_ALLOWED_DOMAIN=test.com
- SMTP pointe vers aiosmtpd (port 10025, pas de TLS)
- Extraction du lien par regex sur le corps de l'email capture
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
