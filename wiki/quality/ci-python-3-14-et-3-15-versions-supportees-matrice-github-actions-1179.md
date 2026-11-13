---
id: 1179
title: "CI / Python 3.14 et 3.15 : versions supportées + matrice GitHub Actions"
status: review
who: "Claude"
due_date: 
updated_at: 2026-11-13T09:52:11
classified_at: 2026-11-13T09:52:11
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #1179 — CI / Python 3.14 et 3.15 : versions supportées + matrice GitHub Actions

**TL;DR** — Python 3.14 et 3.15 n'étaient ni déclarés ni testés. Ils sont ajoutés aux classifiers, à la matrice GitHub Actions (Linux + Windows) et à Sonar ; une fuite de `HTTPError` non fermée dans le client `ken`, qui faisait échouer 4 tests sur ces versions, est corrigée.

Ajouter Python 3.14 et 3.15 aux versions supportées (classifiers pyproject, sonar.python.version) et à la matrice de build GitHub (jobs windows-unit et build).

## Résolution

### Modifications

- `pyproject.toml` — classifiers `Python :: 3.14` et `3.15` (`requires-python >=3.11` inchangé).
- `.github/workflows/python-package.yml` — matrice `build` 3.11 → 3.15, matrice `windows-unit` 3.12 → 3.15.
- `sonar-project.properties` — `sonar.python.version` étendu à 3.14, 3.15.
- `src/dashboard/ken/http.py` — `_request` et `_try_request` ferment le corps des `HTTPError`. Python 3.14+ émet sinon `ResourceWarning: Implicitly cleaning up <HTTPError …>`, que `filterwarnings = error` transforme en échec (4 tests de `tests/unit/test_ken.py`, attribués au hasard du GC).

### Comportements obtenus

- Suite hors e2e : 713 passed sur 3.14.10 et 3.15.2 en local (venvs jetables), contre 4 failed avant le correctif.
- CI run 43396043855 : 10 jobs verts — `build` 3.11/3.12/3.13/3.14/3.15, `windows-unit` 3.12/3.13/3.14/3.15, SonarCloud.

### Garde-fous

- `pdm run check` (3.13 local) : exit 0 — mypy 0 erreur, interrogate 100 %, ruff OK, vitest 81 passed, pytest 713 passed.
- Non couvert : e2e Playwright sur 3.14/3.15 (seulement joués sur l'interpréteur local du publish).
- Constat annexe : sur 3.15, `pyyaml` n'a pas de wheel binaire et s'installe depuis le sdist (sans effet en CI ; à surveiller pour un hôte sans compilateur).
---

[← retour à quality](index.md) · [voir log](../log/2026-11-13.md)
