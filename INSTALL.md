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
+---------------------+
| Tables_in_dashboard |
+---------------------+
| categories          |
| projects            |
| tasks               |
+---------------------+
```

### Rollback

```sh
yoyo rollback --batch \
  --database "mysql://dashboard_admin:mot_de_passe@localhost/dashboard" \
  migrations/
```

## 6. Lancer le serveur

### Developpement

```sh
kenboard serve --debug
```

Le serveur demarre sur http://127.0.0.1:5000

### Production

```sh
pip install gunicorn
gunicorn "dashboard.app:create_app()" --bind 0.0.0.0:8080 --workers 4
```

## 7. Tests

Les tests utilisent la base `dashboard_test` et ne touchent jamais
a la base de production.

```sh
pdm run test
```

Verifier la qualite complete :

```sh
sh publish.sh --quality
```

## 8. Generer les pages statiques (optionnel)

```sh
kenboard build
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

## 10. Verification

```sh
curl http://localhost:5000/api/v1/categories
open http://localhost:5000
```
