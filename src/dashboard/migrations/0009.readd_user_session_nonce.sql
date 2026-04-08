-- Recovery: ensure users.session_nonce exists. 0008 was recorded as applied
-- by yoyo but the column was missing on at least one DB (likely a manual
-- rollback between dev runs — yoyo only hashes the migration_id, not the
-- file contents, so it never re-runs an already-recorded migration).
-- This migration is idempotent: a no-op where the column already exists.
-- depends: 0008.add_user_session_nonce

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'session_nonce'
);

SET @stmt := IF(
    @col_exists = 0,
    'ALTER TABLE users ADD COLUMN session_nonce CHAR(32) NOT NULL DEFAULT '''''
    ,
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
-- intentional no-op: this is a recovery migration, the column itself is
-- owned by 0008.
SELECT 1;
