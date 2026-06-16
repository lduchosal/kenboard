---
id: 857
title: "wiki / journal / day page"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-16T16:28:14
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #857 — wiki / journal / day page

La page de jour du journal n'est pas ergonomique, pour chaque tâche réalisée beaucoup de bruit vient casser le signal.

Exemple :
#444 PERF / GET /cat/.html / budget 554.0ms > 500ms — backend/perf — done — par key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e

Le bruit par ligne (statut toujours "done", acteur opaque "par key:…:user:…") casse le signal (titre de la tâche). À nettoyer dans _format_log_day_md (wiki_log.py).

---

## Résolution

Nettoyage de la ligne par-tâche de la page de jour, en alignant ses conventions sur l'index de section (`_format_section_md`, qui omet déjà `who` et masque le statut archivé).

### Modifications
- `src/dashboard/ken/wiki_log.py` — `_format_log_day_md` : suppression de `— par {who}` (acteur `classified_by` = token opaque `key:…:user:…`, zéro signal) ; le statut n'est affiché que s'il porte une info, masqué quand archivé (`done`). Ajout de la constante `_ARCHIVED_STATUSES` (source unique).
- `src/dashboard/ken/wiki_sync.py` — importe désormais `_ARCHIVED_STATUSES` depuis `wiki_log` au lieu de le redéfinir (DRY, une seule source de vérité).
- `tests/unit/test_ken.py` — `test_format_log_day_renders_each_task_with_link` mis à jour (plus de `par Claude`) ; ajout de `test_format_log_day_drops_opaque_actor` et `test_format_log_day_hides_status_when_archived`.

### Comportements obtenus
- Avant : `#444 … — backend/perf — done — par key:038c1b37-…:user:049c2571-…`
- Après : `#444 … — backend/perf` (tâche done) ; une tâche en review garde `— review`.
- Ni `par `, ni `key:`, ni `user:` ne peuvent atteindre la page rendue.

### Garde-fous
- `pytest tests/unit/test_ken.py` : 152 passed.
- `ruff` : clean. `mypy` (strict) : success. `flake8` : clean. `interrogate` : 100%%. `vulture` : clean.
---

[← retour à wiki](index.md) · [voir log](../log/2026-06-16.md)
