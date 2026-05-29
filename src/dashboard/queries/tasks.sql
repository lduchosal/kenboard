-- name: task_get_by_project
-- Get tasks for a project ordered by position.
SELECT id, project_id, title, description, status, who, due_date, position,
       created_at, updated_at
FROM tasks
WHERE project_id = :project_id
ORDER BY position ASC;

-- name: task_get_by_category
-- Get every task in every project of a category, ordered by project then
-- position. Consumed by the category page to avoid the N+1 fan-out of
-- calling ``task_get_by_project`` once per project (#338). The caller
-- groups by ``project_id`` in Python.
SELECT t.id, t.project_id, t.title, t.description, t.status, t.who,
       t.due_date, t.position, t.created_at, t.updated_at
FROM tasks t
JOIN projects p ON p.id = t.project_id
WHERE p.cat_id = :category_id
ORDER BY t.project_id ASC, t.position ASC;

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

-- name: task_find_open_by_title^
-- Find an open (not done) task with an exact title in a project, or NULL.
-- Used to dedup auto-filed error tasks so a recurring 500 doesn't spam the
-- board (#517).
SELECT id FROM tasks
WHERE project_id = :project_id AND title = :title AND status != 'done'
LIMIT 1;

-- name: task_counts_by_project
-- Get total and done counts per project in one query (#226).
SELECT project_id,
       COUNT(*) AS total,
       SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done
FROM tasks
GROUP BY project_id;

-- name: task_get_all_doing
-- Get all doing tasks across all projects (#226).
SELECT id, project_id, title, description, status, who, due_date, position,
       created_at, updated_at
FROM tasks
WHERE status = 'doing'
ORDER BY position ASC;
