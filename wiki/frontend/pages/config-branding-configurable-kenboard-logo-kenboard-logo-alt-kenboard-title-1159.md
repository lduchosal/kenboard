---
id: 1159
title: "CONFIG / Branding configurable : KENBOARD_LOGO, KENBOARD_LOGO_ALT, KENBOARD_TITLE"
status: done
who: "Claude"
due_date: 
updated_at: 2026-10-30T10:42:56
classified_at: 2026-10-30T10:29:35
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #1159 — CONFIG / Branding configurable : KENBOARD_LOGO, KENBOARD_LOGO_ALT, KENBOARD_TITLE

**TL;DR** — Le logo, le nom et le favicon « Kenboard » étaient écrits en dur dans les templates et les routes. Ils se configurent maintenant via 5 variables `.env` (`KENBOARD_TITLE`, `KENBOARD_SHORT_TITLE`, `KENBOARD_LOGO`, `KENBOARD_LOGO_ALT`, `KENBOARD_FAVICON`), passées à tous les templates sous `brand`.

Rendre le branding configurable via `.env` / `Config`, pour afficher le logo et le nom de l'entreprise à la place de Kenboard.

## Variables à ajouter (`src/dashboard/config.py`)

| Variable | Défaut | Usage |
|---|---|---|
| `KENBOARD_LOGO` | `/static/logo.svg` | URL/chemin du logo (pages d'authentification) |
| `KENBOARD_LOGO_ALT` | `Kenboard` | attribut `alt` du logo |
| `KENBOARD_TITLE` | `Kenboard` | nom affiché : `<title>`, `<h1>` du header, titre des pages d'authentification, emails |

Exposer via un `context_processor` (ex. `brand`) pour que tous les templates y aient accès sans toucher chaque route.

## Occurrences en dur à remplacer

- Pages d'authentification — `login.html`, `register.html`, `forgot_password.html`, `reset_password.html` :
  - `<title>Kenboard &mdash; …</title>` (l.6)
  - `<img src="/static/logo.svg" alt="Kenboard">` (l.15)
  - `<h1 class="login-title">KENBOARD</h1>` (`login.html` l.18)
- Header — `partials/header.html` l.2 : `<h1>KENBOARD</h1>`
- `<title>` des pages — `base.html` rend `{{ title }}`, construit dans les routes avec un préfixe `"KEN"` :
  - `routes/pages.py:225,252`, `routes/category_page.py:89`, `routes/admin_pages.py:41,78,106`
- `error_fatal.html` l.6 : `<title>Erreur — kenboard</title>`
- `index.html` l.37 : `"Bienvenue sur KENBOARD"`
- Emails : sujets `auth_reset.py:73`, `auth_register.py:123` + templates `email/*.html|txt`

À ne pas toucher : les mentions techniques (`pip install kenboard`, `kenboard set-password`, lien GitHub, `title="kenboard {{ version }}"` du badge de version).

## À faire aussi

- `.env.example` + `INSTALL.md` : documenter les 3 variables
- Tests unitaires/intégration : valeurs par défaut inchangées + override (logo, alt, titre rendus dans login + header)
- Option : `KENBOARD_FAVICON` (aujourd'hui `/static/favicon-32.png` + `favicon.ico` en dur dans `base.html`), à décider

## Résolution

### Modifications

- `src/dashboard/config.py` — `KENBOARD_TITLE` (défaut `Kenboard`), `KENBOARD_SHORT_TITLE` (`KEN`, préfixe du `<title>` des pages du board — demande utilisateur : « KENBOARD prend trop de place » dans les onglets), `KENBOARD_LOGO` (`/static/logo.svg`), `KENBOARD_LOGO_ALT` (`Kenboard`), `KENBOARD_FAVICON` (vide = jeu intégré).
- `src/dashboard/branding.py` (nouveau) — `page_title(*parts)` → `"<titre court> / <part>…"`, `brand_context()` (context processor qui expose `brand` à tous les templates, emails compris), `init_branding(app)` appelé dans `app.create_app`.
- `templates/partials/favicon.html` (nouveau) — un seul `<link rel="icon">` + `apple-touch-icon` quand `KENBOARD_FAVICON` est renseigné, sinon le jeu png/ico/apple-touch d'origine ; inclus par `base.html`, les 4 pages d'authentification et `error_fatal.html` (qui reçoit ainsi aussi `favicon.ico` et `apple-touch-icon`).
- `login.html`, `register.html`, `forgot_password.html`, `reset_password.html` — `<title>`, `<img src/alt>`, `<h1 class="login-title">` (`brand.title | upper`).
- `partials/header.html` (`<h1>`), `index.html` (« Bienvenue sur … »), `error_fatal.html` (`<title>`).
- `routes/pages.py`, `routes/admin_pages.py`, `routes/category_page.py` — `"KEN / …"` → `page_title(…)`.
- `auth_reset.py`, `auth_register.py` + `templates/email/*` — sujets et corps des emails.
- `.env.example`, `INSTALL.md` (§ Branding : table des variables + conseil de servir les fichiers par le reverse proxy, pour qu'ils survivent aux mises à jour).
- Tests : `tests/unit/test_branding.py` (nouveau, 19 tests). Les e2e qui vérifient les titres `KEN / …` sont inchangés.

### Comportements obtenus

- Par défaut, tout s'affiche exactement comme avant : les onglets du board gardent `KEN`, `KEN / Aide`, `KEN / <catégorie>` (`KENBOARD_SHORT_TITLE`) ; les pages d'authentification et les emails utilisent `KENBOARD_TITLE`.
- Avec un titre personnalisé, plus aucun « Kenboard » n'apparaît sur les pages d'authentification (vérifié par test). Les mentions techniques restent (`pip install kenboard`, `kenboard set-password`, lien GitHub, badge de version, page Aide).
- Le header et le titre de la page de login sont affichés en majuscules, comme le `KENBOARD` d'origine.
- Les valeurs de `Config` sont lues au moment du rendu, donc `monkeypatch.setattr(Config, …)` suffit pour les remplacer.

### Garde-fous

- `pdm run check` : PASS (isort, black, docformatter, mypy 0, flake8, interrogate 100 %, refurb 0, ruff, vulture 0, test-quick).
- `pdm run test` : 683 passed. e2e `test_dashboard.py` + `test_admin_keys.py` : 38 passed.
- `pdm run test-cov` (unit + integration + e2e) : couverture 95.32 %. 2 échecs `TestLoginRateLimit` (`test_burst_blocked_after_5`, `test_429_response_includes_retry_after`) **préexistants** : mêmes échecs après `git stash -u` sur le working tree propre (ordre de la suite complète, sans rapport avec le branding). Un e2e drag & drop a échoué une fois sur deux runs (instable).
- `TestBoardPages` restaure `LOGIN_DISABLED` avec une fixture autouse (même contournement que `test_page_routes.py`) : `test_auth_oidc` laisse le flag modifié sur l'app partagée.
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-10-30.md)
