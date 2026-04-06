-- name: get_all
-- Get all categories ordered by position.
SELECT id, name, color, position
FROM categories
ORDER BY position;

-- name: get_by_id^
-- Get a single category by id.
SELECT id, name, color, position
FROM categories
WHERE id = :id;

-- name: create!
-- Create a new category.
INSERT INTO categories (id, name, color, position)
VALUES (:id, :name, :color, :position);

-- name: update!
-- Update a category.
UPDATE categories
SET name = :name, color = :color
WHERE id = :id;

-- name: delete!
-- Delete a category.
DELETE FROM categories
WHERE id = :id;

-- name: update_position!
-- Update a category's position.
UPDATE categories
SET position = :position
WHERE id = :id;

-- name: max_position$
-- Get the maximum position value.
SELECT COALESCE(MAX(position), -1) FROM categories;
