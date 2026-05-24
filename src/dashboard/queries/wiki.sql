-- Wiki classification queries (#376). Maps each task to a section path
-- declared in the project's ``ARCHITECTURE.md`` frontmatter. Consumed by
-- ``ken wiki groom`` (interactive classification) and ``ken wiki sync``
-- (export to the structured MD tree).

-- name: wiki_classify!
-- Upsert the classification for a single task. The (task_id) UNIQUE key
-- means a re-classify overwrites the prior section + bumps classified_at
-- + records the new actor.
INSERT INTO task_wiki_classifications (task_id, section_path, classified_by)
VALUES (:task_id, :section_path, :classified_by)
ON DUPLICATE KEY UPDATE
    section_path = VALUES(section_path),
    classified_by = VALUES(classified_by),
    classified_at = CURRENT_TIMESTAMP;


-- name: wiki_clear!
-- Drop the classification for a task (operator wants to re-groom from
-- scratch after an ARCHITECTURE.md refactor).
DELETE FROM task_wiki_classifications WHERE task_id = :task_id;


-- name: wiki_get_for_task^
-- Return the classification row for a single task or NULL if unclassified.
SELECT id, task_id, section_path, classified_at, classified_by
FROM task_wiki_classifications
WHERE task_id = :task_id;


-- name: wiki_get_all
-- Every classification row, joined with the task title for downstream
-- convenience (sync writes ``<id> - <title>.md`` filenames).
SELECT c.task_id, c.section_path, c.classified_at, c.classified_by,
       t.title, t.description, t.status, t.who, t.project_id
FROM task_wiki_classifications c
JOIN tasks t ON t.id = c.task_id
ORDER BY c.section_path ASC, c.task_id ASC;


-- name: wiki_get_unclassified_tasks
-- Tasks that have no row in task_wiki_classifications. Consumed by
-- ``ken wiki groom`` so the agent knows what's left to triage. Ordered
-- by id ASC so the queue is stable across runs.
SELECT t.id, t.title, t.status, t.who, t.project_id
FROM tasks t
LEFT JOIN task_wiki_classifications c ON c.task_id = t.id
WHERE c.id IS NULL
ORDER BY t.id ASC;
