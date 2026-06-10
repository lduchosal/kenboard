---
id: 778
title: "CLI / Split .ken (secrets) + ken.ini (config versionnée)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-09T09:01:05
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #778 — CLI / Split .ken (secrets) + ken.ini (config versionnée)

## Contexte

Aujourd'hui `ken` ne lit qu'un seul fichier `.ken` (key=value, gitignoré, mode 0600) qui mélange secret (`api_token`) et config partageable (`project_id`, `base_url`, `sync_dir`, `architecture`, `wiki_dir`, `wiki_html_dir`, `description`).

Objectif : permettre à une équipe de versionner la config commune dans le repo, tout en gardant le token côté poste.

**Hors scope : pas de hooks.** Décision prise — on garde `ken` minimal, le besoin d'automatisation passe par d'autres canaux (scripts manuels, `angel publish`, etc.).

## Proposition

1. **Deux fichiers :**
   - `ken.ini` versionné (committé) — config partagée uniquement.
   - `.ken` gitignoré — uniquement `api_token` (et éventuels overrides locaux : `base_url` perso, etc.).
2. **Format `ken.ini`** : `configparser` (stdlib, zéro dep), section `[ken]`. Garder le parser legacy `.ken` en lecture pour rétro-compat.
3. **Merge dans `_load_config`** (`src/dashboard/ken.py:137`) : chaîne flag > env `KEN_*` > `.ken` > `ken.ini` > défaut.
4. **`ken init`** :
   - écrit `ken.ini` (versionné, **non** ajouté à `.gitignore`) avec `project_id`, `base_url`, `description`.
   - écrit `.ken` (mode 0600, ajouté à `.gitignore`) seulement si un `api_token` est dispo.

---

## Résolution

### Modifications

- `src/dashboard/ken.py`
  - +`configparser` import, +constantes `KEN_INI_FILE = "ken.ini"` / `KEN_INI_SECTION = "ken"`.
  - `KenConfig` gagne `ini_file: Path | None`.
  - `_parse_ini_file()` : nouveau, lit section `[ken]` via `configparser` (sections inconnues ignorées).
  - `_load_config()` réécrit avec helper interne `_pick(key, env)` qui résout env > `.ken` > `ken.ini`. La chaîne finale est flag > env > `.ken` > `ken.ini` > défaut, exactement comme spécifié.
  - `--config FILE` : extension `.ini` → parsé en INI, sinon parser legacy. Un seul fichier lu dans ce mode.
  - `_resolve_sync_dir()` anchor sur `ini_file` en priorité, fallback `ken_file`.
  - `_persist_sync_dir()` écrit dans `ken.ini` si présent (via `configparser.write`), fallback append `.ken` legacy. No-op si la clé est déjà recordée.
  - `init` : split en deux écritures. `ken.ini` toujours créé ; `.ken` créé uniquement si `api_token` résolu (`--token` ou `KEN_API_TOKEN`). Sans token, note sur stderr expliquant comment relancer avec `--force`.
- `tests/unit/test_ken.py`
  - `TestCliInit` réécrit : `test_init_with_uuid_writes_ini_only_when_no_token`, `test_init_with_token_writes_ken_with_mode_0600`, `test_init_refuses_overwrite_of_ini`, `test_init_force_overwrites_both`, ajustement du test gitignore (vérifie que `ken.ini` n'y est PAS ajouté).
  - Nouveau `TestLoadConfigInI` : ini seul, ken override ini, env > ini, walk-up, ini sans section `[ken]` inerte, `--config custom.ini`.
  - Nouveau `TestPersistSyncDir` : écrit dans ini si dispo, fallback `.ken`, no-op si clé déjà set.
- `doc/ken-cli.md` : section "Architecture" réécrite — deux fichiers, exemples des deux formats, tableau de résolution mis à jour, note `--config` accepte `.ini` ou legacy.
- `CLAUDE.md` (kenboard) : note du workflow `ken init` mise à jour pour décrire les deux fichiers.

### Comportements obtenus

- `ken init UUID` sans token → écrit `ken.ini`, pas de `.ken`, pas de `.gitignore`. Note explicite "pas d'api_token résolu — skipped .ken".
- `ken init UUID` avec `KEN_API_TOKEN=...` → écrit `ken.ini` (config) + `.ken` mode 0600 (token), `.ken` ajouté au `.gitignore` du repo.
- Une équipe peut commiter `ken.ini` ; chaque dev pose son `.ken` perso à la racine.
- Compat legacy : un `.ken` legacy contenant `project_id=...` continue à fonctionner sans `ken.ini`.
- Override local : un `.ken` qui contient `base_url=http://staging:9090` surcharge le `base_url` partagé de `ken.ini`.
- `ken sync` persiste `sync_dir` dans `ken.ini` quand il existe (donc partagé), sinon dans `.ken`.

### Garde-fous

- `pdm run lint` (ruff) → All checks passed.
- `pdm run typecheck` (mypy strict) → no issues found in 30 source files.
- `pdm run flake8` → propre (après ajout docstring sur helper interne `_pick`).
- `pdm run interrogate` → 99.7% (seuil 95%).
- `pdm run isort` / `pdm run format` (black) / `pdm run docformatter` → reformat appliqué.
- `pdm run vulture` / `pdm run refurb` → propres.
- `pdm run test-quick` → **549 passed**, dont 17 tests nouveaux/modifiés sur `TestCliInit` + `TestLoadConfigInI` + `TestPersistSyncDir`.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-06-09.md)
