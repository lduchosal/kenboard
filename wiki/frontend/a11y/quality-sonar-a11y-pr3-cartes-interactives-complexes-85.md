---
id: 85
title: "QUALITY / Sonar a11y - PR3: cartes interactives complexes"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:24
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/a11y
section_title: "Accessibility"
---

# #85 — QUALITY / Sonar a11y - PR3: cartes interactives complexes

Sous-tâche de #78. Cas tordus où on ne peut pas simplement utiliser <button>.

Cibles:
1. task_card.html:8 — <div class='kanban-task' onclick='toggleDetail'>
   - Contient déjà des <button> internes (Editer)
   - Solution: role='button' tabindex='0' + handler keydown Enter/Space
   - Conséquence: chaque carte devient tabbable (potentiellement 50+ tab stops)

2. index.html:28 — <div class='cat-project' onclick='window.location=...'> imbriqué dans <a class='cat-card'>
   - HTML actuellement invalide (lien dans lien masqué)
   - Refactor structurel: extraire les cat-projects hors du parent <a>, ou faire que cat-card ne soit plus un <a>

À traiter en dernier, après PR1 et PR2 validés. Risque visuel + risque sur les tests e2e (sélecteurs et drag SortableJS).

~7 issues.
---

[← retour à frontend/a11y](index.md) · [voir log](../../log.md)
