# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Project

**kenboard** — Flask + MySQL kanban / project-management dashboard. Published on
PyPI as `kenboard`. Internal package name is still `dashboard`.

Two console entry points (`pyproject.toml`):

- `kenboard` → `dashboard.cli:cli` — admin commands (`serve`, `build`,
  `migrate`, `migrate-test`, `set-password`)
- `ken` → `dashboard.ken:cli` — task CLI used both interactively and by Claude
  to drive the board over the REST API

## Stack & architecture principles

See `doc/architecture.md` for the full picture. Hard rules from that doc:

- **No ORM.** SQL files in `src/dashboard/queries/*.sql` (loaded by `aiosql`)
  and `src/dashboard/migrations/*.sql` (run by `yoyo`) are the source of truth.
- **Pydantic v2** validates inputs/outputs only — it does *not* generate SQL.
- **PyMySQL** is the driver. `db.get_connection()` returns a dict-cursor
  connection with autocommit.
- **Flask blueprints** under `src/dashboard/routes/` (categories, projects,
  tasks, users, keys, pages). App factory is `dashboard.app:create_app`.
- **Jinja2 templates** in `src/dashboard/templates/` are rendered by Flask.
- **Frontend** is vanilla JS + SortableJS, no build step. Single `app.js`.

## Layout

```
src/dashboard/
  app.py          # Flask factory
  cli.py          # `kenboard` admin CLI (click)
  ken.py          # `ken` task CLI (click, talks to REST API via stdlib)
  config.py       # Env / .env config
  db.py           # PyMySQL connection + aiosql loader
  auth.py         # API key middleware
  auth_user.py    # Flask-Login session auth
  logging.py      # structlog setup
  models/         # Pydantic v2 models (category, project, task, user, api_key)
  queries/        # *.sql consumed by aiosql
  migrations/     # *.sql consumed by yoyo (numbered, with `-- rollback`)
  routes/         # Flask blueprints
  templates/      # Jinja2
  static/         # app.js, style.css, vendored sortable.min.js, marked.min.js
tests/
  unit/           # fast, no DB
  integration/    # hits dashboard_test DB
  e2e/            # Playwright browser tests
```

## Databases

Four MySQL users with least privilege (see `INSTALL.md` for the full setup):

| User | DB | Privileges |
|---|---|---|
| `dashboard` | `dashboard` | CRUD only |
| `dashboard_admin` | `dashboard` | DDL (used by `kenboard migrate`) |
| `dashboard_test` | `dashboard_test` | CRUD only |
| `dashboard_test_admin` | `dashboard_test` | DDL (used by `kenboard migrate-test`) |

Tests must never touch the production DB. Connection params come from `.env`
(see `.env.example`).

## Common commands

All managed via PDM scripts (`pyproject.toml [tool.pdm.scripts]`):

```sh
pdm run serve              # not defined — use: kenboard serve --debug
pdm run test               # pytest, excluding e2e
pdm run test-quick         # -x, fail fast
pdm run test-ci            # excludes integration + e2e
pdm run test-unit          # tests/unit only
pdm run test-integration   # tests/integration only (needs dashboard_test DB)
pdm run test-e2e           # tests/e2e (Playwright, needs running server + DB)
pdm run test-cov           # with coverage report

pdm run format             # black
pdm run isort
pdm run docformatter
pdm run lint               # ruff --fix
pdm run flake8
pdm run typecheck          # mypy (strict: disallow_untyped_defs)
pdm run interrogate        # docstring coverage (fail-under 95)
pdm run vulture
pdm run refurb

pdm run check              # composite: isort, format, docformatter, typecheck,
                           # flake8, interrogate, refurb, lint, vulture, test-quick
```

`sh publish.sh --quality` runs the full quality gate. `sh publish.sh
[--patch|--minor|--major]` bumps the version (via `pdm-bump`, version lives in
`src/dashboard/__init__.py:__version__`) and publishes to PyPI.

## Code-quality gates

- mypy is strict: `disallow_untyped_defs`, `disallow_incomplete_defs`,
  `strict_equality`. Tests are exempted.
- Coverage `fail_under = 75`.
- interrogate `fail-under = 95` — every public function/class needs a
  docstring. Init methods/modules are exempted.
- Line length **88** (black, isort) but **125** for flake8.
- Docstring convention: **google** (per `.flake8`).
- vulture min_confidence 80; whitelist lives in `vulture_whitelist.py`.

## `ken` CLI workflow

Project metadata is in `KENBOARD.md` (gitignored). Bootstrap once per repo
with `ken init <project-id>`, which writes `.ken` (mode 0600) and adds it to
`.gitignore`. Then:

```sh
ken list --who Claude --status doing   # always use native filters
ken show <id>                          # human-readable by default
ken add "Title" --desc "..." --who Claude --status todo --json
ken update <id> --status review
ken move <id> --to doing
ken done <id>
```

Statuses: `todo` | `doing` | `review` | `done`. Prefer the human-readable
output (no `--json`) for `list` and `show` — the text format is compact and
directly readable. Only add `--json` when you need to capture a value as
input to another command (e.g. `ken add --json` to get the new task ID).
The `ken` binary uses only the stdlib for HTTP — do not add
`requests`/`httpx` as a runtime dep just for it.

### Working a task off the board

When the user asks Claude to pick up a kenboard task, follow this loop:

1. `ken list --who Claude --status todo` to see the queue. Pick one,
   announce the choice and why.
2. `ken move <id> --to doing` *before* starting the implementation, so the
   board reflects WIP and other agents/humans don't grab the same card.
3. Implement. Run the relevant quality gates (`pdm run lint`, the matching
   `pdm run test-*`). If pre-existing failures show up in unrelated areas
   (e.g. WIP from another in-flight task in the working tree), confirm they
   are not caused by your changes — `git stash && pdm run test-unit && git
   stash pop` is the quick way to prove a clean baseline.
4. `ken move <id> --to review` once the work is ready for the user.
5. **Append a resolution block to the task description** with `ken update
   <id> --desc "<original>\n\n---\n\n## Résolution\n..."`. Preserve the
   original description verbatim, then add sections for *Modifications*
   (file paths + one-line summary), *Comportements obtenus*, and *Garde-fous*
   (which gates ran + their result). This is how the board accumulates an
   audit trail — the commit message alone is not enough since not every task
   maps 1:1 to a commit.

Do **not** mark a task `done` yourself; that's the user's call after review.

## When making changes

- Read the relevant `queries/*.sql` and `models/*.py` before touching a route
  — the SQL file is the contract.
- New columns require both a numbered migration (with `-- rollback`) **and**
  updates to the matching query file and Pydantic model.
- Add/refresh docstrings for any new public symbol so `interrogate` stays
  green.
- Run `pdm run check` (or at least `pdm run lint typecheck test-quick`) before
  declaring work done.
- Don't introduce an ORM, don't add a JS build step, don't bypass the
  Pydantic validation layer.

## Writing migrations (read before adding any `migrations/*.sql`)

We've been burned twice (0008 → 0009 for `session_nonce`, 0010 → 0011 for
`api_key.user_id`) by yoyo recording a migration as applied while the DDL
silently never persisted. To stop the bleeding, **all** new migrations
must follow these rules:

1. **Idempotent by construction.** Each DDL step must check
   `INFORMATION_SCHEMA.COLUMNS` / `TABLE_CONSTRAINTS` before running, and
   no-op (`DO 0`) if the change already exists. Use the
   `PREPARE`/`EXECUTE` pattern from `0009.readd_user_session_nonce.sql` or
   `0011.readd_api_key_user_id.sql` as a template — copy them, don't
   reinvent.
2. **One concern per `ALTER TABLE`.** Never combine `ADD COLUMN` +
   `ADD CONSTRAINT` + `ADD INDEX` in a single multi-clause ALTER. Split
   each into its own statement so a partial failure can be replayed
   step-by-step. Multi-clause ALTERs are the failure mode that creates
   stuck states.
3. **Let FKs auto-create their index.** Don't add an explicit
   `INDEX idx_xxx (col)` next to a `FOREIGN KEY (col)` — MySQL creates a
   covering index for the FK automatically and the redundancy is the
   kind of thing that bit us.
4. **Never edit a migration file after it has been applied anywhere.**
   yoyo hashes the `migration_id` (filename), not the file contents, so
   editing an applied migration changes *nothing* on a DB that already
   recorded it. If a previously-applied migration is broken on prod,
   add a recovery migration `00NN.readd_<thing>.sql` that `depends:` on
   the broken one and idempotently re-applies the change.
5. **Every migration needs a `-- rollback` block**, but it **MUST be a
   no-op** (`SELECT 1`). yoyo's SQL parser may fail to split at the
   `-- rollback` marker and execute the **entire file** in one pass.
   A destructive rollback (`DROP COLUMN`) after an `ADD COLUMN` in the
   same file = the column is added then immediately dropped, while yoyo
   records the migration as "applied". This is exactly what broke 0012
   (the `DROP COLUMN email` rollback fired during forward apply).
   If you need a real rollback, write it as a **separate forward
   migration** (`00NN.drop_<thing>.sql`).
6. **Mirror schema changes in `tests/conftest.py`.** The test DB is
   hand-rolled, not migrated by yoyo. Add the column to the
   `CREATE TABLE` block *and* add a back-fill `ALTER TABLE` (split into
   atomic steps) for legacy carried-over test schemas.

When in doubt, read `0011.readd_api_key_user_id.sql` end-to-end — it is
the canonical example of every rule above applied together.
