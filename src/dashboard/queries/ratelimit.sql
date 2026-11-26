-- name: rl_hit!
-- Count one request of ``client`` in the current window of ``bucket`` (#1250).
-- Atomic: concurrent workers increment the same row.
INSERT INTO rate_limit_hits (bucket, client, window_start, expires_at, hits)
VALUES (:bucket, :client, :window_start, :expires_at, 1)
ON DUPLICATE KEY UPDATE hits = hits + 1;

-- name: rl_hits$
-- Requests counted so far in this window (read right after rl_hit).
SELECT hits FROM rate_limit_hits
WHERE bucket = :bucket AND client = :client AND window_start = :window_start;

-- name: rl_refund!
-- Give one request back: rejected (429) or not deducted (e.g. a successful login).
UPDATE rate_limit_hits
SET hits = IF(hits > 0, hits - 1, 0)
WHERE bucket = :bucket AND client = :client AND window_start = :window_start;

-- name: rl_purge!
-- Drop counters of windows that are over (bounded batch, run on new windows).
DELETE FROM rate_limit_hits WHERE expires_at <= :now LIMIT 1000;

-- name: rl_reset!
-- Forget every counter (tests, or an admin clearing a lock-out).
DELETE FROM rate_limit_hits;
