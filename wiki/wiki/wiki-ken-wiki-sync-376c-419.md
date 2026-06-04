---
id: 419
title: "WIKI / ken wiki sync (#376c)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:55:40
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #419 — WIKI / ken wiki sync (#376c)

Sous-tâche C de #376. Chunks A (#412) et B (#415) ont livré la DB + le CLI de classification. Ici on émet l'arbre MD à partir des classifications.

## À livrer

CLI `ken wiki sync` — exporte le wiki sur disque.

- Lit toutes les classifications via GET /api/v1/wiki/all (à exposer côté serveur — nouvelle route)
- Pour chaque section déclarée dans `ARCHITECTURE.md`, écrit `<out>/<section_path>/index.md` listant les tâches de la section
- Écrit `<out>/log.md` — log chronologique de toutes les classifications
- Écrit `<out>/index.md` — table des matières (sections + compteurs)
- Options : `--out PATH`, `--architecture PATH`, `--json` pour un dry-run
- Idempotent : ré-écrit complètement le dossier de sortie

## Hors scope

Pas de build HTML (D), pas de lint (E).

---

## Résolution

### Modifications

- `src/dashboard/routes/wiki.py` — nouveau `GET /api/v1/wiki/all` qui retourne
  `(task_id, section_path, classified_at, classified_by, title, description,
  status, who, project_id)` pour toutes les classifs. Filtre `?project=`
  optionnel comme `/unclassified`.
- `src/dashboard/auth.py` — `_resolve_project_id` ajoute `/api/v1/wiki/all`
  à la même liste que `/unclassified` (api_keys par-projet exigent
  `?project=...` ; admin key passe partout).
- `src/dashboard/ken.py` — nouvelle commande `ken wiki sync` :
  - `--out PATH` (défaut `./wiki`), `--architecture PATH`
    (défaut `./ARCHITECTURE.md`), `--json` (dry-run).
  - Helpers purs `_build_sync_plan` / `_format_*_md` / `_write_sync_plan`
    pour rester unit-testables sans I/O.
  - Émet `index.md` racine (TOC + compteurs), `<section>/index.md` pour
    chaque section déclarée (vide marquée explicite), `log.md` trié
    desc par `classified_at`, et `orphans.md` quand une classif
    référence un chemin disparu d'`ARCHITECTURE.md`.
  - Idempotent : `shutil.rmtree(out)` puis recrée tout.
- `tests/unit/test_wiki_routes.py::TestListAll` — 3 tests pour
  `/api/v1/wiki/all`.
- `tests/unit/test_ken.py::TestCliMutations` — 6 tests pour
  `ken wiki sync` (arbre, log chronologique, json dry-run,
  ARCHITECTURE manquant, orphans, overwrite idempotent).

### Comportements obtenus

- Le wiki est généré à partir de la DB sans connaissance côté serveur
  d'`ARCHITECTURE.md` (l'arbre est décidé par le CLI).
- Les sections sans tâches restent visibles avec leur titre et
  description pour signaler "à remplir".
- Les classifications stale (section supprimée d'`ARCHITECTURE.md`)
  sont remontées dans `orphans.md` au lieu d'être avalées
  silencieusement.

### Garde-fous

- `pdm run check` : OK (450 tests, lint, typecheck, interrogate,
  format, refurb).
- 9 nouveaux tests passent en isolation et dans la suite complète.
---

[← retour à wiki](index.md) · [voir log](../log/2026-05-24.md)
