---
id: 807
title: "QUALITY / Palier 5 (final) — gate vert : fichiers ≤ 300, fonctions ≤ 50, dette = 0, min_file_cov ≥ 75"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T22:32:29
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #807 — QUALITY / Palier 5 (final) — gate vert : fichiers ≤ 300, fonctions ≤ 50, dette = 0, min_file_cov ≥ 75

## Objectif

Rendre `pdm run metrics-gate` **vert au palier 5 — le palier final**. Une fois vert : metrics-record committé, et le gate reste en **mode verrou permanent** (cibles + ratchet best-ever) ; plus aucun resserrage planifié (sauf PLR1702 à sa sortie de preview ruff).

Sortie rouge actuelle :

```
gate (palier 5): FAIL
  ✗ max_file_lines = 386 > plafond absolu 300   (9 fichiers)
        386 ken/tasks.py ; 376 ken/wiki_build.py ; 364 ken/wiki.py ; 363 ken/wiki_sync.py ;
        360 auth.py ; 356 cli.py ; 343 routes/pages.py ; 325 perf.py ; 314 auth_user.py
  ✗ max_func_lines = 60 > plafond absolu 50     (20 fonctions, de 60 à 51 lignes)
        sync 60 ; init 60 ; _load_config 60 ; category 59 ; show 58 ; register_post 58 ;
        create_app 57 ; update_task 56 ; create_onboard_token 56 ; _build_taskers_daily_chart 56 ;
        send_email 55 ; onboarding_text_full 55 ; _enforce_api_key 55 ; oidc_callback 54 ;
        _enforce_cookie_session 54 ; _build_wiki_sections_per_project_chart 54 ; _build_sync_plan 53 ;
        index 52 ; _layout_taskers_bars 52 ; _register_fatal_handler 51
  ✗ ruff_debt = 9 > plafond absolu 0 (ANN401 — détail : ruff check src --extend-select ANN401)
  ✗ min_file_cov = 71.03 < plancher absolu 75 (au dernier snapshot — relancer pdm run test-ci pour identifier le fichier)
```

## Travail

1. **9 fichiers ≤ 300** — extractions de 15 à 90 lignes chacun ; la sortie du gate donne la liste triée à chaque run.
2. **20 fonctions ≤ 50** — toutes entre 51 et 60 lignes : extractions légères de helpers, pas de noqa.
3. **ANN401 = 0 (×9)** — typer les 9 derniers `Any` ; une fois à zéro, **activer ANN401 dans [tool.ruff.lint] extend-select** (verrou final — DEBT_SELECT peut rester tel quel, il mesurera zéro).
4. **min_file_cov ≥ 75** — remonter le(s) fichier(s) sous 75 % ; tout module né des découpes doit naître testé.

## Contraintes

- Ne PAS modifier GATE_PALIER/GATE_MAX/GATE_MIN ni doc/quality-history.csv : le vert vient du code uniquement.
- Critère de done : `pdm run check` entièrement vert (inclut metrics-gate palier 5) + `pdm run metrics-record` committé une fois vert + mention dans doc/code-quality.md que le palier 5 est atteint (tableau + passage en mode verrou).
- Workflow board : ken move --to doing avant de commencer ; résolution appendée avant move --to review ; ken wiki groom <id> quality.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-10.md)
