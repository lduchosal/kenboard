-- Add session_nonce to users for server-side session invalidation (ken #54)
-- depends: 0007.add_project_default_who

ALTER TABLE users
    ADD COLUMN session_nonce CHAR(32) NOT NULL DEFAULT '';

-- rollback
ALTER TABLE users
    DROP COLUMN session_nonce;
