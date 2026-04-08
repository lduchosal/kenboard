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
- **Jinja2 templates** in `src/dashboard/templates/` are shared by Flask and by
  the static `build.py` generator.
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
ken show <id> --json
ken add "Title" --desc "..." --who Claude --status todo --json
ken update <id> --status review --json
ken move <id> --to doing
ken done <id>
```

Statuses: `todo` | `doing` | `review` | `done`. Use `--json` whenever
parsing the output. The `ken` binary uses only the stdlib for HTTP — do not
add `requests`/`httpx` as a runtime dep just for it.

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
