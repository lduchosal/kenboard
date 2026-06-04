---
id: 10
title: "PYPI / Quality and publish"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:05
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: ops
section_title: "Ops & deployment"
---

# #10 — PYPI / Quality and publish

Execute la qualité, résoud les problèmes et publie le package sur pypi.

## sh publish.sh --quality

17/17 étapes OK. Un seul fix appliqué : `docformatter` a auto-reformaté les docstrings des nouveaux tests (split en deux lignes au lieu d'une longue). Tous les autres checks (black, isort, mypy, flake8, ruff, refurb, vulture, interrogate 100%) passaient déjà. 64 unit + 26 e2e = 90 tests verts.

## sh publish.sh

24/24 étapes OK.

- Version : 0.1.12 → **0.1.13**
- PyPI : https://pypi.org/project/kenboard/0.1.13/ — sdist + wheel uploadés
- Git : commit `7404571` `chore: release version 0.1.13` (9 fichiers, +200/-7), tag `kenboard-0.1.13`, pushé sur `main`

## Contenu de la release 0.1.13

- Fix #11 : bug du dropdown status après drag&drop
- Feature #14 : auto-refresh JS toutes les minutes (avec garde-fous modale/drag/onglet caché)
- Feature #15 : rendu Markdown des descriptions de tâches via marked.js (vendoré)
- Feature : route `/marked.min.js` dans `app.py`
- Tests #18 : 3 nouveaux tests e2e (régression #11, rendu MD, garde-fou refresh)
---

[← retour à ops](index.md) · [voir log](../log/2026-05-24.md)
