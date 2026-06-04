---
id: 159
title: "AGENT / ONBOARDING / Automatic onboarding"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #159 — AGENT / ONBOARDING / Automatic onboarding

Le "copy onboarding link" :
- crée un API token sur le projet sélectionné, user claude, read / write de type onboarding
- si un token onboarding est déjà présent pour ce projet, ne pas en créer un nouveau
- le lien copié contient, le cat_id, le project_id, le token, le host complet avec https obligatoire
- le lien est fournis à un Agent
- l'agent a tout le nécessaire pour travailler immediatement, installer ken cli, créer le .ken, récupérer la liste des tâches
- une fois l'agent connecté avec le token "onboarding", le token change de type et devient "onboarded" et on peut créer un nouveau onboarding token.

---

## Résolution

### Modifications

- **`src/dashboard/migrations/0014.add_api_key_type.sql`** (nouveau) — colonne `api_keys.key_type VARCHAR(20) NULL` (`NULL`=regular, `onboarding`=pending, `onboarded`=utilisé). Idempotente, rollback no-op.
- **`src/dashboard/queries/api_keys.sql`** — `key_create` accepte `key_type`, `key_get_by_hash` retourne `key_type`. Deux nouvelles queries : `key_get_onboarding_for_project` (cherche un token onboarding actif) et `key_update_type` (mute le type).
- **`src/dashboard/routes/keys.py`** — nouvel endpoint `POST /api/v1/keys/onboard` : révoque l'éventuel token onboarding existant pour le projet, en crée un nouveau avec scope `write`, retourne la clé en clair + cat_id + project_id.
- **`src/dashboard/auth.py`** — `_enforce_api_key()` : après validation réussie d'un token `key_type='onboarding'`, appelle `_promote_onboarding_key()` qui mute le type en `onboarded`. Log structuré `auth.onboarding_promoted`.
- **`src/dashboard/onboarding.py`** — la route `/onboard/...` lit `?token=` du query string, sanitize via `_sanitize_token()` (regex `[^a-zA-Z0-9_-]`), et affiche un `.ken` complet copier-coller : `cat_id`, `project_id`, `base_url`, `api_token` — zéro réflexion pour l'agent. Page restructurée en 3 sections (Installer, Configurer, Travailler) + bonnes pratiques + footer avec toutes les valeurs.
- **`src/dashboard/static/app.js`** — `copyOnboardLink()` appelle `POST /api/v1/keys/onboard` (async), récupère la clé, construit l'URL complète `/onboard/cat/.../project/...?token=kb_...`, copie dans le clipboard.
- **`tests/conftest.py`** — colonne `key_type` dans CREATE TABLE + backfill legacy.
- **`tests/unit/test_api_keys.py`** — `key_type=None` ajouté aux appels `key_create` existants.

### Sécurité

Les 3 valeurs provenant de l'URL sont sanitizées avant interpolation dans le body :
- `cat_id`, `project_id` → `_sanitize_id()` : `[^a-zA-Z0-9-]` supprimé
- `token` → `_sanitize_token()` : `[^a-zA-Z0-9_-]` supprimé
- `base_url` → dérivé de `request.host_url` (contrôlé par Flask, pas par le query string)

Aucun `< > " ' & \n` ne peut passer → pas de XSS/injection (cf. sonar S5131 corrigé en #140).

### Cycle de vie du token

1. Admin clique "Copy onboard link" → JS appelle `POST /api/v1/keys/onboard`
2. Si un token `onboarding` existe pour ce projet → révoqué. Nouveau token créé (`key_type='onboarding'`, scope `write`).
3. L'URL copiée contient : `https://host/onboard/cat/<id>/project/<id>?token=kb_...`
4. L'agent ouvre l'URL → voit le `.ken` complet pré-rempli → `pip install kenboard`, crée le `.ken`, `ken list`
5. Au premier appel API réussi avec le token → middleware mute `onboarding` → `onboarded`
6. Le prochain clic sur le bouton crée un nouveau token (l'ancien est `onboarded`, pas de doublon)

### Garde-fous

- 269 tests verts, `pdm run check` OK
- Migration `0014` requise sur web2 (`kenboard migrate`)
- Le token onboarding a le scope `write` (pas `admin`) : l'agent peut lire/écrire des tâches mais pas gérer les users/keys/categories
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-24.md)
