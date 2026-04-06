-- name: get_all
-- Get all projects ordered by position.
SELECT id, cat_id, name, acronym, status, position
FROM projects
ORDER BY position;

-- name: get_by_cat
-- Get projects for a category ordered by position.
SELECT id, cat_id, name, acronym, status, position
FROM projects
WHERE cat_id = :cat_id
ORDER BY position;

-- name: get_by_id^
-- Get a single project by id.
SELECT id, cat_id, name, acronym, status, position
FROM projects
WHERE id = :id;

-- name: create!
-- Create a new project.
INSERT INTO projects (id, cat_id, name, acronym, status, position)
VALUES (:id, :cat_id, :name, :acronym, :status, :position);

-- name: update!
-- Update a project.
UPDATE projects
SET name = :name, acronym = :acronym, cat_id = :cat_id, status = :status
WHERE id = :id;

-- name: delete!
-- Delete a project.
DELETE FROM projects
WHERE id = :id;

-- name: update_position!
-- Update a project's position.
UPDATE projects
SET position = :position
WHERE id = :id;

-- name: max_position_in_cat$
-- Get the maximum position in a category.
SELECT COALESCE(MAX(position), -1) FROM projects WHERE cat_id = :cat_id;

-- name: count_tasks$
-- Count tasks in a project.
SELECT COUNT(*) FROM tasks WHERE project_id = :project_id;
