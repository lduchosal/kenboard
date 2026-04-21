-- name: evt_create!
-- Create an email verification token with the pending password hash.
INSERT INTO email_verification_tokens (id, email, password_hash, token_hash, expires_at)
VALUES (:id, :email, :password_hash, :token_hash, :expires_at);

-- name: evt_get_by_hash^
-- Look up a valid (not used, not expired) token by its SHA256 hash.
SELECT id, email, password_hash, token_hash, created_at, expires_at, used_at
FROM email_verification_tokens
WHERE token_hash = :token_hash
  AND used_at IS NULL
  AND expires_at > NOW();

-- name: evt_mark_used!
-- Mark a token as used (single-use).
UPDATE email_verification_tokens
SET used_at = NOW()
WHERE id = :id;

-- name: evt_cleanup!
-- Delete expired or used tokens older than 48 hours.
DELETE FROM email_verification_tokens
WHERE used_at IS NOT NULL
   OR expires_at < NOW() - INTERVAL 2 DAY;
