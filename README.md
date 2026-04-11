# KENBOARD

> **Un kanban pour les BOT.**

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

## Usage pour les humains

<p align="center">
  <img src="./doc/images/kanban.png" alt="Vue kanban KENBOARD" width="800">
</p>

> Regenerer le screenshot apres une evolution UI : `pdm run screenshots`

## Usage pour les BOT

KENBOARD livre `ken`, une CLI pensee pour Claude Code et autres assistants :
output JSON, filtres natifs, exit codes propres.

### Onboarding automatique

1. Un admin clique **Copy onboard link** sur un projet dans le kenboard
2. Le lien est donne a l'agent (Claude Code, GPT, etc.)
3. L'agent ouvre le lien et recoit un fichier `.ken` complet avec un
   token API pre-rempli — zero interaction humaine pour l'API key
4. L'agent fait `pip install kenboard`, cree le `.ken`, et commence a
   travailler immediatement

### Workflow quotidien

```sh
ken list --status todo --who Claude --json   # taches assignees
ken show <id> --json                         # detail d'une tache
ken move <id> --to doing                     # passer en cours
ken add "MODULE / Titre" --desc "..." --who Claude  # creer
ken move <id> --to review                    # soumettre
```

Le workflow complet : `todo` → `doing` → `review` → `done`.
L'agent gere `todo` → `doing` → `review`. Seul l'utilisateur passe
`review` → `done`.

### References

- CLI complete : [`doc/ken-cli.md`](doc/ken-cli.md)
- Guide agent : `ken help`
- API REST : [`doc/api.md`](doc/api.md), [`doc/openapi.yaml`](doc/openapi.yaml)

## Entreprise

KENBOARD est concu pour un deploiement self-hosted en entreprise :

- **Authentification OIDC** — connexion via un Identity Provider
  d'entreprise (Microsoft ADFS, Google Workspace, Authentik, Keycloak,
  etc.) en complement ou remplacement du login par mot de passe.
  Voir [`doc/oidc-adfs.md`](doc/oidc-adfs.md) pour le guide ADFS.
- **Self-hosted** — aucune dependance cloud. MySQL + Flask + gunicorn
  sur votre infrastructure, derriere votre reverse proxy / WAF.
- **API keys par projet** — chaque agent ou integration recoit un
  token scope (read/write) sur un projet specifique. Les agents IA
  s'auto-onboardent via le runbook servi par le serveur.
- **Support commercial** — accompagnement a la mise en place,
  integration IdP, et support operationnel disponibles sur demande.
  Contact : [2113.ch](https://www.2113.ch)

## Installation

Voir [`INSTALL.md`](INSTALL.md) pour la mise en place complète (MySQL, utilisateurs, migrations, reverse proxy, OIDC).

## Licence

MIT — voir [`LICENSE`](LICENSE).

