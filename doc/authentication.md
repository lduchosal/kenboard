# Authentication — schema users + politique de mot de passe

Ce document decrit la table `users`, la politique de mot de passe et
le hashing argon2. Pour le flow login / session / OIDC, voir
[`auth-user.md`](auth-user.md). Pour l'auth API REST par bearer
token, voir [`api-keys.md`](api-keys.md). Pour les permissions par
categorie / projet, voir [`permissions.md`](permissions.md).

## Schema

### users

| Colonne | Type | Description |
|---------|------|-------------|
| id | VARCHAR(36) PK | UUID, genere par MySQL `UUID()` au seed et par `uuid.uuid4()` au runtime |
| name | VARCHAR(100) UNIQUE | Identifiant humain (egalement utilise dans `tasks.who`) |
| email | VARCHAR(255) NULL UNIQUE | Optionnel pour les users password-only ; requis pour OIDC et reset-password (#231) |
| color | VARCHAR(50) | Couleur d'avatar (hex `#0969da` ou variable CSS) |
| password_hash | VARCHAR(255) | Hash argon2, vide tant qu'aucun mot de passe defini |
| is_admin | TINYINT(1) | Drapeau admin (0 ou 1) |
| session_nonce | CHAR(32) | Anti-replay des cookies. Rotate au logout, password reset, OIDC link (#198) |
| created_at | DATETIME | Auto |
| updated_at | DATETIME | Auto on update |

Migrations :
- `0004.create_users.sql` — cree la table + insere les 4 utilisateurs
  historiques (Q, Alice, Bob, Claire) avec `password_hash` vide. Q est
  seed avec `is_admin = 1`.
- `0008` / `0009` (recovery) — `session_nonce`.
- `0012` / `0013` (recovery) — `email` + index unique.

Le nom de l'utilisateur est aussi la cle utilisee dans `tasks.who`
(texte libre, sans foreign key). Renommer un user via PATCH ne
propage pas le nouveau nom dans les tasks existantes.

## Politique de mot de passe (#198)

Tout mot de passe saisi via l'API (`POST /api/v1/users/<id>/password`,
`POST /api/v1/users/<id>/reset-password`, `POST /register`,
`POST /reset-password/<token>`) ou la CLI (`kenboard set-password`)
passe par `dashboard.password_strength.validate_password_strength()` :

| Critère | Valeur | Source |
|---|---|---|
| Longueur minimale | **8** caractères | `MIN_LENGTH` (`password_strength.py`) |
| Score zxcvbn | **≥ 3 / 4** ("safely unguessable") | `MIN_SCORE` |

La double vérification (longueur + zxcvbn) bloque les mots de passe
courants même quand ils sont longs. Exemples rejetés : `password`,
`Password123`, `abcdefghij`, `qwerty1234`. Exemples acceptés :
`correct horse battery staple`, `Xk9$mQ2!vL`, toute chaîne de 10+
caractères avec un mix lettres/chiffres/symboles.

Les erreurs de validation incluent le feedback de zxcvbn (warning +
suggestions) afin que l'utilisateur sache comment corriger :

```
Password is too weak (strength 1/4, need 3/4). This is a very common password.
Add another word or two. Uncommon words are better.
```

La logique vit dans un module dédié pour qu'il n'y ait qu'une seule
source de vérité entre Pydantic (`PasswordChange`, `PasswordReset`,
`UserCreate`) et la CLI `set-password`.

## Hash de mot de passe

Argon2 via `argon2-cffi`. Une instance partagee `PasswordHasher()` est
definie dans `src/dashboard/routes/users.py` et utilisee a la fois par
`POST` et `PATCH`.

```python
from argon2 import PasswordHasher
_hasher = PasswordHasher()

password_hash = _hasher.hash("plaintext")  # ecriture
_hasher.verify(stored_hash, "plaintext")   # lecture (login + change-password)
```

Choix d'argon2 plutot que bcrypt ou SHA-2 :
- Resistant GPU (memory-hard)
- Cout configurable (defaut sur le profil interactif suffisant)
- Salt et parametres encode dans le hash lui-meme (pas de colonne separee)

Un hash typique commence par `$argon2id$v=19$m=...`.

## API utilisateurs (résumé)

Endpoints sous `/api/v1/users`, **admin only** (cookie session avec
`is_admin = 1` ou `KENBOARD_ADMIN_KEY`). Cf. [`api.md`](api.md) pour
le détail.

```
GET    /api/v1/users                        Liste tous les users + scopes
POST   /api/v1/users                        Cree (rate-limit 10/h)
PATCH  /api/v1/users/:id                    Modifie name, color, is_admin (PAS le password)
DELETE /api/v1/users/:id                    Supprime
POST   /api/v1/users/:id/password           Self-service password change (owner only)
POST   /api/v1/users/:id/reset-password     Admin reset (rate-limit 5/h)
PUT    /api/v1/users/:id/scopes             Replace les scopes par categorie
```

Le `password_hash` n'est **jamais** retourne par l'API. Le modele
pydantic `User` (output) ne contient pas ce champ. Seul
`usr_get_by_name` renvoie le hash, pour usage interne par le
middleware d'auth (`auth_user.py`).

`UserUpdate` ne contient PAS de champ `password` (#53) — pour changer
un mot de passe il faut passer par `/password` (self) ou
`/reset-password` (admin).

## Page d'administration

Route : `GET /admin/users`. Template : `templates/admin_users.html`.
Lien dans le menu deroulant de l'avatar
(`templates/partials/header.html`).

La page liste tous les users dans une table editable :

| Colonne | Action |
|---------|--------|
| Avatar | Apercu de la couleur |
| Nom | Edition inline |
| Email | Edition inline |
| Couleur | Edition inline (texte libre) |
| Admin | Checkbox `is_admin` |
| Accès boards | Badges `[Category: scope]`, click pour editer (#197) |
| Mot de passe | Bouton « Reset » qui appelle `POST /api/v1/users/:id/reset-password` |
| Boutons | Enregistrer, Supprimer |

Une ligne supplementaire en bas permet de creer un nouvel utilisateur.
Les actions sont des appels `fetch()` vers l'API REST. Pas de JS
framework, juste les modules ES de `static/js/`. La page recharge
apres chaque operation.

## Couplage avec la liste avatar_colors

Avant la table users, le dict `AVATAR_COLORS` etait hardcode dans
`routes/pages.py`. Il a ete supprime. A la place, `_load_all_data()`
charge tous les users (`queries.usr_get_all`) et `_build_context()`
reconstruit le dict :

```python
users = data.get("users", [])
avatar_colors = {u["name"]: u["color"] for u in users}
```

Ce dict est passe aux templates sous le nom `avatar_colors`, identique
a l'ancien contrat. Les templates qui itererent dessus (notamment le
`<select>` de la modale tache, `templates/modals/task.html`) sont
**inchanges** :

```jinja
<select id="task-modal-who">
  {% for name in avatar_colors %}
  <option {% if name == current_user.name %}selected{% endif %}>{{ name }}</option>
  {% endfor %}
</select>
```

Le user logué est preselectionné par défaut (#1). Le rendu du nom dans
`partials/task_card.html` retombe sur `var(--dimmed)` si le `who`
d'une tache ne correspond a aucun user en base.

## Tests

`tests/unit/test_api.py::TestUserAPI` couvre :

- list vide
- creation avec et sans password
- nom dupplique (409)
- hash argon2 (verifie le prefixe `$argon2`)
- update color / is_admin (mais pas password, c'est sur l'endpoint dedie)
- update sur id inexistant (404)
- rename collision (409)
- delete

`tests/unit/test_auth_user.py` couvre les flows login / logout / reset
/ register / scope check (cf. [`auth-user.md`](auth-user.md)).

`tests/conftest.py` cree la table users et la nettoie entre tests,
mais ne seed aucun utilisateur dans la fixture `db` (volontaire : la
majorite des tests sont isoles). La migration de seed n'est appliquee
qu'en prod via `kenboard migrate`.
