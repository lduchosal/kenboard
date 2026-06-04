---
id: 111
title: "UX / Double clic sur une tâche amène à l'édition de la tâche"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:23
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #111 — UX / Double clic sur une tâche amène à l'édition de la tâche

Double-cliquer sur une carte de tâche ouvre directement la modale d'édition (sans passer par le bouton "Editer").

---

## Résolution

### Modifications

- **`src/dashboard/templates/partials/task_card.html`** — ajout d'un attribut `ondblclick` qui appelle `openEditTask(this, ...)` avec les mêmes paramètres inlinés que le bouton "Editer". Le handler n'est posé que sur les cartes en mode kanban (pas sur celles avec `task_href`, qui naviguent ailleurs au premier clic).
- **`src/dashboard/static/app.js`** — `toggleDetail` accepte maintenant l'event et bail-out si `event.detail > 1` (le 2e clic d'un double-clic), pour ne pas refermer le mode détail sous la modale qui s'apprête à s'ouvrir.

### Comportements obtenus

- Simple clic → mode détail (comportement existant inchangé, hash URL #ID-x sync via #109).
- Double clic → mode détail bref sur le 1er clic (~50-100ms selon la vitesse), puis ouverture de la modale d'édition. Le 2e clic est neutralisé.
- Clavier (Enter/Espace) → équivalent du simple clic via `this.click()` synthétique (`event.detail === 0`), donc aucune régression.
- Cartes du "doing overview" sur l'index : pas de dblclick ajouté, elles continuent de naviguer au premier clic vers la catégorie + tâche en mode détail (#109).
- Bouton "Editer" interne : inchangé, son `event.stopPropagation()` empêche déjà le toggleDetail de tirer.

### Garde-fous

- \`pdm run lint\` : OK.
- Tests unitaires (hors test_api_keys lié au WIP de la tâche #110) : 182 passed.
---

[← retour à frontend/ux](index.md) · [voir log](../../log.md)
