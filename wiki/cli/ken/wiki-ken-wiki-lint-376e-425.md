---
id: 425
title: "WIKI / ken wiki lint (#376e)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T18:00:22
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #425 — WIKI / ken wiki lint (#376e)

Sous-tâche E de #376. Chunks A–F ont livré la DB, le CLI de classification, l'export MD + HTML, et la refonte format détail. Ici on ajoute le lint pour garder le wiki en bonne santé en CI.

## À livrer

CLI `ken wiki lint` — check de cohérence, exit code CI-friendly.

Checks :
- **ORPHAN** (error) : classification pointe vers une section pas déclarée dans `ARCHITECTURE.md`
- **UNCLASSIFIED** (warn) : tâche sans classification
- **EMPTY-SECTION** (info) : section déclarée mais aucune tâche dedans

Options :
- `--architecture PATH` (défaut `./ARCHITECTURE.md`)
- `--strict` : warnings comptent aussi comme errors
- `--json` : sortie structurée pour CI

Exit code : 0 si aucun ERROR (et aucun WARN en mode `--strict`), 1 sinon.

## Tests

- lint orphans → ERROR, exit 1
- lint unclassified → WARN, exit 0 par défaut, 1 avec `--strict`
- lint empty section → INFO, n'influence pas l'exit
- lint clean → exit 0
- `--json` → schéma stable `{summary, errors, warnings, info}`

## Hors scope

Q5 (enrichissement log/orphans) — repoussé.
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
