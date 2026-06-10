---
id: 808
title: "QUALITY / Palier 5 (final) — gate vert : fichiers ≤ 300, fonctions ≤ 50, dette = 0, min_file_cov ≥ 75"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T22:14:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #808 — QUALITY / Palier 5 (final) — gate vert : fichiers ≤ 300, fonctions ≤ 50, dette = 0, min_file_cov ≥ 75

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 5 — la cible finale** (GATE_PALIER=5 actif). Ensuite le gate reste en mode verrou. Sortie rouge :

```
gate (palier 5): FAIL
  ✗ max_file_lines : 9 fichiers > 300
      ken/tasks 386, ken/wiki_build 376, ken/wiki 364, ken/wiki_sync 363,
      auth 360, cli 356, routes/pages 343, perf 325, auth_user 314
  ✗ max_func_lines : 20 fonctions > 50 (max 60)
  ✗ ruff_debt = 9 (ANN401) > 0
  ✗ min_file_cov = 71.0 < 75 (cli.py)
```

## Travail

### 1. Fichiers ≤ 300 (découpes cohérentes)
- ken/tasks.py → commandes de mutation (add/update + helpers attachement/desc + reminders) dans ken/task_edit.py
- ken/wiki_build.py → rendu des pages détail (.fullscreen-card) dans ken/wiki_detail.py
- ken/wiki.py → commande groom dans ken/wiki_groom.py (les helpers sections/slug restent)
- ken/wiki_sync.py → journal d'exploitation (#742) dans ken/wiki_log.py
- auth.py → enforcement bearer/api_key dans auth_api_key.py
- cli.py → burndown snapshot/backfill dans cli_burndown.py
- routes/pages.py → page catégorie dans routes/category_page.py
- perf.py → PerfCollector dans perf_collector.py
- auth_user.py → session (CurrentUser, loader, nonce) dans auth_session.py

### 2. Fonctions ≤ 50 : extraire des helpers (pas de noqa) sur les 20 listées par le gate

### 3. ruff_debt = 0 : les 9 ANN401 restants sont des Any honnêtes (wrapper dynamique aiosql, varargs, **ctx jinja, payloads JSON) → noqa argumentés, puis ratchet : ANN401 activé dans extend-select, DEBT_SELECT vidé (le compteur reste comme verrou à zéro)

### 4. min_file_cov ≥ 75 : compléter les tests cli.py (71 %) + vérifier les nouveaux modules après découpe

## Contraintes
- Ne PAS modifier GATE_PALIER/GATE_MAX/GATE_MIN ni l'historique.
- Critère de done : `pdm run check` vert + e2e verts + `pdm run metrics-record` committé une fois vert.
- Workflow board : move --to doing ; résolution avant review ; ken wiki groom <id> quality.

---

## Résolution

### Modifications

**1. Fichiers ≤ 300 (0 au-dessus, max 299)** — 10 extractions :
- `ken/task_edit.py` ← ken/tasks.py (add/update + helpers attachement/desc + reminders) ; tasks.py 386 → 155
- `ken/wiki_groom.py` ← ken/wiki.py (commande groom #376) ; wiki.py 364 → 110
- `ken/wiki_log.py` ← ken/wiki_sync.py (journal #742 + orphans) ; wiki_sync.py 363 → ~280
- `ken/wiki_detail.py` ← ken/wiki_build.py (pages détail .fullscreen-card, cycle d'import résolu en y logeant _render_markdown/_rewrite_md_links) ; wiki_build.py 376 → ~270
- `auth_api_key.py` ← auth.py (lookup/scopes/promotion des bearer tokens) ; auth.py 360 → ~230
- `auth_session.py` ← auth_user.py (CurrentUser, user_loader, nonce, _unauthorized) ; auth_user.py 314 → ~215
- `cli_burndown.py` ← cli.py (snapshot/backfill #206) ; cli.py 356 → 227
- `routes/category_page.py` ← routes/pages.py (page catégorie #221) ; pages.py 343 → ~240
- `perf_collector.py` ← perf.py (PerfCollector) ; perf.py 325 → ~270

**2. Fonctions ≤ 50 (max 50, zéro noqa de longueur)** — 18 helpers extraits : `_apply_sync`, `_write_config_files`, `_resolved_fields`, `_choose_project`, `_category_ctx`/`_category_rows`, `_validate_registration`→`_create_verification_token`, `_make_flask_app`, `_log_update_activity`, `_rotate_onboarding_key`, `_check_key_scope`, `_csrf_reject`, `_reject_oidc_email`, `_activity_series`, `_fatal_response`, `_bar_grid`, `_project_card`, `_taskers_axis_legend`+ctx, `_build_message`, `_token_section`, `_print_task`/`_save_attachement`.

**3. ruff_debt = 0** — les 9 `Any` irréductibles (proxy aiosql, varargs blinker, **ctx jinja, payloads JSON) portent des noqa argumentés ; **ratchet final : ANN401 verrouillé dans `[tool.ruff.lint] extend-select`** (tests exemptés, comme mypy). Le gate est désormais en mode verrou : 21 familles ruff actives, DEBT_SELECT=ANN401 reste mesuré à zéro.

**4. min_file_cov 76.9 (≥ 75)** — +6 tests backfill/burndown (helpers purs + CLI sur DB de test) : `cli_burndown.py` 42 % → 88 %. test_cov 94.1 %.

### Comportements obtenus

- `pdm run metrics-gate` : **PASS palier 5 — cible finale atteinte**. max_file 299, max_func 50, funcs>50 = 0, c901 = 0, dette = 0, docstrings 100 %, cov 94.1 %.
- Aucun changement fonctionnel ; historique intact ; snapshot final committé.

### Garde-fous

- `pdm run check` complet : exit 0. Suite hors e2e : 595 verts ; **e2e 52/52**.
- Commit d15c699 poussé sur main.
- Trajectoire complète (quality-history.csv, 2 jours) : dette 267 → 0, max_file 2266 → 299, max_func 126 → 50, fichiers>500 3 → 0, cov 89.3 → 94.1 %, 30 → 60 modules.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)
