---
id: 541
title: "EXTENSION / paintbrush overlay — epic (remplace #520)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-10T07:24:41
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #541 — EXTENSION / paintbrush overlay — epic (remplace #520)

Remplacer le mode quote-and-push d'#520 par un éditeur paintbrush minimaliste en overlay de la page.

## Outils (ultra-limités)
- Rectangle rouge : bordure 5px, fond transparent. Drag pour entourer un élément.
- Texte rouge : 12px. Clic pour poser une annotation à côté d'un rectangle.

## Sortie au push
- SVG (transparent, juste rectangles + textes, coordonnées page) → nouveau champ tasks.attachement (MEDIUMTEXT NULL).
- Description markdown : pour chaque rectangle, on extrait le texte de la zone encadrée (innerText des éléments sous le rectangle) + le texte d'annotation associé.
- POST /api/v1/tasks classique avec ces deux champs + URL.

## Décisions validées
1. SVG = couche d'annotations seule (option b), pas la page entière.
2. Remplace #520 (Alt+K). Cleanup deps dom-anchor-text-* + code quote-mode.
3. Colonne attachement sur tasks (1 par tâche).

## Hors scope
- Agent / LLM post-processeur qui reformule titre + description → tâche séparée.
---

[← retour à extension](index.md) · [voir log](../log/2026-06-10.md)
