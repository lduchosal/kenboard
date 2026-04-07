# API keys avec scopes par projet

Spec validée pour les tâches #6 (backend) et #7 (UI). Couvre l'auth des
clients de l'API REST `/api/v1/*` (CLI `ken`, scripts, intégrations).
L'auth web user (login form, cookie) est séparée et reste hors scope —
voir `doc/authentication.md` et la tâche #1.

## Schéma

Migrations `0005.create_api_keys.sql` + `0006.create_api_key_projects.sql`.

```sql
CREATE TABLE api_keys (
    id              VARCHAR(36) NOT NULL PRIMARY KEY,
    key_hash        CHAR(64)    NOT NULL UNIQUE,    -- sha256 hex
    label           VARCHAR(100) NOT NULL,
    expires_at      DATETIME    NULL,
    last_used_at    DATETIME    NULL,
    revoked_at      DATETIME    NULL,
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_key_hash (key_hash)
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

## Rollout — flag opt-in

Variable `KENBOARD_AUTH_ENFORCED` dans le `.env`. Par défaut `false`.

| Mode | Comportement |
|---|---|
| `false` (défaut) | Code et table en place, le middleware **ne bloque jamais**. Si une clé valide est présente, il met à jour `last_used_at`. Permet de déployer sans casser la web UI actuelle (qui parle à `/api/v1/*` sans token). |
| `true` | Mode strict : 401 si pas de header, 401 si clé invalide/révoquée/expirée, 403 si scope insuffisant. |

Le flag sera basculé à `true` quand la web UI saura s'authentifier
elle-même (cf #1, login user + cookie session). D'ici là, on peut tester
le middleware avec des clients API tout en gardant la web UI ouverte.

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `KENBOARD_ADMIN_KEY` | `""` | Clé statique passe-partout. Génère-la avec `python -c 'import secrets; print("kb_" + secrets.token_urlsafe(32))'` et stocke-la dans le vault ansible. Sans cette clé, pas moyen d'accéder aux endpoints admin (`/api/v1/keys`, `/api/v1/users`, `/api/v1/categories`, `/api/v1/projects`). |
| `KENBOARD_AUTH_ENFORCED` | `false` | Active le mode strict. |

## CRUD `/api/v1/keys`

```
POST   /api/v1/keys          {label, expires_at?, scopes:[{project_id,scope}]}
GET    /api/v1/keys           liste (sans clé en clair, jamais)
PATCH  /api/v1/keys/<id>     {label?, expires_at?, scopes?}
DELETE /api/v1/keys/<id>     revoke (set revoked_at = NOW())
```

`POST` renvoie `201` avec `{"id": ..., "key": "kb_...", "scopes": [...]}`.
La clé en clair est dans le champ `key` et n'est plus jamais renvoyée
ensuite — y compris par GET et PATCH.

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

Comme `/admin/users`, la page reste **ouverte** (pas d'auth UI) tant
que #1 (web user auth) n'est pas fait. Quand #1 arrivera, on protégera
les deux pages via le même mécanisme de session.

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

# Création de la première api_key via curl (en mode soft, avant enforce)
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
