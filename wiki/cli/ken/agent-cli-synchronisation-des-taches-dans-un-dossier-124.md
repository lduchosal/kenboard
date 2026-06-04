---
id: 124
title: "AGENT / CLI / Synchronisation des tâches dans un dossier"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:25
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #124 — AGENT / CLI / Synchronisation des tâches dans un dossier

Le ken CLI permet de synchroniser les tâches du KENBOARD dans un dossier pour répertorier toutes les décisions d'architecture et de conception.

  ken sync 

Synchronise les tâches dans le dossier doc/kenboard/0001 - Titre de la tâche.md
Le titre est sanitizé pour éviter les / ou chars invalid sur le file system
le dossier doc/kenboard est configuré dans le fichier de config .ken (ajouté automatiquement si pas présent)

---

## Résolution

### Modifications

- src/dashboard/ken.py — ajout de la commande `ken sync`, helpers `_sanitize_filename`, `_sync_filename`, `_format_sync_markdown`, `_resolve_sync_dir`, `_persist_sync_dir`. Ajout du champ `sync_dir` à `KenConfig` (defaut `doc/kenboard`) et de la résolution `KEN_SYNC_DIR` / clé `sync_dir` dans `_load_config`.
- tests/unit/test_ken.py — deux nouvelles classes `TestSyncHelpers` (sanitization, formatage markdown, résolution de chemin) et `TestCliSync` (création des fichiers, persistance dans .ken, dédoublonnage de la clé, renommage sur changement de titre, suppression des fichiers orphelins, préservation des fichiers non gérés, sortie JSON, échec sans projet).
- doc/ken-cli.md — la commande `ken sync`, la clé `sync_dir`/`KEN_SYNC_DIR` dans le tableau de config et un exemple ajoutés.

### Comportements obtenus

- `ken sync` lit `GET /api/v1/tasks?project=<id>` et écrit un fichier markdown par tâche dans `<sync_dir>/<id zero-padded sur 4> - <titre sanitizé>.md`.
- Le contenu du fichier comporte un frontmatter YAML (id, status, who, due_date, position, created_at, updated_at) suivi du titre en H1 et de la description.
- Sanitization des titres: `/ \ : * ? " < > |` et caractères de contrôle remplacés par `_`, espaces multiples écrasés, points/espaces de fin supprimés, `untitled` si vide.
- Renommage transparent quand le titre change (l'ancien fichier portant le même id est supprimé avant l'écriture du nouveau).
- Suppression des fichiers orphelins (id qui n'existe plus côté board) — uniquement les fichiers qui matchent `^\d+ - .+\.md$`, les fichiers manuels comme `README.md` sont préservés.
- Premier appel: ajoute automatiquement `sync_dir=doc/kenboard` au `.ken` (s'il existe). Pas de duplication aux appels suivants.
- Chemins relatifs résolus par rapport au dossier qui contient `.ken` (pour fonctionner depuis n'importe quel sous-répertoire), fallback sur cwd si pas de `.ken`.
- `--json` retourne `{target, written, deleted}`.

### Garde-fous

- `pdm run check` (composite isort, format, docformatter, typecheck, flake8, interrogate, refurb, lint, vulture, test-quick) → ✅ 239 tests passed, 0 lint/type/style/docstring issue.
- 16 nouveaux tests unitaires ciblant la commande sync.
- Pas d'impact sur les tests existants (les tests `TestRequest` qui construisent `KenConfig` manuellement continuent de fonctionner grâce au défaut `sync_dir=doc/kenboard`).
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
