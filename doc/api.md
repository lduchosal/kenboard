# API REST

Reference des endpoints HTTP exposes par kenboard. Toutes les routes sont
prefixees `/api/v1` et retournent du JSON.

> Voir aussi : [`authentication.md`](authentication.md) pour le detail des
> users et des hashes argon2, et [`openapi.yaml`](openapi.yaml) pour la
> specification machine-readable des endpoints `users`.

## Conventions communes

- **Content-Type** : `application/json` pour les requetes avec body, response
  toujours en JSON sauf pour `204 No Content`.
- **IDs** :
  - `categories`, `projects`, `users` : UUID `VARCHAR(36)`
  - `tasks` : entier auto-increment
- **Codes de retour** :
  - `200` lecture / update OK
  - `201` creation OK
  - `204` suppression OK (pas de body)
  - `404` ressource inexistante
  - `409` conflit (nom deja pris pour les users)
  - `422` erreur de validation pydantic
  - `500` erreur serveur

Aucune authentification n'est requise pour le moment (cf. `authentication.md`,
section "Ce qui manque").

## Categories

```
GET    /api/v1/categories               Liste toutes les categories
POST   /api/v1/categories                Cree (name, color)
PATCH  /api/v1/categories/:id            Modifie (name, color, project_order)
DELETE /api/v1/categories/:id            Supprime (cascade sur projects/tasks)
POST   /api/v1/categories/reorder        Reordonne {from: int, to: int}
```

## Projects

```
GET    /api/v1/projects                  Liste tous les projects
POST   /api/v1/projects                  Cree (cat_id, name, acronym, status)
PATCH  /api/v1/projects/:id              Modifie
DELETE /api/v1/projects/:id              Supprime
```

## Tasks

```
GET    /api/v1/tasks?project=:proj_id    Liste les tasks d'un projet (parametre obligatoire)
POST   /api/v1/tasks                     Cree (project_id, title, description, status, who, due_date)
PATCH  /api/v1/tasks/:id                 Modifie (incl. status, position)
DELETE /api/v1/tasks/:id                 Supprime
```

Statuts valides : `todo`, `doing`, `review`, `done`.

## Users

```
GET    /api/v1/users                     Liste tous les users (sans password_hash)
POST   /api/v1/users                     Cree (name, color, password?, is_admin?)
PATCH  /api/v1/users/:id                 Modifie (name, color, password, is_admin)
DELETE /api/v1/users/:id                 Supprime
```

Specifique users :
- `password` est optionnel a la creation et au PATCH ; vide = inchange
- `password_hash` n'est jamais retourne par l'API
- 409 sur `name` deja pris (creation ou rename)

Pour les details (schemas exacts, exemples, codes), voir
[`openapi.yaml`](openapi.yaml).

## Standards de documentation

Le standard de fait pour documenter une API REST est **OpenAPI** (anciennement
Swagger), aujourd'hui maintenu par la Linux Foundation. Une specification
OpenAPI est un fichier YAML (ou JSON) qui decrit :

- Les endpoints (paths, methods)
- Les schemas d'input / output (referencables, reutilisables)
- Les codes de retour
- Les schemas d'authentification
- Des exemples

Une fois ecrit, ce fichier peut etre :

- **Affiche** par Swagger UI ou Redoc dans une page interactive
- **Valide** par des outils CLI (`spectral`, `openapi-cli`)
- **Genere en clients** SDK dans n'importe quel langage (`openapi-generator`)
- **Importe** dans Postman, Insomnia, Bruno
- **Teste contre** par schemathesis (fuzzing API)

### Maintenance manuelle vs auto-generation

Deux ecoles :

1. **Spec-first** : on ecrit le YAML a la main, le code l'implemente. Avantage :
   le contrat de l'API est explicite et stable. Inconvenient : risque de drift
   entre le code et la spec.

2. **Code-first** : on annote les routes Python (decorators ou pydantic) et un
   outil genere le YAML. Bibliotheques courantes en Flask :

   - **flask-smorest** : marshmallow + decorators, integration assez
     intrusive mais auto-genere une spec complete et un Swagger UI
   - **flasgger** : decorators legers, doit etre maintenu en parallele du
     code (pas vraiment auto-genere)
   - **apispec** : module bas niveau, sert de base aux deux precedents
   - **pydantic-flask** ou **flask-openapi3** : plus aligne avec la stack
     pydantic deja en place dans kenboard

   FastAPI fait ca nativement (auto-spec depuis pydantic + type hints), c'est
   l'argument numero un de FastAPI vs Flask.

### Choix retenu pour kenboard

**Spec-first manuelle, scope minimal**, fichier `doc/openapi.yaml` :

- Couvre uniquement les endpoints `/api/v1/users` pour l'instant (les nouveaux
  endpoints, qui sont l'objet de cette tache de doc)
- Versions OpenAPI **3.1** (compatible JSON Schema 2020-12)
- Aucune dependance ajoutee au runtime
- Lisible par tous les outils Swagger UI / Redoc / Postman / Insomnia hors-ligne
  (par ex. `npx @redocly/cli preview-docs doc/openapi.yaml`)

A faire ensuite (pas dans le scope de cette tache, dette assumee) :

- Etendre `openapi.yaml` aux endpoints categories / projects / tasks
- Brancher Swagger UI sur une route `/api/v1/docs` (servir le YAML + une page)
- Eventuellement migrer vers `flask-openapi3` pour auto-generer la spec depuis
  les modeles pydantic existants — c'est le moins de travail manuel a long
  terme et le plus coherent avec le stack actuel
