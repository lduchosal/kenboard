---
id: 1
title: "AUTH / Password authentification"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:28:56
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1 — AUTH / Password authentification

Un user password doit protéger le kenboard. Implémenté avec Flask-Login.

## Spec

`doc/auth-user.md` (validée par 7 questions OPEN soumises à Q via AskUserQuestion).

Décisions retenues :
- **Lib** : Flask-Login (standard, 1 dep, API connue)
- **Bootstrap 1er password** : nouvelle CLI `kenboard set-password <name>`
- **Strict mode flip** : dans la même release que #1 (atomic)
- **Lifetime cookie** : 30 jours absolus
- **who des tasks** : dropdown libre, pré-sélectionne le user logué
- **Logout** : form POST inline (pas vulnérable au CSRF via lien)
- **Login page** : plein écran minimaliste

## Livraisons (release 0.1.16)

- `pyproject.toml` : `flask-login>=0.6` ajouté aux deps
- `config.py` : nouvelle var `KENBOARD_SECRET_KEY` (fail-fast au boot si vide ET strict mode activé)
- `auth_user.py` (~170 lignes) : `LoginManager` config, `CurrentUser(UserMixin)`, `_load_user`, `_unauthorized` handler avec next param, `_verify_credentials` argon2, `_is_safe_url` anti open-redirect, blueprint `/login` `/logout`, helper `admin_required()` qui respecte `LOGIN_DISABLED` pour les tests
- `templates/login.html` : page plein écran centrée avec form name/password, erreur inline
- `templates/partials/header.html` : avatar du user logué (couleur, initiale), menu admin conditionnel sur `is_admin`, form POST inline pour Déconnexion
- `templates/modals/task.html` : `who` pré-sélectionne `current_user.name`
- `routes/pages.py` : `@login_required` sur `/`, `/cat/<id>.html`, `/admin/users`, `/admin/keys` ; `admin_required()` sur les /admin/*
- `auth.py` (middleware api keys) : accepte une session cookie comme principal full-access (équivalent admin), checké AVANT la logique bearer token
- `app.py` : `init_login_manager()` avant `init_auth()` ; `HTTPException` exclue du handler 500 pour préserver les vrais codes 401/403
- `cli.py` : nouvelle commande `kenboard set-password <name>` avec getpass + confirmation + min 8 chars + argon2
- `style.css` : styles `.login-body`, `.login-card`, `.login-form`, `.login-error`, `.logout-link`, `.logout-form`

## Tests

- `tests/unit/test_auth_user.py` : **27 tests** (helpers `_is_safe_url`, `_verify_credentials`, `TestLoginFlow` GET/POST/redirect/safe_next, `TestPageProtection` redirects + admin check, `TestApiAcceptsSession` session cookie débloque l'API en strict mode pour admin et non-admin)
- `tests/e2e/test_auth_user.py` : **6 tests Playwright** (anonymous redirect, login OK, bad password popup, logout clears, normal user 403 sur /admin/users, admin user OK sur /admin/users) — utilisent un live_server dédié sur port 5098 avec `LOGIN_DISABLED=False`
- `tests/conftest.py` : 2 nouvelles autouse session-scoped fixtures (`patch_db_connection` pour assurer le monkey-patch indépendamment de `app`, `LOGIN_DISABLED=True` sur l'app de test pour ne pas casser les 162 tests existants)

## État

- 195 tests verts (162 pré-existants + 33 nouveaux pour #1)
- Tous les checks qualité passent
- **0.1.16 publié** : https://pypi.org/project/kenboard/0.1.16/, commit `a0cd5fc`, tag `kenboard-0.1.16`

## Bootstrap prod (à faire après `service kenboard update`)

```sh
# 1. Set password Q via la CLI
service kenboard stop
su -m kenboard -c "venv/bin/kenboard set-password Q"

# 2. Ajouter dans le vault ansible :
#    KENBOARD_SECRET_KEY=<openssl rand -base64 32>
#    KENBOARD_AUTH_ENFORCED=true
ansible-playbook ~/ansible/kenboard.yml --tags dotenv

service kenboard start

# 3. Tester : visiter https://www.kenboard.2113.ch/ → doit redirect vers /login
```

Si bug : `KENBOARD_AUTH_ENFORCED=false` dans le vault et redéployer.
---

[← retour à backend/auth](index.md) · [voir log](../../log.md)
