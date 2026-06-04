---
id: 480
title: "KEN / WEB CLI"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-27T18:02:21
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: frontend/js
section_title: "JS modules"
---

# #480 — KEN / WEB CLI

Browser extension qui permet de créer une ken task depuis n'importe quel site visité — pour capturer des bugs sur le pouce.

## Design (revisité 2026-05-27)

Pivot du JS-injection vers une **extension navigateur** :
- Usage : perso (moi sur n'importe quel site), pas multi-utilisateur.
- Auth : api_token existant. **Zéro nouveau code serveur.**
- Server : POST `/api/v1/tasks` existant suffit.
- Screenshot : `chrome.tabs.captureVisibleTab()` raster PNG.
- Distribution : sideload pour usage perso (load unpacked).

---

## Résolution

### Modifications

- `extension/` (nouveau dossier à la racine) :
  - `manifest.json` (manifest v3, permissions `storage` + `activeTab` +
    `host_permissions: ["<all_urls>"]`, raccourci `Ctrl+Shift+K` /
    `Cmd+Shift+K` qui exécute `_execute_action` → ouvre le popup)
  - `popup.html` + `popup.css` + `popup.js` : form title / description /
    who / "Include screenshot" checkbox. Au load, pré-remplit title
    depuis `tab.title` et capture le viewport avant POST.
  - `options.html` + `options.js` : settings (base_url, api_token,
    project_id, default who) stockés dans `chrome.storage.local` +
    bouton "Test connection" qui hit `GET /api/v1/projects`.
  - `README.md` : install (Chrome / Firefox sideload) + first-run +
    notes (captureVisibleTab impossible sur chrome://, file://, etc.).
- `README.md` (principal) : nouvelle section "Browser extension" sous
  "For BOTs" avec lien vers `extension/README.md` + GitHub Releases.

### Comportements obtenus

- `Cmd+Shift+K` depuis n'importe quel onglet → popup, pré-rempli avec
  le titre de la page. Submit crée une tâche `todo` dans le projet
  configuré, description = corps utilisateur + URL source + screenshot
  PNG embarqué en base64 data-URL.
- Erreurs réseau / HTTP affichées inline dans le popup (rouge), succès
  vert + auto-close après 800ms.
- "Test connection" dans options valide le triplet base_url + token +
  project_id avant de sauvegarder.

### Garde-fous

- `pdm run check` : OK (480 tests inchangés, l'extension est hors du
  scope biome/vitest/python).
- L'extension utilise l'auth bearer existante (`POST /api/v1/tasks`
  accepte déjà ce header). Aucune migration, aucune route nouvelle.

### Suite

#485 (DEPLOY) ajoute l'auto-zip + GitHub Release pour distribuer le
package sideload sans cloner le repo.
---

[← retour à frontend/js](index.md) · [voir log](../../log/2026-05-27.md)
