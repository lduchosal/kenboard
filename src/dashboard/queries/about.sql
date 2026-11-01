-- name: about_db_server^
-- Server version and current schema, shown on the admin part of /about (#1165).
SELECT VERSION() AS version, DATABASE() AS name;

-- name: about_migrations^
-- Applied yoyo migrations: count and most recent one (#1165).
SELECT COUNT(*) AS applied,
       MAX(migration_id) AS last_id,
       MAX(applied_at_utc) AS last_applied_at
FROM _yoyo_migration;
