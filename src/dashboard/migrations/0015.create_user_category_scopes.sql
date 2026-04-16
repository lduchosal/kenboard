-- Create user_category_scopes junction table for per-board user permissions.
-- #197 — humans get category-level access (read/write) mirroring the
-- project-level api_key_projects table. Cookie-session enforcement only;
-- API keys keep their existing project-level scopes untouched.
-- depends: 0014.add_api_key_type

-- 1. Create the table if missing.
SET @tbl_exists := (
    SELECT COUNT(*) FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_category_scopes'
);

SET @stmt := IF(
    @tbl_exists = 0,
    'CREATE TABLE user_category_scopes (
        user_id      VARCHAR(36)            NOT NULL,
        category_id  VARCHAR(36)            NOT NULL,
        scope        ENUM(''read'',''write'') NOT NULL,
        created_at   DATETIME               NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, category_id),
        FOREIGN KEY (user_id)     REFERENCES users(id)      ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
-- Intentional no-op: per CLAUDE.md rule #5, destructive rollback blocks in
-- the same file run on forward apply in some yoyo parser paths. If a real
-- rollback is ever needed, write it as a separate forward migration.
SELECT 1;
