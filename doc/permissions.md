# Permissions

Kenboard has a **dual permission model** (#197):

| Caller type | Granularity | Storage |
|---|---|---|
| **Humans** (cookie session) | Category — "board" in the UI | `user_category_scopes` |
| **API keys** (bearer token) | Project | `api_key_projects` |

Humans are granted access to whole boards (categories), which
transitively covers every project and task inside. API keys are scoped
narrowly to a single project so that a leaked token has the smallest
possible blast radius.

## Scopes

Both tables use a `scope` column that is one of:

- `read` — GET access only
- `write` — GET + POST/PATCH/DELETE

`write` implies `read`. API keys additionally accept an `admin` scope
used by the onboarding tokens, which has no equivalent on the human
side (admin humans are flagged with `users.is_admin = 1` instead).

## Admin bypass

A user with `is_admin = 1` ignores `user_category_scopes` entirely and
has full access to every board. This is the canonical way to make
someone a board-admin for the whole instance — the scope table is only
consulted for non-admin users.

## How admins assign scopes

Open `/admin/users` and use the **Accès boards** column:

- Each user has a row of badges `[Category: scope]`, colour-matched to
  the category.
- Click a badge to change its scope (read/write) or remove it.
- Click `+ Ajouter` to grant access to a category the user is not yet
  scoped on.

Every action calls `PUT /api/v1/users/<id>/scopes` with the full
replacement scope list, inside a single transaction (clear + add).

For admin users the column displays *"admin — tous les boards"* and
cannot be edited: flip `is_admin` off first if you need to scope them
per-board.

## Default-closed policy

After applying migration `0015.create_user_category_scopes.sql`, every
**non-admin** user starts with **no scopes at all** — the `/` index and
category pages will be empty until an admin assigns them boards.

This is intentional (least privilege). Two knobs exist for
administrators who need to restore the legacy "everyone sees
everything" behaviour:

### `kenboard grant-legacy-read`

Grants `read` on every existing category to every non-admin user.
Idempotent (`INSERT IGNORE`), so running it twice is safe.

```sh
kenboard grant-legacy-read        # interactive confirmation
kenboard grant-legacy-read --yes  # scripted use
```

Use this **once** during the upgrade to 0.1.60+ on deployments that
previously ran with no user-level permissions and don't want to
disrupt users.

### Manual per-user grants

Run a SQL statement such as:

```sql
INSERT INTO user_category_scopes (user_id, category_id, scope)
VALUES ('<user-uuid>', '<category-uuid>', 'write');
```

Then the user regains access on their next request (scopes are read
per-request, not cached).

## API reference

### `GET /api/v1/users`

Returns every user including their `scopes` array. Admin only.

### `PUT /api/v1/users/<id>/scopes`

```json
{
  "scopes": [
    {"category_id": "uuid-of-cat-a", "scope": "read"},
    {"category_id": "uuid-of-cat-b", "scope": "write"}
  ]
}
```

The list **replaces** the user's current scopes atomically. Pass an
empty array to revoke everything. Admin only.

## Enforcement details

Two code paths enforce scopes independently:

- **Cookie sessions**: `dashboard.auth_user.current_user_can()` and
  `current_user_can_project()` — called from the route handlers for
  categories, projects, tasks, and the pages blueprint.
- **API keys**: `dashboard.auth._project_scope_for_key()` — called
  from the global `before_request` middleware.

A bearer-token caller always bypasses the cookie-session scope check
(it was already scoped earlier in the middleware) so there is no
double-gating.

## Related

- `ADMIN_ONLY_PREFIXES` in `dashboard/auth.py` — endpoints that stay
  admin-only regardless of scopes (users, keys, category
  creation/deletion, reorder).
- `api_admin_required()` — helper used in routes that must remain
  admin-only but live under a prefix that accepts non-admins for other
  methods (e.g. `POST /api/v1/categories`).
