---
id: 206
title: "STATS / stats on categories"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:47
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/api
section_title: "REST API"
---

# #206 — STATS / stats on categories

Stats on category seems to mean nothing, can you make it meaningful.

---

## Résolution

Ancien "burndown" remplacé par un **vrai burndown avec historique** basé sur des snapshots quotidiens.

### Modifications

**Schéma + queries**
- `src/dashboard/migrations/0016.create_burndown_snapshots.sql` — nouvelle table dénormalisée (1 row/jour/projet, 4 colonnes statut)
- `src/dashboard/queries/burndown.sql` — `burndown_record_snapshot` (upsert), `burndown_get_by_project` (60j), `burndown_get_by_category` (agrégation SUM), `burndown_task_counts_by_project`
- `tests/conftest.py` — miroir de la table + clean-up dans le fixture `db`

**CLI**
- `src/dashboard/cli.py` — `kenboard snapshot` : itère tous les projets, compte les tâches par statut, upsert dans `burndown_snapshots`. Idempotent (ON DUPLICATE KEY UPDATE). Conçu pour un cron quotidien : `0 2 * * * kenboard snapshot`

**Rendu SVG server-side**
- `src/dashboard/templates/partials/burndown.html` — remplacement complet : SVG polyline + filled area au lieu d'une single bar CSS. Axe X = snapshot_date, axe Y = remaining (todo+doing+review). Placeholder "Pas encore de données" si < 2 snapshots.
- `src/dashboard/templates/index.html` — category cards : burndown SVG avec snapshots agrégés par catégorie (60j)
- `src/dashboard/templates/category.html` — burndown SVG par projet (au-dessus du kanban)
- `src/dashboard/static/style.css` — `.burndown-svg` remplace `.cat-burndown` + dead CSS `.burndown` nettoyé

**Routes**
- `src/dashboard/routes/pages.py` — `_load_all_data` charge les snapshots par projet + par catégorie. `aggregate_burndown` (l'ancienne logique single-bar) supprimé.

**Tests**
- `tests/unit/test_burndown.py` — 8 tests : upsert, idempotent, agrégation catégorie, CLI snapshot, template SVG (rendu + placeholder)

**Doc**
- `doc/burndown.md` — architecture complète (collecte, rendu, rétention)
- `INSTALL.md` — nouvelle section 5b (cron quotidien)

### Comportements obtenus

- **Index** : chaque carte catégorie affiche un SVG polyline montrant la tendance des tâches restantes sur 60 jours. La courbe descend quand des tâches passent en "done".
- **Page catégorie** : chaque projet montre son burndown individuel au-dessus du kanban.
- **Pas de données** : message clair "Pas encore de données" jusqu'à ce que le cron ait tourné ≥ 2 jours.
- **CLI** : `kenboard snapshot` safe à relancer (upsert), 1 ligne par projet, retour propre.

### Garde-fous

- `pdm run check` (isort + black + mypy + flake8 + interrogate + refurb + lint + vulture + test-quick) → 321 passed, tout vert
- `pdm run test-e2e` → 53 passed
---

[← retour à backend/api](index.md) · [voir log](../../log/2026-05-24.md)
