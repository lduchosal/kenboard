---
id: 1164
title: "doc / extension vscode : /aide ne parle pas de l'installation de l'extension vscode"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-01T10:16:06
classified_at: 2026-11-01T10:06:34
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: docs
section_title: "Documentation"
---

# #1164 — doc / extension vscode : /aide ne parle pas de l'installation de l'extension vscode

**TL;DR** — `/aide` ignorait l'extension VS Code → ajout d'une carte *VS Code — Le ken pour l'éditeur* (télécharger, installer, configurer, utiliser) + test.

La page `/aide` (`src/dashboard/templates/aide.html`) documente le `ken` CLI (section *Bots*) et l'extension navigateur (section *Extension*), mais rien sur l'extension VS Code (ken #1127, `vscode/`).

À ajouter, sur le modèle de la section navigateur :

1. **Télécharger** — GitHub Releases → `kenboard-vscode-<version>.vsix` (version alignée sur kenboard).
2. **Installer** — `code --install-extension kenboard-vscode-<version>.vsix`, ou VS Code → Extensions → `…` → *Install from VSIX…*.
3. **Configurer** — aucune config propre : lit `ken.ini` / `.ken` du workspace (chaîne `KEN_*` > `.ken` > `ken.ini`, recherche vers le haut) → renvoyer vers `ken init "<onboarding-url>"`.
4. **Utiliser** — vue barre latérale todo/doing/review, clic = détail, clic droit → *Move to…*, boutons rafraîchir / ouvrir le board.

Source : `vscode/README.md`. Vérifier aussi les tests de la page aide (`tests/`) si le contenu est asserté.

## Résolution

### Modifications
- `src/dashboard/templates/aide.html` — nouvelle carte (badge vert *VS Code*) après la carte navigateur : 1. Télécharger (`kenboard-vscode-<version>.vsix` sur GitHub Releases, version alignée sur kenboard) ; 2. Installer (`code --install-extension …` ou *Install from VSIX…*) ; 3. Configurer (aucune saisie : lit `ken.ini`/`.ken` comme le CLI, `KEN_*` priment → `ken init "<Copy onboard link>"` ; réglage `kenboard.autoRefreshSeconds`) ; 4. Utiliser (vue *Tâches* todo/doing/review, détail, *Move to…*, *Ouvrir dans kenboard*, boutons rafraîchir / ouvrir le board).
- `tests/unit/test_page_routes.py` — `TestAidePage.test_has_vscode_section` : titre de section, nom du `.vsix`, `code --install-extension`, `ken init`.

### Comportements obtenus
- `/aide` couvre les trois clients : CLI `ken`, extension navigateur, extension VS Code.

### Garde-fous
- `pdm run test-unit` : vert (dont le nouveau test).
- `pdm run lint` : All checks passed.
---

[← retour à docs](index.md) · [voir log](../log/2026-11-01.md)
