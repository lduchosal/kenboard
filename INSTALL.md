# Installation

## Prerequis

- Python 3.11+
- MySQL 8.0+
- PDM (pour le developpement)

## 1. Installation depuis PyPI

```sh
pip install kenboard
```

## 2. Installation depuis les sources (developpement)

```sh
git clone <repo-url>
cd dashboard
pdm install
pdm install -G dev
```

## 3. Base de donnees MySQL 8

### Creer les bases et les utilisateurs

Se connecter en root :

```sh
mysql -u root -p
```

Creer les 2 bases de donnees :

```sql
CREATE DATABASE dashboard
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE DATABASE dashboard_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Creer les 4 utilisateurs avec le principe du moindre privilege :

```sql
-- App runtime : CRUD uniquement sur la base de production
CREATE USER 'dashboard'@'localhost'
  IDENTIFIED BY 'votre_mot_de_passe_app';
GRANT SELECT, INSERT, UPDATE, DELETE
  ON dashboard.* TO 'dashboard'@'localhost';

-- Migrations production : DDL (create/alter/drop tables)
CREATE USER 'dashboard_admin'@'localhost'
  IDENTIFIED BY 'votre_mot_de_passe_admin';
GRANT ALL PRIVILEGES
  ON dashboard.* TO 'dashboard_admin'@'localhost';

-- Test runtime : CRUD uniquement sur la base de test
CREATE USER 'dashboard_test'@'localhost'
  IDENTIFIED BY 'votre_mot_de_passe_test';
GRANT SELECT, INSERT, UPDATE, DELETE
  ON dashboard_test.* TO 'dashboard_test'@'localhost';

-- Test migrations : DDL sur la base de test
CREATE USER 'dashboard_test_admin'@'localhost'
  IDENTIFIED BY 'votre_mot_de_passe_test_admin';
GRANT ALL PRIVILEGES
  ON dashboard_test.* TO 'dashboard_test_admin'@'localhost';

FLUSH PRIVILEGES;
```

Verifier les utilisateurs :

```sql
SELECT user, host FROM mysql.user WHERE user LIKE 'dashboard%';
```

Resultat attendu :

```
+----------------------+-----------+
| user                 | host      |
+----------------------+-----------+
| dashboard            | localhost |
| dashboard_admin      | localhost |
| dashboard_test       | localhost |
| dashboard_test_admin | localhost |
+----------------------+-----------+
```

### Verifier les connexions

```sh
mysql -u dashboard -p dashboard -e "SELECT 'app OK';"
mysql -u dashboard_admin -p dashboard -e "SELECT 'migrate OK';"
mysql -u dashboard_test -p dashboard_test -e "SELECT 'test OK';"
mysql -u dashboard_test_admin -p dashboard_test -e "SELECT 'test migrate OK';"
```

### Matrice des privileges

| Utilisateur | Base | SELECT | INSERT | UPDATE | DELETE | CREATE | ALTER | DROP |
|-------------|------|:------:|:------:|:------:|:------:|:------:|:-----:|:----:|
| dashboard | dashboard | x | x | x | x | | | |
| dashboard_admin | dashboard | x | x | x | x | x | x | x |
| dashboard_test | dashboard_test | x | x | x | x | | | |
| dashboard_test_admin | dashboard_test | x | x | x | x | x | x | x |

### Configuration sur FreeBSD

Si MySQL est installe via pkg :

```sh
pkg install mysql80-server mysql80-client
sysrc mysql_enable="YES"
service mysql-server start
mysql_secure_installation
```

## 4. Configuration

Copier le fichier d'exemple et adapter les mots de passe :

```sh
cp .env.example .env
```

Quickstart minimal pour démarrer en dev :

```env
DB_HOST=localhost
DB_PORT=3306

DB_USER=dashboard
DB_PASSWORD=votre_mot_de_passe_app

DB_MIGRATE_USER=dashboard_admin
DB_MIGRATE_PASSWORD=votre_mot_de_passe_admin

DB_NAME=dashboard

DB_TEST_USER=dashboard_test
DB_TEST_PASSWORD=votre_mot_de_passe_test

DB_TEST_MIGRATE_USER=dashboard_test_admin
DB_TEST_MIGRATE_PASSWORD=votre_mot_de_passe_test_admin

DB_TEST_NAME=dashboard_test

DEBUG=true
```

### Référence complète des variables `.env`

Toutes les variables sont lues par `src/dashboard/config.py` (sauf `LOG_DIR`,
lue par `src/dashboard/logging.py`). Les variables `KEN_*` sont propres au
CLI `ken` et lues depuis `src/dashboard/ken.py` ; elles peuvent vivre dans
`.env`, dans `.ken`, ou dans l'environnement shell.

#### Base de données (obligatoires sauf défauts)

| Variable | Défaut | Description |
|---|---|---|
| `DB_HOST` | `localhost` | Hôte MySQL. |
| `DB_PORT` | `3306` | Port MySQL. |
| `DB_USER` | `dashboard` | Utilisateur runtime applicatif (CRUD only). |
| `DB_PASSWORD` | *(vide)* | Mot de passe de `DB_USER`. Obligatoire. |
| `DB_NAME` | `dashboard` | Base de données applicative. |
| `DB_MIGRATE_USER` | `dashboard_admin` | Utilisateur DDL (CREATE/ALTER/DROP), utilisé par `kenboard migrate`. |
| `DB_MIGRATE_PASSWORD` | *(vide)* | Mot de passe de `DB_MIGRATE_USER`. Obligatoire pour les migrations. |
| `DB_TEST_USER` | `dashboard_test` | Utilisateur runtime tests (CRUD only, séparé). |
| `DB_TEST_PASSWORD` | *(vide)* | Mot de passe de `DB_TEST_USER`. |
| `DB_TEST_NAME` | `dashboard_test` | Base de données de test. **Ne doit jamais** être la base prod. |
| `DB_TEST_MIGRATE_USER` | `dashboard_test_admin` | Utilisateur DDL tests, utilisé par `kenboard migrate-test`. |
| `DB_TEST_MIGRATE_PASSWORD` | *(vide)* | Mot de passe de `DB_TEST_MIGRATE_USER`. |

#### Mode & logs

| Variable | Défaut | Description |
|---|---|---|
| `DEBUG` | `false` | Mode debug Flask. `kenboard serve` exige `DEBUG=true`. En prod (`DEBUG=false`), `KENBOARD_SECRET_KEY` devient **obligatoire**. |
| `LOG_DIR` | `logs` | Répertoire où `dashboard.log` est écrit (rotated via `WatchedFileHandler`, compatible newsyslog). Défini dans `logging.py`. |

#### Sécurité / session

| Variable | Défaut | Description |
|---|---|---|
| `KENBOARD_SECRET_KEY` | *(vide)* | Clé de signature des sessions Flask. **REQUIS en prod** (`DEBUG=false`) — l'app refuse de booter sans. Générer : `python -c "import secrets; print(secrets.token_urlsafe(48))"`. La changer invalide toutes les sessions actives. |
| `KENBOARD_ADMIN_KEY` | *(vide)* | Bearer token statique pour `/api/v1/*` (cf. `doc/api-keys.md`). Nécessaire pour bootstrap le premier admin via l'API et pour les endpoints admin-only en CLI/CI. Générer : `python -c "import secrets; print('kb_' + secrets.token_urlsafe(32))"`. Vide = bearer-token admin auth désactivé (cookie session uniquement). |
| `KENBOARD_CORS_ORIGINS` | *(vide)* | Allow-list CORS pour `/api/v1/*`, origines séparées par virgule. Vide = aucun header CORS (same-origin policy, défaut sécurisé). À définir uniquement quand un client externe consomme l'API. |
| `KENBOARD_HTTPS` | `false` | Mettre à `true` quand kenboard est servi sur HTTPS (directement ou derrière un reverse proxy TLS). Active les cookies `Secure` et l'header HSTS. En dev HTTP local, laisser `false` sinon le navigateur drop le cookie de session. |

#### Auto-reporting des erreurs 500 (#517)

| Variable | Défaut | Description |
|---|---|---|
| `KENBOARD_ERROR_PROJECT_ID` | *(vide)* | UUID du projet kenboard sur lequel les exceptions 500 non gérées sont auto-créées en BUG. Vide = feature désactivée (aucun changement de comportement). |
| `KENBOARD_ERROR_WHO` | `kenboard` | Valeur `who` (assigné) des tâches BUG auto-créées. |

#### OIDC (optionnel, cf. `doc/auth-user.md`)

Les trois variables `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID` et
`OIDC_CLIENT_SECRET` doivent **toutes** être renseignées pour que la page
`/login` affiche le bouton « Sign in with OIDC » et que les routes
`/oidc/login` + `/oidc/callback` deviennent actives. Si une seule manque,
OIDC est silencieusement désactivé (fail-soft, password-only login).

| Variable | Défaut | Description |
|---|---|---|
| `OIDC_DISCOVERY_URL` | *(vide)* | URL `.well-known/openid-configuration` de l'IdP (Google, Authentik, Keycloak, ADFS, …). |
| `OIDC_CLIENT_ID` | *(vide)* | Client ID enregistré côté IdP. |
| `OIDC_CLIENT_SECRET` | *(vide)* | Client secret correspondant. |
| `OIDC_ALLOWED_EMAIL_DOMAIN` | *(vide)* | Restreint les logins OIDC aux emails de ce domaine (ex. `example.com`). Vide = tout email accepté (l'IdP contrôle qui s'authentifie). |
| `OIDC_REQUIRE_EMAIL_VERIFIED` | `true` | Exige le claim `email_verified=true`. Mettre à `false` pour ADFS qui n'émet pas ce claim (#127). |
| `OIDC_SCOPES` | `openid email profile` | Scopes OIDC demandés. Pour ADFS, utiliser `openid profile allatclaims` (ADFS n'a pas de scope `email`, l'email vient des Issuance Transform Rules). |

#### Registration (#232)

| Variable | Défaut | Description |
|---|---|---|
| `REGISTER_ALLOWED_DOMAIN` | *(vide)* | Quand renseigné, active la page `/register` et n'accepte que les emails de ce domaine (ex. `2113.ch`). Vide = registration désactivée. |

#### Email / SMTP (#231)

`SMTP_HOST` non vide active l'envoi d'emails (réinitialisation de mot de
passe, notifications). Vide = pas d'envoi (les flux qui en dépendent
sont no-op ou affichent un message).

| Variable | Défaut | Description |
|---|---|---|
| `SMTP_HOST` | *(vide)* | Hôte SMTP. Renseigner = active la feature email. |
| `SMTP_PORT` | `587` | Port SMTP (587 STARTTLS, 465 SMTPS, 25 plain). |
| `SMTP_USER` | *(vide)* | Login SMTP (souvent l'adresse email). |
| `SMTP_PASSWORD` | *(vide)* | Mot de passe SMTP. |
| `SMTP_FROM` | *(vide)* | Adresse `From:` des emails envoyés. |
| `SMTP_USE_TLS` | `true` | Utiliser STARTTLS. Mettre à `false` pour SMTP en clair (déconseillé hors réseau de confiance). |

#### Performance monitoring (#214)

Auto-file des tâches `PERF` quand une requête dépasse les budgets.
Désactivable globalement via `PERF_ENABLED=false`.

| Variable | Défaut | Description |
|---|---|---|
| `PERF_ENABLED` | `true` | Active l'instrumentation perf et la création auto de tâches. |
| `PERF_BUDGET_MS` | `500` | Budget total par requête (ms). Au-dessus = tâche créée. |
| `PERF_MAX_QUERIES` | `20` | Nombre max de requêtes SQL par requête HTTP. |
| `PERF_MAX_SQL_MS` | `300` | Temps SQL total max par requête (ms). |
| `PERF_MAX_RESPONSE_KB` | `512` | Taille max de la réponse HTTP (KB). |
| `PERF_PROJECT_ID` | *(vide)* | UUID du projet kenboard où les tâches PERF sont créées. Vide = feature en observation uniquement (logs), pas de création de tâches. |
| `PERF_TASK_WHO` | `Claude` | Valeur `who` des tâches PERF auto-créées. |
| `PERF_COOLDOWN_S` | `3600` | Délai (s) avant de re-créer une tâche pour la même route, pour éviter le spam. |

#### CLI `ken` (lu depuis `.env`, `.ken` ou l'environnement)

Le binaire `ken` lit sa config par ordre de priorité :
flag CLI > variable d'environnement > fichier `.ken` > défaut. `.ken` est
créé par `ken init <project-id>` (mode 0600, contient le token API — ne
**jamais** le commiter).

| Variable | Défaut | Description |
|---|---|---|
| `KEN_PROJECT_ID` | — | UUID du projet kenboard ciblé. |
| `KEN_BASE_URL` | — | URL de l'instance kenboard (ex. `https://kenboard.example.com`). |
| `KEN_API_TOKEN` | — | Bearer token API (`kb_…`). |
| `KEN_SYNC_DIR` | `doc/kenboard` | Répertoire de sortie pour `ken wiki sync`. |
| `KEN_WIKI_DIR` | `wiki` | Répertoire source markdown pour `ken wiki build`. |
| `KEN_WIKI_HTML_DIR` | `wiki-html` | Répertoire de sortie HTML pour `ken wiki build`. |
| `KEN_ARCHITECTURE` | `ARCHITECTURE.md` | Fichier déclarant la hiérarchie des sections wiki. |

## 5. Migrations

Appliquer les migrations sur la base de production :

```sh
kenboard migrate
```

Appliquer les migrations sur la base de test :

```sh
kenboard migrate-test
```

### Verifier les tables

```sh
mysql -u dashboard -p dashboard -e "SHOW TABLES;"
```

Resultat attendu :

```
+-----------------------+
| Tables_in_dashboard   |
+-----------------------+
| api_key_projects      |
| api_keys              |
| categories            |
| projects              |
| tasks                 |
| user_category_scopes  |
| users                 |
+-----------------------+
```

### Breaking change : migration 0015 (permissions par board)

Depuis la migration `0015.create_user_category_scopes.sql` (#197), les
utilisateurs **non administrateurs** doivent avoir un accès explicite
sur chaque board. Après l'application de la migration, ils n'ont
**aucun accès par défaut** (principe du moindre privilège).

Deux façons de gérer la transition :

1. **Assignation explicite** — un admin va sur `/admin/users`, colonne
   *Accès boards*, et assigne read/write à chaque utilisateur sur les
   boards voulus.
2. **Opt-in legacy** — pour restaurer le comportement "tout le monde
   voit tout" en lecture seule :

   ```sh
   kenboard grant-legacy-read
   ```

   Cette commande one-shot accorde `read` sur toutes les categories à
   tous les utilisateurs non-admins existants. Idempotente, donc sûre
   à relancer. Voir `doc/permissions.md` pour le détail du modèle.

### Rollback

```sh
yoyo rollback --batch \
  --database "mysql://dashboard_admin:mot_de_passe@localhost/dashboard" \
  migrations/
```

## 5b. Burndown chart (cron quotidien)

La migration `0016.create_burndown_snapshots.sql` ajoute une table pour
le suivi historique du burndown. Afin de collecter les données, un cron
quotidien doit appeler `kenboard snapshot`.

Sur FreeBSD avec le déploiement ansible, le cron est déjà configuré dans
`/usr/local/etc/cron.d/kenboard` :

```
0 2 * * * kenboard cd /usr/local/kenboard && . ./venv/bin/activate && kenboard snapshot > /var/log/kenboard_snapshot.log 2>&1
```

Pour un déploiement Linux (systemd) ou manuel, adapter le chemin :

```
0 2 * * * www-data cd /opt/kenboard && . ./venv/bin/activate && kenboard snapshot
```

Le burndown apparaîtra sur les cartes catégories (index) et les pages
catégorie après 2 jours de données collectées. Voir
`doc/burndown.md` pour le détail.

### Backfill initial

Pour un déploiement existant avec des tâches déjà créées, le burndown
peut être pré-rempli à partir des timestamps des tâches :

```sh
kenboard backfill --days 60
```

Cette commande reconstruit un historique approximatif (les tâches done
sont comptées comme "open" entre `created_at` et `updated_at`, puis
"done" après). A lancer une seule fois après la migration.

## 6. Initialiser le mot de passe de l'admin

La migration `0004.create_users.sql` insere quatre utilisateurs de
demonstration (`Q`, `Alice`, `Bob`, `Claire`) avec un `password_hash`
vide. Tant qu'aucun mot de passe n'a ete defini, **personne ne peut se
loguer** sur la web UI : `kenboard set-password` est l'unique facon
d'amorcer le premier admin.

`Q` est l'utilisateur admin (`is_admin=1`), c'est lui qu'il faut
initialiser en premier :

```sh
kenboard set-password Q
```

La commande prompt deux fois (saisie + confirmation) et refuse les mots
de passe de moins de 8 caracteres. Le hash est calcule en argon2 et
ecrit dans `users.password_hash`.

```
$ kenboard set-password Q
New password for Q: ********
Confirm: ********
Password updated for Q
```

La meme commande sert plus tard pour reinitialiser n'importe quel autre
utilisateur (`kenboard set-password Alice`, ...) ou pour changer son
propre mot de passe en CLI sans passer par la web UI.

> Si tu vois `User Q not found`, c'est que les migrations n'ont pas ete
> appliquees — repasser par l'etape 5.

## 7. Lancer le serveur

### Developpement

```sh
kenboard serve --debug
```

Le serveur demarre sur http://127.0.0.1:5000

Connecte-toi avec `Q` + le mot de passe defini a l'etape 6.

> `kenboard serve` refuse de demarrer sans `--debug` : c'est le serveur
> Werkzeug, mono-thread et non-hardene, conçu uniquement pour le dev local.
> Pour la production, voir ci-dessous.

### Production

Installer kenboard avec l'extra `prod` (gunicorn) puis lancer en mode prod :

```sh
pip install "kenboard[prod]"
kenboard prod
```

Defaut : `--bind 0.0.0.0:8080 --workers 4`. Surchargeable :

```sh
kenboard prod --bind 127.0.0.1:9090 --workers 8
```

Sous le capot, `kenboard prod` lance gunicorn avec
`dashboard.app:create_app()` comme cible WSGI. Si tu as besoin d'options
gunicorn avancees (config file, hooks, logs structures), tu peux toujours
appeler gunicorn directement :

```sh
gunicorn "dashboard.app:create_app()" --bind 0.0.0.0:8080 --workers 4 \
  --access-logfile - --error-logfile -
```

## 8. Tests

Les tests utilisent la base `dashboard_test` et ne touchent jamais
a la base de production.

```sh
pdm run test
```

Verifier la qualite complete :

```sh
sh publish.sh --quality
```

## 9. Reverse proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name dashboard.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ~* \.(css|js|png|jpg|ico)$ {
        root /path/to/dashboard;
        expires 7d;
    }
}
```

## 10. OIDC (optionnel)

Pour activer l'authentification via un fournisseur OIDC (Google,
Authentik, Keycloak, ADFS, ...), ajouter dans `.env` :

```env
OIDC_DISCOVERY_URL=https://idp.example.com/.well-known/openid-configuration
OIDC_CLIENT_ID=<client_id>
OIDC_CLIENT_SECRET=<client_secret>
```

La page `/login` affichera un bouton « Sign in with OIDC » en dessous
du formulaire password. Si les variables ne sont pas definies, kenboard
reste en mode password-only.

Options supplementaires :

```env
# Restreindre aux emails d'un domaine
OIDC_ALLOWED_EMAIL_DOMAIN=example.com

# ADFS ne renvoie pas email_verified, desactiver le check
OIDC_REQUIRE_EMAIL_VERIFIED=false
```

Ne pas oublier d'enregistrer le redirect URI cote IdP :
`https://kenboard.<domaine>/oidc/callback`

Pour Microsoft ADFS specifiquement, voir `doc/oidc-adfs.md` (provisioning
PowerShell, Issuance Transform Rules, troubleshooting).

Voir `doc/auth-user.md` section OIDC pour le detail du flow.

## 11. Verification

```sh
curl http://localhost:5000/api/v1/categories
open http://localhost:5000
```
