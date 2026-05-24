# kenboard agent guide

Best practices for an LLM agent (Claude, GPT, etc.) that manages tasks
on a kenboard project board through the `ken` CLI. This file is shipped
with the package and printed by `ken help`.

## The loop: pick → wip → review → resolution

1. **Read the queue.** List the todo tasks assigned to you and pick one
   based on its title + description. Announce the choice and the reason
   in chat *before* doing anything else:

       ken list --who <YourName> --status todo

2. **Mark it WIP before starting.** Move the chosen task to `doing` so
   the board reflects work-in-progress and other agents/humans don't
   grab the same card:

       ken move <id> --to doing

3. **Implement.** Read the relevant code, make the change, and run your
   project's quality gates (linters, type checkers, tests). If a
   pre-existing failure shows up in an unrelated area, confirm it is
   not caused by your change before proceeding.

4. **Update the task description BEFORE moving to review.** Append a
   resolution block so the board accumulates an audit trail (commit
   messages alone are not enough — not every task maps 1:1 to a commit).

   ### Passing multi-line markdown safely

   ⚠️ **Do NOT** use `--desc "line1\nline2"`. In a bash double-quoted
   string the backslash-n is **not** interpreted as a newline — it
   stores the literal two characters `\n`, which then renders as one
   broken line and corrupts every markdown block (lists, code fences,
   headings).

   **Best practice for agents: `--desc-file path/to/body.md`.** Write
   the body to a file on disk (a capability nearly every agent host
   exposes), then pass the path. No shell escaping, no heredoc tricks,
   no stdin plumbing — just two steps:

   ```sh
   # 1. Write the resolution body to a temp file
   cat > /tmp/ken-<id>.md <<'EOF'
   <original description verbatim>

   ---

   ## Résolution

   ### Modifications
   - path/to/file.py: short summary

   ### Comportements obtenus
   - what works now

   ### Garde-fous
   - pdm run check: passed
   EOF

   # 2. Hand the path to ken
   ken update <id> --desc-file /tmp/ken-<id>.md
   ```

   This is the recommended idiom because it works the same way across
   bash / zsh / sh / cmd.exe, doesn't depend on stdin redirection, and
   the temp file gives you a second chance to inspect what you're
   about to send.

   Two alternatives if you can't write a file:

   **B. Heredoc into `$(cat <<'EOF' …)`** — preserves newlines verbatim:

   ```sh
   ken update <id> --desc "$(cat <<'EOF'
   <original description verbatim>

   ---

   ## Résolution
   ...
   EOF
   )"
   ```

   **C. `--desc -` reads from stdin** — pipe a heredoc directly:

   ```sh
   ken update <id> --desc - <<'EOF'
   <description body here>
   EOF
   ```

   For a quick two-liner, `$'first line\nsecond line'` (ANSI-C quoting)
   also works, but for anything beyond two lines prefer `--desc-file`.

   Passing both `--desc` and `--desc-file` is an error — pick one.

   Preserve the original description verbatim, then add three sections:

   - **Modifications** — file paths + a one-line summary each
   - **Comportements obtenus** — what now works that did not before
   - **Garde-fous** — which gates ran and their result

5. **Then move to REVIEW.**

       ken move <id> --to review

   Do **not** mark a task `done` yourself. That is the user's call
   after review.

6. **Classify the task for the wiki (#376).** Once it is in review,
   assign it to a section of `ARCHITECTURE.md` so `ken wiki sync` can
   include it in the exported tree. The CLI prints a reminder after
   every `ken move --to review` / `ken update --status review`:

       ken wiki groom                 # list unclassified + sections
       ken wiki groom <id> <section>  # assign

   Use the deepest matching section path (`backend/api` beats
   `backend`). Skipping this step leaves the task invisible to
   `ken wiki sync` until someone backfills it.

## Statuses and ownership

    todo → doing → review → done

The agent owns transitions `todo → doing → review`. The user owns the
`review → done` transition.

## Filters and output

Always use the native filters; never pipe through jq, awk, or Python:

    ken list --who Claude --status doing   # good — human-readable table
    ken list --json | jq '.[] | ...'       # bad — verbose and pointless

**Use the human-readable output by default.** The text format from
`ken list` (aligned table) and `ken show` (key-value pairs) is compact
and directly readable by an LLM — no post-processing needed. Only add
`--json` when you need machine-parseable output as input to another
command (e.g. `ken add --json` to capture the created task ID).

## Quick reference

    ken list --who Claude --status todo
    ken show <id>
    ken add "Title" --desc "..." --who Claude --status todo --json
    ken update <id> --status review
    ken update <id> --desc "<original>\n\n---\n\n## Résolution\n..."
    ken move <id> --to doing
    ken wiki groom                 # list unclassified + sections
    ken wiki groom <id> <section>  # classify after move-to-review
    ken done <id>          # avoid; let the user mark done after review

## Task title convention

Every task title **must** follow the format `MODULE / Titre` where
`MODULE` is a short uppercase tag indicating the area of the codebase:

    AUTH / Login OIDC via Authlib
    BUG / Remove user fails with 403
    CLEAN / Remove dead kenboard build command
    SEC / Sanitize reflected data in onboarding
    UI / Logo on login page
    DOC / INSTALL update for set-password
    QUALITY / Sonarcloud issues
    AGENT / CLI / Sync tasks to folder
    ONBOARDING / WebFetch returns 200

Common modules: `AUTH`, `BUG`, `CLEAN`, `SEC`, `UI`, `DOC`, `QUALITY`,
`AGENT`, `ONBOARDING`, `FIX`. Sub-modules are separated by ` / `
(e.g. `AGENT / CLI / Sync`). Keep titles short — details go in the
description.

Example:

    ken add "SEC / XSS sanitize onboarding IDs" --desc "..." --who Claude

## Other practices

- The `ken` binary uses only the stdlib for HTTP. Do **not** add
  `requests` or `httpx` as a runtime dependency just for it.
- The `.ken` file is gitignored and contains an API token (mode 0600).
  Never commit it; never echo its contents.
- Don't add features, refactor code, or make "improvements" beyond what
  was asked. A bug fix doesn't need surrounding cleanup.
- A task title cannot contain `<` or `>` characters (server-side
  validation): use plain words instead of HTML-like tags.

## See also

- `ken --help` for the full command reference.
- The 401 onboarding runbook (returned by any kenboard URL hit without
  credentials) explains how to install ken and configure `.ken`.
