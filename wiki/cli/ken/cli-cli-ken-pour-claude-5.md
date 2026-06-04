---
id: 5
title: "CLI / CLI ken pour Claude"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:28:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #5 — CLI / CLI ken pour Claude

CLI `ken` implémentée selon spec validée dans `doc/ken-cli.md`.

## Livraisons

- `src/dashboard/ken.py` (~470 lignes) : module Click avec 8 sous-commandes (`init`, `projects`, `list`, `show`, `add`, `update`, `move`, `done`). HTTP via `urllib.request` stdlib (zéro dépendance ajoutée).
- `pyproject.toml` : entry point `ken = "dashboard.ken:cli"` à côté du `kenboard` existant.
- `tests/unit/test_ken.py` : **30 unit tests** (mock urlopen, résolution config flags > env > .ken > defaults, walk-up parents, format columns, gitignore handling, mode 0600, toutes les commandes).
- `tests/e2e/test_ken.py` : **5 e2e tests** contre le live_server fixture via CliRunner (lifecycle complet add→list→update→move→done→show, init + .gitignore, walk-up parents).
- `README.md` : nouvelle section "CLI ken" avec bootstrap, commandes, configuration, sécurité du `.ken`, exemples.

## Garde-fous sécurité du `.ken`

- Mode 0600 à la création
- Auto-add au `.gitignore` du repo (créé si manquant)
- Warning stderr si le fichier n'est pas dans un repo git
- Warning stderr si le mode est plus permissif que 0600 à chaque exécution
- Token jamais affiché sur stdout

## Tests live

Testé manuellement contre la prod :
```
$ ken --base-url https://www.kenboard.2113.ch projects
ID                                    ACRONYM  NAME    
76a70206-0e6a-4485-a426-d7eb5ab53aac  KEN      KENBOARD

$ ken --base-url https://www.kenboard.2113.ch --project 76a70206-... list --status doing
ID  STATUS  WHO     WHEN  TITLE                    
5   doing   Claude  --    CLI / CLI ken pour Claude
```

## État global

- 129 tests verts (94 unit + 35 e2e dont 30 unit + 5 e2e ken)
- Tous les checks qualité passent : ruff, mypy, black, isort, docformatter, flake8, vulture, refurb, interrogate 100%
- Prêt pour publish 0.1.15
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-24.md)
