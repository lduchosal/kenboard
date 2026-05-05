-- Test database schema. Loaded by tests/conftest.py and tests/e2e/conftest.py
-- via tests._schema.load_schema(). Hand-rolled (not run through yoyo) and must
-- mirror the production schema produced by src/dashboard/migrations/.
--
-- Extracted from inline cur.execute("""...""") blocks because docformatter
-- 1.7.x mangles function-argument triple-quoted strings (treats them as
-- docstrings, reflows them, adds PEP 257 trailing periods).
--
-- Idempotent ALTER TABLE back-fills for legacy carried-over schemas remain in
-- the Python conftests — this file only owns the green-field CREATE TABLE
-- statements.

CREATE TABLE IF NOT EXISTS categories (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(250) NOT NULL,
    color VARCHAR(50) NOT NULL,
    position INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    cat_id VARCHAR(36) NOT NULL,
    name VARCHAR(250) NOT NULL,
    acronym VARCHAR(4) NOT NULL,
    status ENUM('active', 'archived') NOT NULL DEFAULT 'active',
    position INT NOT NULL DEFAULT 0,
    default_who VARCHAR(100) NOT NULL DEFAULT '',
    FOREIGN KEY (cat_id) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tasks (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    title VARCHAR(250) NOT NULL,
    description TEXT NOT NULL DEFAULT (''),
    status ENUM('todo', 'doing', 'review', 'done') NOT NULL DEFAULT 'todo',
    who VARCHAR(100) NOT NULL DEFAULT '',
    due_date DATE NULL,
    position INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_project_status (project_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NULL,
    color VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL DEFAULT '',
    is_admin TINYINT(1) NOT NULL DEFAULT 0,
    session_nonce CHAR(32) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    user_id VARCHAR(36) NULL,
    key_type VARCHAR(20) NULL,
    key_hash CHAR(64) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    expires_at DATETIME NULL,
    last_used_at DATETIME NULL,
    last_used_ip VARCHAR(45) NULL,
    last_used_agent VARCHAR(200) NULL,
    revoked_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_key_hash (key_hash),
    CONSTRAINT fk_api_keys_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS api_key_projects (
    api_key_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL,
    scope ENUM('read','write','admin') NOT NULL,
    PRIMARY KEY (api_key_id, project_id),
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_category_scopes (
    user_id VARCHAR(36) NOT NULL,
    category_id VARCHAR(36) NOT NULL,
    scope ENUM('read','write') NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, category_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS burndown_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    project_id VARCHAR(36) NOT NULL,
    todo INT NOT NULL DEFAULT 0,
    doing INT NOT NULL DEFAULT 0,
    review INT NOT NULL DEFAULT 0,
    done INT NOT NULL DEFAULT 0,
    UNIQUE KEY uq_snapshot (snapshot_date, project_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    token_hash CHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_prt_token_hash (token_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    token_hash CHAR(64) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    INDEX idx_evt_token_hash (token_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
