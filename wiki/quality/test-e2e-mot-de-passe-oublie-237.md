---
id: 237
title: "TEST / E2E / mot de passe oublié"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:57
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #237 — TEST / E2E / mot de passe oublié

Test end-to-end pour le mot de passe oublie.

---

## Resolution

`tests/e2e/test_email_flows.py` — Test E2E Playwright avec serveur SMTP en memoire (aiosmtpd).

### TestForgotPasswordE2E (1 test)

1. **test_full_reset_flow** — Parcours complet navigateur :
   - Login → clic 'Mot de passe oublie' → formulaire forgot-password
   - Saisie email → submit → message de confirmation
   - SMTP capture l'email → extraction du lien de reset
   - Playwright suit le lien → formulaire nouveau mot de passe
   - Saisie nouveau mot de passe → submit → message 'modifie'
   - Login avec le nouveau mot de passe → acces au board

### Infrastructure partagee avec #236

- Meme fichier de test, meme serveur Flask + SMTP
- aiosmtpd comme dev dependency
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
