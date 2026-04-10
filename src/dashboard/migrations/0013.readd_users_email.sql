-- Recovery: ensure users.email and its unique index exist. 0012 was
-- recorded as applied by yoyo but the DDL may not have persisted —
-- same failure mode as 0008→0009 (session_nonce) and 0010→0011
-- (api_key.user_id). yoyo only hashes the migration_id, not the file
-- contents, so it never re-runs an already-recorded migration.
--
-- This migration is fully idempotent: each step is a no-op where the
-- column / index already exists.
-- depends: 0012.add_users_email

-- 1. Add the column if missing.
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'email'
);

SET @stmt := IF(
    @col_exists = 0,
    'ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL AFTER name',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Add the unique index if missing.
SET @idx_exists := (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND INDEX_NAME = 'uq_users_email'
);

SET @stmt := IF(
    @idx_exists = 0,
    'ALTER TABLE users ADD UNIQUE INDEX uq_users_email (email)',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
-- Intentional no-op: the column is owned by 0012. This recovery
-- migration only ensures the change actually landed.
SELECT 1;
