---
id: 422
title: "WIKI / SPEC / Format de l'export (#376 followup)"
status: done
who: "Q"
due_date: 
classified_at: 2026-05-24T18:17:27
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #422 — WIKI / SPEC / Format de l'export (#376 followup)

Le wiki shippé en 0.1.103 (#376a–d) ne listait que `#id Titre — status — who`, sans la description.

But : aligner sur le format final avant d'investir dans le chunk d'impl.

## Décisions actées et livrées (chunk F #424, shipped 0.1.104)

- **Q1 — Format** : Option B (une page par ticket). ✅
- **Q4 — Slug** : `<slug-section>/<slug-detail>-<id>.md`. Id en suffixe pour
  garder le slug lisible et désambiguïser les titres dupliqués. ✅
- **Q2 — Section index** :
  - colonnes = titre (lien) + status (masqué quand `done`) + due_date
    (affichée seulement si renseignée ET non-done)
  - `who` retiré (toujours Q/Claude → bruit)
  - segmentation visuelle "En cours" (todo/doing/review) puis "Archivé" (done)
  - ✅
- **Q3 — Page détail** : template `task_fullscreen.html` + CSS `.fullscreen-*`
  réutilisés, layout header (#id + badge status) / title / meta (avatar +
  who + due + classified_at) / description rendue en MD / footer nav
  "← retour section" + "voir log". CSS inline pour pages auto-suffisantes. ✅

## Suivi follow-up (#473 + #479)

- **#473** : `architecture=` dans `.ken` (résolution flag > env > .ken > défaut)
  pour pointer les 4 sous-commandes `wiki *` vers un fichier hors racine.
  Shipped 0.1.108. ✅
- **#479** : `wiki_dir=` + `wiki_html_dir=` dans `.ken` (même chaîne de
  résolution) pour `wiki sync` / `wiki build`. Shipped 0.1.109. ✅

## Questions repoussées (à reprendre comme tâches dédiées si besoin)

### Q5 — Enrichissement log.md / orphans.md

Format actuel suffisant à l'usage. Pistes pour plus tard si besoin émerge :
- lien depuis chaque page détail vers son entrée `log.md`
- `recent.md` = derniers N classifiés
- `log.md` segmenté par section au lieu d'une liste plate

### Q6 — Flag `--no-archived`

Q2 ayant tranché en faveur de la segmentation visuelle, le besoin d'une
variante "vivant uniquement" ne s'est pas matérialisé. À ouvrir comme
tâche séparée si un consommateur du wiki demande explicitement la
version filtrée.
---

[← retour à wiki](index.md) · [voir log](../log.md)
