# Installation

## Prerequis

- Python 3.11+
- MySQL 8.0+
- PDM (pour le developpement)

## 1. Installation depuis PyPI

```sh
pip install dashboard
```

## 2. Installation depuis les sources (developpement)

```sh
git clone <repo-url>
cd dashboard
pdm install
pdm install -G dev
```

## 3. Base de donnees MySQL 8

### Creer la base et l'utilisateur

```sql
-- Se connecter en root
mysql -u root -p
```

```sql
-- Creer la base de donnees
CREATE DATABASE dashboard
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Creer l'utilisateur
CREATE USER 'dashboard'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';

-- Accorder les privileges
GRANT ALL PRIVILEGES ON dashboard.* TO 'dashboard'@'localhost';

-- Appliquer
FLUSH PRIVILEGES;

-- Verifier
SHOW GRANTS FOR 'dashboard'@'localhost';
```

### Verifier la connexion

```sh
mysql -u dashboard -p dashboard -e "SELECT VERSION();"
```

Resultat attendu :

```
+-----------+
| VERSION() |
+-----------+
| 8.x.x    |
+-----------+
```

### Configuration sur FreeBSD

Si MySQL est installe via pkg :

```sh
pkg install mysql80-server mysql80-client
sysrc mysql_enable="YES"
service mysql-server start
mysql_secure_installation
```

## 4. Configuration

Copier le fichier d'exemple et adapter :

```sh
cp .env.example .env
```

Editer `.env` :

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=dashboard
DB_PASSWORD=votre_mot_de_passe
DB_NAME=dashboard
DEBUG=true
```

## 5. Migrations

Appliquer les migrations pour creer les tables :

```sh
dashboard migrate
```

Ou manuellement :

```sh
yoyo apply --database "mysql://dashboard:votre_mot_de_passe@localhost/dashboard" migrations/
```

### Verifier les tables

```sql
mysql -u dashboard -p dashboard -e "SHOW TABLES;"
```

Resultat attendu :

```
+---------------------+
| Tables_in_dashboard |
+---------------------+
| _yoyo_log           |
| _yoyo_migration     |
| _yoyo_version       |
| categories          |
| projects            |
| tasks               |
+---------------------+
```

### Rollback

Pour annuler la derniere migration :

```sh
yoyo rollback --database "mysql://dashboard:votre_mot_de_passe@localhost/dashboard" migrations/
```

## 6. Lancer le serveur

### Developpement

```sh
dashboard serve --debug
```

Le serveur demarre sur http://127.0.0.1:5000

### Production

```sh
dashboard serve --host 0.0.0.0 --port 8080
```

Pour la production, utiliser un serveur WSGI :

```sh
pip install gunicorn
gunicorn "dashboard.app:create_app()" --bind 0.0.0.0:8080 --workers 4
```

## 7. Generer les pages statiques

Si vous souhaitez generer des pages HTML statiques (sans serveur) :

```sh
dashboard build
```

Les fichiers sont generes dans `index.html` et `cat/`.

## 8. Importer des donnees existantes

Pour importer les donnees de `data.json` dans MySQL :

```sh
dashboard import-data
```

(A implementer)

## 9. Reverse proxy (Nginx)

Exemple de configuration Nginx :

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

    # Fichiers statiques (optionnel, pour les performances)
    location ~* \.(css|js|png|jpg|ico)$ {
        root /path/to/dashboard;
        expires 7d;
    }
}
```

## 10. Verification

Tester que tout fonctionne :

```sh
# API
curl http://localhost:5000/api/v1/categories

# Dashboard
open http://localhost:5000
```
