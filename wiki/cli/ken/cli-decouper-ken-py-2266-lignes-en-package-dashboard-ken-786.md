---
id: 786
title: "CLI / Découper ken.py (2266 lignes) en package dashboard/ken/"
status: review
who: "Claude"
due_date: 
classified_at: 2026-06-10T07:24:05
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #786 — CLI / Découper ken.py (2266 lignes) en package dashboard/ken/

Chantier 4 du plan doc/code-quality.md (ken #783). ken.py = 28% du code source et fichier le plus modifié du repo. Le découper en package dashboard/ken/ (config, client HTTP, formatting, commandes task, commandes wiki) en conservant l'entry point dashboard.ken:cli et le comportement à l'identique (zéro régression : la suite de tests existante doit passer sans changement fonctionnel ; seuls les patch-targets des tests peuvent bouger). Attendu : max_file_lines < 500.

---

## Résolution

### Modifications

`src/dashboard/ken.py` (2 266 lignes) supprimé, remplacé par le package `src/dashboard/ken/` — code déplacé à l'identique (y compris le WIP #778 présent dans l'arbre), seuls les imports inter-modules ont changé :

- `__init__.py` — bloc UTF-8 Windows (#148), imports d'enregistrement des commandes, re-exports de compat (`cli`, `KenConfig`, `_load_config`, `_slugify`, etc. avec `__all__`) pour que `from dashboard import ken; ken.X` continue de marcher. Entry point `dashboard.ken:cli` inchangé.
- `config.py` (271) — constantes, KenConfig, parsing .ken/ken.ini, `_load_config`, `_add_to_gitignore`, `_resolve_sync_dir`, `_persist_sync_dir`.
- `http.py` (85) — `_ssl_context`, `_request`, `_require_project`.
- `fmt.py` (104) — tables alignées (`_format_columns`, `_output`) + markdown de `ken sync`.
- `cli.py` (172) — groupe racine + `init`, `self-update`, `help`.
- `tasks.py` (454) — `projects`, `list`, `show`, `add`, `update`, `polish`, `move`, `done` + helpers attachement/desc + reminders.
- `sync.py` (80) — commande `ken sync`.
- `wiki.py` (330) — groupe `wiki`, `groom`, helpers sections/slug.
- `wiki_sync.py` (352), `wiki_build.py` (418), `wiki_lint.py` (147) — pipeline wiki.
- Tests : 6 lignes adaptées dans `tests/unit/test_ken.py` (patch urlopen → `dashboard.ken.http.urllib_request.urlopen`, mutation `_ATTACHEMENT_MAX_BYTES` → `dashboard.ken.tasks`). Aucun autre test modifié.
- Docs : références `ken.py` → `ken/` dans CLAUDE.md, doc/architecture.md, doc/ken-cli.md.

### Comportements obtenus

- CLI identique : `ken --help` liste les 13 commandes + groupe wiki (4 sous-commandes), smoke-test réel `ken list` OK contre l'API.
- Métriques (doc/quality-history.csv) : max_file_lines 2 266 → 890 (auth_user.py désormais), files_over_500 3 → 2, tous les modules ken < 500 lignes (max 454).

### Garde-fous

- isort, black, docformatter, ruff, flake8, mypy strict (40 fichiers), interrogate 100%, vulture, refurb : tous verts.
- Suite complète hors e2e : 549 passed, couverture 89.54% (vs 89.29% avant).
- e2e non rejoués (nécessitent serveur lancé) ; `tests/e2e/test_ken.py` n'utilise que `ken.cli`, re-exporté.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-06-10.md)
