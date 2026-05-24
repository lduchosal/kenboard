-- Create task_wiki_classifications for the ken wiki feature (#376).
-- One row per task: assigns the task to a section of the project wiki
-- (e.g. "backend/api", "frontend/ui"). Storage is separate from the
-- ``tasks`` table because grooming is a distinct concern (who did it,
-- when, what section) and benefits from its own audit trail.
-- depends: 0020.create_activities

-- 1. Create the table if missing.
SET @tbl_exists := (
    SELECT COUNT(*) FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'task_wiki_classifications'
);

SET @stmt := IF(
    @tbl_exists = 0,
    'CREATE TABLE task_wiki_classifications (
        id              INT          AUTO_INCREMENT PRIMARY KEY,
        task_id         INT          NOT NULL,
        section_path    VARCHAR(255) NOT NULL,
        classified_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        classified_by   VARCHAR(100) NOT NULL DEFAULT '''',
        UNIQUE KEY uq_task (task_id),
        INDEX idx_section (section_path),
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
