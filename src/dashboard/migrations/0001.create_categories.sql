-- Create categories table
-- depends:

CREATE TABLE categories (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(250) NOT NULL,
    color VARCHAR(50) NOT NULL,
    position INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
