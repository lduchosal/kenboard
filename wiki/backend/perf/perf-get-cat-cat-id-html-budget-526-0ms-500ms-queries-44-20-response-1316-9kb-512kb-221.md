---
id: 221
title: "PERF / GET /cat/<cat_id>.html / budget 526.0ms > 500ms, queries 44 > 20, response 1316.9KB > 512KB"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:51
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: backend/perf
section_title: "Performance & observability"
---

# #221 — PERF / GET /cat/<cat_id>.html / budget 526.0ms > 500ms, queries 44 > 20, response 1316.9KB > 512KB

Performance issue on `GET /cat/<cat_id>.html`.

## Metriques initiales

- **Temps total** : 526.0ms
- **Queries SQL** : 44 (2.6ms cumule)
- **Template** : category.html (244.8ms)
- **Taille reponse** : 1316.9KB

## Phase 1 — Lazy-load descriptions (FAIT)

Descriptions retirees du HTML initial, chargees via API au clic. Publie en v0.1.67.

## Phase 2 — Supprimer _load_all_data()

Ne pas refactorer _load_all_data(), la supprimer. Chaque route charge exactement ce dont elle a besoin. Pour la page categorie : 1 categorie, ses projets, leurs taches, burndown de cette categorie.

Queries attendues apres fix : ~7 (1 categorie, projets by cat, tasks by project x N, burndown categorie)

## Phases restantes

- Phase 3 : Bulk query tasks par categorie (eliminer le N+1 restant)
- Phase 4 : Pagination serveur de la colonne done

## Prerequis

- #227 TEST / Unit tests des page routes (filet de securite avant refactoring)

---

*Tache creee automatiquement par le monitoring de performance (#214).*
---

[← retour à backend/perf](index.md) · [voir log](../../log/2026-05-24.md)
