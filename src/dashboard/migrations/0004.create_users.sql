-- Create users table
-- depends: 0003.create_tasks

CREATE TABLE users (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    color VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL DEFAULT '',
    is_admin TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO users (id, name, color, password_hash, is_admin) VALUES
    (UUID(), 'Q',      '#0969da', '', 1),
    (UUID(), 'Alice',  '#8250df', '', 0),
    (UUID(), 'Bob',    '#bf8700', '', 0),
    (UUID(), 'Claire', '#1a7f37', '', 0);
