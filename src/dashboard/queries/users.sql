-- name: usr_get_all
-- Get all users ordered by name.
SELECT id, name, color, is_admin, created_at, updated_at
FROM users
ORDER BY name;

-- name: usr_get_by_id^
-- Get a single user by id.
SELECT id, name, color, is_admin, created_at, updated_at
FROM users
WHERE id = :id;

-- name: usr_get_by_name^
-- Get a single user by name (used for authentication).
SELECT id, name, color, password_hash, is_admin, created_at, updated_at
FROM users
WHERE name = :name;

-- name: usr_create!
-- Create a new user.
INSERT INTO users (id, name, color, password_hash, is_admin)
VALUES (:id, :name, :color, :password_hash, :is_admin);

-- name: usr_update!
-- Update a user's name, color and admin flag.
UPDATE users
SET name = :name, color = :color, is_admin = :is_admin
WHERE id = :id;

-- name: usr_update_password!
-- Update a user's password hash.
UPDATE users
SET password_hash = :password_hash
WHERE id = :id;

-- name: usr_delete!
-- Delete a user.
DELETE FROM users
WHERE id = :id;
