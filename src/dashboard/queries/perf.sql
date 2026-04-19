-- name: perf_find_open_task^
-- Find an open perf task matching a route pattern in a project.
SELECT id, title, status
FROM tasks
WHERE project_id = :project_id
  AND title LIKE :title_pattern
  AND status IN ('todo', 'doing', 'review')
LIMIT 1;
