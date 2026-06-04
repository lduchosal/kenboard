---
id: 741
title: "wiki / Liens HTML cassés en navigation file:// (Home off-by-one)"
status: review
who: "Claude"
due_date: 
classified_at: 2026-06-04T16:28:09
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #741 — wiki / Liens HTML cassés en navigation file:// (Home off-by-one)

## Symptôme

Quand on ouvre `wiki-html/` directement depuis le file system (sans serveur web), les liens du menu de gauche cassent dès qu'on est à `docs/index.html` ou plus profond — on tombe sur la page courante au lieu de remonter à la racine. À une profondeur ≥ 2 (`backend/api/…`) on n'atteint jamais la home.

## Cause précise

`_format_sidebar_nav` dans `src/dashboard/ken.py:1707` calcule le lien "Home" ainsi (ligne 1714) :

```python
root_href = (
    "../" * current_path.count("/") + "index.html" if current_path else "index.html"
)
```

Le calcul est **off-by-one**. `current_path` est un chemin sans extension (ex. `docs`, `backend/api`, `wiki/wiki`) — son `count("/")` vaut `depth - 1` côté file system. Pour remonter à la racine il faut donc `"../" * (count + 1)`, pas `"../" * count`.

`_relative_href` (ligne 1731) fait le bon calcul (`count + 1`), d'où l'inconsistance.

## Résultats observés (`wiki-html/`)

| Page | Href "Home" généré | Résolution FS | Attendu |
|---|---|---|---|
| `docs/index.html` | `index.html` | `docs/index.html` ❌ (lui-même) | `../index.html` |
| `docs/doc-readme-…-256.html` | `index.html` | `docs/index.html` ❌ | `../index.html` |
| `backend/api/index.html` | `../index.html` | `backend/index.html` ❌ | `../../index.html` |
| `backend/api/quality-…-80.html` | `../index.html` | `backend/index.html` ❌ | `../../index.html` |
| `cli/ken/index.html` | `../index.html` | `cli/index.html` ❌ | `../../index.html` |
| `index.html` (racine) | `index.html` | `index.html` ✅ | OK |
| `log.html` (racine) | `index.html` | `index.html` ✅ | OK (par coïncidence — `current_path="log.md"`, count=0) |

Les liens inter-sections du sidebar (`../backend/index.html`, `../../frontend/api/index.html`) sont **corrects** car ils passent par `_relative_href` qui applique bien `count + 1`. Seul le lien "Home" est cassé.

## Fix proposé

Aligner le calcul de `root_href` sur `_relative_href`. Idéalement : réutiliser `_relative_href(current_path, "index.html")` directement, ce qui élimine la duplication de logique. Attention au cas spécial `current_path=""` (page racine) et `current_path="log.md"` (fichier racine sans dossier) :

- `_relative_href("", "index.html")` retourne `"index.html"` ✅
- `_relative_href("log.md", "index.html")` retournerait `"../index.html"` ❌ (le fichier `log.html` est à la racine)

Donc soit corriger `_relative_href` pour distinguer "page dans un dossier" vs "fichier à plat" (drapeau ou détection `.md`/`.html` dans le chemin), soit gérer `log.md` à part dans le sidebar. Le plus propre : faire transiter `current_path` toujours comme **chemin du fichier MD avec extension** (`docs/index.md`, `backend/api/foo.md`, `log.md`) et calculer la profondeur uniquement via `count("/")` — supprime l'ambiguïté.

---

## Résolution

### Approche

Choix de l'option "chemin du fichier MD avec extension" mentionnée dans les pistes : on dissocie complètement les deux responsabilités qui étaient confondues dans `current_path`.

- **`current_file`** : chemin réel du fichier MD relatif à la racine du wiki (`index.md`, `log.md`, `docs/index.md`, `backend/api/foo.md`). Sert uniquement à calculer la profondeur via `count("/")`, sans ambiguïté.
- **`current_section`** : chemin de section pour le highlight `class="current"` (inchangé sémantiquement, juste renommé pour clarté).

Effet de bord positif : la fonction `_relative_href` (3 lignes utiles) devient inutile et est supprimée — toute la logique de `../` est centralisée dans `_format_sidebar_nav`. Plus de duplication, plus d'inconsistance possible.

### Modifications

- `src/dashboard/ken.py` :
  - `_format_sidebar_nav` (ligne ~1716) : nouvelle signature `(sections, current_file, current_section)`. Calcule `up = "../" * current_file.count("/")` une fois et l'applique uniformément à Home et à chaque lien de section. Docstring étoffée pour expliquer le rôle de chaque param et référencer #741.
  - `_relative_href` : supprimée (plus de caller).
  - `_build_html_plan` (ligne ~1795) : passe `str(rel)` en `current_file` en plus du `section_key` existant.

- `tests/unit/test_ken.py` :
  - Ajout de `import re` (utilisé par les helpers de la nouvelle suite).
  - Nouvelle classe `TestSidebarNav` après `TestSlugify` : 7 tests couvrant racine, fichier racine (log.md), section L1 (index + task page), section L2 (index + task page), et l'absence de Home quand `current_section is None`.

### Comportements obtenus

Vérifié par `grep` sur `wiki-html/` après `ken wiki build` :

| Page | Home href avant | Home href après |
|---|---|---|
| `docs/index.html` | `index.html` ❌ | `../index.html` ✅ |
| `backend/api/index.html` | `../index.html` ❌ | `../../index.html` ✅ |
| `cli/ken/index.html` | `../index.html` ❌ | `../../index.html` ✅ |
| `backend/api/<task>.html` | `../index.html` ❌ | `../../index.html` ✅ |
| `index.html` (racine) | `index.html` ✅ | `index.html` ✅ (préservé) |

Les liens inter-sections (déjà corrects via `_relative_href`) restent identiques — l'unification de la logique n'a pas régressé.

### Garde-fous

- `pytest tests/unit/test_ken.py tests/unit/test_wiki.py` : 140 tests passés (dont 7 nouveaux `TestSidebarNav`).
- `ruff check src/dashboard/ken.py tests/unit/test_ken.py` : All checks passed.
- `mypy src/dashboard/ken.py` : no issues.
- `interrogate` : 100.0% docstring coverage (seuil 95%).
- `ken wiki build` : 280 fichiers générés, Home href vérifié manuellement à plusieurs profondeurs.
---

[← retour à wiki](index.md) · [voir log](../log/2026-06-04.md)
