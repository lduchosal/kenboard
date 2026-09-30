---
id: 1127
title: "VSCODE / plugin vscode pour le kenboard ?"
status: done
who: "Claude"
due_date: 
updated_at: 2026-09-30T14:44:59
classified_at: 2026-09-30T14:36:54
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #1127 — VSCODE / plugin vscode pour le kenboard ?

**TL;DR** — Pas d'outil kenboard dans VS Code → extension `vscode/` qui parle à l'API REST (token de `.ken` / `ken.ini`) : liste des tâches du projet dans la barre latérale, détail rendu comme la vue plein écran du site, « Move to… », ouverture sur le site ; qualité branchée dans `publish.sh --quality` et `.vsix` joint à chaque release GitHub.

Idée d'origine : extension VS Code pour kenboard — lister/afficher les tâches du projet courant (ken.ini), changer de statut (todo/doing/review), créer une tâche depuis l'éditeur, en réutilisant l'API REST (même auth token que `ken`). À explorer : périmètre, réutilisation du CLI `ken` vs appel direct à l'API, distribution (marketplace vs .vsix).

## Décision d'architecture : l'API REST, pas le site encapsulé

On n'encapsule pas le site dans une webview, parce que ce n'est pas faisable sans affaiblir la sécurité :
- `app.py` envoie `frame-ancestors 'none'` + `X-Frame-Options: DENY`, donc le site refuse de s'afficher en iframe ;
- les cookies de session sont en `SameSite=Lax` : dans une iframe de webview (contexte cross-site), ils ne sont pas envoyés ;
- le contrôle CSRF Origin == Host (`auth.py`) rejette l'origine `vscode-webview://`.

On passe donc par l'**API REST** `/api/v1/*` avec `Authorization: Bearer <token>`, la même authentification que `ken`.
L'appel est direct en TypeScript (`fetch` natif), sans lancer le CLI `ken` : pas de dépendance au venv Python, pas de processus lancé à chaque action.

## Périmètre MVP (preuve de concept)

1. **Configuration automatique** : lire `ken.ini` (`base_url`, `project_id`) et `.ken` (`api_token`) à la racine du workspace. Si l'un des deux manque, afficher un message clair, sans UI de configuration.
2. **Arborescence « Kenboard »** dans la barre latérale : les tâches du projet (`GET /api/v1/tasks?project=<id>`) groupées par statut (todo / doing / review), avec « #id titre » et l'assignee. Un bouton pour rafraîchir.
3. **Changer de statut** : clic droit sur une tâche, puis « Move to… » (`PATCH /api/v1/tasks/<id>`), et rafraîchissement.
4. **Ouvrir dans kenboard** : ouvre la tâche ou le board dans le navigateur.

Hors MVP (à voir si le concept tient) : création de tâche, vue détail en markdown (webview locale avec marked + dompurify), classement wiki (`groom`), filtres par assignee, publication sur la marketplace.

## Livrable / critères de validation

- Extension TypeScript minimale (`yo code` ou squelette à la main), zéro dépendance runtime.
- Packagée en `.vsix` et installée localement (`code --install-extension`), sans publication.
- Validation : ouvrir le repo kenboard dans VS Code, voir les tâches du projet, déplacer une tâche todo → doing, et vérifier le changement avec `ken show <id>`.
- À trancher après la preuve de concept : emplacement (sous-dossier `vscode/` du repo kenboard ou repo séparé), publication sur la marketplace.


---

## Résolution

### Modifications

- `vscode/src/config.js` — résolution `KEN_*` > `.ken` > `ken.ini`, recherche vers le haut depuis le workspace (même chaîne que `ken`).
- `vscode/src/api.js` — client `/api/v1` en `fetch` natif, Bearer ; liste des tâches, projet, `PATCH` statut ; URL `/cat/<cat_id>.html#ID-<id>`.
- `vscode/src/tree.js` — groupement todo / doing / review, tri par position.
- `vscode/src/extension.js` — vue « kenboard » (barre d'activité), panneau détail réutilisé, commandes Afficher le détail / Move to… / Ouvrir dans kenboard / Rafraîchir / Ouvrir le board.
- `vscode/src/detail.js` + `vscode/media/render.js` — webview qui reprend la vue plein écran du site (`task_fullscreen.html`, styles `.fullscreen-*`), rendu par le `marked` + `DOMPurify` du site (`gfm` + `breaks`), CSP à nonce ; icône kenboard (carré arrondi, ombre) au-dessus du bouton « Ouvrir sur kenboard ».
- `vscode/test/*.test.js` — 14 tests `node:test` (config, API avec fetch simulé, arbre, HTML du détail / échappement).
- `vscode/package.json`, `jsconfig.json`, `.vscodeignore`, `README.md` — manifeste, tsc strict, packaging, doc.
- `biome.json`, `package.json` (`@types/vscode` ~1.90 aligné sur `engines.vscode`, `@types/node`), `pyproject.toml` (`vscode-lint` / `vscode-typecheck` / `vscode-test` / `vscode-package`).
- `publish.sh` — étape qualité VS Code ; au bump, version de `vscode/package.json` synchronisée ; `dist/kenboard-vscode-<version>.vsix` joint à la release GitHub avec le zip navigateur ; compteurs d'étapes 24/23 et 38/36.
- Infra (angel/ansible) : `roles/reverse/files/nginx/sites/www.kenboard.2113.ch.conf` + `www.todo.2113.ch.conf` — en-têtes CSP sur une ligne ; la version multi-ligne était rejetée par le `fetch` Node (`HPE_INVALID_HEADER_TOKEN`).

### Comportements obtenus

- Zéro configuration dans un repo déjà initialisé par `ken init` ; message explicite sinon (ken.ini/.ken absent, project_id ou api_token manquant, board injoignable).
- Clic sur une tâche → détail markdown identique au site ; clic droit → Move to… (le détail ouvert se met à jour).
- Le site n'est pas encapsulé (frame-ancestors 'none', SameSite=Lax, CSRF Origin) : tout passe par l'API.
- Distribution : `.vsix` en asset de la GitHub Release, `code --install-extension`. Marketplace non visée (éditeur, LICENSE, anglais, icône à revoir).
- Limite relevée → #1129 (corrigée sur main, `0a81f26`, pas encore publiée) : `GET /api/v1/tasks/<id>` refusé aux clés API projet ; l'extension affiche le détail depuis la liste.

### Garde-fous

- `sh publish.sh --quality` : vert (lint/types/tests Python, JS, VS Code 14/14, 664 unit + 52 E2E, metrics gate).
- tsc strict sur `vscode/src` ; biome sur `vscode/`.
- Rendu du détail vérifié hors VS Code (jsdom, vraie description de #1127) ; appels live liste + projet contre le board de prod.
- Packaging simulé (version 9.9.9 → `dist/`, liste d'assets de release) ; `.vsix` installé et validé dans VS Code par l'utilisateur.
---

[← retour à extension](index.md) · [voir log](../log/2026-09-30.md)
