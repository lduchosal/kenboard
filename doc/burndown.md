# Burndown chart

The burndown chart (#206) shows the trend of remaining tasks (todo +
doing + review) over the last 60 days for each category and project.

## Architecture

### Data collection

A **daily snapshot** is stored in the `burndown_snapshots` table. Each
row records the task counts per status for one project on one date:

| Column | Type | Description |
|---|---|---|
| snapshot_date | DATE | Day the snapshot was taken |
| project_id | VARCHAR(36) | FK to `projects.id` |
| todo | INT | Tasks in "todo" at snapshot time |
| doing | INT | Tasks in "doing" |
| review | INT | Tasks in "review" |
| done | INT | Tasks in "done" |

The `(snapshot_date, project_id)` pair is unique. Running the snapshot
command twice on the same day overwrites (upsert via `ON DUPLICATE KEY
UPDATE`).

### Collection command

```sh
kenboard snapshot
```

Iterates all projects, counts tasks per status, and upserts one row
per project at today's date. Designed for a nightly cron:

```
0 2 * * * /usr/local/bin/kenboard snapshot
```

No daemon, no background process — consistent with kenboard's
architecture.

### Why not reconstruct from task timestamps?

The `tasks.updated_at` column is bumped by **any** edit (title,
description, assignee), not just status changes. There is no status
history table. Inferring "when did this task become done" from
`updated_at` is unreliable and would produce incorrect burndowns.

Daily snapshots are simple, accurate, and support any future metric
(velocity, lead time, cycle time) without schema changes.

## Rendering

The burndown is an **SVG polyline** rendered server-side by Jinja:

- **Y axis**: remaining tasks (todo + doing + review)
- **X axis**: one point per snapshot_date
- **Fill**: semi-transparent area under the curve
- **Stroke**: category color

No JavaScript chart library (Chart.js, D3, etc.) — consistent with
the "no JS build step" constraint.

### Where it appears

| Page | Content |
|---|---|
| Index (`/`) | One mini burndown per category card (aggregated across projects) |
| Category (`/cat/<id>.html`) | One burndown per project (above the kanban) |

### When there's not enough data

If fewer than 2 snapshots exist for a category/project, the chart is
replaced with the message *"Pas encore de données"*. The burndown
becomes useful after 2+ days of `kenboard snapshot` runs.

## No data retention / purge

Snapshots are kept indefinitely. At ~100 bytes per row, a deployment
with 10 projects accumulates ~365 KB/year — negligible. If retention
ever becomes a concern, a `DELETE WHERE snapshot_date < ...` is safe
(the chart simply shows a shorter history).

## Related

- Migration: `0016.create_burndown_snapshots.sql`
- Queries: `queries/burndown.sql`
- CLI: `cli.py` → `kenboard snapshot`
- Template: `templates/partials/burndown.html`
- CSS: `static/style.css` → `.burndown-svg`
