-- Create api_keys table
-- depends: 0004.create_users

CREATE TABLE api_keys (
    id              VARCHAR(36) NOT NULL PRIMARY KEY,
    key_hash        CHAR(64)    NOT NULL UNIQUE,
    label           VARCHAR(100) NOT NULL,
    expires_at      DATETIME    NULL,
    last_used_at    DATETIME    NULL,
    revoked_at      DATETIME    NULL,
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_key_hash (key_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
