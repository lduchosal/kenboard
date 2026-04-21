-- name: prt_create!
-- Create a password reset token.
INSERT INTO password_reset_tokens (id, user_id, token_hash, expires_at)
VALUES (:id, :user_id, :token_hash, :expires_at);

-- name: prt_get_by_hash^
-- Look up a valid (not used, not expired) token by its SHA256 hash.
SELECT id, user_id, token_hash, created_at, expires_at, used_at
FROM password_reset_tokens
WHERE token_hash = :token_hash
  AND used_at IS NULL
  AND expires_at > NOW();

-- name: prt_mark_used!
-- Mark a token as used (single-use).
UPDATE password_reset_tokens
SET used_at = NOW()
WHERE id = :id;

-- name: prt_cleanup!
-- Delete expired or used tokens older than 24 hours.
DELETE FROM password_reset_tokens
WHERE used_at IS NOT NULL
   OR expires_at < NOW() - INTERVAL 1 DAY;
