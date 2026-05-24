---
id: 422
title: "WIKI / SPEC / Format de l'export (#376 followup)"
status: todo
who: "Q"
due_date: 
classified_at: 2026-05-24T18:17:27
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #422 — WIKI / SPEC / Format de l'export (#376 followup)

Le wiki shippé en 0.1.103 (#376a–d) est trop pauvre : la page section ne liste que `#id Titre — status — who`, sans la description.

But : aligner sur le format final avant d'investir dans le chunk d'impl.

## Décisions actées

- **Q1 — Format** : Option B (une page par ticket).
- **Q4 — Slug** : `<slug-section>/<slug-detail>-<id>.md`. Id en suffixe pour
  garder le slug lisible et désambiguïser les titres dupliqués.
- **Q2 — Section index** :
  - colonnes = titre (lien) + status (masqué quand `done`) + due_date
    (affichée seulement si renseignée ET non-done)
  - `who` retiré (toujours Q/Claude → bruit)
  - segmentation visuelle "En cours" (todo/doing/review) puis "Archivé"
    (done) plus discret
- **Q3 — Page détail** : reprendre le template **kenboard task
  fullscreen** (`templates/modals/task_fullscreen.html` + CSS
  `.fullscreen-*` dans `static/style.css`).
  - Header : `#id` (dimmed) + badge status
  - Title (h2, 22px, bold)
  - Meta row : avatar coloré + who (bold) + when (due_date, dimmed)
  - Description rendue en MD, séparée par un border-top
  - Pas de bouton "Éditer / Fermer" (page statique) ; à la place :
    "← retour section" + "voir log"
  - CSS à recopier inline depuis style.css (pas de var(--…) — le HTML
    est auto-suffisant). Garder la même hiérarchie visuelle pour que
    le wiki ressemble immédiatement au board.

## Questions encore ouvertes

### Q5 — Périmètre log.md / orphans.md

Actuels :
- `log.md` chronologique de toutes les classifs (sans contexte de la section)
- `orphans.md` quand une section référencée n'existe plus dans `ARCHITECTURE.md`

À étendre ? Lien depuis chaque page détail vers son entrée log ?
Ajouter un `recent.md` = derniers N classifiés ?

### Q6 — Flag CLI `--no-archived` ?

Q2 tranche : tout inclure, segmenter visuellement (en cours / archivé).
Reste à décider : faut-il quand même offrir `ken wiki sync --no-archived`
pour générer une variante allégée (sans les `done`) ?

## Livrable

Pas de code. Réponses Q5/Q6, puis ouverture du chunk d'impl #376f.
---

[← retour à wiki](index.md) · [voir log](../log.md)
