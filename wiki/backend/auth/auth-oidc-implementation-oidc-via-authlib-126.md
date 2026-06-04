---
id: 126
title: "AUTH / OIDC / Implémentation OIDC via Authlib"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:26
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #126 — AUTH / OIDC / Implémentation OIDC via Authlib

Suite à l'analyse de la tâche #125 (cf. son résolution block), implémenter le support OIDC en s'appuyant sur **Authlib**, en mode additif au login user/password existant.

## Objectif

Permettre à un user de se connecter via un fournisseur OIDC (Google, Authentik, Keycloak, ADFS, …) **sans toucher** au flow user/password existant : OIDC devient une option à côté de `/login`, pas un remplacement. Si l'IdP est down, le password local continue de fonctionner.

## Contraintes (à respecter, validées dans #125)

- **Réutiliser** la table `users` et le mécanisme `session_nonce` (révocation immédiate au logout). Le callback OIDC se termine par un `login_user(CurrentUser(row), remember=True)` exactement comme `/login` aujourd'hui.
- **Ne rien changer** à `src/dashboard/auth.py` (middleware bearer-token API), au rate limit `/login` (qui ne s'applique qu'au password), à la défense CSRF Origin/Referer, ni au CLI `ken`.
- Authlib doit rester l'unique nouvelle dépendance runtime (`authlib` + transitives `cryptography`, `joserfc`).
- Fail-soft : si la config OIDC est absente, le bouton n'apparaît pas et `/oidc/*` retourne 404 — kenboard reste 100 % fonctionnel sans IdP.
- Lazy-create du user : si l'email du token n'existe pas dans `users`, créer la row avec `is_admin=false`. La promotion admin reste manuelle via le panel `/admin/users`.

## Stack de test

**`oidc-provider-mock`** (Python pur, fixture pytest intégrée, pas de Docker) comme mock IdP pour les tests d'intégration. Lancé en thread via `run_server_in_thread()`, configurable par test via HTTP PUT. Ajouté au groupe `dev`.

## Étapes d'implémentation

1. **Dépendances** — `pdm add authlib` (runtime) + `pdm add -G dev oidc-provider-mock` (test)
2. **Config** — ajouter à `src/dashboard/config.py` :
   - `OIDC_DISCOVERY_URL`
   - `OIDC_CLIENT_ID`
   - `OIDC_CLIENT_SECRET`
   - `OIDC_ALLOWED_EMAIL_DOMAIN` (optionnel, défaut tout accepté)
   - `OIDC_REQUIRE_EMAIL_VERIFIED` (défaut `true`, mettre à `false` pour ADFS, cf. #127)
   - `OIDC_ENABLED` dérivé : `bool(OIDC_DISCOVERY_URL and OIDC_CLIENT_ID and OIDC_CLIENT_SECRET)`
   Documenter dans `.env.example`.
3. **Module `src/dashboard/auth_oidc.py`** :
   - `init_oidc(app)` : enregistre le client Authlib via `OAuth(app).register(name='oidc', ...)`. No-op si `not Config.OIDC_ENABLED`.
   - Blueprint avec deux routes :
     - `GET /oidc/login` → `oauth.oidc.authorize_redirect(...)`. Stocke `next` en session.
     - `GET /oidc/callback` → `authorize_access_token()` ; vérifie `email_verified` (sauf si `OIDC_REQUIRE_EMAIL_VERIFIED=false`) et le domaine ; lookup `users` par email ; lazy-create si absent ; rotate `session_nonce` ; `login_user(CurrentUser(row), remember=True)` ; redirect.
4. **Schéma DB** — vérifier si `users.email` existe. Si non : migration idempotente + `tests/conftest.py` + query `usr_get_by_email`.
5. **Template `login.html`** — bouton « Sign in with OIDC » conditionné sur `OIDC_ENABLED`.
6. **Câblage `app.py`** — `auth_oidc.init_oidc(app)` après `init_login_manager(app)`.
7. **Tests unit** (`tests/unit/test_auth_oidc.py`) — mock du client Authlib :
   - login OIDC user existant → session posée, `session_nonce` rotaté
   - login OIDC user inconnu → lazy-create `is_admin=false`
   - `email_verified=false` → 403
   - domaine non autorisé → 403
   - `OIDC_ENABLED=false` → 404 + bouton absent
8. **Tests intégration** (`tests/integration/test_auth_oidc.py`) — `oidc-provider-mock` en fixture :
   - flow complet auth code → callback → `login_user` → session vérifiée
   - PKCE S256 validé end-to-end
   - claims configurables par test (PUT sur le mock)
9. **Doc** — `doc/auth-user.md` section OIDC, `INSTALL.md` section OIDC, `.env.example`.
10. **Quality gates** — `pdm run check` vert.

## Garde-fous techniques

- PKCE S256 activé via `client_kwargs`
- Leeway 120s sur validation `id_token` (Authlib default, clock skew)
- JWKS caché en mémoire au niveau du metadata client
- Pas de refresh token en v1

## Hors scope

- Multi-IdP simultané (trivial via `oauth.register()` plus tard)
- Logout côté IdP (`end_session_endpoint`)
- Mapping groupes IdP → `is_admin`
- SCIM, sync profil, photo

## Acceptation

- Sans `OIDC_*` : aucune régression, bouton absent, `/oidc/*` → 404
- Avec IdP configuré : click → flow → user créé/logué → `/logout` invalide la session
- Aucune ligne touchée dans `auth.py` ni `ken.py`
- `pdm run check` vert

## Référence

- Analyse : #125 (review)
- Validation ADFS : #127 (todo, bloquée par celle-ci)
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
