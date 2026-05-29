---
id: 473
title: "WIKI / ARCHITECTURE"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-27T10:44:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #473 — WIKI / ARCHITECTURE

Ajouter un paramètre dans le .ken pour spécifier l'emplacement du fichier ARCHITECTURE

Doc/Spécifications/Architecture.md
  
  …qui alimenterait le défaut de --architecture pour les quatre sous-commandes (groom, sync, lint, build) — le flag CLI restant prioritaire en override.

---

## Résolution

### Modifications

- `src/dashboard/ken.py` :
  - Nouvelle constante `DEFAULT_ARCHITECTURE = "ARCHITECTURE.md"`.
  - `KenConfig` gagne un champ `architecture: str = DEFAULT_ARCHITECTURE`.
  - `_load_config` résout `architecture` selon la chaîne :
    `KEN_ARCHITECTURE` env > `architecture=` dans .ken > défaut. Le
    parsing UTF-8 existant de `_parse_ken_file` couvre les chemins
    accentués (`Doc/Spécifications/…`).
  - Les 4 sous-commandes `wiki groom/sync/build/lint` passent à
    `--architecture` `default=None`, et résolvent en début de body :
    `architecture = architecture or cfg.architecture`. Le flag CLI
    reste donc prioritaire quand explicitement passé.
  - `wiki_build` (qui ignorait `cfg`) prend maintenant `ctx.obj["cfg"]`.
  - Help text des flags mis à jour pour expliquer la chaîne de
    résolution.
- `tests/unit/test_ken.py` :
  - `TestLoadConfig` : 3 tests (défaut, lecture depuis .ken avec
    chemin accenté, env > file).
  - `TestCliMutations` : 2 tests d'intégration sur `ken wiki groom`
    (utilise bien le path .ken quand pas de flag, le flag CLI override).

### Comportements obtenus

- `.ken` avec `architecture=Doc/Spécifications/Architecture.md` →
  `ken wiki {groom,sync,build,lint}` lit l'arch depuis ce chemin sans
  flag.
- `ken wiki sync --architecture other.md` continue de prendre `other.md`.
- Chemin accenté géré (UTF-8 round-trip vérifié par test).

### Garde-fous

- `pdm run check` : OK (471 tests, lint, typecheck, format, refurb).
- 5 nouveaux tests dans `test_ken.py`.

### Non couvert ici

Les deux side-points de la demande originale sont hors scope de cette tâche :
1. Le 500 sur `POST /api/v1/wiki/classify` / `GET /api/v1/wiki/unclassified`
   (error_id E-6a16abca-53c5) — migration 0021 non appliquée. À traiter via
   `kenboard migrate` sur l'instance concernée, indépendant du .ken.
2. La gestion des chemins accentués est validée par test (couvert ici).
---

[← retour à cli/ken](index.md) · [voir log](../../log.md)
