-- Link an api_key to its owning user (#110, traceability "qui fait quoi").
-- Nullable: legacy keys and the static admin key have no owner. ON DELETE
-- SET NULL preserves the row (keeping last_used_at / audit data) when the
-- user is removed; admins can still revoke the orphaned key separately.
-- depends: 0009.readd_user_session_nonce

ALTER TABLE api_keys
    ADD COLUMN user_id VARCHAR(36) NULL AFTER id,
    ADD CONSTRAINT fk_api_keys_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    ADD INDEX idx_api_keys_user (user_id);

-- rollback
ALTER TABLE api_keys
    DROP FOREIGN KEY fk_api_keys_user,
    DROP INDEX idx_api_keys_user,
    DROP COLUMN user_id;
