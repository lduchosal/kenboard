---
id: 999
title: "WIKI / publish — remplacer la date de génération par la date de modif du ticket (File Churn)"
status: done
who: "Claude"
due_date: 
updated_at: 2026-07-31T10:54:12
classified_at: 2026-07-31T10:35:18
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #999 — WIKI / publish — remplacer la date de génération par la date de modif du ticket (File Churn)

La génération du wiki (ken wiki build) modifie TOUTES les pages HTML générées avec la date de dernière génération. Le wiki HTML étant committé dans SVN, cela crée beaucoup de File Churn : chaque publish touche toutes les pages même sans changement de contenu.

À faire : retirer la date de génération du HTML rendu et afficher à la place la date de dernière modification du ticket (stable tant que le ticket ne change pas), pour que seules les pages réellement modifiées diffèrent d'un build à l'autre.

---

## Résolution

### Modifications

- `src/dashboard/queries/wiki.sql` — `wiki_get_all` remonte `t.updated_at` (la colonne existe depuis 0003, auto `ON UPDATE CURRENT_TIMESTAMP`).
- `src/dashboard/routes/wiki.py` — `GET /api/v1/wiki/all` sérialise `updated_at` en ISO.
- `src/dashboard/ken/wiki_sync.py` — `_format_task_detail_md` écrit `updated_at:` dans le frontmatter YAML des pages de tâches.
- `src/dashboard/ken/wiki_build.py` — `_format_footer` ne prend plus `datetime.now(UTC)` : pages de détail → « Modifié le <updated_at du ticket> — kenboard <version> » ; pages sans ticket (index, sections, journal) → « kenboard <version> » seul. Plus aucun timestamp de build nulle part.
- `src/dashboard/ken/wiki_css.py` — commentaire du footer mis à jour.
- Tests : `tests/unit/test_ken.py` (footer réécrit + nouveau test `test_wiki_build_is_deterministic_across_runs` : deux builds successifs = HTML octet-identique), `tests/unit/test_wiki_routes.py` (assert `updated_at` dans /wiki/all).

### Comportements obtenus

- `ken wiki build` est déterministe : à wiki/ identique, le HTML produit est octet-identique → `svn ci` ne committe plus que les pages dont le contenu a réellement changé.
- Le footer des pages de détail affiche la date de dernière modification du ticket (stable tant que le ticket ne bouge pas) au lieu de la date de génération.
- Dégradation douce : tant que le serveur kenboard déployé ne renvoie pas encore `updated_at` (release à publier), le footer des pages de détail affiche seulement la version — aucun crash.
- Transition : le premier publish après release touchera une dernière fois toutes les pages (frontmatter + footer changent), puis le churn disparaît.

### Garde-fous

- `pdm run lint` (ruff) ✅, `pdm run typecheck` (mypy strict) ✅, `pdm run flake8` ✅, `pdm run interrogate` 100% ✅
- `pdm run test-unit` : 615 passed ✅ — `pdm run test-integration` : 10 passed ✅
---

[← retour à wiki](index.md) · [voir log](../log/2026-07-31.md)
