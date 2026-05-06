# `ken` — CLI tasks pour Claude Code

> Spec v1, validée par l'opérateur. Les décisions notées **« Choix »** ont
> été arbitrées explicitement, ne pas les revisiter sans en discuter.

## Objectif

Permettre à Claude Code (et à un humain qui scripte) de manipuler les tasks
du board kenboard depuis un shell, sans passer par WebFetch ou par un client
HTTP ad-hoc. Une commande `ken` exposée à côté de l'existant `kenboard`,
partageant le même package PyPI `kenboard` et le même module Python
`dashboard`.

Périmètre v1 : **tasks + lecture des projects**. Categories, users,
édition de projects : hors scope, gérés par l'UI web.

## Surface CLI

```
ken init     [PROJECT_UUID]                          # crée/met à jour le .ken du cwd
ken projects [--json]                                # liste les projects (pour trouver l'UUID)
ken list     [--status STATUS] [--who WHO] [--json]  # tasks du projet courant
ken show     ID [--json]                             # détail d'une task
ken add      TITLE [--desc TEXT] [--who WHO] [--status STATUS] [--when YYYY-MM-DD] [--json]
ken update   ID [--title T] [--desc D] [--status S] [--who W] [--when YYYY-MM-DD] [--json]
ken move     ID --to STATUS                          # raccourci status
ken done     ID                                      # raccourci `update ID --status done`
ken sync     [--json]                                # mirror les tasks dans sync_dir
```

`STATUS` ∈ `todo|doing|review|done` (les 4 colonnes kanban).

### Sorties

**Choix : colonnes par défaut, `--json` pour Claude**. Convention Unix
classique (`git`, `kubectl`). Le mode `--json` retourne le payload exact que
renvoie l'API REST, avec dates ISO `YYYY-MM-DD`.

- Erreurs : sur `stderr`, exit non nul. Résultats : sur `stdout`.
- Exit codes : `0` succès, `1` erreur API/réseau, `2` erreur de syntaxe CLI
  (Click le fait nativement).
- **Choix : dates en ISO `YYYY-MM-DD` même en mode colonnes**, pour la
  précision (année incluse), le tri lexico, et la friendliness machine. La
  vue web garde son `DD.MM`, c'est juste le CLI qui est plus verbeux.

### Exemples

```sh
# Bootstrap : trouver le projet et créer le .ken
$ ken projects
ID                                    NAME                ACRONYM
76a70206-0e6a-4485-a426-d7eb5ab53aac  Kenboard            KEN

$ ken init 76a70206-0e6a-4485-a426-d7eb5ab53aac
Wrote .ken (project: Kenboard)

# Lister les tasks ouvertes
$ ken list --status doing
ID  STATUS  WHO     WHEN        TITLE
8   doing   Claude  --          RC / script update dans un cron
14  doing   Q       2026-04-12  UX / Refresh automatique

# Mode JSON pour Claude
$ ken list --json
[{"id":8,"status":"doing","who":"Claude","title":"...",...}, ...]

# Créer une task
$ ken add "Fix le typo dans le footer" --who Claude
{"id":22,"title":"Fix le typo dans le footer","status":"todo",...}

# Déplacer
$ ken move 22 --to doing
$ ken done 22

# Synchroniser le board dans doc/kenboard/ (un .md par task)
$ ken sync
Synced 14 task(s) to /repo/doc/kenboard
```

## Architecture

### Module Python

Nouveau fichier `src/dashboard/ken.py`, exposé par un nouveau script entry
point dans `pyproject.toml` :

```toml
[project.scripts]
kenboard = "dashboard.cli:cli"   # existant — admin (serve, migrate, build)
ken      = "dashboard.ken:cli"   # nouveau — tasks (init, list, add, ...)
```

Les deux CLI restent **séparées** : `kenboard` pour les opérations admin,
`ken` pour le workflow quotidien. Pas de sous-commande
`kenboard task list ...` qui mélangerait les rôles.

Implémentation : **Click** (déjà utilisé par `cli.py`), **`urllib.request`**
de la stdlib pour parler à l'API REST (zéro dépendance ajoutée — `httpx` est
plus agréable mais surdimensionné pour 5 endpoints REST simples).

### Fichier `.ken` du cwd

**Choix : fichier `.ken` à la `git`**, self-contained. Format `key=value`,
une clé par ligne :

```
project_id=76a70206-0e6a-4485-a426-d7eb5ab53aac
base_url=http://localhost:9090
api_token=k_abc123xyz...
```

Recherche : `ken` remonte le cwd vers `/` jusqu'à trouver un `.ken`. Comme
`git`, ça permet de lancer `ken` depuis n'importe quel sous-répertoire d'un
projet sans devoir `cd` à la racine.

#### Sécurité — `.ken` contient un secret

**Choix arbitré : on accepte le risque de tout regrouper** dans `.ken` pour
la simplicité (zéro fichier annexe, zéro variable d'env à exporter, copie de
dossier = transfert complet du contexte). En contrepartie, le CLI prend
plusieurs garde-fous **obligatoires** :

1. `ken init` crée `.ken` en **mode `0600`** (lecture/écriture user-only).
2. `ken init` ajoute `.ken` à `.gitignore` du repo courant si il n'y est pas
   déjà (et crée le `.gitignore` au besoin). Si pas dans un repo git, émet
   un warning.
3. À chaque exécution, `ken` vérifie le mode du fichier ; si `0600` n'est
   pas respecté (groupe ou autres ont des bits), affiche un warning sur
   stderr (mais continue, pour ne pas bloquer).
4. La doc README mentionne explicitement : « `.ken` contient un token,
   ne pas le committer, ne pas le partager. »

Convention différente du standard `gh`/`kubectl`/`aws` qui séparent
credentials et contexte projet — choix conscient pour la simplicité de
workflow Claude Code, à revisiter si on déploie `ken` au-delà d'un user
unique sur sa propre machine.

#### `ken init`

```
ken init [UUID] [--base-url URL] [--token TOKEN] [--force]
```

- Si `UUID` est fourni → écrit `.ken` avec ce project_id (vérifie qu'il
  existe via `GET /api/v1/projects` et affiche le name).
- Si omis → liste les projects, propose un choix interactif.
- `--base-url` et `--token` permettent de seeder ces clés à la création ;
  sinon le CLI utilise les défauts (`http://localhost:9090`, pas de token).
- Refuse de réécrire un `.ken` existant sans `--force`.
- Crée le fichier avec `chmod 0600`.
- Ajoute `.ken` à `.gitignore` du repo si nécessaire.

### Configuration

Lecture par ordre de priorité (le premier qui résout l'emporte) :

1. Flags de ligne de commande (`--project`, `--base-url`, `--token`)
2. Variables d'environnement (`KEN_*`)
3. Fichier `.ken` du cwd (project_id, base_url, api_token)
4. Défauts hardcodés

| Clé `.ken` / env | Défaut | Rôle |
|---|---|---|
| `base_url` / `KEN_BASE_URL` | `http://localhost:9090` | URL de l'API kenboard. **Choix** : 9090 = port d'écoute kenboard sur web2 (cf `KENBOARD.md`), cohérent prod ↔ dev. |
| `project_id` / `KEN_PROJECT_ID` | (aucun) | UUID du projet ciblé. |
| `api_token` / `KEN_API_TOKEN` | aucun | Bearer token. **Choix** : préparé maintenant, envoyé en header `Authorization` dès qu'il est défini, même si l'API ne le lit pas encore (cf #6). |
| `sync_dir` / `KEN_SYNC_DIR` | `doc/kenboard` | Dossier cible de `ken sync`. Chemin relatif résolu par rapport au dossier qui contient `.ken`. La clé est ajoutée automatiquement au `.ken` lors du premier `ken sync`. |

Si après cette résolution `project_id` est toujours absent et qu'aucun
`--project` n'est passé, `ken` échoue avec :

```
$ ken list
Error: no project configured. Run `ken init <UUID>` or set KEN_PROJECT_ID.
```

### Auth

L'API n'a aucune auth aujourd'hui (cf. #1, #6, #7). Le CLI envoie quand
même `Authorization: Bearer <KEN_API_TOKEN>` si la variable est définie,
**comme préparation**. Quand #6 sera mergé, on n'aura qu'à distribuer un
token sans changer le CLI.

## Tests

- **Unit** (`tests/unit/test_ken.py`) :
  - Mock HTTP (via `unittest.mock` ou `responses`)
  - Resolution de la config (priorité flags > env > .ken > .env > défaut)
  - Recherche du `.ken` en remontant les parents
  - Formatting des sorties (texte colonnes alignées et JSON)
  - Parsing des arguments Click
  - Erreurs : status invalide, ID inexistant, projet manquant

- **E2E** (`tests/e2e/test_ken.py`) :
  - Utilise la fixture `live_server` existante
  - Invoque `ken` via `click.testing.CliRunner` (pas besoin de subprocess)
  - Crée projet + tasks, vérifie list/update/done end-to-end
  - Vérifie qu'un `.ken` est trouvé en remontant 2 niveaux de cwd

## Étapes d'implémentation

1. ✅ Spec validée (ce document)
2. Création du module `src/dashboard/ken.py` avec Click
3. Ajout entry point `ken` dans `[project.scripts]`
4. Tests unit + e2e
5. Doc `README.md` mise à jour avec une section "CLI ken"
6. Publish 0.1.x via `sh publish.sh`

## Notes pour futures versions

- v2 : sous-commandes `ken cat list`, `ken proj add` quand on veut admin
  via CLI sans aller sur l'UI
- v2 : `ken delete ID` (volontairement absent en v1, l'UI le fait, Claude
  n'en a pas besoin)
- v2 : `ken assign ID WHO` raccourci (équivalent `update --who`)
- v2 : `ken comment ID TEXT` quand l'API supportera les commentaires
- v2 : output `--watch` qui repoll toutes les N secondes (intéressant en
  conjonction avec #14 refresh automatique)
