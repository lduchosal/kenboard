# API REST

Reference des endpoints HTTP exposes par kenboard. Toutes les routes
applicatives sont prefixees `/api/v1` et retournent du JSON.

> Voir aussi : [`auth-user.md`](auth-user.md) pour le login web (cookie
> Flask-Login), [`api-keys.md`](api-keys.md) pour le bearer token /
> scoping par projet, [`permissions.md`](permissions.md) pour les
> scopes utilisateur par categorie, et [`openapi.yaml`](openapi.yaml)
> pour la specification machine-readable.

## Conventions communes

- **Content-Type** : `application/json` pour les requetes avec body,
  reponse toujours en JSON sauf pour `204 No Content`.
- **IDs** :
  - `categories`, `projects`, `users`, `api_keys`, `password_reset_tokens`,
    `email_verification_tokens` : UUID `VARCHAR(36)`
  - `tasks` : entier auto-increment
- **Codes de retour** :
  - `200` lecture / update OK
  - `201` creation OK
  - `204` suppression / action OK (pas de body)
  - `400` requete mal formee (ex: `project=` manquant sur `GET /tasks`)
  - `401` token absent / invalide / revoque / expire
  - `403` scope insuffisant, route admin-only, ou CSRF refuse
  - `404` ressource inexistante
  - `409` conflit (nom deja pris pour les users/categories)
  - `422` erreur de validation pydantic
  - `429` rate limit depasse (login, register, forgot-password,
    create-key, create-user, reset-password)
  - `500` erreur serveur

## Authentification

Le middleware (`src/dashboard/auth.py`) accepte trois principaux pour
les routes `/api/v1/*`, dans l'ordre :

1. **Cookie session Flask-Login** — le user logue via `/login` peut
   parler a l'API directement depuis la web UI. Sur les methodes
   non-safe (`POST/PATCH/DELETE/PUT`), un check Origin/Referer protege
   contre le CSRF.
2. **Bearer token statique** — `Authorization: Bearer <KENBOARD_ADMIN_KEY>`
   passe partout (admin global). La cle est lue depuis le `.env`, ne
   transite pas par la DB.
3. **Bearer api_key** — `Authorization: Bearer kb_<43_chars>`, scope
   par projet (`read|write|admin`) lookup dans la table
   `api_key_projects`. Cf. [`api-keys.md`](api-keys.md).

Les routes admin-only (`/api/v1/users`, `/api/v1/keys`) refusent les
api_keys per-projet : il faut soit une session admin (`is_admin = 1`),
soit la cle statique `KENBOARD_ADMIN_KEY`. La seule exception est
`POST /api/v1/users/<id>/password` (changement de mot de passe par
l'utilisateur lui-meme).

Exemple curl avec api_key :

```sh
curl -H "Authorization: Bearer kb_<key>" \
     https://kenboard.example.com/api/v1/tasks?project=<uuid>
```

## Categories

```
GET    /api/v1/categories             Liste les categories visibles par le caller
POST   /api/v1/categories             Cree (admin only) — body: {name, color}
PATCH  /api/v1/categories/:id         Modifie (write scope) — {name?, color?, project_order?}
DELETE /api/v1/categories/:id         Supprime (admin only) — cascade projects/tasks
POST   /api/v1/categories/reorder     Reordonne (admin only) — {from: int, to: int}
```

Pour les non-admins, `GET /api/v1/categories` filtre selon les scopes
de l'utilisateur (`user_category_scopes`). Un admin voit tout.

`POST /api/v1/categories` cree automatiquement un projet
`Project {name}` dans la categorie en meme temps (commodite UI).

## Projects

```
GET    /api/v1/projects?cat=:cat_id    Liste tous les projects (optionnellement filtres par cat)
POST   /api/v1/projects                Cree — {name, acronym, cat, status?, default_who?}
PATCH  /api/v1/projects/:id            Modifie — incl. project_order pour reorder
DELETE /api/v1/projects/:id            Supprime (refuse si tasks ; 400)
```

Champs : `name` (max 250), `acronym` (max 4), `status` ∈ `active|archived`,
`default_who` (assignee pre-rempli sur les nouvelles tasks du projet).

Les non-admins doivent avoir `read` sur la categorie source ; pour creer
ou deplacer un projet, il faut `write` sur la categorie cible.

## Tasks

```
GET    /api/v1/tasks?project=:proj_id   Liste les tasks d'un projet (param obligatoire)
GET    /api/v1/tasks/:id                Detail d'une task
POST   /api/v1/tasks                    Cree — {project_id, title, description?, status?, who?, due_date?}
PATCH  /api/v1/tasks/:id                Modifie — incl. status, position, project_id (move)
DELETE /api/v1/tasks/:id                Supprime
```

Statuts valides : `todo`, `doing`, `review`, `done`. Le `due_date`
accepte deux formats au POST/PATCH : ISO `YYYY-MM-DD` ou europeen
`DD.MM` (annee courante deduite). Pydantic normalise vers `date` ;
l'API renvoie toujours du ISO.

## Users

```
GET    /api/v1/users                          Liste tous les users + leurs scopes (admin)
POST   /api/v1/users                          Cree (admin) — {name, email?, color, password?, is_admin?}
PATCH  /api/v1/users/:id                      Modifie (admin) — {name?, color?, is_admin?}
DELETE /api/v1/users/:id                      Supprime (admin)
POST   /api/v1/users/:id/password             Changement self-service — {old_password, new_password}
POST   /api/v1/users/:id/reset-password       Reset admin — {new_password}
PUT    /api/v1/users/:id/scopes               Remplace les scopes — {scopes: [{category_id, scope}]}
```

Specifique users :
- `password_hash` n'est jamais retourne par l'API.
- `password` n'est PAS dans `UserUpdate` (#53) — pour changer un mot
  de passe il faut passer par `/password` (self) ou `/reset-password`
  (admin), tous deux soumis a la politique de force argon2/zxcvbn (cf
  [`auth-user.md`](auth-user.md)).
- 409 sur `name` deja pris (creation ou rename).
- `POST /users` est rate-limite a 10/heure par IP.
- `POST /users/:id/reset-password` est rate-limite a 5/heure par IP.

`PUT /users/:id/scopes` remplace atomiquement la liste de scopes (clear
+ insert dans une transaction). Cf. [`permissions.md`](permissions.md)
pour le modele de permissions par categorie.

## API Keys

```
POST   /api/v1/keys                  Cree (admin) — renvoie la cle en clair une fois
GET    /api/v1/keys                  Liste (admin, sans cle en clair)
PATCH  /api/v1/keys/:id              Modifie (admin) — label, expires_at, user_id, scopes
DELETE /api/v1/keys/:id              Revoque (admin) — set revoked_at
POST   /api/v1/keys/onboard          Cree/remplace un onboarding token (admin)
```

Cf. [`api-keys.md`](api-keys.md) pour le detail (format, scoping,
mode strict, page d'admin `/admin/keys`).

## Routes hors `/api/v1/`

Pages HTML (rendues par Jinja, protegees par `@login_required`) :

```
GET  /                             Dashboard (kanban global)
GET  /cat/:id.html                 Page d'une categorie
GET  /admin/users                  Page admin users (admin only)
GET  /admin/keys                   Page admin api_keys (admin only)
GET  /admin/board                  Page admin categories/projects (admin only)
```

Auth utilisateur (form login + reset + register) :

```
GET  /login                        Form de login
POST /login                        Verifie credentials, set cookie (rate-limit 5/min, 20/h)
POST /logout                       Rotate session_nonce + clear cookie
GET  /forgot-password              Form mot de passe oublie
POST /forgot-password              Genere token + envoie mail (rate-limit 3/h)
GET  /reset-password/:token        Form nouveau mot de passe
POST /reset-password/:token        Applique le nouveau mot de passe + rotate nonce
GET  /register                     Form d'inscription (404 si REGISTER_ALLOWED_DOMAIN vide)
POST /register                     Genere token verification + envoie mail (rate-limit 5/h)
GET  /verify-email/:token          Verifie token, cree user + categorie + projet personnel
```

OIDC (cf. [`auth-user.md`](auth-user.md) section OIDC,
[`oidc-adfs.md`](oidc-adfs.md) pour ADFS) :

```
GET  /oidc/login                   Redirige vers l'IdP (PKCE S256)
GET  /oidc/callback                Echange le code, lookup ou lazy-create user
```

## Standards de documentation

Le standard de fait pour documenter une API REST est **OpenAPI**
(anciennement Swagger), aujourd'hui maintenu par la Linux Foundation.
Une specification OpenAPI est un fichier YAML (ou JSON) qui decrit :

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

1. **Spec-first** : on ecrit le YAML a la main, le code l'implemente.
   Avantage : le contrat de l'API est explicite et stable. Inconvenient :
   risque de drift entre le code et la spec.

2. **Code-first** : on annote les routes Python (decorators ou pydantic)
   et un outil genere le YAML. FastAPI fait ca nativement (auto-spec
   depuis pydantic + type hints), c'est l'argument numero un de FastAPI
   vs Flask. En Flask, `flask-smorest` ou `flask-openapi3` permettent
   un equivalent au prix d'une integration plus intrusive.

### Choix retenu pour kenboard

**Spec-first manuelle, scope partiel**, fichier `doc/openapi.yaml` :

- Couvre les ressources principales : users, categories, projects, tasks,
  keys.
- Version OpenAPI **3.1** (compatible JSON Schema 2020-12).
- Aucune dependance ajoutee au runtime.
- Lisible par tous les outils Swagger UI / Redoc / Postman / Insomnia
  hors-ligne (par ex.
  `npx @redocly/cli preview-docs doc/openapi.yaml`).

A faire ensuite (dette assumee) :

- Brancher Swagger UI sur une route `/api/v1/docs` (servir le YAML +
  une page).
- Eventuellement migrer vers `flask-openapi3` pour auto-generer la
  spec depuis les modeles pydantic existants — c'est le moins de
  travail manuel a long terme et le plus coherent avec le stack actuel.
