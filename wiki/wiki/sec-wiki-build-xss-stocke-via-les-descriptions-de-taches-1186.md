---
id: 1186
title: "SEC / Wiki build : XSS stocké via les descriptions de tâches"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-15T19:37:04
classified_at: 2026-11-15T18:45:00
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #1186 — SEC / Wiki build : XSS stocké via les descriptions de tâches

**TL;DR** — `ken wiki build` copiait tel quel le HTML des descriptions de tâches (`<script>`, `onerror`, `javascript:`) dans le wiki statique → la sortie passe par une liste blanche et les métadonnées sont échappées.

---

Issu de l'audit #1183 (H3). ken wiki build rend le markdown sans assainissement (ken/wiki_detail.py) : <script>, onerror et javascript: passent tels quels dans wiki-html, servi sur la même origine que Semaphore/Nagios.

---

## Résolution

### Modifications

- `src/dashboard/ken/wiki_sanitize.py` (nouveau) — `sanitize_html()` : re-sérialisation depuis le flux de tokens de `html.parser` ; balises et attributs en liste blanche, URL limitées à `http`/`https`/`mailto`/relatif, `style` réduit au `text-align` des tableaux, contenu de `script`/`style`/`svg`/`iframe`… supprimé, éléments non fermés refermés. Stdlib uniquement (pas de dépendance compilée).
- `src/dashboard/ken/wiki_detail.py` — `_render_markdown()` assainit sa sortie ; `who`, `title`, `status`, `classified_by`, `section`, `id` échappés ; le jour du journal est validé (`AAAA-MM-JJ` sinon `unknown`).
- `src/dashboard/ken/wiki_layout.py` — `<title>` échappé.
- `doc/ken-cli.md` — mention de l'assainissement.
- `tests/unit/test_wiki.py` — `TestWikiSanitizer` (16 charges XSS + préservation du markdown) et `TestWikiDetailEscaping`.

### Comportements obtenus

- Aucune des charges testées ne laisse de script, de gestionnaire `on*` ni d'URL active dans la page.
- Le rendu markdown ordinaire est préservé (titres, liens, blocs de code, tableaux alignés).
- Une balise inconnue (`<id>`, `<cat_id>`) est affichée en texte au lieu d'être avalée par le navigateur.
- Reconstruction du wiki réel dans un répertoire temporaire : 360 pages, différences limitées à `<hr />` → `<hr>`, `&quot;` → `"`, placeholders rendus visibles, balises orphelines refermées. Aucune perte de contenu.

### Reste à faire hors dépôt

- `wiki-html/` n'a pas été régénéré (publication manuelle) : le prochain `ken wiki build` produira ce diff une fois.
- Durcir la CSP de `/wiki/` sur `www.monitor.2113.ch` (`script-src 'self'` suffit : la recherche charge `search.js` et `search-index.js` en fichiers externes).

### Garde-fous

- `pdm run check` : exit 0 — isort, black, docformatter, mypy strict, flake8, interrogate 100 %, refurb, ruff, vulture, biome, tsc, vitest, build Vite, 817 tests hors e2e, gate métriques PASS.
- `pdm run test-cov` (e2e inclus) : 867 passés, 2 échecs **pré-existants** et sans rapport (`TestLoginRateLimit`, dépendance d'ordre avec les e2e, reproduits sur HEAD intact — ticket #1196). Couverture 96,15 %, `pdm run metrics-gate` PASS.
- Non commité : les modifications sont dans l'arbre de travail, en attente de revue.
---

[← retour à wiki](index.md) · [voir log](../log/2026-11-15.md)
