---
id: 420
title: "WIKI / ken wiki build (#376d)"
status: review
who: "Claude"
due_date: 
classified_at: 2026-05-24T15:13:23
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #420 — WIKI / ken wiki build (#376d)

Sous-tâche D de #376. Chunks A–C ont livré la DB, le CLI de classification, et l'export MD. Ici on génère le wiki en HTML statique.

## À livrer

CLI `ken wiki build` — convertit l'arbre MD en HTML auto-suffisant.

## Hors scope

Pas de lint (chunk E).

---

## Résolution

### Modifications

- `pyproject.toml` — ajoute `markdown>=3.5` comme runtime dep
  (rendu MD → HTML côté CLI ; vendored `marked.min.js` reste pour
  le rendu in-browser des descriptions de tâches).
- `src/dashboard/ken.py` — nouvelle commande `ken wiki build` :
  - `--in PATH` (défaut `./wiki`), `--out PATH` (défaut `./wiki-html`),
    `--architecture PATH`.
  - Helpers purs `_render_markdown`, `_rewrite_md_links_to_html`,
    `_format_sidebar_nav`, `_wrap_html`, `_build_html_plan`,
    `_write_html_plan` — unit-testables sans I/O.
  - Layout HTML inline (CSS embarqué) : header, sidebar nav arborescent
    (sections d'`ARCHITECTURE.md`), main area. Pages auto-suffisantes
    — aucun fichier CSS / JS externe.
  - Réécrit tous les liens `*.md` → `*.html` post-rendu.
  - Le sidebar marque la page courante via `class="current"`.
  - Idempotent : `shutil.rmtree(out)` puis re-création complète.
- `tests/unit/test_ken.py::TestCliMutations` — 4 tests `wiki_build` :
  arbre HTML, réécriture des liens `.md`, input manquant, overwrite.

### Comportements obtenus

- Pipeline complet `sync → build` validé sur les 195 classifications
  réelles (20 MD → 20 HTML, 240 KB de wiki statique).
- Pages auto-portantes : aucune dépendance d'asset → simple à
  publier (rsync vers un bucket / nginx).
- Sidebar reflète la hiérarchie d'`ARCHITECTURE.md` avec indentation
  par profondeur.

### Garde-fous

- `pdm run check` : OK (456 tests, lint, typecheck, format,
  interrogate, refurb).
- Smoke test manuel : `ken wiki sync && ken wiki build` produit un
  arbre HTML cohérent et navigable.
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
