---
id: 1194
title: "SEC / Inscription : mot de passe choisi avant la preuve d'e-mail"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:11
classified_at: 2026-11-15T18:45:25
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1194 — SEC / Inscription : mot de passe choisi avant la preuve d'e-mail

**TL;DR** — Le mot de passe était choisi avant la preuve de possession de l'e-mail : un attaquant pouvait pré-inscrire une victime avec son propre mot de passe → le mot de passe se choisit maintenant après ouverture du lien de vérification.

---

Issu de l'audit #1183 (M6). Un attaquant inscrit victime@domaine avec son propre mot de passe ; si la victime clique le lien de vérification, le compte est créé avec un mot de passe connu de l'attaquant.

---

## Résolution

### Modifications

- `src/dashboard/auth_register.py` — `POST /register` ne prend que l'email ; `GET /verify-email/<token>` affiche le formulaire de mot de passe sans effet de bord ; nouveau `POST /verify-email/<token>` qui crée le compte. Le `password_hash` stocké avec le token est ignoré (couvre les tokens émis avant le correctif). Réponse identique que l'adresse ait déjà un compte ou non.
- `src/dashboard/templates/register.html` — champ email seul.
- `src/dashboard/templates/reset_password.html` — titre, action et libellé paramétrables, réutilisé pour le choix du mot de passe.
- `src/dashboard/templates/email/verify_email.{html,txt}` — texte adapté.
- `doc/auth-user.md`, `doc/api.md` — flow mis à jour.
- `tests/unit/test_registration.py` (réécrit), `tests/e2e/test_email_flows.py` (flow navigateur adapté).

### Comportements obtenus

- Un mot de passe posté avec l'email n'atteint jamais le token ; un hash pré-rempli sur un token n'est jamais utilisé.
- Ouvrir le lien (préchargement par un scanner de mails) ne crée pas le compte et ne consomme pas le token.
- Mot de passe faible ou non concordant : formulaire réaffiché, token toujours valide.
- Flow complet vérifié en navigateur (Playwright + SMTP de test).

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
