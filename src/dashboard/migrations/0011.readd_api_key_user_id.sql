-- Recovery: ensure api_keys.user_id and its FK to users(id) exist. 0010 was
-- recorded as applied by yoyo (2026-04-08 16:41) but the column was missing
-- on prod — same failure mode as 0008 → 0009 for users.session_nonce. yoyo
-- only hashes the migration_id, not the file contents, so it never re-runs
-- an already-recorded migration.
--
-- This migration is fully idempotent: each step is a no-op where the
-- column / FK already exists.
-- depends: 0010.add_api_key_user_id

-- 1. Add the column if missing.
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'api_keys'
      AND COLUMN_NAME = 'user_id'
);

SET @stmt := IF(
    @col_exists = 0,
    'ALTER TABLE api_keys ADD COLUMN user_id VARCHAR(36) NULL AFTER id',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Add the FK if missing. The FK auto-creates a covering index on user_id.
SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'api_keys'
      AND CONSTRAINT_NAME = 'fk_api_keys_user'
      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
);

SET @stmt := IF(
    @fk_exists = 0,
    'ALTER TABLE api_keys ADD CONSTRAINT fk_api_keys_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
-- intentional no-op: this is a recovery migration, the column itself is
-- owned by 0010.
SELECT 1;
