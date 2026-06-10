# `ken` — CLI tasks pour Claude Code

`ken` est la CLI compagnon de kenboard pour piloter les tasks d'un
projet depuis un shell, sans passer par WebFetch ou un client HTTP
ad-hoc. Pensee pour Claude Code et tout agent qui scripte le board
mais utilisable par un humain.

Module Python : `src/dashboard/ken/` (package Click, #786). Entry point :
`ken = "dashboard.ken:cli"` dans `pyproject.toml`. Aucune dependance
runtime ajoutee — l'HTTP est fait avec `urllib.request` de la stdlib.

Périmètre : **tasks + lecture des projects**. Categories, users,
edition de projects : geres par l'UI web, hors scope CLI.

## Surface CLI

```
ken init     [PROJECT_UUID] [--force]                       # crée/met a jour le .ken du cwd
ken projects [--json]                                       # liste les projects (pour trouver l'UUID)
ken list     [--status STATUS] [--who WHO] [--json]         # tasks du projet courant
ken show     ID [--json]                                    # detail d'une task
ken add      TITLE [--desc TEXT] [--who WHO] [--status STATUS] [--when YYYY-MM-DD] [--json]
ken update   ID [--title T] [--desc D] [--status S] [--who W] [--when YYYY-MM-DD] [--json]
ken move     ID --to STATUS                                 # raccourci status
ken done     ID                                             # raccourci `update ID --status done`
ken sync     [--json]                                       # mirror les tasks dans sync_dir
ken self-update                                             # pip install --upgrade kenboard
ken help                                                    # affiche le agent_guide.md (LLM cheatsheet)
```

`STATUS` ∈ `todo|doing|review|done` (les 4 colonnes kanban).

### Sorties

Convention Unix classique (comme `git`, `kubectl`) : **colonnes par
defaut, `--json` pour les agents**. Le mode `--json` retourne le
payload exact que renvoie l'API REST, avec dates ISO `YYYY-MM-DD`.

- Erreurs : sur `stderr`, exit non nul. Resultats : sur `stdout`.
- Exit codes : `0` succes, `1` erreur API/reseau/auth, `2` erreur de
  syntaxe CLI (Click le fait nativement).
- Dates en ISO `YYYY-MM-DD` meme en mode colonnes — la vue web garde
  son `DD.MM`, c'est juste le CLI qui est plus verbeux pour la
  precision (annee incluse) et le tri lexico.

### Exemples

```sh
# Bootstrap : trouver le projet et creer le .ken
$ ken projects
ID                                    ACRONYM  NAME
76a70206-0e6a-4485-a426-d7eb5ab53aac  KEN      Kenboard

$ ken init 76a70206-0e6a-4485-a426-d7eb5ab53aac
Wrote .ken (project: Kenboard)

# Lister les tasks ouvertes
$ ken list --status doing
ID   STATUS  WHO     WHEN        TITLE
8    doing   Claude  --          RC / script update dans un cron
14   doing   Q       2026-04-12  UX / Refresh automatique

# Mode JSON pour Claude
$ ken list --json
[{"id":8,"status":"doing","who":"Claude","title":"...",...}, ...]

# Creer une task et capturer son ID
$ ken add "Fix le typo dans le footer" --who Claude --json | jq .id
22

# Deplacer
$ ken move 22 --to doing
$ ken done 22

# Synchroniser le board dans doc/kenboard/ (un .md par task)
$ ken sync
Synced 14 task(s) to /repo/doc/kenboard
```

## Architecture

### Deux fichiers : `ken.ini` (versionne) + `.ken` (secrets, gitignore) — #778

Depuis #778, la config est splittee en deux :

- **`ken.ini`** — versionne, partage par l'equipe. Format `configparser`,
  section `[ken]`. Contient `project_id`, `base_url`, `description`,
  `sync_dir`, `architecture`, `wiki_dir`, `wiki_html_dir`. Pas de
  `.gitignore` — c'est le but.
- **`.ken`** — gitignore, local. Format legacy `key=value`. Contient
  `api_token` (le seul vrai secret) et permet aussi de surcharger
  localement n'importe quelle cle de `ken.ini` (utile pour pointer un
  `base_url` perso ou un autre `project_id`).

Exemple `ken.ini` (committable) :

```ini
[ken]
project_id = 76a70206-0e6a-4485-a426-d7eb5ab53aac
base_url = https://kenboard.example.com
description = Kenboard
sync_dir = doc/kenboard
```

Exemple `.ken` (gitignore) :

```
api_token=kb_<43_chars>
```

Recherche : `ken` remonte le cwd vers `/` jusqu'a trouver chacun des
deux fichiers (independamment), comme `git`. Permet de lancer `ken`
depuis n'importe quel sous-repertoire d'un projet.

Compat legacy : un `.ken` qui contient encore tout (project_id, base_url,
api_token, ...) continue a fonctionner — le parser legacy lit toutes
les cles, et l'absence de `ken.ini` n'est pas une erreur.

#### Securite — `.ken` contient le secret

Le `.ken` isole le bearer token de l'API du reste de la config. Les
garde-fous restent identiques :

1. `ken init` cree `.ken` en **mode `0600`** (lecture/ecriture
   user-only).
2. `ken init` ajoute `.ken` a `.gitignore` du repo courant si il n'y
   est pas deja (et cree le `.gitignore` au besoin). `ken.ini` n'est
   **jamais** ajoute a `.gitignore` — c'est l'inverse du but.
3. A chaque execution, `ken` verifie le mode du `.ken` ; si `0600`
   n'est pas respecte, affiche un warning sur stderr (mais continue).
4. Le `.ken` ne doit jamais etre committe.

#### `ken init`

```
ken init [UUID] [--base-url URL] [--token TOKEN] [--force]
```

- Si `UUID` est fourni → ecrit `ken.ini` avec ce project_id (verifie
  qu'il existe via `GET /api/v1/projects` et affiche le name).
- Si omis → liste les projects, propose un choix interactif.
- `--base-url` et `--token` permettent de seeder ces cles a la
  creation.
- `ken.ini` recoit `project_id`, `base_url`, `description`.
- `.ken` est cree **uniquement si un `api_token` est resolu** (via
  `--token` ou `KEN_API_TOKEN`) ; sinon `ken` affiche une note et
  saute l'etape — on pourra relancer plus tard avec `--force`.
- Refuse de reecrire un `ken.ini` ou `.ken` existant sans `--force`.
- `ken.ini` n'est jamais ajoute a `.gitignore` ; `.ken` l'est.

#### Onboarding automatise (Copy onboard link)

Pour les agents AI, le flow recommande est le bouton **Copy onboard
link** sur la page d'un projet (cf. `/admin/board`). Le lien servi
pointe vers `/onboarding/<token>` et inclut un `api_token` jetable
de type `onboarding`. Au premier appel `ken init`, ce token est
consomme et remplace par un token persistant de type `onboarded`
(scope `write` sur le projet uniquement).

### Configuration

Lecture par ordre de priorite (le premier qui resout l'emporte) :

1. Flags de ligne de commande (`--project`, `--base-url`, `--token`,
   `--config`)
2. Variables d'environnement (`KEN_*`)
3. Fichier `.ken` du cwd (secrets + overrides locaux)
4. Fichier `ken.ini` du cwd (defaut partage versionne)
5. Defauts hardcodes

`--config FILE` peut pointer soit sur un `.ini` (parser configparser,
section `[ken]`), soit sur un fichier `.ken` legacy. L'extension
decide. Quand `--config` est utilise, **un seul** fichier est lu.

| Cle | Defaut | Role |
|---|---|---|
| `base_url` / `KEN_BASE_URL` | `http://localhost:9090` | URL de l'API kenboard. |
| `project_id` / `KEN_PROJECT_ID` | (aucun) | UUID du projet cible. |
| `api_token` / `KEN_API_TOKEN` | (aucun) | Bearer token. Envoye en header `Authorization: Bearer <token>` sur chaque requete. A garder dans `.ken`. |
| `sync_dir` / `KEN_SYNC_DIR` | `doc/kenboard` | Dossier cible de `ken sync`. Chemin relatif resolu par rapport au dossier qui contient `ken.ini` (ou `.ken` legacy). |

Si apres cette resolution `project_id` est toujours absent et qu'aucun
`--project` n'est passe, `ken` echoue avec :

```
$ ken list
Error: no project configured. Run `ken init <UUID>` or set KEN_PROJECT_ID.
```

### Auth

L'API est en mode strict depuis #40 : un token bearer valide est
**requis** pour appeler `/api/v1/*`. `ken` envoie automatiquement
`Authorization: Bearer <api_token>` si la cle est definie. Sans
token (et sans cookie session, ce qui n'est jamais le cas en CLI),
l'API repond 401.

Trois facons de fournir le token :

1. Token d'onboarding obtenu via le bouton **Copy onboard link** —
   recommande pour les agents.
2. Cle API creee manuellement via `POST /api/v1/keys` (admin only),
   collee dans `~/.config/ken/...` ou dans `.ken`.
3. Variable d'env `KEN_API_TOKEN` pour les pipelines / cron.

Cf. [`api-keys.md`](api-keys.md) pour le detail des scopes et de la
revocation.

### `ken sync`

Mirror de l'etat du board dans un dossier local (`sync_dir`,
`doc/kenboard` par defaut), un fichier `NNNN - Title.md` par task
avec un frontmatter YAML :

```markdown
---
id: 42
status: doing
who: Claude
due_date: 2026-05-12
---

# Fix le typo dans le footer

(description en markdown)
```

Idempotent : reecriture des fichiers dont le titre/contenu a change,
suppression des fichiers correspondant a des tasks supprimees ou
deplacees hors du projet. Premier appel `ken sync` ajoute la cle
`sync_dir=` au `.ken` si elle n'y est pas encore.

### Commandes utilitaires

- `ken self-update` — `pip install --upgrade kenboard` avec le meme
  Python que la CLI. Pratique pour les agents qui veulent rester sur
  la derniere version sans wrapper externe.
- `ken help` — imprime `src/dashboard/agent_guide.md` (cheatsheet
  embarquee, conventions d'usage pour LLMs, exemples).

## Tests

- **Unit** (`tests/unit/test_ken.py`) : mock HTTP, resolution de la
  config (priorite flags > env > .ken > defaut), recherche du `.ken`
  en remontant les parents, formatting des sorties (texte colonnes
  alignees et JSON), parsing des arguments Click, erreurs (status
  invalide, ID inexistant, projet manquant, token manquant /
  invalide).
- **E2E** (`tests/e2e/test_ken.py`) : utilise la fixture
  `live_server` existante, invoque `ken` via
  `click.testing.CliRunner` (pas besoin de subprocess), cree projet
  + tasks, verifie list/update/done end-to-end, verifie qu'un `.ken`
  est trouve en remontant 2 niveaux de cwd.

## Notes pour futures versions

- v2 : sous-commandes `ken cat list`, `ken proj add` quand on veut
  admin via CLI sans aller sur l'UI.
- v2 : `ken delete ID` (volontairement absent, l'UI le fait, Claude
  n'en a pas besoin).
- v2 : `ken assign ID WHO` raccourci (equivalent `update --who`).
- v2 : `ken comment ID TEXT` quand l'API supportera les commentaires.
- v2 : output `--watch` qui repoll toutes les N secondes.
