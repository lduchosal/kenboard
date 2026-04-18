-- Create burndown_snapshots table for historical task-count tracking (#206).
-- One row per (date, project) with denormalized status counters so the
-- burndown chart can show a 60-day trend without reconstructing history
-- from unreliable task timestamps.
-- depends: 0015.create_user_category_scopes

-- 1. Create the table if missing.
SET @tbl_exists := (
    SELECT COUNT(*) FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'burndown_snapshots'
);

SET @stmt := IF(
    @tbl_exists = 0,
    'CREATE TABLE burndown_snapshots (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        snapshot_date  DATE         NOT NULL,
        project_id    VARCHAR(36)  NOT NULL,
        todo          INT          NOT NULL DEFAULT 0,
        doing         INT          NOT NULL DEFAULT 0,
        review        INT          NOT NULL DEFAULT 0,
        done          INT          NOT NULL DEFAULT 0,
        UNIQUE KEY uq_snapshot (snapshot_date, project_id),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
