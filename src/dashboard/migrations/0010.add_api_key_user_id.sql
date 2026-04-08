-- Link an api_key to its owning user (#110, traceability "qui fait quoi").
-- Nullable: legacy keys and the static admin key have no owner. ON DELETE
-- SET NULL preserves the row (audit data) when the user is removed.
--
-- Idempotent on purpose: each step checks INFORMATION_SCHEMA before running
-- so a previous half-applied attempt (column added but FK rejected for any
-- reason) can be re-run without "column already exists" looping forever.
-- Same pattern as 0009.readd_user_session_nonce.
-- depends: 0009.readd_user_session_nonce

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

-- 2. Add the FK if missing. The FK auto-creates a covering index on
-- user_id, so no explicit ADD INDEX is needed (and adding one alongside
-- caused the original loop on the multi-clause ALTER).
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
-- Best-effort: drop the FK first (auto-drops its index), then the column.
-- Both guarded by INFORMATION_SCHEMA so a partial state can still roll back.
SET @fk_exists := (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'api_keys'
      AND CONSTRAINT_NAME = 'fk_api_keys_user'
      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
);

SET @stmt := IF(
    @fk_exists = 1,
    'ALTER TABLE api_keys DROP FOREIGN KEY fk_api_keys_user',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'api_keys'
      AND COLUMN_NAME = 'user_id'
);

SET @stmt := IF(
    @col_exists = 1,
    'ALTER TABLE api_keys DROP COLUMN user_id',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
