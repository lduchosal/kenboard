# Architecture

## Principes

- SQL pur, pas d'ORM
- Chaque couche a une responsabilite unique
- Les fichiers SQL sont la source de verite pour les queries et les
  migrations
- Pydantic valide les entrees et les sorties, il ne genere pas de SQL
- Le frontend est un mix Jinja2 (rendu serveur des pages) + JS vanilla
  bundle par Vite (interactions, drag&drop, modales)

## Stack technique

| Couche | Outil | Role |
|--------|-------|------|
| API HTTP | Flask | Routes, blueprints, middleware |
| Validation | Pydantic v2 | Modeles de donnees, serialisation JSON |
| Queries | aiosql | Fichiers `.sql` mappes en fonctions Python |
| Migrations | yoyo-migrations | Fichiers `.sql` numerotes avec rollback |
| Connexion DB | PyMySQL | Driver MySQL, dict-cursor + autocommit |
| Templates | Jinja2 | Rendu HTML server-side |
| Auth web | Flask-Login | Cookie session, `@login_required` |
| Auth OIDC | Authlib | OAuth2 + OIDC (Google/Authentik/ADFS) |
| Auth API | Custom middleware | Bearer tokens (api_keys) + cle admin statique |
| Rate limit | flask-limiter | `/login`, `/register`, etc. |
| Mailer | smtplib (stdlib) | Reset password, email verification |
| Frontend | Vanilla JS + SortableJS | Interactions, drag & drop |
| JS bundler | Vite | Bundle ES modules → `static/dist/app.js` |
| JS lint/format | Biome | Lint + format des `static/js/` |
| JS typecheck | tsc + JSDoc | `// @ts-check` opt-in, jsconfig.json |
| JS tests | Vitest + jsdom | `*.test.js` colocalises |
| Quality Python | black, ruff, mypy, pytest, ... | Voir `pyproject.toml` |

Le toolchain JS (Vite + Vitest + Biome + tsc-via-JSDoc) est volontairement
minimaliste : un bundler, un test runner, un linter, pas de plugin
sprawl, pas de pipeline CSS, pas de TS rewrite. C'est la borne haute de
complexite acceptee cote frontend.

## Flux d'une requete API

```
Client (JS fetch ou ken CLI ou curl)
  |
  v
Flask before_request (auth.py)
  - Cookie session valide ? OK + check CSRF Origin/Referer
  - Bearer = KENBOARD_ADMIN_KEY ? OK
  - Bearer = api_key valide ? Check scope projet/categorie, met a jour last_used_*
  - Sinon -> 401 / 403
  |
  v
Flask blueprint (categories_bp, projects_bp, tasks_bp, users_bp, keys_bp, ...)
  |
  v
Pydantic model (validation de l'input)
  |
  v
aiosql query (SQL pur depuis fichier .sql)
  |
  v
PyMySQL (execute sur MySQL)
  |
  v
Pydantic model (serialisation de l'output)
  |
  v
JSON Response
  |
  v
Flask after_request (perf monitoring, #214)
  - Compte queries / SQL ms / template ms / response KB
  - Au-dela du budget : log structlog + insert task dans le projet PERF (avec cooldown)
```

## Mapping SQL -> Python

Le mapping est manuel et explicite, comme Dapper en .NET :

```python
# PyMySQL retourne un dict
row = {"id": "technique", "name": "Technique", "color": "var(--accent)", "position": 2}

# Pydantic valide et mappe
category = Category(**row)
```

Les colonnes SQL correspondent aux champs Pydantic par convention de
noms. Pas de lazy loading, pas de relations implicites, pas de session.

## Structure des fichiers

```
src/dashboard/
  __init__.py            # __version__
  app.py                 # Flask factory, registration des blueprints
  config.py              # Config (env vars, .env via python-dotenv)
  cli.py                 # CLI `kenboard` (serve, prod, migrate, snapshot, ...)
  ken/                   # CLI `ken` en package (workflow tasks pour Claude Code, #786)
  agent_guide.md         # Doc embarquee servie par `ken help`
  db.py                  # Connexion PyMySQL + chargement aiosql
  auth.py                # Middleware bearer token + CSRF + admin-only prefixes
  auth_user.py           # Flask-Login, session_nonce, helpers de scope
  auth_oidc.py           # OIDC client (Authlib), routes /oidc/*
  password_strength.py   # Validation argon2 + zxcvbn (centralise)
  mailer.py              # SMTP wrapper (reset-password, verify-email)
  perf.py                # Performance monitoring (#214)
  logging.py             # structlog setup
  models/                # Pydantic v2 models
    category.py
    project.py
    task.py
    user.py
    api_key.py
  queries/               # Fichiers SQL (aiosql)
    categories.sql
    projects.sql
    tasks.sql
    users.sql
    api_keys.sql
    burndown.sql
    password_reset_tokens.sql
    email_verification_tokens.sql
  routes/                # Flask blueprints
    categories.py
    projects.py
    tasks.py
    users.py
    keys.py
    pages.py             # Routes HTML (login, /, /cat/<id>.html, /admin/*)
    onboard.py           # Endpoint d'onboarding (runbook + token initial)
  migrations/            # *.sql consommes par yoyo (numerote, avec rollback)
  templates/             # Jinja2
    base.html
    index.html
    category.html
    login.html
    register.html
    forgot_password.html
    reset_password.html
    admin_users.html
    admin_keys.html
    admin_board.html
    partials/
    modals/
  static/
    js/                  # Sources ES modules (api.js, tasks.js, ...)
      *.test.js          # Tests colocalises (Vitest)
    dist/app.js          # Bundle Vite (servi par Flask)
    style.css
    sortable.min.js, marked.min.js, dompurify.min.js  # Vendored
```

## Structure des migrations

```
migrations/
  0001.create_categories.sql
  0002.create_projects.sql
  0003.create_tasks.sql
  0004.create_users.sql
  0005.create_api_keys.sql
  0006.create_api_key_projects.sql
  0007.add_projects_default_who.sql
  0008.add_users_session_nonce.sql               # buggy, voir 0009
  0009.readd_user_session_nonce.sql              # recovery idempotent
  0010.add_api_key_user_id.sql                   # buggy, voir 0011
  0011.readd_api_key_user_id.sql                 # recovery idempotent
  0012.add_users_email.sql                       # buggy, voir 0013
  0013.readd_users_email.sql                     # recovery idempotent
  0014.add_api_keys_key_type.sql
  0015.create_user_category_scopes.sql           # #197 permissions humaines
  0016.create_burndown_snapshots.sql             # #206 burndown
  0017.add_api_keys_last_used_metadata.sql       # IP + User-Agent
  0018.create_password_reset_tokens.sql          # #231
  0019.create_email_verification_tokens.sql      # #232 self-register
```

Chaque fichier contient le SQL `CREATE/ALTER` et un bloc `-- rollback`.
**Le rollback doit toujours etre un no-op** (`SELECT 1`) — cf. la
section regles ci-dessous.

### Regles obligatoires pour ecrire une migration

On s'est fait avoir trois fois (0008 -> 0009 pour `users.session_nonce`,
0010 -> 0011 pour `api_keys.user_id`, 0012 -> 0013 pour `users.email`)
par yoyo qui enregistre une migration comme appliquee alors que le DDL
n'a jamais persiste sur le schema. Symptome typique : `_yoyo_migration`
contient le hash de la migration, mais `INFORMATION_SCHEMA.COLUMNS` ne
voit pas la nouvelle colonne, et l'API plante en boucle avec
`Unknown column`.

Cause racine : yoyo ne hash que le `migration_id` (le nom du fichier),
**pas le contenu**. Une fois enregistree, la migration ne sera plus
jamais rejouee. Combine au fait que les statements DDL MySQL font un
implicit commit qui invalide les savepoints de yoyo, un `ALTER TABLE`
multi-clause qui echoue partiellement peut laisser la base dans un
etat ou yoyo croit avoir reussi mais ou rien n'a vraiment ete applique.

Du coup, **toutes les nouvelles migrations** doivent suivre ces
regles :

1. **Idempotente par construction.** Chaque etape DDL verifie
   `INFORMATION_SCHEMA.COLUMNS` ou `TABLE_CONSTRAINTS` avant de
   tourner et fait `DO 0` si la modification existe deja. Pattern :
   `PREPARE`/`EXECUTE` avec une variable `@stmt` calculee par un
   `IF()`. Voir `0011.readd_api_key_user_id.sql` comme template
   canonique.
2. **Une seule preoccupation par `ALTER TABLE`.** Jamais de
   combinaison `ADD COLUMN` + `ADD CONSTRAINT` + `ADD INDEX` dans le
   meme statement. On split en plusieurs `ALTER TABLE` separes pour
   qu'un echec partiel reste rejouable etape par etape.
3. **Pas d'index explicite a cote d'une FK sur la meme colonne.**
   MySQL cree automatiquement un index couvrant pour chaque FK. En
   ajouter un second en parallele est un des trucs qui a contribue
   au stuck state de 0010.
4. **Ne jamais editer une migration deja appliquee quelque part.**
   yoyo ne rejouera pas le fichier modifie. Si une migration deja
   appliquee est cassee sur prod, on ajoute une migration de
   recuperation `00NN.readd_<truc>.sql` qui `depends:` sur la cassee
   et re-applique la modification de maniere idempotente.
5. **Le `-- rollback` doit etre un no-op (`SELECT 1`).** yoyo peut
   echouer a parser le marqueur `-- rollback` et executer le fichier
   complet d'un trait. Un rollback destructif (`DROP COLUMN`) qui
   suit un `ADD COLUMN` dans le meme fichier = la colonne est ajoutee
   puis immediatement droppee, alors que yoyo enregistre la migration
   comme "appliquee". C'est exactement ce qui a casse 0012. Si un
   vrai rollback est necessaire, l'ecrire comme une **migration
   forward separee** (`00NN.drop_<truc>.sql`).
6. **Mirroir dans `tests/conftest.py`.** La base de test est creee
   a la main (sans yoyo), donc toute nouvelle colonne doit etre
   ajoutee dans le `CREATE TABLE` *et* dans le bloc de back-fill
   (en etapes atomiques) pour les schemas de test heritages d'une
   session precedente.

Si une de ces regles parait excessive sur une migration triviale,
c'est qu'on n'a pas encore ete brule par le bon angle — appliquer
les regles quand meme. Le cout d'une migration verbose et idempotente
est nul ; le cout d'une prod qui boucle en 500 sur tout `/api/v1/*`
est tres au-dessus.

## Schema de la base de donnees

### categories

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | UUID |
| name | VARCHAR(250) | Nom affiche |
| color | VARCHAR(50) | Hex `#0969da` ou variable CSS `var(--accent)` |
| position | INT | Ordre d'affichage |

### projects

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | UUID |
| cat_id | VARCHAR(36) FK | Categorie (ON DELETE CASCADE) |
| name | VARCHAR(250) | Nom complet |
| acronym | VARCHAR(4) | Acronyme 4 lettres |
| status | ENUM('active','archived') | Statut |
| position | INT | Ordre dans la categorie |
| default_who | VARCHAR(100) | Assignee par defaut des nouvelles tasks (#7) |

### tasks

| Colonne | Type | Description |
|---------|------|-------------|
| id | INT PK AUTO_INCREMENT | Identifiant unique |
| project_id | VARCHAR(36) FK | Projet (ON DELETE CASCADE) |
| title | VARCHAR(250) | Titre |
| description | TEXT | Detail (markdown rendu cote client) |
| status | ENUM('todo','doing','review','done') | Statut kanban |
| who | VARCHAR(100) | Assignee (texte libre, pas de FK vers `users`) |
| due_date | DATE | Echeance (nullable) |
| position | INT | Ordre dans la colonne |
| created_at | DATETIME | Auto |
| updated_at | DATETIME | Auto on update |

### users

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | UUID |
| name | VARCHAR(100) UNIQUE | Identifiant humain (egalement utilise dans `tasks.who`) |
| email | VARCHAR(255) UNIQUE NULL | Optionnel pour les users password-only, requis pour OIDC |
| color | VARCHAR(50) | Couleur d'avatar |
| password_hash | VARCHAR(255) | Hash argon2, vide tant qu'aucun mot de passe defini |
| is_admin | TINYINT(1) | Drapeau admin |
| session_nonce | CHAR(32) | Anti-replay des cookies. Rotate au logout, password reset, OIDC link |
| created_at | DATETIME | Auto |
| updated_at | DATETIME | Auto on update |

### api_keys

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | UUID |
| user_id | VARCHAR(36) FK NULL | Owner (#110), `ON DELETE SET NULL` |
| key_hash | CHAR(64) UNIQUE | sha256 hex du token en clair |
| key_type | VARCHAR(20) NULL | NULL/`onboarding`/`onboarded` (#14) |
| label | VARCHAR(100) | Description humaine |
| expires_at | DATETIME NULL | Expiration optionnelle |
| last_used_at | DATETIME NULL | Mise a jour a chaque appel |
| last_used_ip | VARCHAR(45) NULL | IP du dernier appel (#17) |
| last_used_agent | VARCHAR(200) NULL | User-Agent du dernier appel (#17) |
| revoked_at | DATETIME NULL | Set par `DELETE /api/v1/keys/:id` |
| created_at | DATETIME | Auto |

### api_key_projects

Junction table api_key ↔ project avec scope.

| Colonne | Type | Description |
|---------|------|-------------|
| api_key_id | VARCHAR(36) FK | (ON DELETE CASCADE) |
| project_id | VARCHAR(36) FK | (ON DELETE CASCADE) |
| scope | ENUM('read','write','admin') | Niveau d'acces |
| PK | (api_key_id, project_id) | |

### user_category_scopes

Junction table user ↔ category avec scope (modele permission humain,
#197). Cf. [`permissions.md`](permissions.md).

| Colonne | Type | Description |
|---------|------|-------------|
| user_id | VARCHAR(36) FK | (ON DELETE CASCADE) |
| category_id | VARCHAR(36) FK | (ON DELETE CASCADE) |
| scope | ENUM('read','write') | Niveau d'acces |
| created_at | DATETIME | Auto |
| PK | (user_id, category_id) | |

### burndown_snapshots

Snapshot quotidien pour le burndown chart (#206). Cf.
[`burndown.md`](burndown.md).

| Colonne | Type | Description |
|---------|------|-------------|
| id | INT PK AUTO_INCREMENT | |
| snapshot_date | DATE | Date du snapshot |
| project_id | VARCHAR(36) FK | (ON DELETE CASCADE) |
| todo, doing, review, done | INT | Compteurs par statut |
| UNIQUE | (snapshot_date, project_id) | Idempotent (upsert) |

### password_reset_tokens / email_verification_tokens

Tokens a usage unique pour les flows reset-password (#231) et
self-register (#232). Stockent un `token_hash` (sha256), un
`expires_at`, et un `used_at` (set a la consommation).

## API REST

Voir [`api.md`](api.md) pour la liste des endpoints et
[`openapi.yaml`](openapi.yaml) pour le schema machine-readable.

## Choix explicites

- **Pas d'ORM** : le SQL est ecrit a la main, visible, testable.
- **Pas de framework JS** : vanilla JS + SortableJS suffisent pour
  les interactions, pas de React/Vue/Svelte.
- **Toolchain JS minimal mais reel** : un bundler (Vite), un test
  runner (Vitest), un linter (Biome), tsc-via-JSDoc pour le typecheck.
  C'est l'upper bound — pas de plugin sprawl, pas de pipeline CSS,
  pas de TS rewrite.
- **Pydantic pour la validation, pas pour le SQL** : il valide les
  inputs/outputs, pas les queries.
- **yoyo pour les migrations** : fichiers SQL purs, pas de Python.
- **aiosql** : organise les queries SQL en fichiers, ne genere rien.
- **Auth split** : Flask-Login pour la web UI (cookie session), bearer
  tokens pour l'API (api_keys par projet + cle admin statique pour
  les operations admin).
- **Permissions split** : par categorie pour les humains
  (`user_category_scopes`), par projet pour les bots
  (`api_key_projects`). Cf. [`permissions.md`](permissions.md).
