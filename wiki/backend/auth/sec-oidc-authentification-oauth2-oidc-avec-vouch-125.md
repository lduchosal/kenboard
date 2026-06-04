---
id: 125
title: "SEC / OIDC / Authentification OAuth2 OIDC avec VOUCH"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:26
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #125 — SEC / OIDC / Authentification OAuth2 OIDC avec VOUCH

Analyser l'intégration possible entre VOUCH PROXY et KENBOARD
https://github.com/vouch/vouch-proxy
Mettre à jour cette tâche avec l'analyse
Etudier d'autres pistes (python, pip ou flask native)

---

## Analyse

### Contexte rappelé

- App Flask 3.1 + MySQL, mono-host (web2, FreeBSD), nginx → gunicorn → Flask.
- Auth en place (`src/dashboard/auth_user.py`) : Flask-Login + argon2 + `users.session_nonce` (révocation cookie au logout), rate limit `/login` (5/min, 20/h), CSRF via Origin/Referer, cookie SameSite=Lax + HttpOnly + Secure si HTTPS.
- Le middleware `auth.py` partage une seule porte d'entrée pour la cookie session **et** les bearer tokens d'API (api_keys par projet + `KENBOARD_ADMIN_KEY`).
- Q est l'unique user effectif, pas de self-signup, pas d'IdP existant.
- Préférence projet : dépendances minimales (le CLI `ken` utilise `urllib` plutôt que `requests`).

### Piste 1 — Vouch Proxy (https://github.com/vouch/vouch-proxy)

#### Architecture

Vouch est un daemon Go qui s'insère **devant** l'app via le module `auth_request` de nginx :

```
browser → nginx (auth_request /validate → vouch:9090) → gunicorn → Flask
                              ↓ 401
                              @error401 → 302 vers vouch:/login → IdP → vouch:/auth → cookie JWT
```

Le cookie de session appartient à Vouch sur un domaine parent (`.2113.ch`), partagé avec kenboard. Après auth réussie, nginx récupère via `auth_request_set` les headers injectés par Vouch (`X-Vouch-User`, `X-Vouch-IdP-Claims-*`, optionnellement `X-Vouch-IdP-IdToken`) et les forwarde à Flask.

Providers supportés : Google, GitHub, Okta, Azure AD, Keycloak, Authentik, Discord, ADFS, Gitea, etc. — n'importe quel OIDC standard.

#### Maintenance

- Dernier tag **v0.45.1** (2025-07-25), avant ça v0.44.0 en 2024 — cadence ~annuelle, pas mort mais lent.
- 50 issues ouvertes, 3247 stars, MIT.
- Pas de package FreeBSD officiel : binaire Go statique à compiler ou récupérer depuis les releases GitHub.

#### Intégration kenboard

Pour honorer Vouch dans kenboard il faudrait :

1. Faire confiance à `X-Vouch-User` côté Flask (réécrire le `@before_request` pour synthétiser un `current_user` à partir du header).
2. Lazy-create / lookup d'une row dans `users` à chaque requête (ou cache mémoire) puisque Vouch ne connaît pas la table interne.
3. **Désactiver la moitié de `auth_user.py`** : la route `/login`, le rate limit, la rotation `session_nonce` au logout (Vouch a son propre `/logout?url=...` qui détruit le cookie JWT côté Vouch). On garderait `is_admin` mais perdrait le contrôle fin sur la révocation.
4. Décider du sort de `/api/v1/*` : soit Vouch protège tout (et le CLI `ken` doit traverser le flow OIDC, ce qui est cassant pour un client headless), soit nginx sépare les locations et seul `/` passe par `auth_request`. La 2ᵉ option garde les bearer tokens mais double la surface d'auth.
5. Stand up un **IdP** : Vouch ne fait que la délégation. Sans Google/GitHub déjà acceptable, il faut Keycloak, Authentik ou équivalent — soit un 2ᵉ daemon à ops, soit la dépendance à un fournisseur externe.

#### Coût opérationnel

- Un binaire Vouch en plus, son `config.yml`, son port (9090), son rc.d FreeBSD à écrire.
- Un IdP en plus (Keycloak ≈ JVM, Authentik ≈ Python+postgres+redis+celery) **ou** acceptation que les comptes Google/GitHub deviennent la racine de confiance.
- Configuration nginx significativement plus complexe (`auth_request`, `error_page`, `auth_request_set`).
- Trust transitif sur deux services au lieu d'un.

#### Pros

- Délègue 100% de l'auth web à un composant éprouvé, plus rien à coder côté Flask pour le flow OIDC.
- Si on veut un jour brancher d'autres apps internes derrière le même IdP, l'investissement est mutualisé.

#### Cons

- **Surdimensionné pour 1 utilisateur**. C'est l'archi qu'on déploie pour 5+ apps internes derrière un SSO partagé, pas pour un kanban perso.
- **Pas d'IdP existant** sur web2 → l'effort réel n'est pas "installer Vouch", c'est "installer Vouch + Keycloak/Authentik + les configurer + les sauvegarder". Multiplie le périmètre opérationnel.
- Casse l'unicité du middleware `auth.py` (cookie + bearer dans la même fonction) : les bearer tokens API ne peuvent pas raisonnablement passer par OIDC.
- La protection `session_nonce` (révocation immédiate côté DB) disparaît : on dépend du TTL JWT de Vouch.
- Cadence de release lente (~annuelle), pas de package FreeBSD.

### Piste 2 — Bibliothèques OIDC Python/Flask

| Lib | Dernière release | Dernier push | Stars | Deps runtime | Statut |
|---|---|---|---|---|---|
| **Authlib** (lepture) | v1.6.9 (2026-03-02) | 2026-04-01 | 5266 | `cryptography`, `joserfc>=1.6.0` | **Très actif**, base de référence |
| **flask-oidc** (fedora-infra) | v2.4.0 (2025-06-16) | 2026-03-02 | 40 | `flask`, `authlib^1.2`, `requests^2.20`, `blinker^1.4` | Actif, wrapper minimal autour d'Authlib, prod chez Fedora |
| **Flask-Dance** | v7.1.0 (2024-03-05) | 2024-06-07 | 1015 | `flask`, `requests`, `oauthlib`, `requests-oauthlib` | Stale (~2 ans), orienté OAuth pur, pas OIDC natif |
| **flask-pyoidc** | v3.14.3 (2023-10-30) | 2024-09-03 | 79 | `oic`, `flask`, `importlib_resources` | Niche, ralenti |

#### Authlib

Bibliothèque de référence pour OAuth/OIDC en Python. Empreinte runtime minuscule (`cryptography` est déjà transitif via `argon2-cffi`, `joserfc` est pur Python). API client OIDC en ~15 lignes :

```python
from authlib.integrations.flask_client import OAuth
oauth = OAuth(app)
oauth.register(
    name='oidc',
    server_metadata_url=Config.OIDC_DISCOVERY_URL,
    client_id=Config.OIDC_CLIENT_ID,
    client_secret=Config.OIDC_CLIENT_SECRET,
    client_kwargs={'scope': 'openid email profile'},
)
```

Les routes `/oidc/login` et `/oidc/callback` font `oauth.oidc.authorize_redirect()` puis `oauth.oidc.authorize_access_token()`, lookup/create dans `users`, `login_user()`. **Co-existe parfaitement avec Flask-Login** : on appelle `login_user(user, remember=True)` à la fin du callback exactement comme le fait `/login` aujourd'hui, donc `session_nonce`, le rate limit (qui ne s'applique qu'à `/login`), `/logout` et le middleware bearer-token restent inchangés.

PKCE supporté nativement, JWKS caché en mémoire, refresh token disponible via `token['refresh_token']` si on en a besoin.

#### flask-oidc (fedora-infra)

Wrapper minimal autour d'Authlib maintenu par l'équipe Fedora Infrastructure (utilisé en prod sur leurs apps internes). API plus opinionated (`@oidc.require_login`, `oidc.user_loggedin`). Apporte `requests` et `blinker` qu'on n'a pas aujourd'hui — petit surcoût pour gagner un décorateur et perdre en flexibilité. Intéressant comme **template d'intégration** plus que comme dépendance.

#### Flask-Dance

Pensé pour le grand public OAuth (login GitHub/Google/Twitter sur une web app). Cadence de release ralentie depuis 2024, abstraction "OAuth blueprint" plus axée sur les providers propriétaires que sur OIDC standard. **Pas le bon outil** pour brancher un IdP générique type Authentik/Keycloak.

#### flask-pyoidc

Basé sur la lib `oic` (CNRI). Communauté restreinte, dernière release fin 2023. Acceptable si on veut un wrapper opinionated, mais Authlib direct est plus future-proof.

### Recommandation

**Authlib en intégration directe**, pas Vouch.

#### Pourquoi pas Vouch

- Aucun IdP en place sur web2 : adopter Vouch revient à empiler Vouch **+** un IdP (Keycloak/Authentik) pour servir 1 utilisateur. Le ratio coût/bénéfice est mauvais.
- Vouch protège mal le cas `/api/v1/*` (le CLI `ken` headless ne peut pas faire le dance OIDC) — on serait obligé de garder une porte bearer-token dérogatoire, ce qui annule le gain de "délégation propre".
- On perd `session_nonce` (révocation immédiate côté DB) au profit du TTL du cookie JWT Vouch.

#### Pourquoi Authlib

- 2 dépendances runtime supplémentaires (`authlib`, `joserfc`), `cryptography` déjà tirée par `argon2-cffi`.
- Très actif (release tous les ~3 semaines, dernière 2026-03-02).
- Co-existe avec Flask-Login : la route OIDC callback fait juste `login_user(CurrentUser(row))` et tout le reste de l'auth (`session_nonce`, rate limit `/login`, CSRF, middleware bearer) **reste inchangé**.
- L'OIDC devient une **option** ajoutée à côté du login user/password existant — fail-soft : si l'IdP est down, le password local fonctionne toujours.
- On peut commencer avec un seul provider (Google ou Authentik si on en monte un un jour) et étendre via `oauth.register()` à la demande.

#### Esquisse d'implémentation

Étapes :

1. `pdm add authlib`
2. Ajouter `OIDC_*` à `Config` (issuer URL, client_id/secret, allowed_email_domain).
3. Créer `src/dashboard/auth_oidc.py` qui enregistre l'OAuth client et expose un blueprint `/oidc/login` / `/oidc/callback`. Le callback :
   - vérifie le claim `email_verified` et le domaine,
   - lookup `users` par email, lazy-create si absent (en `is_admin=false` par défaut),
   - rotate `session_nonce`, appelle `login_user(CurrentUser(row), remember=True)`,
   - redirige vers `next` ou `/`.
4. Ajouter un bouton "Sign in with OIDC" à `login.html` à côté du form user/password.
5. Tests unit : mock des endpoints `/.well-known/openid-configuration` + `/token` + `/userinfo` à la frontière `urllib`/`httpx`, vérifier que le user est créé et que la session est posée.
6. Doc `doc/auth-user.md` et `INSTALL.md` (variables d'env + provider à enregistrer côté IdP).

Coût estimé : ~150 lignes de code Flask + ~100 lignes de tests + 1 dépendance. **Aucun changement** côté `auth.py` (middleware bearer), `session_nonce`, rate limit, CSRF, ni côté CLI `ken`.

### Sources

- https://github.com/vouch/vouch-proxy (README, derniers tags via gh api)
- https://github.com/lepture/authlib (pyproject.toml, tags v1.6.7→v1.6.9 sur 4 semaines)
- https://github.com/fedora-infra/flask-oidc (pyproject.toml, v2.4.0)
- https://github.com/singingwolfboy/flask-dance (v7.1.0, 2024-03-05, push 2024-06)
- https://github.com/zamzterz/Flask-pyoidc (v3.14.3, 2023-10-30)
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-05-24.md)
