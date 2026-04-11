-- Add key_type to api_keys for onboarding token lifecycle (#159).
-- NULL = regular key, 'onboarding' = pending, 'onboarded' = used.
-- Idempotent: no-op if the column already exists.
-- depends: 0013.readd_users_email

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'api_keys'
      AND COLUMN_NAME = 'key_type'
);

SET @stmt := IF(
    @col_exists = 0,
    'ALTER TABLE api_keys ADD COLUMN key_type VARCHAR(20) NULL AFTER user_id',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
