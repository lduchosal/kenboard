---
id: 806
title: "QUALITY / Palier 4 — gate vert : fichiers ≤ 400, fonctions ≤ 60, dette ≤ 20, min_file_cov ≥ 70"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T21:19:15
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #806 — QUALITY / Palier 4 — gate vert : fichiers ≤ 400, fonctions ≤ 60, dette ≤ 20, min_file_cov ≥ 70

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 4** (resserrage en cours dans l'arbre : GATE_PALIER=4, famille PLR complète + RUF100 verrouillées dans le gate ruff, DEBT_SELECT=ANN401). Sortie rouge :

```
gate (palier 4): FAIL
  ✗ max_file_lines : 6 fichiers > 400
      ken/tasks.py 461, auth_user.py 451, auth.py 428,
      routes/pages.py 426, ken/wiki_build.py 426, app.py 421
  ✗ max_func_lines : 10 fonctions > 60
      index 78, ken init 78, oidc_callback 75, ken _load_config 74,
      _build_taskers_daily_chart 70, _register_error_handlers 69,
      register_post 65, _autocreate_error_task 63, _groom_overview 62, polish 61
  ✗ ruff_debt = 39 (ANN401) > plafond absolu 20
  ✗ test_cov ≥ 90 et min_file_cov ≥ 70 : à re-mesurer après les découpes (cli.py à 71 %, marge faible)
```

## Travail

### 1. Fichiers ≤ 400 (découpes cohérentes, pas de saucissonnage)
- ken/tasks.py → sortir `polish` (ken/polish.py)
- auth_user.py → sortir le flow /login (auth_login.py, même pattern blueprint que auth_reset/auth_register)
- auth.py → sortir la résolution project_id (auth_resolve.py)
- routes/pages.py → sortir les pages admin (routes/admin_pages.py)
- ken/wiki_build.py → sortir le CSS (ken/wiki_css.py)
- app.py → sortir les error handlers (errors.py)

### 2. Fonctions ≤ 60 : extraire des helpers (pas de noqa) sur les 10 listées

### 3. ANN401 39 → ≤ 20 : typer ce qui est exprimable (cli.py dates, ken payloads dict[str, Any], handlers) ; garder les Any honnêtes (wrapper db/aiosql, varargs, **ctx jinja)

### 4. Couverture : test_cov ≥ 90, min_file_cov ≥ 70 après découpes (les nouveaux modules héritent des tests existants ; compléter si un fichier passe sous 70)

## Contraintes
- Ne PAS modifier GATE_PALIER/GATE_MAX/GATE_MIN ni l'historique (le resserrage de l'arbre fait partie du chantier et sera committé avec).
- Critère de done : `pdm run check` vert (metrics-gate palier 4 inclus) + e2e verts + `pdm run metrics-record` committé une fois vert.
- Workflow board : move --to doing ; résolution avant review ; ken wiki groom <id> quality.

---

## Résolution

### Modifications

**Resserrage** (préparé par l'agent de surveillance, committé avec ce chantier) : GATE_PALIER=4, famille `PLR` complète + `RUF100` verrouillées dans le gate ruff, `DEBT_SELECT=ANN401`.

**1. Fichiers ≤ 400 (0 au-dessus, max 386)** — 7 extractions cohérentes :
- `errors.py` ← app.py (handlers 422/500, auto-task #517, `_wants_json`) ; app.py 421 → 215
- `auth_login.py` ← auth_user.py (login/logout/429 + `_verify_credentials`/`_is_safe_url`) ; auth_user.py 451 → 314
- `auth_resolve.py` ← auth.py (résolution project_id du middleware) ; auth.py 428 → 360
- `routes/admin_pages.py` ← routes/pages.py (pages admin) ; pages.py 426 → 334
- `routes/charts_pie.py` ← routes/charts.py (camembert ken #620)
- `ken/polish.py` ← ken/tasks.py (commande polish #550) ; tasks.py 461 → 386
- `ken/wiki_css.py` ← ken/wiki_build.py (stylesheet pur data)

**2. Fonctions ≤ 60 (max 60, zéro noqa)** — helpers extraits de : `index` (78), `ken init` (78, `_choose_project`), `oidc_callback` (75, `_get_or_create_oidc_user`), `_load_config` (74, `_locate_config_files` + `_pick_value`), `_build_taskers_daily_chart` (70, axis/legend + ctx vide), `_register_error_handlers` (69, split 422/500), `register_post` (65, `_validate_registration`), `_autocreate_error_task` (63, builder de description), `_groom_overview` (62, rendu texte), `polish` (61, builder de prompt).

**3. ruff_debt 39 → 9 (≤ 20)** — le proxy aiosql devient public et typé (`db.Queries`, `load_queries() -> Queries`) → 16 paramètres `conn`/`queries` typés partout ; enforcers auth → `ResponseReturnValue | None` ; dates burndown typées `date` ; `get_logger -> BoundLogger` ; `ssl.SSLContext | None` et `Section` via TYPE_CHECKING (boot stdlib de ken préservé). Restent 9 `Any` honnêtes (wrapper dynamique db ×4, varargs perf ×2, `**ctx` jinja, payload JSON `_request`, `data` fmt).

**4. Couverture** — +14 tests (`test_auth_resolve.py`, `test_board_pie.py`) : min_file_cov 71.0 (≥ 70), test_cov 92.9 % (≥ 90).

### Comportements obtenus

- `pdm run metrics-gate` : **PASS palier 4**. max_file 386, max_func 60, funcs>50 = 20, c901 = 0, dette 9, docstrings 100 %.
- Aucun changement fonctionnel ; historique intact ; snapshot vert committé.

### Garde-fous

- `pdm run check` complet : exit 0. Suite hors e2e : 585+ verts, **e2e 52/52** (login/admin/routes déplacés).
- Commit ff0595c poussé sur main.
- Flakes préexistants observés (hors périmètre) : `test_oidc_login_redirects_to_idp` (ordre de collection) et `test_last_used_at_is_updated` (1 occurrence sous -x, passe seul et dans son fichier).
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)
