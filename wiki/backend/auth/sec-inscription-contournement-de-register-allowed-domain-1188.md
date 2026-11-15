---
id: 1188
title: "SEC / Inscription : contournement de REGISTER_ALLOWED_DOMAIN"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:06
classified_at: 2026-11-15T18:45:06
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1188 — SEC / Inscription : contournement de REGISTER_ALLOWED_DOMAIN

**TL;DR** — Le contrôle du domaine d'inscription était un `endswith` sur une chaîne libre, contournable avec une adresse forgée → l'adresse doit être une adresse nue unique, validée avant tout envoi.

---

Issu de l'audit #1183 (H5). Le contrôle du domaine est un simple endswith('@domaine') sans validation de format ; smtplib extrait un autre destinataire d'une adresse forgée (ex. 'a@evil.com (x@domaine').

---

## Résolution

### Modifications

- `src/dashboard/email.py` — `is_valid_address()` (une seule adresse `local@domaine`, sans nom affiché, commentaire, chevron, séparateur ni espace) ; `send_email()` refuse tout destinataire invalide.
- `src/dashboard/auth_register.py` — `_validate_registration()` : adresse valide **et** domaine égal après découpage.
- `src/dashboard/auth_reset.py` — le mail de reset part à l'adresse enregistrée, pas à la chaîne soumise.
- `src/dashboard/models/user.py` — même validation sur l'email à la création d'un user par l'admin.
- `tests/unit/test_registration.py::test_forged_address_rejected` (14 formes), `tests/unit/test_email.py::TestRecipientValidation`.

### Comportements obtenus

- `a@evil.com (x@domaine`, `a@evil.com, x@domaine`, `<a@evil.com>x@domaine`, injections CR/LF, sous-domaines et domaines suffixes : tous refusés, aucun token créé, aucun mail envoyé.
- `User@DOMAINE` est accepté et stocké en minuscules.
- La protection ne dépend plus de la version de Python ni du MTA.

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
