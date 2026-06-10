---
id: 743
title: "WIKI / Build / Footer version + date de génération"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-04T17:24:12
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #743 — WIKI / Build / Footer version + date de génération

## Demande

Ajouter en bas de chaque page du wiki HTML (sortie de `ken wiki build`) un footer affichant :

1. **La version de `ken`** (= kenboard) qui a généré le wiki.
2. **La date/heure de génération** (timestamp du build).

But : un lecteur qui ouvre une page sait immédiatement à quelle release le contenu correspond, et depuis quand il n'a pas été régénéré. Utile pour détecter des wikis stale.

## Pistes d'implémentation

### Source de la version

`dashboard.__version__` est déjà accessible via le helper `_version()` dans `src/dashboard/ken.py:43` (utilisé pour le `User-Agent` HTTP). Réutiliser ce helper.

### Source de la date

Deux options :

1. **Date du `ken wiki build`** (heure de génération HTML). `datetime.now(UTC).isoformat(timespec='seconds')`. Bouge à chaque build, donc indique "quand cette copie HTML a été produite".
2. **Date du `ken wiki sync`** (heure d'export depuis la BDD). Plus représentatif du "contenu", mais nécessite de propager l'info via un fichier (`wiki/.synced_at`) que build lit.

Recommandation : option 1 (build time). Simple, suffisant, et le build est en général lancé juste après le sync dans la pipeline (`ken wiki sync && ken wiki build`).

### Où l'afficher

`_wrap_html` dans `src/dashboard/ken.py:1750` est le seul point qui wrap le HTML autour du main + sidebar — c'est l'endroit naturel pour injecter un `<footer>` après `</main>` ou dans le main.

Format suggéré (petit, discret, en bas du main) :

```html
<footer class="wiki-footer">
  Généré le 2026-06-04 14:32:10 UTC par kenboard 0.1.131
</footer>
```

CSS à ajouter dans `_WIKI_HTML_CSS` :

```css
.wiki-footer{margin-top:32px;padding-top:12px;border-top:1px solid #d0d7de;
  font-size:11px;color:#57606a;text-align:right}
```

### Cohérence avec les pages détail (`.fullscreen-card`)

`_render_task_detail` (`src/dashboard/ken.py:1806`) produit déjà sa propre nav footer (`wiki-nav` avec "← retour" et "voir log"). Le footer global doit cohabiter avec sans dupliquer — sans doute le mettre **après** la `.fullscreen-card` (hors de la card), dans le `<main>` du wrap.

## Tests à ajouter

- `tests/unit/test_ken.py` :
  - `_wrap_html` inclut la version courante (`dashboard.__version__`) dans le HTML rendu.
  - `_wrap_html` inclut une date au format ISO (regex `\d{4}-\d{2}-\d{2}`).
  - Toutes les pages du build (root, section, task detail, log) ont le footer — vérifier sur un sous-ensemble représentatif.
  - Mock `datetime.now` pour des tests déterministes (ou capturer le timestamp puis vérifier qu'il est entre before/after).

## Suite (hors scope)

- Optionnel : afficher le hash git court (`git rev-parse --short HEAD`) en plus de la version PyPI, pour identifier précisément le commit qui a produit le build. Nécessite que `git` soit dans le PATH au moment du build — pas garanti en CI/PyPI.

---

## Résolution

### Décisions de design

- **Source de la version** : helper `_version()` existant (`src/dashboard/ken.py:44`) qui lit `dashboard.__version__`. Pas de fork.
- **Source de la date** : `datetime.now(timezone.utc)` au moment du build (option 1 retenue, comme recommandé). Calculé **une fois** au début de `_build_html_plan` puis injecté dans chaque page, donc toutes les pages d'un même build portent le même timestamp.
- **Placement** : à l'intérieur de `<main>`, après le `body_html`. Reste dans la colonne de contenu, sous la sidebar grid, comme un footer naturel. Cohabite avec `.wiki-nav` des pages détail (les deux blocs s'empilent sans collision).
- **Format affiché** : `Généré le 2026-06-04 14:32:10 UTC par kenboard 0.1.131` — date lisible humain + version PyPI.

### Modifications

- `src/dashboard/ken.py` :
  - Import : `from datetime import datetime, timezone`.
  - Nouveau helper `_format_footer(version, generated_at)` qui retourne le `<footer class="wiki-footer">...\</footer>`.
  - `_wrap_html` : nouveau param `footer_html: str = ""` (optionnel pour rétro-compat). Le footer est inséré **à l'intérieur** de `<main>` après le body.
  - `_build_html_plan` : calcule `footer_html = _format_footer(_version(), datetime.now(timezone.utc))` une fois avant la boucle, passe à chaque `_wrap_html`.
  - `_WIKI_HTML_CSS` : ajout de la règle `.wiki-footer` (margin-top, padding-top, border-top discret, font-size:11px, color:#57606a, text-align:right).

- `tests/unit/test_ken.py` :
  - Nouvelle classe `TestBuildFooter` (3 tests) :
    - `_format_footer` produit la version + date attendues avec un `datetime` fixé.
    - `_wrap_html` insère le footer **à l'intérieur** de `<main>` (pas en dehors).
    - `_wrap_html` est rétro-compatible quand `footer_html` est omis.
  - `test_wiki_build_renders_html_tree` étendu : vérifie que le footer est présent sur la section index, le root `index.html`, et le `log/index.html` (3 types de pages distincts).

### Comportements obtenus

Sur le wiki réel après `ken wiki build` :

```html
<!-- wiki-html/index.html -->
<footer class="wiki-footer">Généré le 2026-06-04 15:23:26 UTC par kenboard 0.1.131</footer>

<!-- wiki-html/backend/api/index.html -->
<footer class="wiki-footer">Généré le 2026-06-04 15:23:26 UTC par kenboard 0.1.131</footer>

<!-- wiki-html/log/2026-06-04.html -->
<footer class="wiki-footer">Généré le 2026-06-04 15:23:26 UTC par kenboard 0.1.131</footer>
```

Timestamp identique sur toutes les pages (calculé une seule fois par invocation de `_build_html_plan`). Style discret : 11px, gris (#57606a), aligné à droite, séparé du contenu par un border-top + padding.

### Garde-fous

- `pytest tests/unit/test_ken.py tests/unit/test_wiki.py` : 153 tests passés (3 nouveaux `TestBuildFooter` + extension du test e2e `test_wiki_build_renders_html_tree`).
- `ruff check` : All checks passed.
- `mypy src/dashboard/ken.py` : no issues.
- `interrogate` : 100.0% docstring coverage.
- `ken wiki build` sur le wiki de prod : 292 fichiers générés, footer vérifié manuellement sur 3 types de pages (root, section L2, journal du jour).
---

[← retour à wiki](index.md) · [voir log](../log/2026-06-04.md)
