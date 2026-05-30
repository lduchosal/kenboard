-- Add tasks.attachement to store an SVG annotation layer pushed by the
-- paintbrush extension (#541). MEDIUMTEXT (16 MB) is comfortable for an
-- annotations-only SVG (rectangles + texts, transparent) — the full page
-- snapshot is **not** stored here (decision (b) on the epic). NULL =
-- task has no attachment.
--
-- Idempotent ADD COLUMN with the canonical PREPARE/EXECUTE pattern; the
-- rollback is a no-op because dropping the column would lose annotation
-- SVGs. If a real rollback is ever needed, ship it as a separate forward
-- migration.
-- depends: 0021.create_task_wiki_classifications

SET @col_exists := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'tasks'
      AND COLUMN_NAME = 'attachement'
);

SET @stmt := IF(
    @col_exists = 0,
    'ALTER TABLE tasks ADD COLUMN attachement MEDIUMTEXT NULL',
    'DO 0'
);

PREPARE stmt FROM @stmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- rollback
-- intentional no-op: narrowing/dropping this column would destroy
-- annotation SVGs. Use a separate forward migration if downgrade needed.
SELECT 1;
