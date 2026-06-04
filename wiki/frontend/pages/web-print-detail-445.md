---
id: 445
title: "WEB / Print detail"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-25T13:53:53
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/pages
section_title: "Page templates (Jinja2)"
---

# #445 — WEB / Print detail

Quand on est dans le détail d'une fiche, l'impression doit proposer d'imprimer la fiche en cours, actuellement on voit la liste. le détail doit être prévu pour être imprimé correctement

---

## Résolution

### Modifications

- `src/dashboard/static/style.css` : nouveau bloc `@media print` à la
  fin du fichier qui cible la `<dialog class="fullscreen-modal">` :
  - Hide tout le body (`visibility: hidden`) sauf `dialog.fullscreen-modal[open]`
    et ses descendants (`visibility: visible`).
  - Repositionne la dialog en flux normal (`position: absolute; display: block`)
    avec largeur 100%, sans backdrop (`::backdrop { display: none }`).
  - Strip le chrome modal : `box-shadow: none`, `border-radius: 0`,
    `max-width/max-height: none`, `overflow: visible`.
  - Cache la croix `.modal-close` et la barre `.fullscreen-actions`
    (Editer / Fermer n'ont aucun sens sur papier).
  - Force `color: black` pour rester lisible en N&B.
  - `page-break-inside: avoid` sur `pre`, `blockquote`, `table` pour
    éviter de couper les blocs de code en deux pages.

### Comportements obtenus

- Cmd+P / Ctrl+P avec une fiche ouverte → imprime la fiche seule
  (titre, métadonnées, description rendue en MD).
- Cmd+P sur la vue kanban (aucune fiche ouverte) → comportement
  inchangé (imprime la liste).
- Pas de JS — purement CSS, fonctionne dans tous les navigateurs
  qui supportent `<dialog>` (Chrome/Edge/Firefox/Safari récents).

### Garde-fous

- `pdm run check` : OK (466 tests, lint, typecheck, format, vitest,
  vite build).
- Vérifié visuellement via DevTools "Emulate CSS print media".
---

[← retour à frontend/pages](index.md) · [voir log](../../log/2026-05-25.md)
