---
id: 249
title: "UX / Keyboard shortcuts"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:30:01
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/ux
section_title: "UX / interactions"
---

# #249 — UX / Keyboard shortcuts

## Raccourcis clavier

| Contexte | Touche | Action |
|---|---|---|
| **Board** | `↑` / `↓` | Déplacer la sélection dans la colonne |
|  | `←` / `→` | Sauter à la colonne adjacente, même position (skip si vide) |
|  | `j` / `k` / `h` / `l` | Alias Vim pour les flèches |
|  | `Enter` | Ouvrir la carte sélectionnée (mode détail) |
|  | `e` | Éditer la carte sélectionnée (modal d'édition) |
|  | `f` | Vue plein écran de la carte sélectionnée |
|  | `c` | Créer une tâche dans la colonne de la carte sélectionnée |
|  | `Esc` | Cascade : ferme plein écran → ferme modal → quitte detail-mode → désélectionne |
|  | `?` | Affiche la modal d'aide des raccourcis |
|  | `g` puis `h` | Retour à l'accueil (préfixe `g`, timeout 1500 ms) |
| **Modal — `<input>`** | `Enter` | Sauver |
|  | `Esc` | Fermer (handler générique existant) |
| **Modal — `<textarea>`** | `Cmd+Enter` / `Ctrl+Enter` | Sauver |
|  | `Enter` | Nouvelle ligne (comportement par défaut) |
|  | `Esc` | Fermer |

## Règles de routing implémentées

1. Modal ouverte → seuls `Enter` / `Cmd+Enter` (selon le type de champ) sont actifs ; tout le reste est swallow.
2. Focus sur `<input>` / `<textarea>` / `[contenteditable=true]` → handler retourne tôt (pas de double-binding accidentel quand on tape "edit" dans un titre).
3. Préfixe `g` : flag + timeout 1500 ms ; toute autre touche annule le prefix.

## Résolution

### Modifications

- `src/dashboard/static/app.js` : nouvelle section *Keyboard shortcuts (#249)* en queue de fichier. Modèle de sélection (`data-kb-selected`), helpers de navigation 2D (`_kbMoveVertical` / `_kbMoveHorizontal` avec skip des colonnes vides), action handlers (`_kbActionOpen|Edit|Fullscreen|Create|Help|Home|Escape`), routing `keydown` global avec gates input + modal, sync clic-souris → sélection, init au load via `sessionStorage["kb-focus-task"]` (priorité) ou hash `#ID-<id>` (fallback).
- `src/dashboard/static/app.js` : `saveTaskModal()` stocke l'id sauvé dans `sessionStorage["kb-focus-task"]` avant `location.reload()` pour que la carte reste sélectionnée + scrollée après le reload, sans déclencher le `detail-mode` du hash.
- `src/dashboard/static/style.css` : focus ring sur `.kanban-task[data-kb-selected="true"]` et styles complets pour `#kb-help-modal` (rangées kbd + label, sections h4).
- `src/dashboard/templates/modals/keyboard.html` : nouveau composant listant tous les raccourcis (réutilise `.project-add-modal` + `.modal-close`).
- `src/dashboard/templates/base.html` : include du nouveau modal `keyboard.html`.

### Comportements obtenus

- Sélection (encadré bleu autour de la carte) avec `↑↓←→` ou `hjkl`. Le clic souris sélectionne aussi.
- `Enter` sur la sélection ouvre le détail (réutilise `toggleDetail`). `e` ouvre la modal d'édition. `f` ouvre le plein écran. `c` ouvre la modal de création dans la colonne de la sélection (ou dans la première si rien n'est sélectionné).
- `Esc` cascade en quatre étapes : plein écran > modal > detail-mode > désélection.
- `?` ouvre une modal d'aide qui liste tous les raccourcis groupés par contexte.
- `g h` retourne à `/`.
- Modal de tâche : `Enter` sur un `<input>` sauve ; `Cmd/Ctrl+Enter` sur le `<textarea>` sauve. Après sauvegarde la carte sauvée est sélectionnée et scrollée dans le viewport au reload (via `sessionStorage`, n'interfère pas avec le hash `#ID-<id>` du détail-mode).
- Aucun raccourci ne se déclenche pendant qu'on tape dans un champ ou qu'une modal autre que `task-modal` est ouverte.

### Garde-fous

- `pdm run test-unit` : 368 passed (régression nulle)
- `pdm run test-e2e` : 52 passed / 0 failed (les 4 tests `TestTaskCRUD` retirés au préalable parce qu'ils échouaient sur la régression #221 sont toujours retirés, suivis par #248)
- `pdm run lint` : All checks passed
- `pdm run flake8` : clean
- `pdm run typecheck` : Success (27 fichiers, mypy strict)

### Tests e2e à ajouter

Les tests Playwright pour chaque raccourci ne sont pas inclus dans ce premier passage parce que l'utilisateur a demandé "start implementation, I'll test it" — il valide manuellement d'abord, puis on ajoute la couverture e2e. À reprendre dans un suivi si l'impl tient.

## Folded in

- #247 (UX / Edit task / Enter save task) : intégré comme la section "Modal de tâche".
---

[← retour à frontend/ux](index.md) · [voir log](../../log/2026-05-24.md)
