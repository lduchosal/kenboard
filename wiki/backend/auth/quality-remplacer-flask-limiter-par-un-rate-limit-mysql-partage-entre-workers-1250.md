---
id: 1250
title: "QUALITY / Remplacer flask-limiter par un rate-limit MySQL partagé entre workers"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-27T00:19:30
classified_at: 2026-11-26T16:55:17
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/auth
section_title: "Authentication & permissions"
---

# #1250 — QUALITY / Remplacer flask-limiter par un rate-limit MySQL partagé entre workers

**TL;DR** — flask-limiter gardait ses compteurs en mémoire, un par worker gunicorn. La limite anti-brute-force de `/login` était donc en réalité jusqu'à 4× plus permissive, et il tirait une chaîne de dépendances morte (`ordered-set`, `deprecated`…) → remplacé par `dashboard.ratelimit`, un limiteur interne dont les compteurs sont dans MySQL, partagés par tous les workers. Vérifié sur un vrai gunicorn `--workers 4` : 5 échecs passent, puis 429. Les limites et leur comportement restent les mêmes, et 6 paquets sortent de la closure runtime.

Suite de #1242 (scoreboard `doc/dep-scorecard.md`). `flask-limiter` cumule un profil de maintenance faible, une chaîne transitive morte et un défaut fonctionnel : le rate-limit anti-brute-force est en réalité ~4× plus permissif que configuré.

## Constat

- **flask-limiter 4.1.1** : Maintained 0, Code-Review 0, Signed-Releases 0, score 3.5 (attesté).
- Transitifs : `limits` (4.0), **`ordered-set` 4.1.0** (dernière release 2022, Maintained 0, score 2.6), `deprecated` (pas de scorecard), `wrapt`.
- **Défaut** : `src/dashboard/auth_user.py:88-93` → `storage_uri="memory://"`, un compteur par process. `kenboard prod` lance gunicorn `--workers 4` (`cli.py:43,69`) : un attaquant réparti sur les workers obtient jusqu'à 4× la limite. Le commentaire `auth_user.py:83-87` le reconnaît et renvoie vers Redis (que l'on n'a pas et ne veut pas ajouter).
- Limites en place (7 décorateurs) :
  - `/login` POST : `5 per minute; 20 per hour` (`auth_user.py:46`), `deduct_when` ≠ 302 (seuls les échecs comptent), `on_breach` → log `auth.brute_force_attempt` (`auth_login.py:58-68`)
  - forgot password : `3 per hour` (`auth_reset.py:31,42`)
  - register : `5 per hour` (`auth_register.py:39,124`)
  - `routes/users.py:74` `10 per hour`, `:190` `5 per hour` ; `routes/keys.py:87` `10 per hour`
- `headers_enabled=True` (en-têtes `X-RateLimit-*`/`Retry-After`).
- Tests : désactivation via `limiter.enabled = False` (`tests/conftest.py:204-207`, `tests/e2e/conftest.py:90-97`, contournement d'un cache d'attribut de flask-limiter 4.x) ; tests de rate-limit dans `tests/unit/test_auth_user.py`.

## Proposition

Limiteur interne adossé à MySQL (`src/dashboard/ratelimit.py`), partagé entre workers :

- Table `rate_limit_hit (bucket, key, window_start, count)` ou fenêtre fixe par `(bucket, ip, floor(now/period))` avec `INSERT … ON DUPLICATE KEY UPDATE count = count + 1` — atomique, une requête par hit. Migration idempotente (règles `CLAUDE.md`) + miroir `tests/conftest.py`.
- Décorateur `@rate_limit("5 per minute; 20 per hour", deduct_when=…, on_breach=…)` gardant la même sémantique que les usages actuels ; réponse 429 + `Retry-After`.
- Purge des fenêtres expirées (opportuniste ou via une commande `kenboard` existante).
- Clé IP : reprendre `get_remote_address` derrière `ProxyFix` (déjà en place) — vérifier que l'IP est bien celle du client en prod.
- Switch d'activation propre pour les tests (config `RATELIMIT_ENABLED`) au lieu du hack d'attribut.
- Retire `flask-limiter` de `pyproject.toml`.

## Critères

- La limite `/login` est globale : 6 échecs en 1 min répartis sur plusieurs workers → 429 (test d'intégration avec 2 connexions / app instances distinctes).
- Les 7 limites existantes conservent leur valeur et leur comportement (`deduct_when`, log `auth.brute_force_attempt`).
- Scoreboard : `flask-limiter`, `limits`, `ordered-set`, `deprecated` (+ `wrapt` si plus requis) sortent de la closure ; GuardDog + scorecard verts.


## Résolution

### Modifications

- `src/dashboard/ratelimit.py` (nouveau) : décorateur `@rate_limit("5 per minute; 20 per hour", deduct_when=…, on_breach=…)`, avec la même interface que les usages flask-limiter précédents.
  - Fenêtres fixes, comme la stratégie par défaut de flask-limiter. Les limites séparées par `;` se cumulent (toutes doivent être respectées). Un compteur distinct par (vue, limite).
  - **On compte d'abord, puis on décide** : l'incrément est atomique (`INSERT … ON DUPLICATE KEY UPDATE`) avant l'exécution de la vue, puis on relit le compteur. Des requêtes parallèles ne peuvent pas se glisser entre un test et un hit, ce que flask-limiter permettait avec `deduct_when`. Une requête rejetée en 429, ou exclue par `deduct_when` (login réussi), est rendue.
  - En-têtes `X-RateLimit-Limit`, `-Remaining` et `-Reset` (epoch), plus `Retry-After` sur le 429. Ils sont posés par un hook `after_request`, donc le formulaire de login re-rendu par le gestionnaire 429 du blueprint les garde.
  - `RATELIMIT_ENABLED=False` désactive tout (tests). L'astuce `limiter.enabled = False` des fixtures n'est plus nécessaire.
  - **Fail-open** : en cas d'erreur MySQL, on log `ratelimit.storage_error` (avec traceback) et la requête passe. C'est une défense en profondeur, elle ne doit pas casser le login, par exemple si la migration 0023 n'est pas encore appliquée.
  - Purge des fenêtres échues (par lots de 1000) quand une nouvelle fenêtre s'ouvre. `reset()` existe pour les tests.
- `src/dashboard/migrations/0023.create_rate_limit_hits.sql` : table `rate_limit_hits`, clé primaire `(bucket, client, window_start)` et index sur `expires_at`. Migration idempotente (modèle 0021) ; ses fichiers voisins sont dans `tests/sql/schema.sql`.
- `src/dashboard/queries/ratelimit.sql` : `rl_hit`, `rl_hits`, `rl_refund`, `rl_purge`, `rl_reset`.
- Routes : `auth_login.py` (`/login`, `on_breach` → `auth.brute_force_attempt`, `get_remote_address` → `client_ip`), `auth_reset.py`, `auth_register.py`, `routes/users.py` (×2) et `routes/keys.py`. Les 7 limites gardent leur valeur.
- `auth_user.py` : le singleton `Limiter` (`memory://`) et son commentaire sur Redis sont retirés ; `init_rate_limit(app)` les remplace.
- `errors.py` : nouveau gestionnaire 429 qui renvoie `{"error": "Rate limit exceeded: 10 per hour"}` en JSON aux appelants API/XHR, conformément à `RateLimited` dans `doc/openapi.yaml`. Avant, flask-limiter renvoyait une page HTML werkzeug sur `/api/v1/users` et `/api/v1/keys`. Les navigateurs gardent la page 429 par défaut, et le blueprint auth son formulaire.
- `pyproject.toml` : retrait de `flask-limiter`. La closure runtime passe de 42 à 36 paquets : sortent flask-limiter, limits, ordered-set, deprecated, wrapt et packaging.
- **Correctif collatéral** : `pytest-playwright[base-url]` en dev.
  - Depuis 0.10, pytest-playwright rend `pytest-base-url` optionnel. Le `pdm sync --clean` de #1249 l'avait donc désinstallé.
  - Sans lui, la fixture de repli `base_url` de pytest-playwright (une méthode d'instance en scope session) lève `PytestRemovedIn10Warning` sous pytest 9.2. Avec `filterwarnings=error`, les 52 tests e2e partent en erreur.
  - Une CI qui installe depuis le lock aurait eu la même panne. J'ai déclaré l'extra plutôt que d'ignorer l'avertissement.
- Tests et fixtures : `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/e2e/test_email_flows.py` et `scripts/screenshots.py` (plus de `limiter.enabled`). `tests/unit/test_migrate.py` ne suppose plus exactement 22 migrations.
- Documentation : `doc/auth-user.md` § Rate limiting (stockage MySQL, sémantique, fail-open, toutes les routes limitées, comment débloquer une IP à la main), `doc/architecture.md` (table des couches) et `CLAUDE.md` (layout).
- `doc/dep-scorecard.{csv,md}` : snapshot généré par `pdm run dep-scorecard`.

### Comportements obtenus

- **Vérification avec un vrai gunicorn** : `gunicorn --workers 4 'dashboard.app:create_app()'` sur la base de test, puis 12 `POST /login` ratés. Résultat : `200 200 200 200 200 429 429 429 429 429 429 429`, et en base, `login_post:5/60` et `login_post:20/3600` sont à 5 chacun.
- `/login` : un login réussi ne décompte pas. Le 429 re-rend le formulaire avec « Trop de tentatives », `X-RateLimit-Limit: 5`, `Remaining: 0` et `Retry-After` ≤ 60.
- Le 429 API est en JSON ; le 429 côté navigateur est la page HTML par défaut, avec `Retry-After`.
- Une panne MySQL ou une table absente ne casse ni le login ni les routes : la requête passe et une erreur est loggée.
- Débloquer une IP : `DELETE FROM rate_limit_hits WHERE client = '<ip>';`.

### Garde-fous

- `tests/unit/test_ratelimit.py` (nouveau, 16 tests) :
  - parsing des limites et rejet des formats invalides ;
  - arithmétique des compteurs ;
  - 3e requête → 429 JSON avec ses en-têtes ;
  - requête rejetée non comptée ;
  - **partage entre 4 apps**, qui simulent 4 workers ;
  - un compteur par vue ;
  - `deduct_when` ;
  - nouvelle fenêtre et purge ;
  - limites désactivées → aucun accès à la base ;
  - fail-open (connexion KO, requête KO, remboursement KO) ;
  - 429 HTML pour les navigateurs.
  - `ratelimit.py` est couvert à 100 %.
- `tests/unit/test_auth_user.py::TestLoginRateLimit` : les 4 tests existants passent, plus un test de partage entre deux `create_app()`.
- `pdm run test-cov` : 928 tests (unit, intégration, e2e), 96,5 % de couverture. Metrics gate palier 5 : PASS (test_cov 96,49).
- `pdm run check` : exit 0, 877 tests ; mypy, ruff, flake8 (DCO), interrogate 100 %, vulture, refurb et deptry propres.
- `pdm run test-e2e` : 52 tests passent, après le correctif `[base-url]`.
- `pdm run py-malware` : GuardDog 0 bloquant, 36 paquets.
- `pdm run dep-scorecard` : 0 divergence, médiane 6.2 → 6.6.
- Limite connue, assumée : en fenêtre fixe, une rafale à cheval sur deux fenêtres peut atteindre 2× la limite (10 essais autour d'une frontière de minute). C'était déjà le cas avec flask-limiter ; la limite de 20 par heure plafonne de toute façon.
---

[← retour à backend/auth](index.md) · [voir log](../../log/2026-11-26.md)
