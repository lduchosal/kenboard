-- name: task_get_by_project
-- Get tasks for a project ordered by position.
SELECT id, project_id, title, description, status, who, due_date, position,
       created_at, updated_at
FROM tasks
WHERE project_id = :project_id
ORDER BY position ASC;

-- name: task_get_by_id^
-- Get a single task by id.
SELECT id, project_id, title, description, status, who, due_date, position,
       created_at, updated_at
FROM tasks
WHERE id = :id;

-- name: task_create!
-- Create a new task.
INSERT INTO tasks (project_id, title, description, status, who, due_date, position)
VALUES (:project_id, :title, :description, :status, :who, :due_date, :position);

-- name: task_update!
-- Update a task.
UPDATE tasks
SET title = :title, description = :description, status = :status,
    who = :who, due_date = :due_date
WHERE id = :id;

-- name: task_update_status!
-- Update only the status and position of a task.
UPDATE tasks
SET status = :status, position = :position
WHERE id = :id;

-- name: task_move!
-- Move a task to a different project, status, and position.
UPDATE tasks
SET project_id = :project_id, status = :status, position = :position
WHERE id = :id;

-- name: task_delete!
-- Delete a task.
DELETE FROM tasks
WHERE id = :id;

-- name: task_max_position$
-- Get the maximum position in a project for a given status.
SELECT COALESCE(MAX(position), -1) FROM tasks
WHERE project_id = :project_id AND status = :status;
