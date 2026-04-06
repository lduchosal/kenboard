-- Create tasks table
-- depends: 0002.create_projects

CREATE TABLE tasks (
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
