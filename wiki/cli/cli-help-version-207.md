---
id: 207
title: "CLI / Help / Version"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:47
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli
section_title: "Command-line interface"
---

# #207 — CLI / Help / Version

Afficher la version dans le kenboard help

---

## Résolution

### Modifications

- `src/dashboard/cli.py` — ajout `@click.version_option(package_name="kenboard")` sur le groupe CLI. Click lit automatiquement la version depuis les métadonnées du package installé.

### Comportements obtenus

- `kenboard --version` → `kenboard, version 0.1.64`
- `kenboard --help` → affiche l'option `--version` dans les options disponibles

### Garde-fous

- `pdm run test-quick` → 321 passed
---

[← retour à cli](index.md) · [voir log](../log/2026-05-24.md)
