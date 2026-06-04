---
id: 117
title: "UX / Initialisation d'un modèle"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:24
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #117 — UX / Initialisation d'un modèle

Quand on fait pointer un modèle LLM ou un agent CLAUDE vers un KENBOARD par exemple https://www.kenboard.2113.ch/cat/0ee51b6f-81b8-4da0-9efc-0bd9e01f9e4f.html La première connexion il n'a pas les droits. La réponse du serveur doit être explicite et l'agent doit comprendre immeditatement qu'il doit faire un pip install kenboard et ken init avec l'ID de la catégorie et demander à l'utilisateur de remplir l' API key.

L'onboarding doit être smooth et facile

---

## Résolution

Quand un agent (curl, requests, ken CLI, WebFetch d'un agent IA) suit une URL kenboard sans credentials, le serveur sert maintenant un runbook copy-pasteable au lieu d'un 302 vers le login HTML. L'agent peut s'auto-onboarder en lisant la réponse.

### Modifications

- **src/dashboard/onboarding.py** (nouveau, 95 lignes) — module helper qui :
  - `cat_id_from_path('/cat/<id>.html')` → extrait l'ID catégorie de l'URL pour interpolation dans `ken init`
  - `wants_machine_response(request)` → heuristique : `Accept` présent sans `text/html` ⇒ agent. `Accept` absent ⇒ browser (préserve le test-client Werkzeug et les stacks HTTP embarquées)
  - `onboarding_text(cat_id)` → corps text/plain : pip install + ken init <id> + /admin/keys + 4 commandes `ken` exemple
  - `onboarding_json(cat_id)` → variante JSON structurée pour les SDK API
- **src/dashboard/auth_user.py:143** — `_unauthorized()` (handler flask-login) : si `wants_machine_response` ⇒ 401 `text/plain` + header `WWW-Authenticate: Bearer realm="kenboard"` + corps onboarding. Sinon, redirect 302 vers /login (flow browser inchangé).
- **src/dashboard/auth.py:321** — middleware API : token absent ⇒ `onboarding_json(cat_id_from_path(path))` au lieu du précédent `{"error": "missing Authorization header"}`.
- **tests/unit/test_auth_user.py** — nouvelle classe `TestAgentOnboardingHints` (4 tests) :
  - browser `Accept: text/html` ⇒ 302 vers login (régression check)
  - agent `Accept: */*` sur `/cat/<uuid>.html` ⇒ 401 text/plain, cat_id interpolé
  - agent sur `/` sans cat_id ⇒ placeholder `<category-id>`
  - `/api/v1/*` sans token ⇒ JSON 401 avec champs `onboarding.install`, `onboarding.init`, `onboarding.get_api_key`

### Comportements obtenus

Smoke tests manuels (`kenboard serve --debug`) :
1. `curl /cat/0ee51b6f-...html` → `HTTP/1.1 401 UNAUTHORIZED`, `Content-Type: text/plain`, `WWW-Authenticate: Bearer realm="kenboard"`, corps avec `pip install kenboard` et `ken init 0ee51b6f-...` interpolé.
2. `curl /api/v1/tasks?project=foo` → `HTTP/1.1 401`, `Content-Type: application/json`, `{"error": "unauthorized", "onboarding": {"install": ..., "init": ..., "get_api_key": "/admin/keys", "next_steps": [...]}}`.
3. `curl -H 'Accept: text/html' /cat/abc.html` → `HTTP/1.1 302`, `Location: /login?next=/cat/abc.html` (browser flow intact).

Un agent IA qui fetch `https://www.kenboard.2113.ch/cat/<id>.html` sans credentials reçoit en clair les 4 étapes pour s'onboarder, avec l'ID de catégorie déjà inséré dans la commande à exécuter.

### Garde-fous

- `pdm run lint` ✅
- `pdm run typecheck` ✅ (23 source files)
- `pdm run flake8` ✅
- `pdm run interrogate` ✅ (100%)
- `pdm run test-quick` ✅ (220 passed, +4 nouveaux tests)
- `pdm run test-e2e` ✅ (54/54 passed, 68s — aucun test browser-flow ne casse car `Accept: text/html` envoyé par Playwright)

### Choix de design

- **Heuristique `Accept` plutôt que User-Agent** : la liste des UA d'agents IA est non-exhaustive et change vite ; le `Accept` header est stable et discrimine bien browser vs CLI/SDK. Le cas `Accept` absent est traité comme browser car (a) c'est ce que fait le test-client Werkzeug qui peuple la suite unit, (b) les vrais agents émettent virtuellement toujours un `Accept` (au minimum `*/*`).
- **text/plain pour les pages HTML, JSON pour les API** : un agent sur `/cat/<id>.html` veut probablement lire le corps directement ; sur `/api/v1/*` il a un parser JSON sous la main. Les deux contiennent la même info.
- **Pas de Content Negotiation totale** : on aurait pu router selon `Accept: application/json` vs `text/plain`, mais l'écrasante majorité des agents envoient `*/*` et le runbook texte est aussi lisible par un parser JSON SDK qu'un humain. KISS.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
