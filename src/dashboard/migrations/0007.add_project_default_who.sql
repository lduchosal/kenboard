-- Add default user (text who) to projects
-- depends: 0006.create_api_key_projects

ALTER TABLE projects
    ADD COLUMN default_who VARCHAR(100) NOT NULL DEFAULT '';
