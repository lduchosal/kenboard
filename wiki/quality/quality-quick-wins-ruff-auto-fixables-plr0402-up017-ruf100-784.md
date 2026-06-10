---
id: 784
title: "QUALITY / Quick wins ruff auto-fixables (PLR0402, UP017, RUF100)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-09T23:46:32
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #784 — QUALITY / Quick wins ruff auto-fixables (PLR0402, UP017, RUF100)

Chantier 1 du plan doc/code-quality.md (ken #783). Appliquer les corrections auto-fixables : PLR0402 (manual-from-import, ×12), UP017 (datetime.timezone.utc → datetime.UTC, ×2), RUF100 (noqa inutile, ×1). ruff check --select ... --fix + revue manuelle du diff. Attendu : ruff_debt baisse d'environ 15, aucun changement de comportement.

---

## Résolution

### Modifications

- 14 fichiers src/ — `import dashboard.x as y` → `from dashboard import x as y` (PLR0402 ×12) et `timezone.utc` → `UTC` (UP017 ×2), via `ruff check --select PLR0402,UP017 --fix` + isort/black + suppression des 2 imports `timezone` devenus orphelins (app.py, ken.py).
- RUF100 (activity.py:73) **volontairement non appliqué** : le `# noqa: BLE001` documente un blind-except délibéré (l'observabilité ne doit pas casser le write path) et deviendra load-bearing quand BLE sera ratcheté dans le gate ruff.

### Comportements obtenus

- Aucun changement fonctionnel (imports et alias équivalents).
- ruff_debt : 267 → ~253.

### Garde-fous

- isort, black, ruff, flake8 : verts. mypy strict : 0 erreur.
- Suite complète hors e2e : 549 passed.
---

[← retour à quality](index.md) · [voir log](../log/2026-06-09.md)
