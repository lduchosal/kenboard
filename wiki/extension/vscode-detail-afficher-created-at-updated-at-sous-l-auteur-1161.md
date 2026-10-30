---
id: 1161
title: "VSCODE / DETAIL / Afficher created at / updated at sous l'auteur"
status: review
who: "Claude"
due_date: 
updated_at: 2026-10-30T11:38:25
classified_at: 2026-10-30T11:38:26
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #1161 — VSCODE / DETAIL / Afficher created at / updated at sous l'auteur

**TL;DR** — La vue détail de l'extension VS Code n'affichait pas les dates de la carte → ajout de « created at …, updated at … » sous le nom de l'auteur, comme sur le site (#1157).

Parité avec le web (#1157) : dans la vue détail de l'extension VS Code, ajouter sous le nom de l'auteur « created at xxxx, updated at xxxx ».

## Résolution

### Modifications
- `vscode/src/detail.js` — `fmtDateTime(iso)` (copie de celui du site : `dd.mm.yyyy HH:MM` par découpage de chaîne, pas de `Date` → pas de décalage UTC) ; `<div class="fullscreen-dates">` sous `.fullscreen-meta` ; CSS `.fullscreen-dates` alignée sur le site (+ marge droite du bloc « Ouvrir sur kenboard »).
- `vscode/src/api.js` — typedef `Task` : `created_at`, `updated_at`.
- `vscode/test/detail.test.js` — tests `fmtDateTime` + rendu de la ligne (et ligne vide si dates absentes).

### Comportements obtenus
- Détail d'une tâche dans VS Code : `created at 30.10.2026 10:02, updated at 30.10.2026 11:45` sous l'avatar + nom ; les dates proviennent de `GET /api/v1/tasks/<id>` (déjà exposées).

### Garde-fous
- `pdm run vscode-lint`, `vscode-typecheck`, `vscode-test` (17 pass, 0 fail) : OK.
- Publié via `sh publish.sh` (release suivante, `.vsix` attaché à la release GitHub).
---

[← retour à extension](index.md) · [voir log](../log/2026-10-30.md)
