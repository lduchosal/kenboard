---
id: 804
title: "QUALITY / Palier 3 — gate vert : fichiers ≤ 500, fonctions ≤ 80, dette ≤ 60, min_file_cov ≥ 60"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T20:33:26
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #804 — QUALITY / Palier 3 — gate vert : fichiers ≤ 500, fonctions ≤ 80, dette ≤ 60, min_file_cov ≥ 60

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 3** (resserrage 62a0ef3, tableau dans doc/code-quality.md § Gate bloquant). Sortie rouge actuelle :

```
gate (palier 3): FAIL
  ✗ max_file_lines = 556 > plafond absolu 500       (auth_user.py)
  ✗ max_func_lines = 90 > plafond absolu 80         (category 90, onboarding_text_full 82, verify_email 81)
  ✗ ruff_debt = 114 > plafond absolu 60             (ANN401 ×111, PLR0913 ×3)
  ✗ min_file_cov = 41.96 < plancher absolu 60       (cli.py 42 %)
```

## Travail

### 1. auth_user.py 556 → ≤ 500
Extraire le bloc permissions/scopes (~110 lignes : _user_scope_for_*, _scope_allows, current_user_can*, _is_api_key_principal) dans un module dédié ; mettre à jour les importeurs (routes, auth, tests).

### 2. Fonctions ≤ 80 (extraire des helpers, pas de noqa)
- `category` (90, routes/pages.py:333)
- `onboarding_text_full` (82, onboarding.py:201)
- `verify_email` (81, auth_register.py:145)

### 3. ruff_debt 114 → ≤ 60 (−54)
- ANN401 ×111 : entamer le stock — routes Flask `-> Any` → `flask.typing.ResponseReturnValue` (gros gisement), payloads typés `dict[str, Any]`/modèles là où c'est exprimable. Garder `Any` seulement où c'est honnête (noqa argumenté si nécessaire).
- PLR0913 ×3 : log_activity (activity.py), _layout_taskers_bars (charts.py), pages.py:84.

### 4. min_file_cov ≥ 60
Tests unitaires `cli.py` (42 %) — commandes admin kenboard (migrate/set-password/build…). Vérifier ensuite qu'aucun autre fichier ne reste < 60.

## Contraintes
- Ne PAS modifier GATE_PALIER/GATE_MAX/GATE_MIN ni doc/quality-history.csv : le vert vient du code uniquement.
- Familles tombées à zéro → extend-select + retrait de DEBT_SELECT (script + doc), principe ratchet.
- Critère de done : `pdm run check` vert (inclut metrics-gate palier 3) + e2e verts (les zones auth/routes bougent) + `pdm run metrics-record` committé une fois vert.
- Workflow board : move --to doing avant de commencer ; résolution appendée avant review ; ken wiki groom <id> quality.

---

## Résolution

### Modifications

**1. auth_user.py 556 → 450** — bloc permissions/scopes (#197) extrait dans `auth_scopes.py` (120 lignes : `_user_scope_for_*`, `_scope_allows`, `_is_api_key_principal`, `current_user_can`, `current_user_can_project`) ; importeurs mis à jour (routes categories/pages/projects/tasks/wiki). Plus aucun fichier > 500 (max = 461, charts.py).

**2. Fonctions ≤ 80 (max = 78)** — `category` : chargement tasks+burndown extrait dans `_attach_category_project_data` ; `onboarding_text_full` : section statique du runbook en constante module `_RUNBOOK_GUIDE` ; `verify_email` : provisioning (user+catégorie+projet+scope) extrait dans `_provision_user`.

**3. ruff_debt 114 → 39 (≤ 60)** — ANN401 115 → 39 : routes Flask `-> Any` → `flask.typing.ResponseReturnValue` (~45 routes), hooks/handlers typés (`Response`, `Request`, `Exception`, `Template`, `Flask`), erreurs pydantic en `Sequence[Mapping[str, Any]]`, authlib casté. **Découverte clé : les stubs obsolètes `types-Flask`/`types-Werkzeug`/`types-Jinja2`/`types-click` (Flask 1.x) masquaient le typage natif de Flask 3** et rendaient `jsonify`/`route` intypables — retirés des dev-deps, `pdm.lock` resynchronisé. PLR0913 ×3 : noqa argumentés (un kwarg par champ, design identique à `ken add`/`update`). Restent en dette : ANN401 ×39 honnêtes (wrappers dynamiques db/aiosql, varargs, payloads ken CLI) pour les paliers 4-5.

**4. min_file_cov 41.96 → 70.63 (≥ 60)** — `tests/unit/test_cli.py` +7 tests (migrate/migrate-test avec subprocess mocké, set-password ×4 chemins, grant-legacy-read sur DB de test) : `cli.py` 42 % → 71 %.

### Comportements obtenus

- `pdm run metrics-gate` : **PASS palier 3**. max_file 461, files>500 = 0, max_func 78, funcs>50 = 23, c901 = 0, dette 39, test_cov 92.0 %, min_file_cov 70.63.
- Aucun changement fonctionnel ; seuils GATE_* et historique intacts ; snapshot vert committé.

### Garde-fous

- `pdm run check` complet : exit 0. Suite hors e2e : 568+7 verts, couverture 92 % ; **e2e 52/52** (routes/auth touchées par le typage et la découpe scopes).
- mypy strict 44 fichiers : 0 erreur — et le typage est maintenant réellement vérifié sur les routes (les vieux stubs neutralisaient flask).
- Commit 97426fa poussé sur main.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)
