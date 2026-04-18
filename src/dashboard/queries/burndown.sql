-- name: burndown_get_by_project
-- Snapshots for a project over the last :days days, ordered chronologically.
SELECT snapshot_date, todo, doing, review, done
FROM burndown_snapshots
WHERE project_id = :project_id
  AND snapshot_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
ORDER BY snapshot_date;

-- name: burndown_get_by_category
-- Aggregated snapshots across all projects in a category.
SELECT s.snapshot_date,
       SUM(s.todo) AS todo, SUM(s.doing) AS doing,
       SUM(s.review) AS review, SUM(s.done) AS done
FROM burndown_snapshots s
JOIN projects p ON p.id = s.project_id
WHERE p.cat_id = :category_id
  AND s.snapshot_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
GROUP BY s.snapshot_date
ORDER BY s.snapshot_date;

-- name: burndown_record_snapshot!
-- Upsert a snapshot for a project at today's date. Idempotent: running
-- multiple times on the same day updates the counters to the latest values.
INSERT INTO burndown_snapshots (snapshot_date, project_id, todo, doing, review, done)
VALUES (CURDATE(), :project_id, :todo, :doing, :review, :done)
ON DUPLICATE KEY UPDATE todo=VALUES(todo), doing=VALUES(doing),
                        review=VALUES(review), done=VALUES(done);

-- name: burndown_task_counts_by_project
-- Count tasks per status for a given project. Used by `kenboard snapshot`
-- to collect the values before upserting.
SELECT status, COUNT(*) AS cnt
FROM tasks
WHERE project_id = :project_id
GROUP BY status;
