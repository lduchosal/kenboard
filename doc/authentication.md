# Authentication

## Etat actuel

Kenboard a une **table users en base** avec mots de passe hashes argon2 et un drapeau `is_admin`.
La verification de mot de passe au login **n'est pas encore branchee** : les endpoints
publics et la page admin restent ouverts. La cinematique d'auth a proprement parler
(login, session, middleware) sera l'objet d'un travail dedie (cf. tache du board sur
l'authentification).

Ce document decrit ce qui existe et ce qui manque, pour eviter de re-decouvrir le
sujet a chaque iteration.

## Schema

### users

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | UUID, genere par MySQL `UUID()` au seed et par `uuid.uuid4()` au runtime |
| name | VARCHAR(100) UNIQUE | Identifiant humain (egalement utilise dans `tasks.who`) |
| color | VARCHAR(50) | Couleur d'avatar (hex `#0969da` ou variable CSS) |
| password_hash | VARCHAR(255) | Hash argon2, vide tant qu'aucun mot de passe defini |
| is_admin | TINYINT(1) | Drapeau admin (0 ou 1) |
| created_at | DATETIME | Auto |
| updated_at | DATETIME | Auto on update |

Migration : `src/dashboard/migrations/0004.create_users.sql`. Cette migration cree
la table puis insere les 4 utilisateurs historiques (Q, Alice, Bob, Claire) avec
leurs couleurs d'origine et un `password_hash` vide. Q est seed avec `is_admin = 1`.

Le nom de l'utilisateur est aussi la cle utilisee dans `tasks.who` (texte libre,
sans foreign key). Renommer un user via PATCH ne propage pas le nouveau nom dans
les tasks existantes.

## Politique de mot de passe (#198)

Tout mot de passe saisi via l'API (`POST /api/v1/users`, `POST /.../password`,
`POST /.../reset-password`) ou la CLI (`kenboard set-password`) passe par
`dashboard.password_strength.validate_password_strength()` :

| Critère | Valeur | Source |
|---|---|---|
| Longueur minimale | **8** caractères | `MIN_LENGTH` (`password_strength.py`) |
| Score zxcvbn | **≥ 3 / 4** ("safely unguessable") | `MIN_SCORE` |

La double vérification (longueur + zxcvbn) bloque les mots de passe courants même
quand ils sont longs. Exemples rejetés : `password`, `Password123`,
`abcdefghij`, `qwerty1234`. Exemples acceptés : `correct horse battery staple`,
`Xk9$mQ2!vL`, toute chaîne de 10+ caractères avec un mix lettres/chiffres/symboles.

Les erreurs de validation incluent le feedback de zxcvbn (warning + suggestions)
afin que l'utilisateur sache comment corriger :

```
Password is too weak (strength 1/4, need 3/4). This is a very common password.
Add another word or two. Uncommon words are better.
```

La logique vit dans un module dédié pour qu'il n'y ait qu'une seule source de
vérité entre Pydantic (`PasswordChange`, `PasswordReset`, `UserCreate`) et la CLI
`set-password`.

## Hash de mot de passe

Argon2 via `argon2-cffi`. Une instance partagee `PasswordHasher()` est definie dans
`src/dashboard/routes/users.py` et utilisee a la fois par `POST` et `PATCH`.

```python
from argon2 import PasswordHasher
_hasher = PasswordHasher()

password_hash = _hasher.hash("plaintext")  # ecriture
_hasher.verify(stored_hash, "plaintext")   # lecture (a venir, pour le login)
```

Choix d'argon2 plutot que bcrypt ou SHA-2 :
- Resistant GPU (memory-hard)
- Cout configurable (defaut sur le profil interactif suffisant)
- Salt et parametres encode dans le hash lui-meme (pas de colonne separee)

Un hash typique commence par `$argon2id$v=19$m=...`.

## API

Toutes les routes sont sous `/api/v1/users` et **non authentifiees** pour l'instant.

### Endpoints

```
GET    /api/v1/users               Liste tous les users (sans password_hash)
POST   /api/v1/users                Cree un user (name, color, password?, is_admin?)
PATCH  /api/v1/users/:id            Modifie name, color, is_admin, password
DELETE /api/v1/users/:id            Supprime
```

### Conventions JSON

Le `password_hash` n'est **jamais** retourne par l'API. Le modele pydantic
`User` (output) ne contient pas ce champ. Seul `usr_get_by_name` renvoie le
hash, pour usage interne par le futur middleware d'auth.

Sur PATCH, le champ `password` est optionnel : s'il est absent ou vide, le hash
en base reste inchange.

```jsonc
// POST /api/v1/users
{
  "name": "Dave",
  "color": "#abcdef",
  "password": "topsecret",
  "is_admin": false
}

// Reponse 201
{
  "id": "9f3e...",
  "name": "Dave",
  "color": "#abcdef",
  "is_admin": false,
  "created_at": "2026-04-07T11:00:00",
  "updated_at": "2026-04-07T11:00:00"
}
```

### Codes d'erreur

| Code | Cas |
|------|-----|
| 201 | Creation OK |
| 200 | Update OK |
| 204 | Delete OK |
| 404 | PATCH sur id inexistant |
| 409 | POST avec un name deja pris, ou PATCH renommant en un name deja pris |
| 422 | Validation pydantic (champ manquant, longueur, etc.) |

## Page d'administration

Route : `GET /admin/users`. Template : `templates/admin_users.html`. Lien dans le
menu deroulant de l'avatar (`templates/partials/header.html`).

La page liste tous les users dans une table editable :

| Colonne | Action |
|---------|--------|
| Avatar | Apercu de la couleur |
| Nom | Edition inline |
| Couleur | Edition inline (texte libre) |
| Admin | Checkbox `is_admin` |
| Mot de passe | Vide = inchange. Saisi = nouveau hash. |
| Boutons | Enregistrer, Supprimer |

Une ligne supplementaire en bas permet de creer un nouvel utilisateur.

Les actions sont des appels `fetch()` vers l'API REST decrite plus haut. Pas de
JS framework, juste des handlers inline. La page recharge apres chaque operation.

## Couplage avec la liste avatar_colors

Avant la table users, le dict `AVATAR_COLORS` etait hardcode dans
`routes/pages.py`. Il a ete supprime. A la place, `_load_all_data()` charge tous
les users (`queries.usr_get_all`) et `_build_context()` reconstruit le dict :

```python
users = data.get("users", [])
avatar_colors = {u["name"]: u["color"] for u in users}
```

Ce dict est passe aux templates sous le nom `avatar_colors`, identique a
l'ancien contrat. Les templates qui itererent dessus (notamment le `<select>`
de la modale tache, `templates/modals/task.html`) sont **inchanges** :

```jinja
<select id="task-modal-who">
  {% for name in avatar_colors %}
  <option>{{ name }}</option>
  {% endfor %}
</select>
```

Le rendu du nom dans `partials/task_card.html` retombe sur `var(--dimmed)` si le
`who` d'une tache ne correspond a aucun user en base (par ex. apres suppression
d'un user qui avait des taches).

## Ce qui manque

| Point | Etat | Tache |
|-------|------|-------|
| Login form + session cookie | **Fait** | Cf. `doc/auth-user.md`, tache #1 |
| Middleware exigant un user logge sur les routes ecriture | **Fait** | Idem (`@login_required` sur toutes les routes pages, session cookie accept\u00e9 par le middleware api keys) |
| Protection de `/admin/users` par `is_admin` | **Fait** | Idem (`admin_required()` helper) |
| API keys avec scopes par projet | **Fait** | Cf. `doc/api-keys.md`, tache #6 |
| Page de gestion des API keys `/admin/keys` | **Fait** | Cf. `doc/api-keys.md`, tache #7 |
| Reset / changement de mot de passe par l'utilisateur lui-meme | Pas fait | A planifier (le PATCH actuel impose de connaitre l'id, accessible aux admins via UI ou via la CLI `kenboard set-password`) |

## Auth API REST (Bearer keys)

Mise en place dans la release qui ferme #6 et #7. Voir `doc/api-keys.md`
pour le detail. En resume :

- Table `api_keys` (sha256 du token, label, expires_at, last_used_at,
  revoked_at) + table `api_key_projects` (scope `read|write|admin` par
  projet)
- Header `Authorization: Bearer kb_<key>`
- Cle admin globale `KENBOARD_ADMIN_KEY` dans le `.env` pour les
  endpoints non scopes par projet (`/api/v1/keys`, `/api/v1/users`,
  `/api/v1/categories`, `/api/v1/projects`)
- **Toujours strict** depuis #40 : middleware bloque toute requête API
  sans token valide, sauf pour les sessions Flask-Login (web UI) et
  les tests qui activent `LOGIN_DISABLED=True`.
- Page d'admin `/admin/keys` calquee sur `/admin/users`

Tant que ces points ne sont pas faits, considerer kenboard comme une application
**ouverte sur son reseau d'ecoute** : tout le monde a acces de creation/modification.
Le pf table sur web2 (`/usr/local/etc/pf.conf.d/kenboard`) liste les hotes
autorises a joindre le port d'ecoute, c'est la seule barriere actuelle.

## Tests

`tests/unit/test_api.py::TestUserAPI` couvre :

- list vide
- creation avec et sans password
- nom dupplique (409)
- hash argon2 (verifie le prefixe `$argon2`)
- update color
- update password (verifie que le hash change)
- update sur id inexistant (404)
- rename collision (409)
- delete

`tests/conftest.py` cree la table users et la nettoie entre tests, mais ne seed
aucun utilisateur dans le `db` fixture (volontaire : la majorite des tests sont
isoles). La migration de seed n'est appliquee qu'en prod via
`kenboard migrate`.
