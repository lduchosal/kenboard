---
id: 128
title: "CLEAN / Nettoyer les anceinnes fonctionnaltiés / kenboard build"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:27
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: cli/kenboard
section_title: "kenboard admin CLI"
---

# #128 — CLEAN / Nettoyer les anceinnes fonctionnaltiés / kenboard build

kenboard build date de la version 0.0.1 qui créait du HTML static, n'est plus utilisé à présent

---

## Résolution

### Constat

La commande `kenboard build` était **déjà cassée** : son implémentation appelait `subprocess.run([sys.executable, "build.py"])`, mais le fichier `build.py` n'existait plus à la racine du projet depuis longtemps. Toute exécution se serait terminée par un `FileNotFoundError`. L'historique : avant que kenboard devienne une app Flask + MySQL, la 0.0.1 était un générateur de site statique qui lisait `data.json` et produisait des `.html` via Jinja. Le générateur `build.py` et son `data.json` ont été supprimés du repo lors d'une refonte antérieure, mais la commande CLI et toute la doc qui la mentionnait ont survécu comme code mort.

### Modifications (suppressions)

- **`src/dashboard/cli.py`** — suppression complète de la commande `@cli.command() def build()` (8 lignes). C'était le point d'entrée vers le `subprocess.run(["python", "build.py"])` cassé.
- **`pyproject.toml`** — suppression du PDM script `build-html = "python build.py"` qui pointait vers le même fichier inexistant.
- **`INSTALL.md`** — suppression de la section `## 9. Generer les pages statiques (optionnel)`. Renumérotation des sections suivantes : 10 → 9 (Reverse proxy Nginx), 11 → 10 (Verification).
- **`CLAUDE.md`** — la phrase "Jinja2 templates ... are shared by Flask and by the static `build.py` generator" devient "Jinja2 templates ... are rendered by Flask". Plus de mention du générateur statique dans les hard rules.
- **`doc/architecture.md`** — suppression complète de la section `## Generation statique vs dynamique` (qui décrivait l'ancien dual-mode templates Jinja partagés entre build.py et Flask, et notait "À terme, data.json disparait" — c'est fait).
- **`doc/structure.md`** — **fichier supprimé entièrement**. Il documentait l'arborescence `build.py / data.json / index.html / cat/*.html` de l'ère 0.0.1, ainsi qu'un usage `python3 build.py`. Aucun lien depuis aucun autre doc/code (vérifié par grep). C'était de la doc orpheline qui contredisait l'architecture actuelle (`doc/architecture.md`).

### Comportements obtenus

- `kenboard --help` ne liste plus `build` (qui était de toute façon cassée).
- `pdm run build-html` n'existe plus (`pdm run` retourne une erreur claire "script not found").
- L'arborescence du projet ne référence plus `build.py`, `data.json`, `index.html` ou `cat/*.html` nulle part — ces fichiers n'existaient déjà plus, mais la doc qui les mentionnait est maintenant nettoyée.
- 252 tests unitaires verts (inchangé : aucun test ne couvrait `build`, ce qui confirme qu'il n'était plus utilisé).
- Aucun changement d'API publique, aucune migration DB, aucune dépendance touchée.

### Garde-fous

- `pdm run check` (composite isort, format, docformatter, typecheck, flake8, interrogate, refurb, lint, vulture, test-quick) → ✅ vert
- Grep final `grep -rn 'kenboard build|build\.py|build-html|data\.json' --include='*.py' --include='*.md' --include='*.toml' --include='*.html' --include='*.sh'` → **0 résultats**, pas de référence résiduelle
- Coverage interrogate **passe à 100%** (la `build()` qui n'était documentée que par une docstring d'une ligne ne tire plus la moyenne)

### Hors scope

- Le `build.py` à la racine n'existait déjà plus — rien à supprimer côté fichiers générateurs.
- Le `screenshots = "python scripts/screenshots.py"` PDM script (utilisé pour générer les captures d'écran du README) est conservé : c'est un outil dev/CI distinct, pas lié au générateur statique mort.
- `README.md` ne mentionne pas `kenboard build` (vérifié) — pas de changement nécessaire.
---

[← retour à cli/kenboard](index.md) · [voir log](../../log/2026-05-24.md)
