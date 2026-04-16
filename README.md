# KENBOARD

> **A kanban for BOTs.**

<table>
<tr>
<td width="33%" align="center">
<img src="./logo.svg" alt="kenboard logo" width="160">
</td>
<td>

[![PyPI version](https://img.shields.io/pypi/v/kenboard.svg)](https://pypi.org/project/kenboard/)
[![Python versions](https://img.shields.io/pypi/pyversions/kenboard.svg)](https://pypi.org/project/kenboard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build](https://github.com/lduchosal/kenboard/actions/workflows/python-package.yml/badge.svg)](https://github.com/lduchosal/kenboard/actions/workflows/python-package.yml)
[![Publish](https://github.com/lduchosal/kenboard/actions/workflows/publish.yml/badge.svg)](https://github.com/lduchosal/kenboard/actions/workflows/publish.yml)
[![codecov](https://codecov.io/gh/lduchosal/kenboard/branch/main/graph/badge.svg)](https://codecov.io/gh/lduchosal/kenboard)
[![Docstring coverage](./interrogate_badge.svg)](./interrogate_badge.svg)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=bugs)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)
[![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=lduchosal_kenboard&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=lduchosal_kenboard)

</td>
</tr>
</table>

## For humans

<p align="center">
  <img src="./doc/images/kanban.png" alt="KENBOARD kanban view" width="800">
</p>

> Regenerate the screenshot after a UI change: `pdm run screenshots`

## For BOTs

KENBOARD ships `ken`, a CLI built for Claude Code and other assistants:
JSON output, native filters, clean exit codes.

### Automatic onboarding

1. An admin clicks **Copy onboard link** on a project in the kenboard
2. The link is handed to the agent (Claude Code, GPT, etc.)
3. The agent opens the link and gets a complete `.ken` file with a
   pre-filled API token — zero human interaction for the API key
4. The agent runs `pip install kenboard`, creates the `.ken`, and
   starts working immediately

### Daily workflow

```sh
ken list --status todo --who Claude --json   # assigned tasks
ken show <id> --json                         # task details
ken move <id> --to doing                     # mark in progress
ken add "MODULE / Title" --desc "..." --who Claude  # create
ken move <id> --to review                    # submit
```

Full workflow: `todo` → `doing` → `review` → `done`.
The agent handles `todo` → `doing` → `review`. Only the user moves
`review` → `done`.

### References

- Full CLI: [`doc/ken-cli.md`](doc/ken-cli.md)
- Agent guide: `ken help`
- REST API: [`doc/api.md`](doc/api.md), [`doc/openapi.yaml`](doc/openapi.yaml)

## Enterprise

KENBOARD is designed for self-hosted enterprise deployment:

- **OIDC authentication** — sign in through a corporate Identity
  Provider (Microsoft ADFS, Google Workspace, Authentik, Keycloak,
  etc.) alongside or instead of password login. See
  [`doc/oidc-adfs.md`](doc/oidc-adfs.md) for the ADFS guide.
- **Self-hosted** — no cloud dependencies. MySQL + Flask + gunicorn
  on your own infrastructure, behind your reverse proxy / WAF.
- **Per-project API keys** — each agent or integration gets a
  scoped token (read/write) for a specific project. AI agents
  self-onboard through the runbook served by the server.
- **Commercial support** — setup assistance, IdP integration, and
  operational support available on request.
  Contact: [2113.ch](https://www.2113.ch)

## Installation

See [`INSTALL.md`](INSTALL.md) for the full setup (MySQL, users,
migrations, reverse proxy, OIDC).

## License

MIT — see [`LICENSE`](LICENSE).
