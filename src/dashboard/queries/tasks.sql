-- name: get_by_project
-- Get tasks for a project ordered by position.
SELECT id, project_id, title, description, status, who, due_date, position,
       created_at, updated_at
FROM tasks
WHERE project_id = :project_id
ORDER BY position;

-- name: get_by_id^
-- Get a single task by id.
SELECT id, project_id, title, description, status, who, due_date, position,
       created_at, updated_at
FROM tasks
WHERE id = :id;

-- name: create<!
-- Create a new task and return its id.
INSERT INTO tasks (project_id, title, description, status, who, due_date, position)
VALUES (:project_id, :title, :description, :status, :who, :due_date, :position);

-- name: update!
-- Update a task.
UPDATE tasks
SET title = :title, description = :description, status = :status,
    who = :who, due_date = :due_date
WHERE id = :id;

-- name: update_status!
-- Update only the status and position of a task.
UPDATE tasks
SET status = :status, position = :position
WHERE id = :id;

-- name: delete!
-- Delete a task.
DELETE FROM tasks
WHERE id = :id;

-- name: max_position_in_project$
-- Get the maximum position in a project for a given status.
SELECT COALESCE(MAX(position), -1) FROM tasks
WHERE project_id = :project_id AND status = :status;
