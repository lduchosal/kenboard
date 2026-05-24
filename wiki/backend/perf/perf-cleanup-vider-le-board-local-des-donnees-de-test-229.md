---
id: 229
title: "PERF / Cleanup / Vider le board local des donnees de test"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:54
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #229 — PERF / Cleanup / Vider le board local des donnees de test

Supprimer les 120 categories de test via l'API REST.

---

## Resolution

Script Python avec ThreadPoolExecutor (4 workers) envoyant DELETE /api/v1/categories/{id} pour chaque categorie dont le nom commence par 'Cat '. Le CASCADE DB supprime les projets et taches associes.

### Resultats

- 120 categories supprimees via API en 1.3s
- 3000 projets et 330000 taches supprimes par CASCADE
- Le monitoring perf a observe chaque DELETE
- Les categories existantes (Project test, Performance, etc.) preservees
---

[← retour à backend/perf](index.md) · [voir log](../../log.md)
