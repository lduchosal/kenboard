-- Add last_used_ip and last_used_agent to api_keys (#209, #210).
-- Tracks the IP and User-Agent of the most recent API call for each key
-- so the admin UI can show where and from what client the key was used.
-- depends: 0016.create_burndown_snapshots

-- 1. Add last_used_ip if missing.
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'api_keys'
      AND COLUMN_NAME = 'last_used_ip'
);

SET @stmt := IF(
    @col_exists = 0,
    'ALTER TABLE api_keys ADD COLUMN last_used_ip VARCHAR(45) NULL AFTER last_used_at',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Add last_used_agent if missing.
SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'api_keys'
      AND COLUMN_NAME = 'last_used_agent'
);

SET @stmt := IF(
    @col_exists = 0,
    'ALTER TABLE api_keys ADD COLUMN last_used_agent VARCHAR(200) NULL AFTER last_used_ip',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
