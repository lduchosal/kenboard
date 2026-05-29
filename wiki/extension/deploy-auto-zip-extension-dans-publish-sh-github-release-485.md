---
id: 485
title: "DEPLOY / Auto-zip extension dans publish.sh + GitHub Release"
status: review
who: "Claude"
due_date: 
classified_at: 2026-05-29T08:13:07
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: extension
section_title: "Browser extension"
---

# #485 — DEPLOY / Auto-zip extension dans publish.sh + GitHub Release

Ajouter au pipeline `publish.sh` un step qui zippe `extension/` et l'attache à la GitHub Release créée au tag.

---

## Résolution

### Modifications

- `publish.sh` :
  - Après le `sed` qui sync `__init__.py`, nouveau bloc qui patche
    `extension/manifest.json` pour aligner son champ `"version"` sur
    `__version__`. Pattern sed portable (BSD + GNU) qui ne matche que
    `"version"` (pas `"manifest_version"`).
  - Après `git push --tags`, nouveau bloc :
    - `zip -r dist/kenboard-extension-${VERSION}.zip extension/` (exclut
      `.DS_Store`), best-effort avec warning si échec.
    - `gh release create kenboard-${VERSION} --generate-notes <zip>` —
      crée la GitHub Release avec notes auto-générées depuis le git
      log + attache le zip. Si `gh` n'est pas dispo ou échoue, warning
      uniquement (le wheel PyPI a déjà été uploadé en amont).
- `extension/README.md` : nouvelle section "Download" pointant vers
  https://github.com/lduchosal/kenboard/releases.
- `README.md` : lien Releases ajouté dans la section Browser extension.

### Comportements obtenus

- À chaque `sh publish.sh --patch`, le `manifest.json` de l'extension
  embarque le numéro de version du wheel, le zip de `extension/` est
  produit et une GitHub Release est créée avec ce zip attaché.
- `gh` absent ou non-authentifié → warning, pas un blocker pour le
  reste du pipeline (PyPI publish n'en dépend pas).
- Le zip exclut `.DS_Store` pour rester propre sur les sideload macOS.

### Garde-fous

- `sh -n publish.sh` : OK (parse sans erreur).
- Test sed sur `manifest.json` avec `VERSION=9.9.99` : substitue bien
  `"version"` sans toucher `"manifest_version"`.
- `pdm run check` : OK (480 tests inchangés).

### Validation à la première release

L'effet réel (zip + GitHub release) se verra au prochain `sh publish.sh
--patch` (cette release-ci, qui inclut #480 + #485, devrait en être
l'auto-test).
---

[← retour à extension](index.md) · [voir log](../log.md)
