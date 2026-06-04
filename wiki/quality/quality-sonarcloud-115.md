---
id: 115
title: "QUALITY / Sonarcloud"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:24
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #115 — QUALITY / Sonarcloud

https://sonarcloud.io/project/overview?id=lduchosal_kenboard
revue des issues, correction

---

## Résolution

Scan de référence : 2026-04-08T18:48:22 (rev 691cc69). 3 issues ouvertes traitées.

### Modifications

- **src/dashboard/auth_user.py** — `login_rate_limited` retourne désormais `make_response(render_template(...), 429)` au lieu d'un tuple `(html, 429)`. Import de `make_response` ajouté. Fixe `python:S6863` (MAJOR/BUG) — Sonar ne reconnaissait pas le raccourci tuple comme un status explicite sur un error handler Flask.
- **src/dashboard/templates/index.html:49** — `<div class="cat-project" role="button" tabindex="0" onkeydown=...>` → `<button type="button" class="cat-project">`. Fixe `Web:S6819` (MAJOR/CODE_SMELL) sur l'index.
- **src/dashboard/static/style.css:876** — ajout de `.cat-project` à la règle `button:where(...)` du reset pour que le bouton garde l'apparence de l'ancienne div (font, border, padding existants de `.cat-project` gagnent déjà en spécificité).
- **src/dashboard/templates/partials/task_card.html** — commentaire NOSONAR-style expliquant pourquoi la conversion en `<button>` est impossible (cf. Garde-fous).
- **sonar-project.properties** — `sonar.issue.ignore.multicriteria` ciblé : `Web:S6819` ignoré uniquement sur `task_card.html` avec justification dans le commentaire du fichier.

### Comportements obtenus

- Les 3 issues SonarCloud devraient disparaître au prochain scan : 2 par fix réel (S6863 + S6819 index), 1 par exclusion ciblée (S6819 task_card).
- L'effort de dette technique annoncé par Sonar passe de 15min à 0.
- Aucun changement de comportement utilisateur : cat-project reste cliquable clavier + souris (natif côté button), navigation vers `cat/X.html#Y` inchangée. Le kanban-task garde son `role="button"` + onkeydown custom pour Enter/Space.

### Garde-fous

- `pdm run lint` ✅
- `pdm run typecheck` ✅
- `pdm run flake8` ✅
- `pdm run interrogate` ✅ (100%)
- `pdm run test-quick` ✅ (216 passed)
- `pdm run test-e2e` ✅ (54/54 passed, 68s — la carte cat-project reste cliquable et le kanban-task reste manipulable dans tous les tests existants)

### Pourquoi task_card.html ne peut pas devenir un `<button>`

Le `.kanban-task` contient en mode détail un `<button class="btn-edit">Editer</button>` (ligne 28). HTML5 spec interdit tout descendant interactif dans un `<button>`, et l'algorithme de parsing des navigateurs ferme implicitement le `<button>` externe quand il rencontre un `<button>` interne — ce qui sortirait le bouton Editer de la carte et casserait le layout et la propagation du clic. Le pattern `role="button"` + `tabindex="0"` + `onkeydown" Enter/Space" est l'accessibilité correcte pour cette composition. D'où l'exclusion Sonar ciblée plutôt qu'un fix structurel risqué.
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
