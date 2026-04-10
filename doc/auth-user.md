# Authentification utilisateur (login + session)

Spec validée pour la tâche #1 (`AUTH / Password authentification`). Voir
aussi `doc/authentication.md` (état pré-#1) et `doc/api-keys.md` (auth
API REST).

## Objectif

Protéger l'accès au kenboard par un login user/password. Une fois logué,
l'utilisateur navigue librement dans la web UI ; sans session, tout est
inaccessible. Permet enfin de basculer `KENBOARD_AUTH_ENFORCED=true`
(mode strict) sans casser la web UI.

Hors scope :
- Reset password par email (pas de SMTP)
- 2FA, OAuth, SSO
- Self-signup (les users sont créés par un admin via `/admin/users`)

## Décisions arbitrées

| Sujet | Choix |
|---|---|
| Lib | **Flask-Login** |
| Bootstrap 1er password | **CLI `kenboard set-password <name>`** |
| Strict mode flip | **Dans la même release que #1** (atomic) |
| Lifetime cookie | **30 jours absolus** |
| `who` des tasks | **Dropdown libre, pré-sélectionne le user logué** |
| Logout | **Form POST inline** |
| Page login | **Plein écran minimaliste** |

## Surface

### Routes nouvelles

```
GET  /login            page HTML avec form (name + password)
POST /login            valide credentials, set cookie, redirect next ou /
POST /logout           clear cookie, redirect /login
```

### Pages protégées

Toutes les routes HTML (`/`, `/cat/<id>.html`, `/admin/users`,
`/admin/keys`) deviennent protégées via `@login_required`. Sans session
valide → redirect 302 vers `/login?next=<original_path>`.

`/admin/*` exigent en plus `current_user.is_admin = True` → 403 sinon.

### Endpoints API

Le middleware `auth.py` accepte désormais **deux principaux** :
- **Bearer token** (api_key, comme aujourd'hui)
- **Session cookie** valide (user logué)

Quand la session est valide, le user a un accès **équivalent admin
global** : il passe tous les checks (admin-only endpoints + scopes
read/write/admin sur n'importe quel projet).

## Stack technique

### Flask-Login

Une nouvelle dépendance dans `pyproject.toml`. API utilisée :

- `LoginManager` initialisé dans `app.py` après les blueprints
- `@login_required` décorateur sur les routes pages
- `current_user` proxy global pour récupérer l'user courant
- `login_user(user, remember=True, duration=timedelta(days=30))`
- `logout_user()`
- `@login_manager.user_loader` qui charge un user par id depuis la DB
- `UserMixin` pour wrapper la row DB en objet Flask-Login compatible

### Cookie

- Signé par `app.secret_key` (nouvelle var `KENBOARD_SECRET_KEY`)
- HTTP-only, SameSite=Lax (défauts Flask)
- Durée 30 jours via `REMEMBER_COOKIE_DURATION = timedelta(days=30)`
- Pas de `Secure` flag forcé en dev (HTTP local) — nginx termine TLS
  en prod

### `CurrentUser`

```python
class CurrentUser(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.name = row["name"]
        self.is_admin = bool(row["is_admin"])

@login_manager.user_loader
def load_user(user_id):
    conn = db.get_connection()
    try:
        row = db.load_queries().usr_get_by_id(conn, id=user_id)
    finally:
        conn.close()
    return CurrentUser(row) if row else None
```

### Middleware `auth.py`

Intégration : avant la logique bearer token, checker
`current_user.is_authenticated`. Si oui → laisser passer.

```python
def _enforce():
    if not request.path.startswith("/api/v1/"):
        return None
    if current_user and current_user.is_authenticated:
        return None
    # ... logique bearer token existante
```

### Pages HTML

```python
@bp.route("/")
@login_required
def index(): ...

@bp.route("/admin/users")
@login_required
def admin_users():
    if not current_user.is_admin:
        abort(403)
    ...
```

### Page login

`templates/login.html` plein écran centré :
- KENBOARD en titre
- Form POST `/login` : input name, input password, bouton
- Erreur inline si bad credentials
- CSS minimaliste réutilisant les variables existantes

### Logout

Le placeholder `<a href="#">Deconnexion</a>` dans `header.html` devient :

```html
<form method="post" action="/logout" style="display:inline">
  <button type="submit" class="logout-link">Deconnexion</button>
</form>
```

Stylé pour ressembler à un lien (pas de border, dim color).

### `who` des tasks

`task.html` modal :
```html
<select id="task-modal-who">
  {% for name in avatar_colors %}
  <option {% if name == current_user.name %}selected{% endif %}>{{ name }}</option>
  {% endfor %}
</select>
```

Le user logué est sélectionné par défaut. Reste éditable.

### CLI `kenboard set-password`

Nouvelle sous-commande dans `cli.py` :

```python
@cli.command()
@click.argument("name")
def set_password(name: str) -> None:
    """Set or reset a user's password (prompt for value)."""
    import getpass
    from argon2 import PasswordHasher
    pw = getpass.getpass(f"New password for {name}: ")
    pw2 = getpass.getpass("Confirm: ")
    if pw != pw2:
        click.echo("Passwords do not match", err=True)
        sys.exit(1)
    if len(pw) < 8:
        click.echo("Password must be at least 8 chars", err=True)
        sys.exit(1)
    h = PasswordHasher().hash(pw)
    conn = db.get_connection()
    try:
        row = db.load_queries().usr_get_by_name(conn, name=name)
        if not row:
            click.echo(f"User {name} not found", err=True)
            sys.exit(1)
        db.load_queries().usr_update_password(
            conn, id=row["id"], password_hash=h
        )
        click.echo(f"Password updated for {name}")
    finally:
        conn.close()
```

## Variables d'environnement

| Variable | Défaut | Rôle |
|---|---|---|
| `KENBOARD_SECRET_KEY` | `""` (force fail au boot quand `DEBUG=false`) | Secret Flask pour signer le cookie session. Généré avec `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. À mettre dans le vault ansible. |

> Note : `KENBOARD_AUTH_ENFORCED` a été supprimé (tâche #40). La middleware
> est maintenant toujours stricte ; les tests désactivent via
> `app.config["LOGIN_DISABLED"] = True`.

## Rate limiting (#44)

`POST /login` est rate-limité par IP via `flask-limiter` :

- **5 requêtes / minute** (burst)
- **20 requêtes / heure** (long terme)

Les deux limites sont AND-combinées. Les logins **réussis** (302) ne
décomptent pas du budget grâce à `deduct_when=lambda r: r.status_code != 302`,
donc un utilisateur qui se trompe 4 fois puis tape juste à la 5e ne brûle
pas son quota horaire.

Quand la limite est dépassée :

- Le browser reçoit la page `login.html` re-rendue avec le message
  `"Trop de tentatives. Réessaye dans une minute."` et un statut HTTP 429.
- Un événement `auth.brute_force_attempt` est loggé via structlog avec
  l'IP et la limite touchée.
- Les headers `X-RateLimit-*` et `Retry-After` sont émis (côté script).

Stockage par défaut : in-memory (`memory://`). Une instance par worker
Gunicorn — c'est volontairement approximatif. Pour passer à une vraie
limite globale, définir `RATELIMIT_STORAGE_URI=redis://...` côté env
(flask-limiter le lit automatiquement).

Tests : `tests/unit/test_auth_user.py::TestLoginRateLimit`. Les autres
tests désactivent le limiter via `app.config["RATELIMIT_ENABLED"] = False`
(set par défaut dans `tests/conftest.py`).

## Tests

- **Unit** (`tests/unit/test_auth_user.py`) :
  - `set_password` CLI : prompt, mismatch, < 8 chars, user not found, OK
  - Login OK / bad password / unknown user / empty form
  - Logout efface la session
  - `@login_required` redirige vers /login pour anonymes
  - `/admin/*` exige `is_admin` (403 sinon)
  - Le middleware `auth.py` accepte une session cookie comme principal
    (équivalent admin)
  - Le `who` du task modal pré-sélectionne le user logué
- **E2E** (`tests/e2e/test_auth_user.py`) :
  - Anonyme `/` → redirect /login
  - Login Q + password → redirect / + table chargée
  - Logout → redirect /login + nouvel accès `/` redirige
  - Login non-admin → `/admin/users` retourne 403
  - Login Q → `/admin/users` rendu OK

Toute la suite e2e existante doit également continuer à passer : il
faudra une fixture qui crée Q + password + login session pour les tests
qui exercent la web UI.

## Étapes d'implémentation

1. ✅ Spec validée
2. Ajout `flask-login>=0.6` dans `pyproject.toml dependencies`
3. Ajout `KENBOARD_SECRET_KEY` dans `Config`, fail-fast au boot si vide
   et `KENBOARD_AUTH_ENFORCED=true`
4. Module `dashboard/auth_user.py` : `LoginManager`, `CurrentUser`,
   `user_loader`, blueprint `/login` `/logout`
5. Template `login.html` + CSS
6. `header.html` : form logout inline
7. `@login_required` sur toutes les routes pages, `is_admin` check
   sur `/admin/*`
8. Modif `auth.py` : accepter session cookie comme principal admin
9. Modif `task.html` modal : pré-sélection du user logué
10. CLI `kenboard set-password <name>`
11. Mise à jour des fixtures de test (e2e : login automatique pour les
    tests qui touchent la web UI)
12. Tests unit + e2e
13. Mise à jour `doc/authentication.md` (section "ce qui manque")
14. **Activation `KENBOARD_AUTH_ENFORCED=true`** + ajout
    `KENBOARD_SECRET_KEY` dans le `.env` rendu par ansible
15. Publish 0.1.x

## Bootstrap (procédure prod)

Sur web2, après déploiement de la release :

```sh
# 1. Set le password de Q (admin existant en DB)
service kenboard stop
su -m kenboard -c "venv/bin/kenboard set-password Q"
service kenboard start

# 2. Tester le login
curl -i https://www.kenboard.2113.ch/login   # → 200 page login
# Login via browser, vérifier que tout marche

# 3. Si OK, le service tourne en mode strict, fini.
```

Si ça ne marche pas, rollback : flip `KENBOARD_AUTH_ENFORCED=false`
dans le `.env` ansible et redéployer (`ansible-playbook
~/ansible/kenboard.yml --tags dotenv`).

## OIDC (optionnel, #126)

Kenboard supporte l'authentification via un fournisseur OIDC
(Google, Authentik, Keycloak, Microsoft ADFS, ...) **en complément**
du login user/password. L'OIDC est opt-in : si les variables d'env ne
sont pas renseignées, kenboard reste en mode password-only.

### Activation

Renseigner dans `.env` (cf. `.env.example`) :

```env
OIDC_DISCOVERY_URL=https://idp.example.com/.well-known/openid-configuration
OIDC_CLIENT_ID=<client_id>
OIDC_CLIENT_SECRET=<client_secret>
```

Options supplémentaires :

| Variable | Défaut | Rôle |
|---|---|---|
| `OIDC_DISCOVERY_URL` | (vide) | URL du discovery document OIDC |
| `OIDC_CLIENT_ID` | (vide) | Client ID enregistré côté IdP |
| `OIDC_CLIENT_SECRET` | (vide) | Client secret |
| `OIDC_ALLOWED_EMAIL_DOMAIN` | (vide = tout) | Restreindre aux emails d'un domaine |
| `OIDC_REQUIRE_EMAIL_VERIFIED` | `true` | Mettre à `false` pour ADFS (pas de claim `email_verified`) |

Quand les trois variables requises sont définies, la page `/login`
affiche un bouton « Sign in with OIDC » sous le formulaire password.

### Flow

1. Le user clique « Sign in with OIDC ».
2. Kenboard redirige vers l'IdP (`/oidc/login` → IdP authorize endpoint).
3. L'IdP authentifie le user et redirige vers `/oidc/callback` avec un
   authorization code.
4. Kenboard échange le code contre un `id_token` via Authlib (PKCE S256).
5. Le callback vérifie :
   - `email` présent dans le token (sinon erreur)
   - `email_verified` (sauf si `OIDC_REQUIRE_EMAIL_VERIFIED=false`)
   - domaine email (si `OIDC_ALLOWED_EMAIL_DOMAIN` est défini)
6. Lookup `users.email` :
   - Si trouvé → login avec le user existant
   - Si absent → lazy-create un user (nom = claim `name`, `is_admin=false`,
     couleur aléatoire, `password_hash` vide)
7. Rotation `session_nonce`, `login_user(user, remember=True)`.
8. Redirect vers la page d'origine.

### Coexistence avec le login password

- Le flow password (`/login` POST) est **inchangé** : mêmes routes,
  même rate limit, même `session_nonce`.
- `/logout` invalide la session kenboard (rotation nonce) mais ne
  déconnecte PAS côté IdP (`end_session_endpoint` hors scope v1).
- L'API bearer-token (`auth.py`) n'est **pas touchée** : les api_keys
  et le `KENBOARD_ADMIN_KEY` fonctionnent comme avant.
- Si l'IdP est down ou mal configuré, le bouton OIDC ne fonctionne
  pas mais le login password reste disponible (fail-soft).

### Migration DB

La migration `0012.add_users_email.sql` ajoute une colonne `email
VARCHAR(255) NULL` à la table `users` avec un index unique (NULLs
autorisés pour les users existants créés par password).

Appliquer : `kenboard migrate` (production) ou `kenboard migrate-test`
(test).

### Tests

- **Unit** (`tests/unit/test_auth_oidc.py`) : 9 tests, mock du client
  Authlib. Couvre : OIDC disabled → 404, login user existant, lazy-create,
  email_verified rejeté/accepté, domaine rejeté, pas d'email, rotation
  nonce.
- **Intégration** (`tests/integration/test_auth_oidc.py`) : 2 tests avec
  `oidc-provider-mock` (mock IdP Python en thread, pas de Docker).
  Couvre : redirect vers IdP, callback complet avec token → session.

### Fournisseurs documentés

| IdP | Discovery URL | Doc |
|---|---|---|
| `oidc-provider-mock` | `http://localhost:<port>/.well-known/...` | Tests intégration |
| Microsoft ADFS | `https://<host>/adfs/.well-known/...` | [`doc/oidc-adfs.md`](oidc-adfs.md) |

### Hors scope v1

- Multi-IdP simultané (un seul `oauth.register` en v1)
- Logout côté IdP (`end_session_endpoint`)
- Mapping groupes IdP → `is_admin`
- Refresh token (la session Flask-Login a sa propre durée de vie)
- SCIM / sync profil / photo
