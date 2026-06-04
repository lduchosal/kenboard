---
id: 238
title: "QUALITY / Sonarcloud"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #238 — QUALITY / Sonarcloud

https://sonarcloud.io/project/overview?id=lduchosal_kenboard

---

## Resolution

20 issues trouvees, 12 corrigees :

### Corriges

- **Web:PageWithoutTitleCheck** (2) — Ajout `<title>` aux templates email HTML
- **css:S4656** (1) — Suppression `display: none` duplique dans .badge-menu-dropdown
- **python:S1192** (1) — Extraction constante _INVALID_LINK_MSG pour le litteral duplique 3x
- **python:S5799** (1) — Fusion des f-strings implicitement concatenees
- **javascript:S6582** (1) — Optional chaining pour le fullscreen check
- **plsql:OrderByExplicitAscCheck** (6) — Ajout ASC explicite dans burndown.sql et user_scopes.sql

### Non corriges (refactoring lourd)

- **python:S3776** (3) — Cognitive complexity de create_app (44), cli.py (26), perf.py:init_perf (19). Necessitent un refactoring structurel.
- **javascript:S3776** (1) — Cognitive complexity de toggleDetail (19). Lie au lazy-load ajoute en #221.
- **jssecurity:S8476** (1) — Tainted data dans openEditTask. False positive: les donnees viennent de l'API interne.
- **javascript:S7785** (1) — Top-level await preference. Pas applicable dans ce contexte.

### Garde-fous

- pytest unit : 368 passed
- mypy : clean
- flake8 : clean
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
