-- Email verification tokens (#232). Stores the pending registration
-- (email + password_hash) until the user clicks the verification link.
--
-- Idempotent: checks INFORMATION_SCHEMA before creating.
-- depends: 0018.create_password_reset_tokens

SET @tbl_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'email_verification_tokens'
);

SET @sql = IF(@tbl_exists = 0,
    'CREATE TABLE email_verification_tokens (
        id VARCHAR(36) NOT NULL PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        token_hash CHAR(64) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL,
        used_at DATETIME NULL,
        INDEX idx_evt_token_hash (token_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
    'DO 0'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
SELECT 1;
