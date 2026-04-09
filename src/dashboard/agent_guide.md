# kenboard agent guide

Best practices for an LLM agent (Claude, GPT, etc.) that manages tasks
on a kenboard project board through the `ken` CLI. This file is shipped
with the package and printed by `ken help`.

## The loop: pick → wip → review → resolution

1. **Read the queue.** List the todo tasks assigned to you and pick one
   based on its title + description. Announce the choice and the reason
   in chat *before* doing anything else:

       ken list --who <YourName> --status todo --json

2. **Mark it WIP before starting.** Move the chosen task to `doing` so
   the board reflects work-in-progress and other agents/humans don't
   grab the same card:

       ken move <id> --to doing

3. **Implement.** Read the relevant code, make the change, and run your
   project's quality gates (linters, type checkers, tests). If a
   pre-existing failure shows up in an unrelated area, confirm it is
   not caused by your change before proceeding.

4. **Move to REVIEW, not done.** Once the work is ready for the user
   to look at:

       ken move <id> --to review

   Do **not** mark a task `done` yourself. That is the user's call
   after review.

5. **Append a resolution block** to the task description so the board
   accumulates an audit trail (commit messages alone are not enough —
   not every task maps 1:1 to a commit):

       ken update <id> --desc "<original>\n\n---\n\n## Résolution\n..."

   Preserve the original description verbatim, then add three sections:

   - **Modifications** — file paths + a one-line summary each
   - **Comportements obtenus** — what now works that did not before
   - **Garde-fous** — which gates ran and their result

## Statuses and ownership

    todo → doing → review → done

The agent owns transitions `todo → doing → review`. The user owns the
`review → done` transition.

## Filters and parsing

Always use the native filters; never pipe `ken list --json` through
jq, awk, or Python:

    ken list --who Claude --status doing --json   # good
    ken list --json | jq '.[] | select(...)'      # bad

Always pass `--json` when parsing the output programmatically.

## Quick reference

    ken list --who Claude --status todo --json
    ken show <id> --json
    ken add "Title" --desc "..." --who Claude --status todo --json
    ken update <id> --status review --json
    ken update <id> --desc "<original>\n\n---\n\n## Résolution\n..."
    ken move <id> --to doing
    ken done <id>          # avoid; let the user mark done after review

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
