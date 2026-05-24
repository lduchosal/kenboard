---
id: 118
title: "AGENT / CLI / Bonnes pratiques"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:25
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #118 — AGENT / CLI / Bonnes pratiques

Ajouter dans le ken help les bonnes pratiques du KENBOARD.
- Lire les tâches TODO
- Les faire progresse en DOING quand le modèle travaille dessus
- Les faire proegresser en REVIEW quand le travail est fini
- Modifier le contenu de la tâche pour résumer les opération éffectuées

etc..
ces bonnes pratiques sont référencées dans un fichier MD qui est distribué avec le kenboard et affiché dans le ken help

---

## Résolution

### Modifications

- **src/dashboard/agent_guide.md** (nouveau, ~90 lignes) — guide markdown qui décrit le workflow agent : pick → wip → review → resolution. Sections : The loop (5 étapes), Statuses and ownership, Filters and parsing (interdiction du jq pipeline), Quick reference (toutes les commandes ken essentielles), Other practices (no requests/httpx, .ken sécurisé, pas de scope creep, validation titre sans `<>`), See also (renvoi vers `ken --help` et le runbook 401).
- **src/dashboard/ken.py** — nouvelle commande `@cli.command(name="help") def help_cmd()`. Charge `agent_guide.md` via `importlib.resources.files('dashboard').joinpath('agent_guide.md').read_text()` et l'echo. Import `from importlib import resources` ajouté en haut du fichier.
- **tests/unit/test_ken.py** — nouvelle classe `TestCliHelp` avec 2 tests :
  - `test_help_prints_agent_guide` : vérifie exit 0 et présence des marqueurs clés (titre, transitions de status, commandes du workflow)
  - `test_help_subcommand_listed_in_main_help` : vérifie que `ken --help` advertise bien la nouvelle subcommand

### Comportements obtenus

- `ken help` affiche le guide complet (vérifié smoke test : 90+ lignes de markdown lisible).
- `ken --help` liste maintenant la subcommand : `help      Print the agent guide (kenboard best practices for LLM agents).`
- Le fichier MD est embarqué dans le wheel via le comportement par défaut de pdm-backend (qui inclut tous les non-Python de `src/dashboard/` — vérifié pour les .sql existants). Aucun changement dans `pyproject.toml` requis.
- L'agent fraîchement onboardé (#117) peut immédiatement appeler `ken help` après installation pour découvrir le workflow attendu.

### Garde-fous

- `pdm run lint` ✅
- `pdm run typecheck` ✅ (23 source files, importlib stdlib)
- `pdm run flake8` ✅
- `pdm run interrogate` ✅ (100% — la nouvelle commande a sa docstring)
- `pdm run test-quick` ✅ (222 passed, +2 nouveaux tests dans `TestCliHelp`)
- Smoke test manuel : `ken help | head -25` affiche le guide ; `ken --help | tail -20` liste la subcommand

### Choix de design

- **Pas de `ken --help` override** : Click génère automatiquement `--help` à partir des docstrings des commandes ; on garde ça pour la référence brute des commandes. `ken help` (subcommand sans tiret) est le complément qui donne le **workflow** + bonnes pratiques.
- **Fichier MD plutôt que docstring inline** : (a) un agent peut en faire un `cat` brut sans Click ; (b) le contenu est lisible/éditable comme un doc git normal ; (c) si le projet ajoute un site doc statique, le même fichier peut être réutilisé.
- **`importlib.resources` plutôt que chemin absolu** : ça marche pareil en dev (editable install) et en wheel installé ; c'est l'API stdlib moderne (3.9+) ; pas de hard-code de `__file__ + '../agent_guide.md'`.
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
