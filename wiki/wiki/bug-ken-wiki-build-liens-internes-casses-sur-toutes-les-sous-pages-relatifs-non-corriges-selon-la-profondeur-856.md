---
id: 856
title: "BUG — `ken wiki build` : liens internes cassés sur toutes les sous-pages (relatifs non corrigés selon la profondeur)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-16T16:19:58
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #856 — BUG — `ken wiki build` : liens internes cassés sur toutes les sous-pages (relatifs non corrigés selon la profondeur)

# BUG — `ken wiki build` : liens internes cassés sur toutes les sous-pages (relatifs non corrigés selon la profondeur)

## Résumé
`ken wiki build` génère, dans **chaque** page HTML, exactement le même jeu de liens internes, écrits **relatifs à la racine du wiki** (`href="functional/index.html"`, `href="index.html"`, `href="log/2026-06-12.html"`…), **sans tenir compte de la profondeur de la page courante**.

Résultat : les liens ne fonctionnent que depuis la page racine `index.html`. Sur **toute sous-page**, la navigation latérale (sidebar) et les liens de contenu pointent vers des chemins inexistants → toute la navigation est cassée dès qu'on quitte l'accueil.

- **Composant** : `ken wiki build`
- **Version** : kenboard 0.2.1 (vu dans le footer généré : « Généré le 2026-06-12 13:30:39 UTC par kenboard 0.2.1 »)
- **Sévérité** : haute — le wiki rendu est inutilisable en navigation au-delà de la page d'accueil.
- **Indépendant du mode de service** : casse identique en `file://`, servi à la racine `/`, ou sous un sous-chemin `/wiki/` (les liens étant relatifs au document, pas à la racine).

## Reproduction
1. Avoir un arbre wiki avec des sections imbriquées (ex. `functional/base/`, `clients/cfr/`, `log/<date>`).
2. `ken wiki build --in <wiki_md> --out <wiki_html>`
3. Ouvrir `wiki-html/index.html` → les liens marchent.
4. Cliquer sur n'importe quelle section, p.ex. `functional/base/index.html`, puis cliquer un lien de la sidebar → 404 / page introuvable.

## Comportement observé
Les liens émis sont **identiques** sur des pages de profondeurs différentes. Exemple réel (tronqué) :

`index.html` (racine, profondeur 0) :
```html
<a href="index.html" class="current">Home</a>
<a href="functional/index.html">Hostgroups fonctionnels</a>
<a href="functional/base/index.html">BASE</a>
<a href="log/2026-06-12.html">2026-06-12</a>
```

`functional/base/index.html` (profondeur 2) — **mêmes liens, donc faux** :
```html
<a href="index.html">Home</a>                  <!-- résout vers functional/base/index.html (la page elle-même) -->
<a href="functional/index.html">...</a>        <!-- résout vers functional/base/functional/index.html → 404 -->
<a href="functional/base/index.html">BASE</a>  <!-- résout vers functional/base/functional/base/index.html → 404 -->
```

Résolution navigateur (base = répertoire du document `functional/base/`) :
| Lien émis | Résolu depuis `functional/base/index.html` | Attendu |
|---|---|---|
| `index.html` | `functional/base/index.html` (soi-même) | `../../index.html` |
| `functional/index.html` | `functional/base/functional/index.html` ❌ | `../index.html` |
| `functional/freebsd/index.html` | `functional/base/functional/freebsd/index.html` ❌ | `../freebsd/index.html` |
| `log/2026-06-12.html` | `functional/base/log/2026-06-12.html` ❌ | `../../log/2026-06-12.html` |

## Comportement attendu
Tout lien interne d'une page donnée doit pointer vers le bon fichier **quel que soit l'emplacement de la page**. Les liens doivent être calculés **relativement au répertoire de la page courante**.

Depuis `functional/base/index.html`, on attend :
- Home → `../../index.html`
- `functional/index.html` → `../index.html`
- section sœur `functional/freebsd/index.html` → `../freebsd/index.html`
- `log/2026-06-12.html` → `../../log/2026-06-12.html`

## Cause probable
Le rendu utilise vraisemblablement un gabarit de sidebar/navigation **commun et pré-calculé une seule fois** (chemins depuis la racine du wiki), réinjecté tel quel dans chaque page, sans recalcul du chemin relatif en fonction de la profondeur de la page en cours d'écriture.

## Correctif proposé (par ordre de préférence)

### 1. Liens relatifs corrigés selon la profondeur (recommandé — indépendant du point de montage)
Lors du rendu d'une page de chemin `page_path` (relatif à la racine du wiki), calculer chaque lien comme le chemin relatif de la cible par rapport au **répertoire** de la page :
```python
import os, posixpath
def rel_link(target_path, page_path):
    # target_path, page_path : relatifs à la racine du wiki, séparateur '/'
    base_dir = posixpath.dirname(page_path)
    return posixpath.relpath(target_path, start=base_dir or ".")
```
Avantage : le wiki fonctionne en `file://`, à la racine d'un domaine, et sous n'importe quel sous-chemin (`/wiki/`) sans configuration.

### 2. Balise `<base>` par page
Injecter dans `<head>` un `<base href="<préfixe-vers-racine>/">` où le préfixe est le chemin relatif remontant à la racine du wiki (`../../` pour une page de profondeur 2), et conserver les liens « relatifs à la racine » actuels. Plus simple, mais `<base>` affecte aussi les ancres `#fragment` et les URLs relatives de tout le document.

### 3. Préfixe absolu configurable
Ajouter `--base-url` / `base_url=` dans `.ken` et émettre des liens absolus (`href="/wiki/functional/index.html"`). Fonctionne mais fige le point de montage et reste moins portable que (1).

## Critères d'acceptation
- Sur un arbre de test contenant au moins une page de profondeur ≥ 2, **tout** lien interne de **chaque** page résolu via le navigateur pointe vers un fichier existant.
- Test unitaire : pour une page `functional/base/index.html`, le lien « Home » vaut `../../index.html` et le lien vers `functional/index.html` vaut `../index.html`.
- Le rendu reste fonctionnel ouvert en `file://`, servi à `/`, et servi sous un sous-chemin arbitraire.

## Contexte de déploiement (info)
Le wiki est servi en HTML statique sur `arc-srv-monitor-02` sous `https://monitor.arcantel.local/wiki/` (gate vouch), depuis `svn:.../arcantelmonitor/trunk/wiki-html` régénéré par `angel publish` (`ken wiki sync` + `ken wiki build`). Un contournement nginx (`sub_filter` injectant `<base href="/wiki/">`, module `http_sub` disponible sur l'hôte) est possible côté service, mais le correctif pérenne — option (1) — appartient à `ken wiki build`.

---

## Résolution

**Cause racine confirmée** : le bug est dépendant de l'OS de build. `_build_html_plan` passait `str(rel)` (chemin de la page relatif à la racine wiki) à `_format_sidebar_nav`, qui calculait la profondeur via `current_file.count("/")`. Sur **Windows**, `str(WindowsPath("functional/base/index.md"))` vaut `"functional\\base\\index.md"` → `count("/") == 0` → préfixe `up = ""` → **tous** les liens émis relatifs à la racine, sans aucun `../`, exactement le symptôme rapporté (`href="functional/index.html"` sur une page de profondeur 2). Les hrefs restaient en `/` (les paths viennent de `Section.flatten()`, joints avec `/`), d'où des URLs valides mais non préfixées. Sur POSIX le correctif #741 produisait déjà des liens fonctionnels (forme `up`+racine, ex. `../../functional/index.html`) — le bug ne se manifestait donc qu'au build Windows (kenboard a une CI Windows ; le wiki arcantel est buildé par `angel publish` côté client). Démonstration : `PureWindowsPath(rel)` donne `up=""`, `PurePosixPath(rel)` donne `up="../../"`.

**Correctif** : option (1) du rapport — chaque lien interne est désormais calculé via `posixpath.relpath(cible, repertoire_page)` (forme minimale, canonique, indépendante du point de montage : `file://`, `/`, `/wiki/`). Companion indispensable : `_build_html_plan` dérive tous les chemins via `Path.as_posix()` (jamais `str(Path)`), sinon les backslashes Windows neutralisent aussi `posixpath`.

### Modifications
- `src/dashboard/ken/wiki_build.py` :
  - nouveau helper `_rel_href(target, page_dir)` → `posixpath.relpath(target, page_dir or ".")` ;
  - `_format_sidebar_nav` réécrit pour émettre chaque href (Home, sections, Journal, jours) via `_rel_href` à partir de `posixpath.dirname(current_file)` (remplace le schéma `up = "../" * count("/")` de #741) ;
  - `_build_html_plan` : `rel.as_posix()` pour `current_file`, les `section_key`, et la clé `path` de sortie (au lieu de `str(rel)`/`str(rel.parent)`) ;
  - `import posixpath`.
- `tests/unit/test_ken.py` :
  - `TestSidebarNav` (#741) mis à jour vers la forme relpath minimale (ex. depuis `backend/api/`, lien Backend = `../index.html`, lien propre = `index.html`) ;
  - nouveau `test_acceptance_856_depth2_page_links_resolve` (critères d'acceptation exacts du rapport : Home = `../../index.html`, parent = `../index.html`, sœur = `../freebsd/index.html`) ;
  - nouveau `test_links_are_os_independent_with_posix_input` (contrat as_posix, pas de backslash dans la sortie) ;
  - nouveau `test_wiki_build_deep_page_links_resolve` (build bout-en-bout d'un arbre profondeur 2 : Home = `../../index.html`, tous les `.html` pointent vers un fichier existant, aucun backslash — échoue sur Windows CI si le fix `as_posix` régresse).

### Comportements obtenus
- Navigation latérale (sidebar) et liens Journal fonctionnels depuis **toute** page, quelle que soit la profondeur.
- Forme minimale conforme aux critères : depuis `functional/base/index.html`, Home → `../../index.html`, `functional/index.html` → `../index.html`.
- Portable : ouvert en `file://`, servi à `/`, ou sous `/wiki/` (liens relatifs au document).
- Indépendant de l'OS de build (Windows/POSIX).
- La nav des pages détail (`_render_task_detail`) était déjà correcte et OS-indépendante (opère sur la chaîne `section` jointe en `/`) — laissée inchangée.

### Garde-fous (gates exécutés, tous verts)
- `pytest tests/unit` : **586 passed**.
- Audit bout-en-bout du wiki rebuildé : **313 pages, 11 480 liens internes `.html` vérifiés, 0 cassé** (profondeurs 0/1/2).
- `ruff`, `flake8`, `mypy`, `black --check`, `isort --check`, `docformatter --check`, `interrogate` (100%), `refurb`, `vulture` : **clean** sur les fichiers touchés.
---

[← retour à wiki](index.md) · [voir log](../log/2026-06-16.md)
