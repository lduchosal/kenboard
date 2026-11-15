---
id: 1184
title: "SEC / Reset password : lien détournable par X-Forwarded-Host"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:02
classified_at: 2026-11-15T18:44:52
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1184 — SEC / Reset password : lien détournable par X-Forwarded-Host

**TL;DR** — `X-Forwarded-Host` fourni par le client décidait de l'hôte des liens envoyés par mail (reset, vérification) → `ProxyFix` ne lui fait plus confiance et une URL canonique `KENBOARD_BASE_URL` est disponible.

---

Issu de l'audit #1183 (H1). ProxyFix(x_host=1) fait confiance à X-Forwarded-Host et les liens envoyés par mail (reset, vérification) sont construits avec request.host_url. Le nginx du reverse ne pose pas cet en-tête : un client peut imposer l'hôte du lien de reset reçu par la victime.

---

## Résolution

### Modifications

- `src/dashboard/app.py` — `ProxyFix(x_host=0)` : `request.host` ne dépend plus de `X-Forwarded-Host`.
- `src/dashboard/config.py` — nouveau `KENBOARD_BASE_URL` (optionnel).
- `src/dashboard/onboarding.py` — `derive_base_url()` : `KENBOARD_BASE_URL` d'abord, sinon `Host` ; seul `http`/`https` est accepté comme schéma.
- `src/dashboard/auth_reset.py`, `src/dashboard/auth_register.py` — les liens des mails passent par `derive_base_url()` au lieu de `request.host_url`.
- `.env.example`, `INSTALL.md` — documentation de `KENBOARD_BASE_URL` et du fait que le proxy doit transmettre le nom public dans `Host`.
- `tests/unit/test_sec_audit.py::TestEmailedLinkHost` — 4 tests.

### Comportements obtenus

- `POST /forgot-password` avec `X-Forwarded-Host: evil.example` → le lien du mail reste sur l'hôte réel.
- `X-Forwarded-Proto: javascript` (ou tout schéma exotique) est ignoré.
- Avec `KENBOARD_BASE_URL` défini, même un en-tête `Host` falsifié n'influence plus les liens ni le runbook d'onboarding.

### Reste à faire hors dépôt

- Prod : définir `KENBOARD_BASE_URL=https://www.kenboard.2113.ch` dans le dotenv ansible (recommandé), et poser `proxy_set_header X-Forwarded-Proto https;` dans le vhost du reverse.
- Une installation tierce dont le proxy réécrit `Host` et comptait sur `X-Forwarded-Host` doit désormais transmettre le nom public dans `Host` (c'est ce que décrit `INSTALL.md`).

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-15.md)
