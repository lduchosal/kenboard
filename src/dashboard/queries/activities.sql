-- Activity log queries (#261). Every task mutation appends one row; the
-- home page aggregates by day to show overall engagement velocity.

-- name: activity_log!
-- Append one activity row. ``details`` is optional JSON (e.g. a move's
-- from/to status).
INSERT INTO activities (project_id, user_name, action, target_type, target_id, details)
VALUES (:project_id, :user_name, :action, :target_type, :target_id, :details);


-- name: activity_daily_counts
-- Aggregate activity counts by day across all boards over the last :days
-- days. Returns one row per (day, action) so the renderer can either
-- stack-by-action or sum into a single line. Days with zero activity are
-- not returned — the consumer fills the gap.
SELECT DATE(occurred_at) AS day,
       action,
       COUNT(*)            AS count
FROM activities
WHERE occurred_at >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
GROUP BY DATE(occurred_at), action
ORDER BY day ASC, action ASC;


-- name: activity_daily_total
-- Same as ``activity_daily_counts`` but a single sum per day. Cheaper to
-- consume from the home page when the action breakdown isn't displayed.
SELECT DATE(occurred_at) AS day,
       COUNT(*)            AS count
FROM activities
WHERE occurred_at >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
GROUP BY DATE(occurred_at)
ORDER BY day ASC;


-- name: activity_count_by_user
-- Activity count per raw principal since :since (#492). The caller resolves
-- each ``user_name`` to a person (token owner or session user), sums, and
-- ranks them for the home-page "biggest ken tasker" leaderboard.
SELECT user_name,
       COUNT(*) AS count
FROM activities
WHERE occurred_at >= :since
GROUP BY user_name;


-- name: activity_recent_by_project
-- Last :limit activities for a single project, newest first. Reserved for
-- a future per-project activity log; not consumed by the home page yet.
SELECT id, occurred_at, user_name, action, target_type, target_id, details
FROM activities
WHERE project_id = :project_id
ORDER BY occurred_at DESC
LIMIT :limit;
