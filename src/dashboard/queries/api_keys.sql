-- name: key_get_all
-- Get all api_keys (without project scopes) ordered by created_at desc.
SELECT id, user_id, key_hash, label, expires_at, last_used_at, revoked_at, created_at
FROM api_keys
ORDER BY created_at DESC;

-- name: key_get_by_id^
-- Get a single api_key by id.
SELECT id, user_id, key_hash, label, expires_at, last_used_at, revoked_at, created_at
FROM api_keys
WHERE id = :id;

-- name: key_get_by_hash^
-- Lookup an api_key by its sha256 hash, used by the auth middleware.
-- Returns the row only if not revoked and not expired.
SELECT id, user_id, key_hash, label, expires_at, last_used_at, revoked_at, created_at
FROM api_keys
WHERE key_hash = :key_hash
  AND revoked_at IS NULL
  AND (expires_at IS NULL OR expires_at > NOW());

-- name: key_create!
-- Create a new api_key.
INSERT INTO api_keys (id, user_id, key_hash, label, expires_at)
VALUES (:id, :user_id, :key_hash, :label, :expires_at);

-- name: key_update_label_expiry!
-- Update label, expires_at and/or owning user of an api_key.
UPDATE api_keys
SET label = :label, expires_at = :expires_at, user_id = :user_id
WHERE id = :id;

-- name: key_revoke!
-- Mark an api_key as revoked (sets revoked_at = NOW()).
UPDATE api_keys
SET revoked_at = NOW()
WHERE id = :id;

-- name: key_delete!
-- Hard-delete an api_key (cascade removes its scopes).
DELETE FROM api_keys
WHERE id = :id;

-- name: key_touch_last_used!
-- Update last_used_at to NOW for a given api_key.
UPDATE api_keys
SET last_used_at = NOW()
WHERE id = :id;

-- name: key_scopes_get
-- Get all (project_id, scope) for a given api_key.
SELECT project_id, scope
FROM api_key_projects
WHERE api_key_id = :api_key_id;

-- name: key_scopes_get_for_project^
-- Get the scope an api_key has on a specific project, or NULL if none.
SELECT scope
FROM api_key_projects
WHERE api_key_id = :api_key_id AND project_id = :project_id;

-- name: key_scopes_clear!
-- Remove all scopes for an api_key (used before reinserting on update).
DELETE FROM api_key_projects
WHERE api_key_id = :api_key_id;

-- name: key_scopes_add!
-- Insert one (api_key_id, project_id, scope) row.
INSERT INTO api_key_projects (api_key_id, project_id, scope)
VALUES (:api_key_id, :project_id, :scope);
