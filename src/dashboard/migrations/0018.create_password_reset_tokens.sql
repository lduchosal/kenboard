-- Password reset tokens (#231). Short-lived, single-use tokens sent by
-- email so users can reset a forgotten password.
--
-- Idempotent: checks INFORMATION_SCHEMA before creating.
-- depends: 0017.add_api_key_usage_metadata

SET @tbl_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'password_reset_tokens'
);

SET @sql = IF(@tbl_exists = 0,
    'CREATE TABLE password_reset_tokens (
        id VARCHAR(36) NOT NULL PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        token_hash CHAR(64) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL,
        used_at DATETIME NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_prt_token_hash (token_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
    'DO 0'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
