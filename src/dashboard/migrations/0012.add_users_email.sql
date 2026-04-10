-- Add an optional email column to users for OIDC login (#126).
-- The OIDC callback uses the email claim from the id_token to look up
-- or lazy-create users. Existing password-only users keep email=NULL.
--
-- Idempotent: no-ops if the column already exists. One concern per
-- ALTER TABLE (cf. CLAUDE.md migration rules).
-- depends: 0011.readd_api_key_user_id

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

-- 2. Add a unique index if missing (email lookup must be fast and
-- prevent duplicates, but NULLs are allowed for legacy users).
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
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'email'
);

SET @stmt := IF(
    @col_exists > 0,
    'ALTER TABLE users DROP COLUMN email',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
