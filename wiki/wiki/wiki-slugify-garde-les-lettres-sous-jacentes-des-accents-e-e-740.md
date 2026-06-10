---
id: 740
title: "wiki / Slugify garde les lettres sous-jacentes des accents (é → e)"
status: done
who: "Claude"
due_date: 
classified_at: 2026-06-04T16:17:59
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: wiki
section_title: "Wiki (#376)"
---

# #740 — wiki / Slugify garde les lettres sous-jacentes des accents (é → e)

## Problème

`ken wiki sync` (et indirectement `ken wiki build`) génère des noms de fichiers où les caractères accentués sont remplacés par des dashes, ce qui dégrade la lisibilité et casse l'audit trail :

- `mot-de-passe-oubli-237.md` ("oublié" → "oubli")
- `sec-pentest-authentifi-36.md` ("authentifié" → "authentifi")
- `doc-readme-liens-cass-s-vers-doc-md-256.md` ("cassés" → "cass-s")

## Cause

`_slugify()` dans `src/dashboard/ken.py:1301` utilise `_SLUG_NONWORD_RE = re.compile(r'[^a-z0-9]+')` (ligne 1298) après un simple `.lower()`. Aucune normalisation Unicode → les lettres accentuées tombent dans la classe "non-alphanumérique" et sont remplacées par `-`.

## Souhait

Conserver la lettre sous-jacente en stripant uniquement la diacritique : `é → e`, `ô → o`, `ç → c`, `ü → u`, etc. Un `unicodedata.normalize('NFD', text)` suivi d'un filtre sur `unicodedata.combining(c)` fait le job sans dépendance externe.

Attendu après fix :
- `mot-de-passe-oublie-237.md`
- `sec-pentest-authentifie-36.md`
- `doc-readme-liens-casses-vers-doc-md-256.md`

## Pistes

- Modifier `_slugify()` dans `src/dashboard/ken.py` pour appliquer la normalisation NFD + strip combining avant le `re.sub`.
- Vérifier que `_sanitize_filename()` (ligne 330, utilisé pour `NNNN - Title.md` dans l'ancien sync) n'a pas besoin du même traitement — son regex ne touche pas aux accents, mais cohérence à confirmer.
- Couvrir avec un test unitaire (cas é, ô, ç, ü, à, î, mix).
- Régénérer le wiki et committer le nouveau jeu de fichiers (les anciens noms doivent être renommés, pas dupliqués).

---

## Résolution

### Modifications

- `src/dashboard/ken.py` : import `unicodedata` ajouté dans le bloc stdlib (ligne 17). `_slugify()` (ligne 1301) applique désormais `unicodedata.normalize("NFD", text)` puis filtre les marks combinants (`unicodedata.combining(c)`) avant le `.lower()` et le `re.sub`. Docstring étoffée pour expliquer le "pourquoi NFD + filter combining".
- `tests/unit/test_ken.py` : nouvelle classe `TestSlugify` (placée après `TestSyncHelpers`, avant `TestCliSync`) — 7 tests couvrant cas de base, collapse, trim, fallback untitled, diacritiques isolés (é, ô, ç, ü, à, î, naïve, hôtel, über, ça), titres mixtes représentatifs des bugs réels (#256, #237), et propagation jusqu'à `_task_filename`.

### Comportements obtenus

- `oublié` → `oublie` (au lieu de `oubli`)
- `cassés` → `casses` (au lieu de `cass-s`)
- `authentifié` → `authentifie` (au lieu de `authentifi`)
- `hôtel` → `hotel` (au lieu de `h-tel`)
- `naïve` → `naive`
- `über` → `uber`

Vérifié sur le wiki complet : `ken wiki sync` + `ken wiki build` régénèrent 280 fichiers, et les noms attendus apparaissent (`mot-de-passe-oublie-237.md`, `sec-pentest-authentifie-36.md`, `doc-readme-liens-casses-vers-doc-md-256.md`, etc.). Les anciens noms cassés sont remplacés (pas dupliqués) puisque `_write_html_plan` et `_write_sync_plan` font `shutil.rmtree(base)` avant d'écrire.

`_sanitize_filename()` n'est pas touché : son regex `[\\/:*?"<>|\x00-\x1f]` ne match pas les accents, donc `NNNN - Title.md` (sync legacy) conservait déjà les lettres accentuées telles quelles. Cohérence vérifiée.

### Garde-fous

- `pytest tests/unit/test_ken.py tests/unit/test_wiki.py` : 133 tests passés (dont 7 nouveaux pour `_slugify`).
- `ruff check src/dashboard/ken.py` : All checks passed.
- `mypy src/dashboard/ken.py` : no issues.
- `ken wiki sync` + `ken wiki build` : 280 fichiers générés sans erreur.
---

[← retour à wiki](index.md) · [voir log](../log/2026-06-04.md)
