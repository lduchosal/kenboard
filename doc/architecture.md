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
