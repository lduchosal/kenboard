---
id: 1178
title: "WIKI / search / index + recherche full text du wiki statique"
status: done
who: "Claude"
due_date: 
updated_at: 2026-11-13T09:35:50
classified_at: 2026-11-13T09:05:09
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #1178 — WIKI / search / index + recherche full text du wiki statique

**TL;DR** — Le wiki statique n'avait ni recherche ni index. `ken wiki build` émet maintenant un index plat (`search-index.js`), un script vanilla (`search.js`) et une page `search.html` ; un champ de recherche figure en haut de la fenêtre principale de chaque page. Pas de SQLite, pas de dépendance.

## Demande

Est-il possible d'ajouter un index et une recherche full text au wiki static du kenboard ? Je pensais : base de données SQLite populée avec les données du wiki, et poussée avec le wiki. Une interface web et une recherche client full texte (js+sqlite) ? Autre proposition ; j'aime que ça reste simple.

## Constat (2026-11-13)

- Wiki actuel : 352 pages, 1.6 Mo de markdown, 4.1 Mo de HTML. `ken wiki build` (`src/dashboard/ken/wiki_build.py`) produit du HTML autonome, sans aucun JS.
- SQLite côté client = sql.js (WASM ~650 Ko + loader), dont le build par défaut n'embarque pas FTS5 (à vérifier — sinon build custom), plus un `.db` binaire committé à chaque sync : diff illisible et churn, à rebours de #999/#1014.

## Proposition : index JS plat + recherche vanilla

1. `ken wiki build` émet en plus `search-index.js` à la racine de `wiki-html/` : `window.KEN_WIKI_INDEX = [{id, title, section, path, text}, …]` (texte = markdown débarrassé du balisage, tri déterministe → diff texte stable).
   - `.js` chargé par `<script>` plutôt que `.json` + `fetch` : fonctionne aussi en `file://`.
2. Champ de recherche dans la sidebar (`wiki_layout.py`) + `search.js` (~60 lignes vanilla, sans dépendance) : chargement paresseux de l'index au premier focus, découpage en mots, ET logique, insensible à la casse et aux accents, `#123` → saut direct à la tâche, titre pondéré au-dessus du corps, extrait avec surlignage.
3. Page `search.html` : requête vide = index complet des tâches (id, titre, section) → couvre le besoin « index ».

Ordres de grandeur : index ~1.2 Mo brut, ~350 Ko gzip ; scan linéaire de 352 documents < 10 ms. Tient sans changement jusqu'à quelques milliers de pages ; au-delà, passer à un index inversé (ou pagefind) sans toucher l'UI.

## Hors périmètre

- SQLite/WASM, serveur de recherche, lib tierce (lunr, minisearch).

## Résolution

Décision utilisateur (2026-11-13) : proposition acceptée, avec le champ de recherche dans la fenêtre principale (`<main>`) et non dans la sidebar.

### Modifications

- `src/dashboard/ken/wiki_search.py` (nouveau) — `_plain_text` (markdown → texte, NFC), `_search_entry`, `_format_search_index_js` (une entrée par ligne, triée par id), `_search_files` (page + script + index).
- `src/dashboard/ken/wiki_search_js.py` (nouveau) — le script client, donnée pure comme `wiki_css`.
- `src/dashboard/ken/wiki_layout.py` — `_format_search_form` ; `_wrap_html` reçoit `search_href` et place le formulaire en tête de `<main>`.
- `src/dashboard/ken/wiki_build.py` — collecte les entrées des pages tâche, ajoute les trois fichiers au plan.
- `src/dashboard/ken/wiki_css.py` — styles du champ et des résultats.
- `tests/unit/test_wiki_search.py` (nouveau, 10 tests) ; `README.md`, `doc/ken-cli.md`.

### Comportements obtenus

- Chaque page porte un formulaire GET vers `search.html?q=…` (href relatif à la profondeur) : aucun script sur les pages normales, seul `search.html` charge l'index.
- Recherche à la frappe : mots combinés en ET, insensible à la casse et aux accents, titre pondéré au-dessus du corps, `#123` ou `123` met la tâche exacte en tête, extrait surligné, 100 premiers résultats affichés.
- Requête vide : liste de toutes les tâches, la plus récente en premier (l'« index »).
- Seules les pages tâche sont indexées (les index de section et le journal ne sont que des listes de liens).
- Résultats construits en `textContent`, jamais `innerHTML`.
- Mesuré sur le wiki du dépôt (306 tâches) : `search-index.js` 625 Ko, 214 Ko gzippé ; `search.js` 4 Ko.
- Vérifié dans Chromium headless en `file://` : soumission depuis une page profonde, requêtes `oidc session`, `#856`, `1014`, `securite` (→ « sécurité »), `wiki_build`, requête vide, navigation vers un résultat ; aucune erreur console.

### Garde-fous

- isort, docformatter, black, mypy, flake8, interrogate, refurb, ruff, vulture, metrics-gate : verts.
- `pdm run test-quick` : 713 passés. `pdm run test-cov` : 763 passés, 2 échecs dans `tests/unit/test_auth_user.py::TestLoginRateLimit` (200 au lieu de 429), hors périmètre wiki et absents de `test-quick` ; non isolés par `git stash` car l'arbre est partagé avec la session qui traite #1177. Couverture 95,33 %, `wiki_search*.py` et `wiki_layout.py` à 100 %.
- Gate JS non lancé : aucun fichier sous `static/js/` touché, et `js-build` aurait réécrit le `dist/app.js` en cours de modification pour #1177.
- Non fait : rien n'est committé ; `wiki/` et `wiki-html/` du dépôt ne sont pas régénérés (build de vérification fait dans un dossier temporaire).
---

[← retour à wiki](index.md) · [voir log](../log/2026-11-13.md)
