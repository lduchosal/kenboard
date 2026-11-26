-- Create rate_limit_hits: per-IP request counters shared by every gunicorn
-- worker (ken #1250, replaces flask-limiter's per-process memory storage).
-- One row per (bucket, client, fixed window); ``bucket`` names the view and
-- the limit (e.g. ``dashboard.auth_login.login_post:5/60``), ``client`` is
-- the caller IP. ``expires_at`` (epoch seconds) drives the purge of past
-- windows.
-- depends: 0022.add_task_attachement

-- 1. Create the table if missing.
SET @tbl_exists := (
    SELECT COUNT(*) FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'rate_limit_hits'
);

SET @stmt := IF(
    @tbl_exists = 0,
    'CREATE TABLE rate_limit_hits (
        bucket        VARCHAR(160) NOT NULL,
        client        VARCHAR(64)  NOT NULL,
        window_start  INT UNSIGNED NOT NULL,
        expires_at    INT UNSIGNED NOT NULL,
        hits          INT UNSIGNED NOT NULL DEFAULT 0,
        PRIMARY KEY (bucket, client, window_start),
        INDEX idx_rate_limit_expires (expires_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
