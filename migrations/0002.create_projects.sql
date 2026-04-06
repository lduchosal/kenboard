-- Create projects table
-- depends: 0001.create_categories

CREATE TABLE projects (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    cat_id VARCHAR(36) NOT NULL,
    name VARCHAR(250) NOT NULL,
    acronym VARCHAR(4) NOT NULL,
    status ENUM('active', 'archived') NOT NULL DEFAULT 'active',
    position INT NOT NULL DEFAULT 0,
    FOREIGN KEY (cat_id) REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- rollback
DROP TABLE IF EXISTS projects;
