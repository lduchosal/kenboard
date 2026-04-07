-- Create api_key_projects junction table
-- depends: 0005.create_api_keys

CREATE TABLE api_key_projects (
    api_key_id  VARCHAR(36)                  NOT NULL,
    project_id  VARCHAR(36)                  NOT NULL,
    scope       ENUM('read','write','admin') NOT NULL,
    PRIMARY KEY (api_key_id, project_id),
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
