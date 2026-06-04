---
id: 600
title: "DOCS / INSTALL.md : documenter tous les paramètres .env"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-31T19:09:37
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #600 — DOCS / INSTALL.md : documenter tous les paramètres .env

INSTALL.md ne couvre qu'une fraction des variables d'environnement supportées par kenboard. Il manque notamment :

- DB_HOST / DB_PORT (défauts)
- KENBOARD_SECRET_KEY (REQUIS en prod)
- KENBOARD_ADMIN_KEY
- KENBOARD_CORS_ORIGINS
- KENBOARD_HTTPS
- KENBOARD_ERROR_PROJECT_ID / KENBOARD_ERROR_WHO (auto-file 500 errors, #517)
- OIDC_SCOPES (ADFS workaround)
- REGISTER_ALLOWED_DOMAIN (#232)
- SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM / SMTP_USE_TLS (#231)
- PERF_ENABLED / PERF_BUDGET_MS / PERF_MAX_QUERIES / PERF_MAX_SQL_MS / PERF_MAX_RESPONSE_KB / PERF_PROJECT_ID / PERF_TASK_WHO / PERF_COOLDOWN_S (#214)
- LOG_DIR (logging.py)

Objectif : ajouter une section référence dans INSTALL.md listant toutes les variables (nom, défaut, description, références doc/#issue) groupées par catégorie (DB, sécurité, OIDC, SMTP, perf, logging, registration), pour qu'un déployeur ait une vue complète sans devoir lire src/dashboard/config.py.

Source de vérité : src/dashboard/config.py + .env.example + src/dashboard/logging.py.

---

## Résolution

### Modifications

- INSTALL.md (section 4) — ajout de la sous-section *Référence complète des variables `.env`*, qui suit le quickstart minimal préexistant.

### Comportements obtenus

7 tableaux groupés par catégorie, couvrant l'intégralité des os.getenv() du repo :

1. **Base de données** — 12 vars DB_* (host, port, users runtime/migrate × prod/test, names).
2. **Mode & logs** — DEBUG, LOG_DIR (logging.py).
3. **Sécurité / session** — KENBOARD_SECRET_KEY (avec rappel "obligatoire en prod" et commande de génération), KENBOARD_ADMIN_KEY (idem), KENBOARD_CORS_ORIGINS, KENBOARD_HTTPS.
4. **Auto-reporting 500** (#517) — KENBOARD_ERROR_PROJECT_ID, KENBOARD_ERROR_WHO.
5. **OIDC** — 6 vars (DISCOVERY_URL, CLIENT_ID, CLIENT_SECRET, ALLOWED_EMAIL_DOMAIN, REQUIRE_EMAIL_VERIFIED, SCOPES) + note fail-soft.
6. **Registration** (#232) — REGISTER_ALLOWED_DOMAIN.
7. **SMTP** (#231) — 6 vars (HOST, PORT, USER, PASSWORD, FROM, USE_TLS).
8. **Performance monitoring** (#214) — 8 vars PERF_* (ENABLED, BUDGET_MS, MAX_QUERIES, MAX_SQL_MS, MAX_RESPONSE_KB, PROJECT_ID, TASK_WHO, COOLDOWN_S).
9. **CLI ken** — 7 vars KEN_* (PROJECT_ID, BASE_URL, API_TOKEN, SYNC_DIR=doc/kenboard, WIKI_DIR=wiki, WIKI_HTML_DIR=wiki-html, ARCHITECTURE) avec note sur l'ordre de priorité flag > env > .ken > défaut.

Chaque variable a : nom, défaut, description (1-3 phrases). Les références #issue (#517, #127, #232, #231, #214) sont conservées pour traçabilité.

### Garde-fous

- Documentation only, aucun .py touché → pas de pdm run lint / typecheck / test à exécuter.
- Cohérence avec src/dashboard/config.py vérifiée par grep "os.getenv\|os.environ" sur src/ (zéro var oubliée).
- KEN_SYNC_DIR défaut corrigé en "doc/kenboard" (lu depuis DEFAULT_SYNC_DIR dans ken.py:54, pas "wiki").
---

[← retour à docs](index.md) · [voir log](../log.md)
