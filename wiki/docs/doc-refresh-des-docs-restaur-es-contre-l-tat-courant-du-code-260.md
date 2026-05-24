---
id: 260
title: "DOC / refresh des docs restaurées contre l'état courant du code"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:54
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #260 — DOC / refresh des docs restaurées contre l'état courant du code

La tâche #256 a restauré l'arbre `doc/` supprimé par `1fdc315`, mais les fichiers datent du 19 avril 2026. Le code a évolué de ~3 semaines depuis. Sondage rapide identifié dans #256 :

- `doc/api.md` : "Aucune authentification n'est requise pour le moment" — faux, API keys + Flask-Login en place.
- `doc/architecture.md` : pas de mention du bundling Vite (#251) ni du JS toolchain (Vitest/Biome/tsc-via-JSDoc).
- `doc/openapi.yaml` : ne couvre que l'endpoint `users` ; categories/projects/tasks/keys absents.

---

## Résolution

### Audit du code courant

Mapping de l'état réel via un Explore agent : routes (`src/dashboard/routes/*`), modèles Pydantic (`src/dashboard/models/*`), CLI (`cli.py`, `ken.py`), middleware auth (`auth.py`, `auth_user.py`, `auth_oidc.py`), migrations (jusqu'à 0019), config (`config.py`), toolchain JS (`package.json`, `vite.config.js`, `pyproject.toml`).

Dérives confirmées et étendues au-delà du sondage initial :
- `authentication.md` : table « ce qui manque » entièrement obsolète (tout était fait).
- `ken-cli.md` : auth section déclarait \"L'API n'a aucune auth aujourd'hui\" (faux depuis #40 strict mode).
- `api-keys.md` : manquaient `key_type` (#14, onboarding/onboarded), `last_used_ip`/`last_used_agent` (#17), endpoint `POST /api/v1/keys/onboard`, rate-limit 10/h.
- `auth-user.md` : pas de mention des flows password reset par email (#231) ni self-registration (#232).
- `burndown.md` : pas de mention de `kenboard backfill --days N`.
- `permissions.md`, `oidc-adfs.md` : à jour, pas de modification.

### Modifications

Réécriture intégrale des deux docs les plus erronés :

- `doc/api.md` — auth section complète (cookie session, KENBOARD_ADMIN_KEY, api_keys per-projet), endpoints users complets (password / reset-password / scopes), endpoints keys complets (incl. onboard), routes hors `/api/v1/` (login / forgot-password / reset-password / register / verify-email / oidc).
- `doc/architecture.md` — stack table avec toolchain JS, schéma DB complet (toutes les tables : users, api_keys, api_key_projects, user_category_scopes, burndown_snapshots, password_reset_tokens, email_verification_tokens), liste des migrations (incl. recovery 0009/0011/0013), structure fichiers complète avec `auth*.py`, `ken.py`, `password_strength.py`, `mailer.py`, `perf.py`. Suppression de \"Pas de build step JS\" et \"un seul fichier app.js\".

Réécriture du yaml :

- `doc/openapi.yaml` — passe de ~270 lignes (users-only) à ~1000 lignes couvrant categories, projects, tasks, users, keys. Ajout `bearerAuth` + `cookieAuth` dans `securitySchemes`, endpoint `POST /api/v1/keys/onboard`, endpoints `users/{id}/password`, `users/{id}/reset-password`, `users/{id}/scopes`. Notes rate-limit explicites.

Patches ciblés :

- `doc/authentication.md` — recadré comme référence \"table users + politique de mot de passe\". Suppression du framing \"ce qui manque\" devenu obsolète. Lien vers `auth-user.md` / `api-keys.md` / `permissions.md` pour les flows.
- `doc/ken-cli.md` — drop \"Spec v1, validée par l'opérateur\" (c'est shippé), ajout `self-update` + `help`, section auth réécrite (bearer token requis + onboarding link).
- `doc/auth-user.md` — sections ajoutées : password reset par email (#231) avec flow + migration 0018 + config SMTP, self-registration (#232) avec flow + migration 0019.
- `doc/api-keys.md` — schéma SQL mis à jour (`key_type`, `last_used_ip`, `last_used_agent`), section \"Onboarding tokens\" + section \"Audit trail\", correction du commentaire bootstrap (\"mode soft\" → \"mode strict permanent\"), correction du statut /admin/keys (admin_required, pas \"reste ouverte\").
- `doc/burndown.md` — ajout `kenboard backfill --days N` avec caveat sur la précision des statuts intermédiaires.

`doc/permissions.md` et `doc/oidc-adfs.md` : laissés tels quels (déjà alignés sur le code courant).

### Commits

- `f3ae70e chore: release version 0.1.86` (par l'utilisateur, embarque les changements de api.md et architecture.md).
- `0c32dea docs: refresh restored docs against current code state` (les 6 autres fichiers).

### Comportements obtenus

- Tous les liens internes entre docs résolvent.
- Les exemples d'endpoints listés dans les docs matchent les blueprints réels (`src/dashboard/routes/*`).
- Les schémas SQL listés dans les docs matchent les colonnes après application de toutes les migrations jusqu'à 0019.
- L'OpenAPI yaml décrit les 5 ressources principales avec les modèles Pydantic actuels (`UserUpdate` sans `password`, `Project.default_who`, `Task.position`, `ApiKey.last_used_ip/agent`, `ApiKeyCreated.key`, etc.).

### Garde-fous

- Audit du code via Explore agent en lecture seule, croisé avec les modèles Pydantic et migrations (source de vérité pour le schéma).
- Pas de modification de code applicatif, donc pas de quality gate exécutée (lint/typecheck/test inutiles pour des édits Markdown/YAML).
- Inspection des en-têtes pour vérifier que les fichiers n'ont pas été tronqués.

### Hors scope (à traiter dans une tâche dédiée si souhaité)

- Brancher Swagger UI sur `/api/v1/docs` (déjà mentionné comme dette dans `doc/api.md`).
- Migrer vers `flask-openapi3` pour auto-générer la spec depuis les modèles Pydantic (réduit drift à long terme).
- Cron de purge des `password_reset_tokens` / `email_verification_tokens` expirés (mentionné en TODO dans `auth-user.md` section self-register).
---

[← retour à docs](index.md) · [voir log](../log.md)
