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

Editer `.env` :

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
