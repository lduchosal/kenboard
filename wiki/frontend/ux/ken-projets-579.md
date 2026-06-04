---
id: 579
title: "KEN / Projets"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-30T23:57:45
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #579 — KEN / Projets

## Annotations

**Source:** [KEN / Projets](https://www.kenboard.2113.ch/cat/0ee51b6f-81b8-4da0-9efc-0bd9e01f9e4f.html)

> KEN / KENBOARD

les textes sont tronqués, agrandir le bloc

---

## Résolution

Cible identifiée via le SVG attachement (#574 round-trip ✓) : le rectangle rouge encadre la colonne de labels du chart per-project (#572). Labels monospace comme `backend/auth` (12 chars × 6.6px ≈ 80px) ne tenaient pas dans la flex-basis 32% (= ~83px sur cards 260px de min).

### Modifications
src/dashboard/static/style.css :
- `.wiki-bar-label { flex: 0 0 32% → 0 0 50% }` : la moitié de la card pour le label, l'autre moitié reste pour la track de barre + le count à droite.
- `font-size: 11px` (down from inherited 12px) : économise ~10% d'encombrement, lisibilité conservée.

S'applique au chart #540 (dashboard mini-charts) ET au #572 (per-project sur category page) puisque les deux partials utilisent les mêmes classes `.wiki-bar-*`.

### Garde-fous
- TestCategoryPage + TestIndexPage : 8+5 = 13/13 passed.
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-30.md)
