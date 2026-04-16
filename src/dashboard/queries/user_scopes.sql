-- name: usr_scopes_get
-- Get all (category_id, scope) pairs for a user.
SELECT category_id, scope
FROM user_category_scopes
WHERE user_id = :user_id;

-- name: usr_scopes_get_for_category^
-- Get the scope a user has on a specific category, or NULL if none.
SELECT scope
FROM user_category_scopes
WHERE user_id = :user_id AND category_id = :category_id;

-- name: usr_scopes_get_for_project^
-- Get the scope a user has on the category that owns a given project.
SELECT s.scope
FROM user_category_scopes s
JOIN projects p ON p.cat_id = s.category_id
WHERE s.user_id = :user_id AND p.id = :project_id;

-- name: usr_scopes_clear!
-- Remove all scopes for a user (used before reinserting on update).
DELETE FROM user_category_scopes
WHERE user_id = :user_id;

-- name: usr_scopes_add!
-- Insert one (user_id, category_id, scope) row.
INSERT INTO user_category_scopes (user_id, category_id, scope)
VALUES (:user_id, :category_id, :scope);

-- name: cat_list_for_user
-- Categories a user has any scope on, ordered like cat_get_all.
SELECT c.*
FROM categories c
JOIN user_category_scopes s ON s.category_id = c.id
WHERE s.user_id = :user_id
ORDER BY c.position, c.name;

-- name: proj_list_for_user
-- Projects belonging to categories the user has any scope on.
SELECT p.*
FROM projects p
JOIN user_category_scopes s ON s.category_id = p.cat_id
WHERE s.user_id = :user_id
ORDER BY p.position, p.name;

-- name: usr_grant_all_categories_read!
-- Opt-in helper: grant 'read' on every existing category to every
-- non-admin user. Idempotent via INSERT IGNORE. Used by the one-shot
-- `kenboard grant-legacy-read` CLI for deployments migrating from the
-- pre-permissions version.
INSERT IGNORE INTO user_category_scopes (user_id, category_id, scope)
SELECT u.id, c.id, 'read'
FROM users u CROSS JOIN categories c
WHERE u.is_admin = 0;
