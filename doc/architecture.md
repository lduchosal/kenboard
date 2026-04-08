# Architecture

## Principes

- SQL pur, pas d'ORM
- Chaque couche a une responsabilite unique
- Les fichiers SQL sont la source de verite pour les queries et les migrations
- Pydantic valide les entrees et les sorties, il ne genere pas de SQL
- Le frontend est genere statiquement via Jinja2 ou servi dynamiquement par Flask

## Stack technique

| Couche | Outil | Role |
|--------|-------|------|
| API HTTP | Flask | Routes, middleware, CORS |
| Validation | Pydantic v2 | Modeles de donnees, serialisation JSON |
| Queries | aiosql | Fichiers `.sql` mappes en fonctions Python |
| Migrations | yoyo-migrations | Fichiers `.sql` avec up/rollback |
| Connexion DB | PyMySQL | Driver MySQL |
| Templates | Jinja2 | Generation HTML (statique et dynamique) |
| Frontend | Vanilla JS + SortableJS | Interactions, drag & drop |
| Qualite | black, ruff, mypy, pytest... | Voir pyproject.toml |

## Flux d'une requete API

```
Client (JS fetch)
  |
  v
Flask route (@app.get, @app.post, @app.patch, @app.delete)
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
```

## Mapping SQL -> Python

Le mapping est manuel et explicite, comme Dapper en .NET :

```python
# PyMySQL retourne un dict
row = {"id": "technique", "name": "Technique", "color": "var(--accent)", "position": 2}

# Pydantic valide et mappe
category = Category(**row)
```

Les colonnes SQL correspondent aux champs Pydantic par convention de noms.
Pas de lazy loading, pas de relations implicites, pas de session.

## Structure des fichiers

```
src/dashboard/
  __init__.py
  app.py                  # Flask app factory
  config.py               # Configuration (env vars, .env)
  models/                 # Pydantic v2 models
    category.py
    project.py
    task.py
  queries/                # Fichiers SQL (aiosql)
    categories.sql
    projects.sql
    tasks.sql
  routes/                 # Flask blueprints
    categories.py
    projects.py
    tasks.py
  db.py                   # Connexion PyMySQL
  templates/              # Jinja2 templates (existant)
    base.html
    index.html
    category.html
    partials/
    modals/
```

## Structure des migrations

```
migrations/
  0001.create_categories.sql
  0002.create_projects.sql
  0003.create_tasks.sql
```

Chaque fichier contient le SQL `CREATE` et un `-- rollback` avec le `DROP`.

### Regles obligatoires pour ecrire une migration

On s'est fait avoir deux fois (0008 -> 0009 pour `users.session_nonce`,
puis 0010 -> 0011 pour `api_keys.user_id`) par yoyo qui enregistre une
migration comme appliquee alors que le DDL n'a jamais persiste sur le
schema. Symptome typique : `_yoyo_migration` contient le hash de la
migration, mais `INFORMATION_SCHEMA.COLUMNS` ne voit pas la nouvelle
colonne, et l'API plante en boucle avec `Unknown column`.

Cause racine : yoyo ne hash que le `migration_id` (le nom du fichier),
**pas le contenu**. Une fois enregistree, la migration ne sera plus
jamais rejouee. Combine au fait que les statements DDL MySQL font un
implicit commit qui invalide les savepoints de yoyo, un `ALTER TABLE`
multi-clause qui echoue partiellement peut laisser la base dans un etat
ou yoyo croit avoir reussi mais ou rien n'a vraiment ete applique.

Du coup, **toutes les nouvelles migrations** doivent suivre ces regles :

1. **Idempotente par construction.** Chaque etape DDL verifie
   `INFORMATION_SCHEMA.COLUMNS` ou `TABLE_CONSTRAINTS` avant de tourner
   et fait `DO 0` si la modification existe deja. Pattern :
   `PREPARE`/`EXECUTE` avec une variable `@stmt` calculee par un `IF()`.
   Voir `0009.readd_user_session_nonce.sql` ou
   `0011.readd_api_key_user_id.sql` comme templates.
2. **Une seule preoccupation par `ALTER TABLE`.** Jamais de combinaison
   `ADD COLUMN` + `ADD CONSTRAINT` + `ADD INDEX` dans le meme statement.
   On split en plusieurs `ALTER TABLE` separes pour qu'un echec partiel
   reste rejouable etape par etape.
3. **Pas d'index explicite a cote d'une FK sur la meme colonne.** MySQL
   cree automatiquement un index couvrant pour chaque FK. En ajouter un
   second en parallele est un des trucs qui a contribue au stuck state
   de 0010.
4. **Ne jamais editer une migration deja appliquee quelque part.** yoyo
   ne rejouera pas le fichier modifie. Si une migration deja appliquee
   est cassee sur prod, on ajoute une migration de recuperation
   `00NN.readd_<truc>.sql` qui `depends:` sur la cassee et ré-applique
   la modification de maniere idempotente. C'est exactement ce que font
   0009 et 0011.
5. **Le `-- rollback` est aussi idempotent.** Chaque `DROP` est garde
   par un check `INFORMATION_SCHEMA` pour qu'un rollback depuis n'importe
   quel etat partiel converge.
6. **Mirroir dans `tests/conftest.py`.** La base de test est creee a la
   main (sans yoyo), donc toute nouvelle colonne doit etre ajoutee dans
   le `CREATE TABLE` *et* dans le bloc de back-fill (en etapes atomiques)
   pour les schemas de test heritages d'une session precedente.

Si une de ces regles parait excessive sur une migration triviale, c'est
qu'on n'a pas encore ete brule par le bon angle — appliquer les regles
quand meme. Le cout d'une migration verbose et idempotente est nul ; le
cout d'une prod qui boucle en 500 sur tout `/api/v1/*` est tres
au-dessus.

## Schema de la base de donnees

### categories

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | Identifiant unique (slug) |
| name | VARCHAR(250) | Nom affiche |
| color | VARCHAR(50) | Variable CSS (ex: var(--orange)) |
| position | INT | Ordre d'affichage |

### projects

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | Identifiant unique (slug) |
| cat_id | VARCHAR(36) FK | Categorie |
| name | VARCHAR(250) | Nom complet |
| acronym | VARCHAR(4) | Acronyme 4 lettres |
| status | ENUM('active','archived') | Statut |
| position | INT | Ordre dans la categorie |

### tasks

| Colonne | Type | Description |
|---------|------|-------------|
| id | INT PK AUTO_INCREMENT | Identifiant unique |
| project_id | VARCHAR(36) FK | Projet |
| title | VARCHAR(250) | Titre |
| description | TEXT | Detail |
| status | ENUM('todo','doing','review','done') | Statut kanban |
| who | VARCHAR(100) | Assignee |
| due_date | DATE | Echeance (nullable) |
| position | INT | Ordre dans la colonne |
| created_at | DATETIME | Date de creation |
| updated_at | DATETIME | Derniere modification |

### burndown_snapshots

| Colonne | Type | Description |
|---------|------|-------------|
| id | INT PK AUTO_INCREMENT | Identifiant |
| project_id | VARCHAR(36) FK | Projet |
| week | DATE | Debut de semaine |
| remaining | INT | Taches restantes |

## API REST

### Categories

```
GET    /api/v1/categories              Liste
POST   /api/v1/categories              Creer
PATCH  /api/v1/categories/:id          Modifier
DELETE /api/v1/categories/:id          Supprimer
POST   /api/v1/categories/reorder      Reordonner
```

### Projects

```
GET    /api/v1/projects?cat=:cat_id    Liste par categorie
POST   /api/v1/projects                Creer
PATCH  /api/v1/projects/:id            Modifier
DELETE /api/v1/projects/:id            Supprimer
```

### Tasks

```
GET    /api/v1/tasks?project=:proj_id  Liste par projet
POST   /api/v1/tasks                   Creer
PATCH  /api/v1/tasks/:id               Modifier (titre, statut, position...)
DELETE /api/v1/tasks/:id               Supprimer
```

## Generation statique vs dynamique

Le meme jeu de templates Jinja2 sert pour :

1. **build.py** : lit `data.json`, rend les templates, ecrit des fichiers `.html`
2. **Flask** : lit MySQL, rend les memes templates, sert dynamiquement

A terme, `data.json` disparait. Le build statique devient optionnel (export/backup).

## Choix explicites

- **Pas d'ORM** : le SQL est ecrit a la main, visible, testable
- **Pas de framework JS** : vanilla JS suffit pour les interactions
- **Pas de build step JS** : un seul fichier `app.js`
- **Pydantic pour la validation, pas pour le SQL** : il valide les inputs/outputs, pas les queries
- **yoyo pour les migrations** : fichiers SQL purs, pas de Python
- **aiosql** : organise les queries SQL en fichiers, ne genere rien
