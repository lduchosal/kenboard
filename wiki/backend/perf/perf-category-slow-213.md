---
id: 213
title: "PERF / CATEGORY / SLOW"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #213 — PERF / CATEGORY / SLOW

Le kenboard est un peu lent quand on consulte une catégorie avec 100+ tâches (done). Ajouter des logs sur les performances pour pointer les problèmes. On intervient sur le code une fois que les problèmes ont été pointés.

---

## Note

Cette tâche ne doit pas être réalisée manuellement. Le système d'auto-monitoring (#214) doit détecter ce problème automatiquement et créer une tâche avec les métriques techniques précises permettant d'agir efficacement. Cette tâche sert de référence pour valider que le système de monitoring fonctionne : si #214 est bien implémenté, une tâche équivalente à celle-ci sera créée automatiquement par le système.
---

[← retour à backend/perf](index.md) · [voir log](../../log.md)
