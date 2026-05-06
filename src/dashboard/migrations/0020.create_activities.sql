-- Create activities table for per-project event logging (#261).
-- Every task mutation (create / save / move / delete) is appended as one
-- row, indexed by project + day so the home-page activity line graph can
-- aggregate daily counts without scanning the full table.
-- depends: 0019.create_email_verification_tokens

-- 1. Create the table if missing.
SET @tbl_exists := (
    SELECT COUNT(*) FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'activities'
);

SET @stmt := IF(
    @tbl_exists = 0,
    'CREATE TABLE activities (
        id            BIGINT AUTO_INCREMENT PRIMARY KEY,
        occurred_at   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
        project_id    VARCHAR(36)    NOT NULL,
        user_name     VARCHAR(100)   NOT NULL DEFAULT '''',
        action        ENUM(''create'', ''save'', ''move'', ''delete'') NOT NULL,
        target_type   VARCHAR(20)    NOT NULL DEFAULT ''task'',
        target_id     VARCHAR(36)    NOT NULL,
        details       JSON           NULL,
        INDEX idx_activities_project_date (project_id, occurred_at),
        INDEX idx_activities_date (occurred_at),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
