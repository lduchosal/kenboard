---
id: 1181
title: "QUALITY / Sonar : clé Flask de secours en dur (S6779) bloque le gate du publish"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-13T14:52:22
classified_at: 2026-11-13T09:59:51
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1181 — QUALITY / Sonar : clé Flask de secours en dur (S6779) bloque le gate du publish

**TL;DR** — Le gate Sonarcloud bloquait le publish 0.5.2 sur une clé Flask de secours écrite en dur (règle S6779 activée par un changement de profil Sonar). La clé de secours du mode DEBUG est maintenant aléatoire par processus ; le littéral `"search.html"` dupliqué devient une constante.

## Constat

Le publish du 2026-11-13 (0.5.2) est bloqué au quality gate Sonarcloud : `new_security_rating: 5 (threshold: 1)`.

- Issue bloquante : `python:S6779` BLOCKER, `src/dashboard/auth_user.py:183` — « Don't disclose "Flask" secret keys » : la clé de secours `app.secret_key = "dev-only-insecure-key-do-not-use-in-prod"` utilisée quand `KENBOARD_SECRET_KEY` est absent en mode DEBUG.
- La ligne date d'avril 2026 ; l'issue apparaît maintenant parce que l'analyse du commit `94dfbdc` signale « Changes in 'Sonar way comprehensive' (py) » : le profil qualité a changé côté Sonarcloud, pas notre code.
- Autre issue de la même analyse, sur du code neuf (#1178) : `src/dashboard/ken/wiki_search.py:84` CRITICAL — littéral `"search.html"` dupliqué 3 fois.

## Résolution

### Modifications

- `src/dashboard/auth_user.py` — nouveau `_resolve_secret_key()` : clé configurée, sinon `RuntimeError` hors DEBUG (inchangé), sinon `secrets.token_hex(32)` au lieu de la constante. `init_login_manager` l'appelle (extraction imposée par le plafond de 50 lignes par fonction).
- `src/dashboard/ken/wiki_search.py` — constante `_SEARCH_PAGE`.
- `tests/unit/test_auth_user.py` — `TestResolveSecretKey` (3 tests : clé configurée, échec hors DEBUG, clé aléatoire en DEBUG).

### Comportements obtenus

- Prod (`DEBUG=false`) : inchangé, `KENBOARD_SECRET_KEY` reste obligatoire.
- Dev sans `KENBOARD_SECRET_KEY` : les sessions ne survivent plus à un redémarrage (ni au reloader Flask) — définir `KENBOARD_SECRET_KEY` dans `.env` pour les conserver.

### Garde-fous

- `pdm run check` : exit 0 — pytest 716 passed, vitest 81 passed, gate métriques palier 5 PASS.
- `pdm run test-e2e` : 52 passed.
- Verdict Sonar à confirmer sur l'analyse du commit poussé (gate du publish).

### Reste ouvert (hors périmètre)

Même analyse, apparus avec le changement de profil css/web, non bloquants pour le gate : 17 `!important` et 1 `reduced-motion` dans `static/style.css`, 4 `<svg>` sans nom accessible dans les templates.
---

[← retour à quality](index.md) · [voir log](../log/2026-11-13.md)
