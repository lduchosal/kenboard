# API keys avec scopes par projet

Spec validée pour les tâches #6 (backend) et #7 (UI). Couvre l'auth des
clients de l'API REST `/api/v1/*` (CLI `ken`, scripts, intégrations).
L'auth web user (login form, cookie) est séparée et reste hors scope —
voir `doc/authentication.md` et la tâche #1.

## Schéma

Migrations en jeu :
- `0005.create_api_keys.sql` — table principale.
- `0006.create_api_key_projects.sql` — junction scopes.
- `0010` / `0011` (recovery) — `api_keys.user_id` (#110).
- `0014.add_api_keys_key_type.sql` — `key_type` pour les tokens
  d'onboarding.
- `0017.add_api_keys_last_used_metadata.sql` — `last_used_ip` et
  `last_used_agent` (audit trail).

```sql
CREATE TABLE api_keys (
    id               VARCHAR(36)  NOT NULL PRIMARY KEY,
    user_id          VARCHAR(36)  NULL,                -- #110, propriétaire
    key_hash         CHAR(64)     NOT NULL UNIQUE,    -- sha256 hex
    key_type         VARCHAR(20)  NULL,               -- NULL | 'onboarding' | 'onboarded'
    label            VARCHAR(100) NOT NULL,
    expires_at       DATETIME     NULL,
    last_used_at     DATETIME     NULL,
    last_used_ip     VARCHAR(45)  NULL,
    last_used_agent  VARCHAR(200) NULL,
    revoked_at       DATETIME     NULL,
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_key_hash (key_hash),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE api_key_projects (
    api_key_id  VARCHAR(36)                  NOT NULL,
    project_id  VARCHAR(36)                  NOT NULL,
    scope       ENUM('read','write','admin') NOT NULL,
    PRIMARY KEY (api_key_id, project_id),
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

## Format de clé

`secrets.token_urlsafe(32)` préfixée → `kb_<43_chars>`. ≈ 256 bits
d'entropie. Stockée en DB sous forme `sha256(key).hex()` (64 chars).

**La clé en clair n'est retournée qu'une seule fois**, dans la réponse
du `POST /api/v1/keys`. Toutes les autres lectures n'exposent que les
métadonnées.

## Authentification

Header :

```
Authorization: Bearer kb_<key>
```

Le middleware (`src/dashboard/auth.py`) :

1. Lit le header. Strip `Bearer `, calcule `sha256`.
2. **Short-circuit admin** : si le bearer matche
   `Config.KENBOARD_ADMIN_KEY` (variable `.env`), tout passe.
3. Sinon, `SELECT api_keys WHERE key_hash = ? AND revoked_at IS NULL AND
   (expires_at IS NULL OR expires_at > NOW())`. Pas de match → 401.
4. Détermine le project_id de la requête (cf table ci-dessous), check
   le scope.
5. Si OK → `UPDATE last_used_at = NOW()`, continue.

### Mapping endpoint → project_id + scope requis

| Endpoint | project_id source | Scope requis |
|---|---|---|
| `GET    /api/v1/tasks?project=X` | query param `project` | `read` |
| `POST   /api/v1/tasks` | body `project_id` | `write` |
| `PATCH/DELETE /api/v1/tasks/<id>` | SELECT project_id de la task | `write` |
| `PATCH/DELETE /api/v1/projects/<id>` | URL `<id>` | `write` |
| `*      /api/v1/keys/...` | — | **admin key only** |
| `*      /api/v1/users/...` | — | **admin key only** |
| `*      /api/v1/categories/...` | — | **admin key only** |
| `GET/POST /api/v1/projects` | — | **admin key only** |

Les endpoints "admin key only" ne sont accessibles qu'avec
`KENBOARD_ADMIN_KEY` (la clé statique du `.env`). Aucune `api_key`
créée en DB ne peut y toucher, quel que soit son scope.

## Mode strict (toujours actif)

Depuis la tâche #40, le middleware est **toujours strict** :

- 401 si pas de header `Authorization`
- 401 si clé invalide / révoquée / expirée
- 403 si scope insuffisant
- 403 sur endpoint admin-only avec une clé non-admin

La web UI reste utilisable car le middleware court-circuite quand
`current_user.is_authenticated` (Flask-Login session). Les tests
contournent via `app.config["LOGIN_DISABLED"] = True`.

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `KENBOARD_ADMIN_KEY` | `""` | Clé statique passe-partout. Génère-la avec `python -c 'import secrets; print("kb_" + secrets.token_urlsafe(32))'` et stocke-la dans le vault ansible. Sans cette clé, pas moyen d'accéder aux endpoints admin (`/api/v1/keys`, `/api/v1/users`, `/api/v1/categories`, `/api/v1/projects`). |

## CRUD `/api/v1/keys`

```
POST   /api/v1/keys             {label, expires_at?, user_id?, scopes:[{project_id,scope}]}
POST   /api/v1/keys/onboard     {project_id, cat_id} — token d'onboarding pour ken init
GET    /api/v1/keys             liste (sans clé en clair, jamais)
PATCH  /api/v1/keys/<id>        {label?, expires_at?, user_id?, scopes?}
DELETE /api/v1/keys/<id>        revoke (set revoked_at = NOW())
```

`POST /api/v1/keys` est rate-limite a 10 creations / heure / IP pour
limiter le risque d'exfiltration en cas d'admin compromis.

`user_id` est facultatif (#110). Quand il est fourni, l'API vérifie que
l'utilisateur existe avant d'écrire la FK. Comme pour `expires_at`, le
PATCH applique la convention « `null` ≡ pas de changement » : pour
détacher un user d'une clé, il faut pour l'instant passer par SQL ou
créer une nouvelle clé. La suppression d'un user passe la colonne à
`NULL` via `ON DELETE SET NULL` — la clé reste mais devient orpheline.

`POST` renvoie `201` avec `{"id": ..., "key": "kb_...", "scopes": [...]}`.
La clé en clair est dans le champ `key` et n'est plus jamais renvoyée
ensuite — y compris par GET et PATCH.

### Onboarding tokens (`key_type = onboarding`)

Pour les agents AI (Claude Code, etc.), un admin clique **Copy
onboard link** sur la page d'un projet (`/admin/board`). Le serveur
appelle `POST /api/v1/keys/onboard` qui :

1. Revoque tout token `onboarding` existant pour ce projet (un seul
   actif a la fois).
2. Cree une cle `kb_<...>` avec `key_type = "onboarding"`, scope
   `write` sur le projet cible.
3. Retourne le token en clair une seule fois, encode dans le lien
   `/onboarding/<token>`.

Quand l'agent clique le lien et que le runbook est consomme, le
middleware `auth.py` promeut la cle a `key_type = "onboarded"` au
premier appel API reussi. Une cle `onboarded` n'est plus revocable
par un re-onboard accidentel ; seul `DELETE /api/v1/keys/<id>` la
revoque.

### Audit trail (`last_used_*`)

A chaque appel API authentifie par bearer, le middleware met a jour :

- `last_used_at` — timestamp UTC.
- `last_used_ip` — IP du client (extraite via les headers de proxy
  habituels).
- `last_used_agent` — User-Agent (tronque a 200 chars).

Visible dans `GET /api/v1/keys` et sur la page `/admin/keys` —
permet de detecter une cle qui n'est plus utilisee et qu'on peut
revoquer.

## Page `/admin/keys`

Template `templates/admin_keys.html`, calqué sur `admin_users.html`.

- Liste des clés avec colonnes : Label, Statut, Créée, Dernière
  utilisation, Expire, Scopes, Boutons.
- Statut calculé à l'affichage : `révoquée` (rouge) si `revoked_at`
  set, `expirée` (orange) si `expires_at < now`, `active` (vert) sinon.
- Édition inline du label, de la date d'expiration, et des scopes
  (paire `(project, level)` répétable).
- Bouton **Créer** ouvre une modale qui affiche la clé en clair une
  seule fois. La modale ferme et reload la page.
- Bouton **Révoquer** passe par le confirm-modal partagé.

Comme `/admin/users`, la page est protegee par `@admin_required` :
session Flask-Login + `is_admin = 1`. Cf. [`auth-user.md`](auth-user.md)
pour le detail du flow login.

## Tests

- **Unit** (`tests/unit/test_api_keys.py`) — 28 tests : ordre des
  scopes, hashing, CRUD `/api/v1/keys`, middleware en mode soft et
  enforced (no token, invalid, revoked, scope mismatch, wrong project,
  admin key bypass, last_used_at update).
- **E2E** (`tests/e2e/test_admin_keys.py`) — 4 tests : page vide, create
  + modale plain-text, list après reload, revoke.

## Bootstrap

Œuf et poule pour la première clé : utiliser `KENBOARD_ADMIN_KEY` (cf
`.env` rendu par ansible) comme bearer pour appeler `POST /api/v1/keys`,
puis distribuer les clés générées aux clients (CLI `ken`, scripts).

```sh
# Génération d'une clé admin (à mettre dans le vault ansible)
python -c 'import secrets; print("kb_" + secrets.token_urlsafe(32))'

# Création de la première api_key via curl (l'API est en mode strict
# permanent depuis #40 — la KENBOARD_ADMIN_KEY est obligatoire ici)
curl -X POST https://www.kenboard.2113.ch/api/v1/keys \
  -H "Authorization: Bearer $KENBOARD_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "ken-cli-claude",
    "scopes": [
      {"project_id": "76a70206-0e6a-4485-a426-d7eb5ab53aac", "scope": "write"}
    ]
  }'
```

La clé renvoyée se met dans `~/.config/ken/...` ou dans `KEN_API_TOKEN`
côté CLI ken. Le middleware acceptera cette clé pour les opérations sur
le projet KENBOARD seulement.
