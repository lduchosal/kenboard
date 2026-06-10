---
id: 787
title: "QUALITY / Règles d'architecture structurelles automatisées (import-linter + tests)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T22:32:26
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #787 — QUALITY / Règles d'architecture structurelles automatisées (import-linter + tests)

## Besoin

Équivalent Python de NetArchTest/ArchUnit (.NET) : valider des règles structurelles automatiquement, intégré dans publish.sh --quality.

## Outils candidats

1. **import-linter** (recommandé) — contrats déclaratifs sur le graphe d'imports, config dans pyproject.toml, CLI `lint-imports` → s'intègre direct dans `pdm run check` et publish.sh. Types de contrats : layers, forbidden, independence.
2. **pytest-archon** — style ArchUnit fluent dans des tests pytest (le plus proche de l'approche .NET).
3. **tach** — enforcement de boundaries de modules, plus récent.
4. Règles fichiers (pas d'imports) → simple test pytest avec glob.

## Règles candidates pour kenboard

- Les fichiers *.sql vivent uniquement dans queries/ et migrations/ (test glob).
- routes/ n'importe jamais pymysql directement — uniquement via dashboard.db (état actuel : conforme, routes importent `from dashboard import db`).
- models/ (Pydantic) n'importe ni flask ni dashboard.db.
- ken/ (CLI REST) n'importe jamais dashboard.db ni pymysql (stdlib HTTP only).
- Pas de SQL inline (chaîne SELECT/INSERT) hors queries/*.sql — grep/test.

## Intégration

- Ajouter un script pdm (ex. `pdm run archlint`) inclus dans `pdm run check`.
- Ajouter au gate publish.sh --quality.

---

## Spécification affinée (analyse du code, 2026-06-10)

Les règles ci-dessus étaient des exemples. Analyse complète du code effectuée ; les règles ci-dessous remplacent la liste candidate.

### État des lieux

Conforme : pymysql/aiosql confinés à db.py ; models/ purs (pydantic+stdlib) ; ken/ stdlib+click only ; routes via dashboard.db ; aucun render_template_string/Markup.

Écarts trouvés :
1. HTML inline dans ken/wiki_build.py (~40 lignes de markup en f-strings : _wrap_html, _format_sidebar_nav, _render_task_detail, _format_footer).
2. SQL inline : cli.py:289 (INSERT INTO burndown_snapshots), routes/tasks.py:80 (SELECT LAST_INSERT_ID() — aiosql opérateur `<!` le fait nativement).
3. Imports privés inter-modules : routes/keys.py → auth._hash_key ; routes/users.py et auth.py → auth_user._is_login_disabled.
4. Blueprints hors routes/ : onboarding.py, auth_oidc.py, auth_user.py → **décision : whitelist** (pas de déplacement).
5. tests/unit touche la DB : test_activity.py, test_api.py, test_wiki.py (fixture db) → **décision : déplacer vers tests/integration/**.
6. os.getenv hors config.py : logging.py:14 (LOG_DIR), app.py:371 (DEBUG).
7. Dep fantôme : requests déclarée, jamais importée (transitif authlib) — documenter ou deptry.

### Règles — A. Contrats import-linter (pyproject.toml, CLI lint-imports)

- A1 forbidden : dashboard.ken n'importe rien du serveur (db, app, routes, models, auth*, config, email, activity, perf, onboarding). [conforme]
- A2 forbidden externe : ken sans flask/pymysql/requests/httpx. [conforme]
- A3 pymysql + aiosql importables uniquement par dashboard.db. [conforme]
- A4 models/ sans flask, dashboard.db, routes, auth*. [conforme]
- A5 layers : app > routes > (auth_oidc, auth, auth_user, onboarding) > (activity, perf, email) > db > models > (config, logging, password_strength). [conforme — figer]
- A6 independence entre blueprints routes/*. [conforme]
- A7 personne n'importe dashboard.app sauf cli. [conforme]

### Règles — B. Tests structurels pytest (tests/arch/, sans DB)

- B1 *.sql uniquement dans queries/ et migrations/. [conforme]
- B2 pas de SQL inline dans les *.py. [2 violations]
- B3 pas de HTML dans les *.py — markup dans des templates. [wiki_build.py]
- B4 interdiction render_template_string / Markup. [conforme — verrouiller]
- B5 pas d'import privé `from x import _y` inter-modules. [3 violations]
- B6 Blueprint() uniquement dans routes/ + whitelist {auth_user, auth_oidc, onboarding}. [conforme avec whitelist]
- B7 migrations : numérotation séquentielle ; `-- rollback` présent et no-op SELECT 1 ; un concern par ALTER ; pas d'ADD INDEX à côté d'une FK (grandfathering 0001-0008 si besoin).
- B8 symétrie aiosql : toute queries.xxx appelée existe dans queries/*.sql et inversement (SQL mort).
- B9 tests/unit sans DB (pas de fixture db ni pymysql). [3 fichiers à déplacer]
- B10 os.environ/os.getenv confiné à config.py (ken exempté). [2 violations]

### Intégration

- `pdm run archlint` = lint-imports + pytest tests/arch -q ; inclus dans `pdm run check` et publish.sh --quality.
- Optionnel : deptry (cas requests).

### Méthode — TDD

1. **Red** : implémenter d'abord toutes les règles (contrats import-linter + tests/arch/), SANS corriger le code. Valider que chaque règle détecte exactement les défauts connus listés ci-dessus (B2×2, B3, B5×3, B9×3, B10×2) et qu'aucune règle conforme (A1-A7, B1, B4, B6) ne lève de faux positif. Les violations connues sont marquées xfail/whitelist temporaire pour ne pas casser le gate.
2. **Green** : le refactoring (corriger B2/B3/B5/B9/B10, retirer les xfail) est délégué à un agent spécialisé qui utilise les règles comme guide — chaque correction retire son entrée de la whitelist et le gate doit passer.
3. Brancher archlint dans check + publish.sh --quality une fois le tout vert.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)
