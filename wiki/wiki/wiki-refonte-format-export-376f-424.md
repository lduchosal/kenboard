---
id: 424
title: "WIKI / Refonte format export (#376f)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T16:19:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #424 — WIKI / Refonte format export (#376f)

Refonte du format d'export wiki (#376 followup) — voir décisions Q1–Q4 dans #422.

---

## Résolution

### Modifications

- `src/dashboard/ken.py` :
  - `_slugify(text)` + `_task_filename(task)` : convertit le titre en slug
    `lower-case-with-dashes-id`.
  - `_format_section_md` réécrit : split "En cours" (todo/doing/review,
    triés `doing → review → todo`) / "Archivé" (done, dernier).
    Chaque ligne = `[titre](slug-id.md)` + `_status_` quand non-done +
    `due` quand renseigné. `who` retiré.
  - `_format_task_detail_md(task, section_path, section_title)` :
    nouveau, écrit la page MD du détail avec frontmatter YAML
    (`id, title, status, who, due_date, classified_at, classified_by,
    section`) + corps = description verbatim + footer nav
    "← retour section / voir log".
  - `_build_sync_plan` : émet `<section>/index.md` ET un
    `<section>/<slug>-<id>.md` par tâche classifiée.
  - `_WIKI_HTML_CSS` enrichi avec les classes `.fullscreen-*` reprises
    de `static/style.css` (mêmes radius/spacing/palette de statuts).
  - `_split_frontmatter(md_text)` : sépare frontmatter YAML / corps.
  - `_render_task_detail(meta, body_md)` : émet la `.fullscreen-card`
    (header `#id` + badge status, title, meta row avec avatar coloré +
    who + due + classified_at, desc rendue en MD, nav bas de page).
  - `_strip_detail_chrome(body_md)` : enlève le H1 et le footer nav
    du corps avant rendu HTML (le wrapper les fournit déjà).
  - `_build_html_plan` : route les pages avec frontmatter vers le
    rendu fullscreen, les autres vers le rendu MD standard.
- `tests/unit/test_ken.py` : 4 tests pour la refonte (frontmatter +
  slug + collision id, segmentation En cours/Archivé sans who,
  collision de slug résolue par l'id suffixe, rendu HTML détail
  avec `.fullscreen-card`).

### Comportements obtenus

- Le wiki gagne une page de détail par ticket avec la description
  complète (résolutions des agents, blocs Modifications/Comportements/
  Garde-fous, code fences…).
- L'index de section reste scannable : titre + status + due_date,
  segmenté actif / archivé.
- Le HTML détail ressemble au modal fullscreen du board : même
  hiérarchie visuelle, badges de statut colorés, avatar.
- Smoke test sur les 196 classifs réelles : `wiki sync` génère 216
  fichiers (1 root + 18×2 index + 196 détails + log + orphans),
  `wiki build` rend les 216 en HTML auto-suffisant.

### Garde-fous

- `pdm run check` : OK (460 tests, lint, typecheck, format,
  interrogate, refurb).
- 4 nouveaux tests + 81 tests `ken.py` au total.
---

[← retour à wiki](index.md) · [voir log](../log.md)
