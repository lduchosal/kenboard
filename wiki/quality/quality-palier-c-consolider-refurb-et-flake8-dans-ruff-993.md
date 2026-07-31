---
id: 993
title: "QUALITY / palier C — consolider refurb et flake8 dans ruff"
status: done
who: "Claude"
due_date: 
updated_at: 
classified_at: 2026-07-26T15:51:48
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #993 — QUALITY / palier C — consolider refurb et flake8 dans ruff

## Contexte

Suite de ken #992 (adoption des 413 règles par défaut de ruff 0.16). Les défauts couvrent désormais une part significative de ce que font des outils séparés du composite `pdm run check` : 17 règles FURB (périmètre de refurb), pycodestyle/pyflakes (périmètre de flake8), et ruff sait appliquer les conventions pydocstyle (périmètre de flake8-docstrings). Objectif : **consolider sans perdre un seul acquis** — moins d'outils dans le gate, couverture égale ou supérieure, exécution plus rapide.

## Ce qu'il faut faire

### 1. refurb → famille FURB complète

- Activer `FURB` (famille complète) dans `extend-select` et corriger/trier les violations.
- **Audit d'écart obligatoire avant retrait** : lancer `refurb src/` et `ruff check --select FURB` côte à côte ; inventorier les checks refurb sans équivalent ruff (les deux outils ne se recouvrent pas à 100 %). Décision explicite par écart : équivalent ruff existant, perte acceptée (documentée), ou refurb conservé.
- Si l'audit est favorable : retirer `refurb` des dev deps, du script pdm et du composite `check`.

### 2. flake8 (+ flake8-docstrings, flake8-docstrings-complete) → ruff D/DOC

- Inventorier ce que flake8 vérifie réellement aujourd'hui (`.flake8` : max-line-length 125, convention google, extend-ignore E203/W503/D203/D205/D212/D415/DCO020/DCO030/DCO031/DCO060) — ne porte que sur `src/`.
- Migration ruff : activer `D` avec `[tool.ruff.lint.pydocstyle] convention = "google"` (la convention désactive déjà D203/D212/D415 & co — vérifier que seuls les ignores encore nécessaires sont reconduits) ; `E501` via `lint.pycodestyle.max-line-length = 125` (le line-length ruff global reste 88 pour le formatter). E203/W503 n'existent pas dans ruff (compatibles formatter par design) — rien à reconduire.
- Les règles DCO (flake8-docstrings-complete) : évaluer la famille `DOC` de ruff (pydoclint, en preview). Si la couverture n'est pas équivalente en stable, **garder flake8-docstrings-complete** et ne retirer que flake8+flake8-docstrings, ou différer tout le point 2 — pas de perte silencieuse.
- Si migration complète : retirer flake8 et ses plugins des dev deps, supprimer `.flake8`, retirer le script pdm et l'étape du composite.

### 3. Après retrait de flake8 : suppressions natives ruff

- Évaluer la syntaxe 0.16 `ruff: ignore[CODE]` avec raison native (+ `--add-ignore`) pour les suppressions argumentées — colle à notre convention « noqa argumentés ». Bloqué tant que flake8 lit les mêmes commentaires `# noqa` (cf. l'incident E402 de #992). Migration des noqa existants optionnelle et mécanique.

### 4. Évaluations optionnelles (décision utilisateur, pas d'action par défaut)

- `interrogate` → règles `D1xx` (undocumented-public-*) : on est à 100 % de couverture docstring, D1 verrouillerait en binaire ce qu'interrogate mesure en % ; mais interrogate génère aussi le badge. À trancher.
- black/isort/docformatter → `ruff format` + famille `I` : consolidation la plus invasive (reformatage massif possible, docformatter pas entièrement couvert). **Hors périmètre de cette tâche** — ouvrir une tâche dédiée si souhaité.

## Garde-fous

- Principe directeur (cf. #992) : plus de qualité, pas moins. Aucune règle active aujourd'hui ne disparaît sans décision explicite documentée dans la résolution.
- Inventaire avant/après des règles effectives (méthode de #992 : `ruff check --show-settings` + diff des listes).
- `pdm run check` complet vert, metrics-gate PASS avec données de couverture (`pdm run test-ci` puis `pdm run metrics-gate`).
- Mettre à jour `doc/code-quality.md` et le CLAUDE.md du repo (liste des gates) si des outils sortent du composite.
- Pas de borne supérieure sur les versions d'outils (principe ratchet).

---

## Résolution

Commit `e1aedfa` (4 fichiers, +46/−14). Décisions prises volet par volet, audits à l'appui.

### Volet 1 — refurb : CONSERVÉ (audit défavorable au retrait)

- Inventaire : refurb 2.3.1 = **93 checks** ; famille FURB de ruff 0.16 = 36 règles dont **22 stables** seulement. → 57 checks refurb sans aucun équivalent ruff, 14 de plus seulement en preview.
- Décision : retirer refurb serait une perte nette de couverture — contraire au principe directeur. **refurb reste au composite.**
- Bonus verrouillé : `FURB` (famille complète) ajouté à `extend-select` — +5 règles stables au-delà des 18 des défauts, et les preview s'activeront d'elles-mêmes en se stabilisant. 0 violation.

### Volet 2 — flake8 : réduit aux règles DCO, le reste migré vers ruff

- `extend-select` : + `D` (pydocstyle complet, `[tool.ruff.lint.pydocstyle] convention = "google"`), + `E501` (125 via `[tool.ruff.lint.pycodestyle] max-line-length`, héritage .flake8), + `W` (pycodestyle warnings).
- Migration D quasi indolore : **une seule violation** dans src/ (D205, wiki_build.py — corrigée) ; les 488 autres étaient dans tests/ → `D` ajouté aux per-file-ignores `tests/**` (aligné interrogate qui exclut tests/ et mypy qui exempte les tests). Les ignores historiques D203/D212/D415 sont couverts par la convention google native.
- DCO (flake8-docstrings-complete) : la famille `DOC` de ruff (pydoclint) est **100 % preview (7/7)** → pas de migration stable possible. `.flake8` réécrit : `select = DCO` + les 4 ignores existants (DCO020/030/031/060). Sanity-check effectué : DCO024 mord toujours sur un arg fantôme documenté.
- `flake8-docstrings` (plugin pydocstyle) retiré des dev deps — remplacé par le `D` natif ruff. flake8 revérifié fonctionnel sans lui.
- `external = ["DCO"]` dans la config ruff : protège les futurs `# noqa: DCO...` du nettoyage RUF100 (leçon de l'incident E402 de #992).
- Marqueur de sortie : commentaires dans `.flake8` et `pyproject.toml` — retirer flake8 entièrement quand `DOC` sort de preview.

### Volet 3 — `ruff: ignore[reason]` : DIFFÉRÉ

Tant que flake8 (même scopé DCO) lit les commentaires `# noqa`, on garde une seule syntaxe de suppression. À réévaluer au retrait complet de flake8 (= stabilisation de DOC).

### Volet 4 — évaluations optionnelles : NON TRAITÉES (décision utilisateur)

- interrogate → D1xx : les règles D1 sont actives dans src/ depuis ce commit (0 violation, on est à 100 %) — interrogate devient partiellement redondant mais génère le badge. À trancher séparément.
- black/isort/docformatter → `ruff format` : hors périmètre, tâche dédiée si souhaité.

### Modifications

- `pyproject.toml` — extend-select + `D`/`E501`/`W`/`FURB` ; sections `[tool.ruff.lint.pydocstyle]` (google) et `[tool.ruff.lint.pycodestyle]` (125) ; `external = ["DCO"]` ; `D` dans per-file-ignores tests ; dev deps sans flake8-docstrings ; commentaires de décision.
- `.flake8` — scopé `select = DCO`, ignores DCO reconduits, en-tête expliquant le périmètre et la condition de sortie.
- `CLAUDE.md` — section Code-quality gates réécrite (qui vérifie quoi).
- `src/dashboard/ken/wiki_build.py` — fix D205 (résumé de docstring sur une ligne).
- `pdm.lock` (gitignoré) — re-généré sans flake8-docstrings, venv purgé.

### Comportements obtenus

- ruff est le vérificateur unique du style : pycodestyle (E/W/E501@125), pyflakes, pydocstyle google — sur src/ **et** tests/ (flake8 ne voyait que src/). flake8 ne fait plus qu'une chose : la complétude des docstrings (DCO), en attendant ruff DOC stable.
- Couverture en hausse nette : famille D active sur src/ (48 règles), E501/W désormais aussi sur tests/, +5 FURB stables — zéro règle perdue, refurb intact.

### Garde-fous

- `pdm run check` complet vert : 622 tests, ruff_debt 0, mypy 0, interrogate 100 %, refurb 0, vulture 0, gates JS verts, **metrics-gate palier 5 PASS** (couverture 94.06 %, min fichier 76.92).
- Sanity-check DCO documenté ci-dessus (règle non-ignorée vérifiée mordante après le rescope).
- Inventaires avant/après faits à la méthode #992 (`ruff rule --all` + `--show-settings`).
---

[← retour à quality](index.md) · [voir log](../log/2026-07-26.md)
