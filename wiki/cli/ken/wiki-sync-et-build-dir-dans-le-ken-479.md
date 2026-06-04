---
id: 479
title: "WIKI / sync et build / DIR dans le .ken"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-27T13:47:30
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/ken
section_title: "ken task CLI"
---

# #479 — WIKI / sync et build / DIR dans le .ken

Permettre de configurer dans le `.ken` les répertoires d'entrée/sortie utilisés par `ken wiki sync` et `ken wiki build`, pour éviter de répéter `--out` / `--in` sur chaque invocation.

---

## Résolution

### Modifications

- `src/dashboard/ken.py` :
  - Nouvelles constantes `DEFAULT_WIKI_DIR = "wiki"` et
    `DEFAULT_WIKI_HTML_DIR = "wiki-html"`.
  - `KenConfig` gagne deux champs : `wiki_dir` et `wiki_html_dir`.
  - `_load_config` résout chacun selon la chaîne identique aux
    autres clés : `KEN_WIKI_DIR` env > `wiki_dir=` .ken > défaut
    (idem pour `wiki_html_dir`).
  - `ken wiki sync --out` passe à `default=None` et résout à
    `out or cfg.wiki_dir`.
  - `ken wiki build --in` / `--out` même pattern (input = `cfg.wiki_dir`,
    output = `cfg.wiki_html_dir`).
  - Le couplage est délibéré : l'output de `sync` est l'input de
    `build` → une seule clé `wiki_dir` pilote les deux.
- `tests/unit/test_ken.py` :
  - `TestLoadConfig` : 3 tests (défauts, lecture .ken, env > .ken)
    pour `wiki_dir` + `wiki_html_dir`.
  - `TestCliMutations` : 3 tests d'intégration (sync écrit dans le
    dir .ken, build lit + écrit aux deux dirs .ken, flag CLI override).

### Comportements obtenus

- `.ken` avec `wiki_dir=doc/wiki/md` et `wiki_html_dir=doc/wiki/html` →
  `ken wiki sync` puis `ken wiki build` (sans args) tournent dans les
  bons dossiers.
- Le flag CLI `--out` / `--in` reste prioritaire quand explicitement
  passé.
- Suit le même pattern que `architecture=` (#473) et `sync_dir=` —
  pas de surprise pour l'opérateur.

### Garde-fous

- `pdm run check` : OK (480 tests, lint, typecheck, format, refurb).
- 6 nouveaux tests dans `test_ken.py`.
---

[← retour à cli/ken](index.md) · [voir log](../../log/2026-05-27.md)
